"""AuscultaForge — Acquisition Session Recording & Provenance Module.

Consumes SampleBlock streams and commits raw sensor acquisitions to disk with a
JSON metadata sidecar and raw audio WAV. Preserves raw unadulterated sensor data
for reproducible replay, phantom bench verification, and audit trails.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any, Optional
import uuid

import numpy as np
import scipy
from scipy.io import wavfile

from .models import SampleBlock
from .streaming import StreamQualityMonitor
from .experiment import compute_file_sha256, get_git_commit_sha
from .sources import WavSource, RealtimeWavSource


class RecordingSampleRateError(ValueError):
    """Raised when an incoming SampleBlock changes sample rate mid-session."""
    pass


class RecordingStateError(RuntimeError):
    """Raised when invalid state transitions occur on a SessionRecorder."""
    pass


@dataclass(slots=True)
class SessionMetadata:
    """Provenance and acquisition metrics for a recorded PCG session."""
    session_id: str
    started_at_utc: str
    ended_at_utc: str
    source: str
    sample_rate_hz: int
    total_blocks: int
    total_samples: int
    duration_s: float
    first_sequence: Optional[int]
    last_sequence: Optional[int]
    first_timestamp_s: Optional[float]
    last_timestamp_s: Optional[float]
    raw_wav_relpath: str
    raw_wav_sha256: str
    stream_quality: dict[str, Any]
    git_commit_sha: Optional[str]
    environment: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "SessionMetadata":
        return cls.from_dict(json.loads(text))


class SessionRecorder:
    """Records streaming SampleBlock instances to a persistent session directory.

    Structure:
        experiments/sessions/<session_id>/
        ├── raw.wav
        └── session.json
    """

    def __init__(
        self,
        output_dir: str | Path = "experiments/sessions",
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        wav_format: str = "float32",
    ):
        self.output_root = Path(output_dir)
        self.wav_format = str(wav_format).lower()
        if self.wav_format not in ("float32", "int16"):
            raise ValueError(f"Unsupported wav_format: {wav_format}. Must be 'float32' or 'int16'")

        self._active: bool = False
        self._session_id: Optional[str] = session_id
        self._source: str = source or "unknown"
        self._started_at: Optional[datetime] = None
        self._chunks: list[np.ndarray] = []
        self._total_samples: int = 0
        self._total_blocks: int = 0
        self._sample_rate_hz: Optional[int] = None
        self._first_sequence: Optional[int] = None
        self._last_sequence: Optional[int] = None
        self._first_timestamp_s: Optional[float] = None
        self._last_timestamp_s: Optional[float] = None
        self._quality_monitor = StreamQualityMonitor()

    @property
    def is_recording(self) -> bool:
        return self._active

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def sample_rate_hz(self) -> Optional[int]:
        return self._sample_rate_hz

    @property
    def total_samples(self) -> int:
        return self._total_samples

    def start(self, session_id: Optional[str] = None, source: Optional[str] = None) -> str:
        """Start a new recording session."""
        if self._active:
            raise RecordingStateError("A recording session is already active.")

        if session_id:
            self._session_id = str(session_id)
        else:
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_id = uuid.uuid4().hex[:8]
            self._session_id = f"session_{ts_str}_{short_id}"

        if source:
            self._source = str(source)

        self._started_at = datetime.now(timezone.utc)
        self._chunks = []
        self._total_samples = 0
        self._total_blocks = 0
        self._sample_rate_hz = None
        self._first_sequence = None
        self._last_sequence = None
        self._first_timestamp_s = None
        self._last_timestamp_s = None
        self._quality_monitor.reset()
        self._active = True
        return self._session_id

    def record_block(self, block: SampleBlock) -> None:
        """Append a SampleBlock to the active recording.

        Raises:
            RecordingStateError: If no session is currently active.
            RecordingSampleRateError: If block sample rate differs from the session's initial rate.
        """
        if not self._active:
            raise RecordingStateError("Cannot record block: session is not active.")

        # Check sample rate consistency
        if self._sample_rate_hz is None:
            self._sample_rate_hz = block.sample_rate_hz
        elif block.sample_rate_hz != self._sample_rate_hz:
            self._active = False  # Terminate recording on invalid rate change
            raise RecordingSampleRateError(
                f"Sample rate mismatch mid-session: initial session rate was {self._sample_rate_hz} Hz, "
                f"received block with {block.sample_rate_hz} Hz. Recording aborted to prevent corrupt single-rate WAV."
            )

        if self._first_sequence is None:
            self._first_sequence = block.sequence
            self._first_timestamp_s = block.timestamp_s

        self._last_sequence = block.sequence
        self._last_timestamp_s = block.timestamp_s

        # Feed to quality monitor
        self._quality_monitor.inspect_block(block)

        # Store sample chunk
        chunk = np.asarray(block.samples, dtype=np.float32)
        self._chunks.append(chunk)
        self._total_samples += len(chunk)
        self._total_blocks += 1

    def stop(self) -> SessionMetadata:
        """Finalize the recording, write WAV and session.json sidecar, and return metadata."""
        if not self._active:
            raise RecordingStateError("Cannot stop session: no session is currently active.")

        self._active = False
        ended_at = datetime.now(timezone.utc)

        if self._total_samples == 0 or len(self._chunks) == 0:
            raise ValueError("No audio samples were recorded in session.")

        assert self._sample_rate_hz is not None
        assert self._session_id is not None
        assert self._started_at is not None

        # Concatenate audio
        full_audio = np.concatenate(self._chunks)
        duration_s = float(len(full_audio) / self._sample_rate_hz)

        # Create session directory
        session_dir = self.output_root / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        wav_path = session_dir / "raw.wav"
        if self.wav_format == "float32":
            wavfile.write(str(wav_path), self._sample_rate_hz, full_audio.astype(np.float32))
        else:
            # 16-bit integer PCM
            scaled = np.clip(full_audio, -1.0, 1.0) * 32767.0
            wavfile.write(str(wav_path), self._sample_rate_hz, scaled.astype(np.int16))

        # Compute SHA-256 of the written WAV file
        wav_sha256 = compute_file_sha256(wav_path)

        # Stream quality report
        qr = self._quality_monitor.report
        quality_data = {
            "total_blocks": qr.total_blocks,
            "dropped_blocks": qr.dropped_blocks,
            "repeated_sequences": qr.repeated_sequences,
            "sequence_discontinuities": qr.sequence_discontinuities,
            "timestamp_regressions": qr.timestamp_regressions,
            "sample_rate_changes": qr.sample_rate_changes,
            "is_healthy": qr.is_healthy,
        }

        # Environment details
        env_data = {
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "platform": platform.platform(),
        }

        metadata = SessionMetadata(
            session_id=self._session_id,
            started_at_utc=self._started_at.isoformat(),
            ended_at_utc=ended_at.isoformat(),
            source=self._source,
            sample_rate_hz=self._sample_rate_hz,
            total_blocks=self._total_blocks,
            total_samples=self._total_samples,
            duration_s=round(duration_s, 4),
            first_sequence=self._first_sequence,
            last_sequence=self._last_sequence,
            first_timestamp_s=round(self._first_timestamp_s, 4) if self._first_timestamp_s is not None else None,
            last_timestamp_s=round(self._last_timestamp_s, 4) if self._last_timestamp_s is not None else None,
            raw_wav_relpath="raw.wav",
            raw_wav_sha256=wav_sha256,
            stream_quality=quality_data,
            git_commit_sha=get_git_commit_sha(),
            environment=env_data,
        )

        json_path = session_dir / "session.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(metadata.to_json(indent=2))

        return metadata

    def cancel(self) -> None:
        """Cancel and discard the active recording without saving."""
        self._active = False
        self._chunks = []
        self._total_samples = 0
        self._total_blocks = 0


def list_sessions(sessions_dir: str | Path = "experiments/sessions") -> list[dict[str, Any]]:
    """Scan sessions directory and return list of session metadata summaries sorted newest first."""
    root = Path(sessions_dir)
    if not root.exists():
        return []

    sessions: list[dict[str, Any]] = []
    for item in root.iterdir():
        if item.is_dir():
            meta_file = item / "session.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["session_dir"] = str(item.resolve())
                        sessions.append(data)
                except Exception:
                    pass

    # Sort descending by started_at_utc
    sessions.sort(key=lambda s: s.get("started_at_utc", ""), reverse=True)
    return sessions


def get_session(session_id: str, sessions_dir: str | Path = "experiments/sessions") -> Optional[dict[str, Any]]:
    """Load session metadata dictionary for a given session ID."""
    root = Path(sessions_dir)
    target = root / session_id / "session.json"
    if not target.exists():
        return None

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
        data["session_dir"] = str(target.parent.resolve())
        return data


def create_session_source(
    session_id: str,
    sessions_dir: str | Path = "experiments/sessions",
    block_size: int = 256,
    realtime: bool = False,
    speed_factor: float = 1.0,
) -> WavSource | RealtimeWavSource:
    """Create a WavSource or RealtimeWavSource directly from a recorded session."""
    root = Path(sessions_dir)
    wav_path = root / session_id / "raw.wav"
    if not wav_path.exists():
        raise FileNotFoundError(f"Session raw audio not found: {wav_path}")

    if realtime:
        return RealtimeWavSource(
            wav_path,
            block_size=block_size,
            realtime=True,
            speed_factor=speed_factor,
        )
    return WavSource(wav_path, block_size=block_size)
