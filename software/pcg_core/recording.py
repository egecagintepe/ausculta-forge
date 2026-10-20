"""AuscultaForge — Acquisition Session Recording & Provenance Module.

Consumes SampleBlock streams and commits raw sensor acquisitions to disk with a
JSON metadata sidecar, standardized laboratory manifest, and raw audio WAV.
Preserves raw unadulterated sensor data for reproducible replay, phantom bench
verification, and laboratory audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
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


class SessionCorruptedError(ValueError):
    """Raised when session files on disk are corrupted, incomplete, or unreadable."""
    pass


class SessionNotFoundError(FileNotFoundError):
    """Raised when requested session is not found in the sessions directory."""
    pass


class SessionIntegrityError(ValueError):
    """Raised when session SHA-256 hash or sample count validation fails."""
    pass


SAFE_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

WINDOWS_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def validate_session_id(session_id: str, sessions_dir: str | Path = "experiments/sessions") -> str:
    """Validate that session_id is a safe identifier contained strictly within sessions_dir.

    Rejects path traversal characters ('..', '/', '\\'), control characters, null bytes,
    and Windows reserved device names (CON, NUL, COM1-9, LPT1-9).
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id must be a non-empty string")

    clean_id = session_id.strip()
    if not clean_id or not SAFE_SESSION_ID_PATTERN.match(clean_id):
        raise ValueError(
            f"Invalid session_id format: {session_id!r}. Only alphanumeric, '_', and '-' characters allowed."
        )

    if clean_id.upper() in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Reserved identifier not allowed: {session_id!r}")

    root = Path(sessions_dir).resolve()
    target = (root / clean_id).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"Path traversal detected: {session_id!r} resolves outside {sessions_dir}")

    return clean_id


@dataclass(slots=True)
class SessionMetadata:
    """Provenance, acquisition parameters, and data integrity metrics for a recorded PCG session."""
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
    acquisition_mode: str = "offline"
    termination_reason: str = "completed"
    device_info: Optional[dict[str, Any]] = None
    app_version: str = "2.0.0"
    schema_version: str = "2.0.0"
    storage_format: str = "normalized_float32"
    wire_format: Optional[str] = None
    storage_disclaimer: str = (
        "WAV file contains normalized IEEE float32 audio samples in [-1.0, 1.0], "
        "derived via linear scaling from acquisition blocks. It is not an unparsed wire bitstream copy."
    )
    processing_profile: Optional[dict[str, Any]] = None
    status: str = "finalized"
    manifest_version: str = "2.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        """Construct SessionMetadata from a dictionary with robust backward compatibility for schema v1.0.0."""
        return cls(
            session_id=data["session_id"],
            started_at_utc=data.get("started_at_utc", ""),
            ended_at_utc=data.get("ended_at_utc", ""),
            source=data.get("source", "unknown"),
            sample_rate_hz=int(data.get("sample_rate_hz", 48000)),
            total_blocks=int(data.get("total_blocks", 0)),
            total_samples=int(data.get("total_samples", 0)),
            duration_s=float(data.get("duration_s", 0.0)),
            first_sequence=data.get("first_sequence"),
            last_sequence=data.get("last_sequence"),
            first_timestamp_s=data.get("first_timestamp_s"),
            last_timestamp_s=data.get("last_timestamp_s"),
            raw_wav_relpath=data.get("raw_wav_relpath", "raw.wav"),
            raw_wav_sha256=data.get("raw_wav_sha256", ""),
            stream_quality=data.get("stream_quality", {}),
            git_commit_sha=data.get("git_commit_sha"),
            environment=data.get("environment", {}),
            acquisition_mode=data.get("acquisition_mode", "offline"),
            termination_reason=data.get("termination_reason", "completed"),
            device_info=data.get("device_info"),
            app_version=data.get("app_version", "1.0.0"),
            schema_version=data.get("schema_version", "1.0.0"),
            storage_format=data.get("storage_format", "normalized_float32"),
            wire_format=data.get("wire_format"),
            storage_disclaimer=data.get(
                "storage_disclaimer",
                "WAV file contains normalized IEEE float32 audio samples in [-1.0, 1.0], "
                "derived via linear scaling from acquisition blocks. It is not an unparsed wire bitstream copy."
            ),
            processing_profile=data.get("processing_profile"),
            status=data.get("status", "finalized"),
            manifest_version=data.get("manifest_version", "2.0.0"),
        )

    @classmethod
    def from_json(cls, text: str) -> "SessionMetadata":
        return cls.from_dict(json.loads(text))


class SessionRecorder:
    """Records streaming SampleBlock instances to a persistent session directory.

    Structure:
        experiments/sessions/<session_id>/
        ├── raw.wav          (Canonical unfiltered accepted samples in normalized float32)
        ├── session.json     (Authoritative session metadata sidecar)
        └── manifest.json    (Machine-readable laboratory manifest for phantom benchmarks)
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
        self._acquisition_mode: str = "offline"
        self._device_info: Optional[dict[str, Any]] = None
        self._wire_format: Optional[str] = None
        self._processing_profile: Optional[dict[str, Any]] = None

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

    def start(
        self,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        acquisition_mode: str = "offline",
        device_info: Optional[dict[str, Any]] = None,
        wire_format: Optional[str] = None,
        processing_profile: Optional[dict[str, Any]] = None,
    ) -> str:
        """Start a new recording session and persist an in-progress placeholder to disk."""
        if self._active:
            raise RecordingStateError("A recording session is already active.")

        if session_id:
            valid_id = validate_session_id(session_id, self.output_root)
            self._session_id = valid_id
        else:
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_id = uuid.uuid4().hex[:8]
            self._session_id = f"session_{ts_str}_{short_id}"

        if source:
            self._source = str(source)

        self._acquisition_mode = str(acquisition_mode)
        self._device_info = device_info
        self._wire_format = wire_format
        self._processing_profile = processing_profile
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

        # Pre-create session directory and persist in-progress marker
        # Guarantees that mid-stream crashes/aborts leave a detectable incomplete session record
        session_dir = self.output_root / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        in_progress_meta = {
            "session_id": self._session_id,
            "started_at_utc": self._started_at.isoformat(),
            "ended_at_utc": None,
            "source": self._source,
            "acquisition_mode": self._acquisition_mode,
            "status": "recording",
            "termination_reason": "incomplete",
            "schema_version": "2.0.0",
            "storage_format": f"normalized_{self.wav_format}",
            "wire_format": self._wire_format,
            "device_info": self._device_info,
            "processing_profile": self._processing_profile,
        }
        marker_path = session_dir / "session.json"
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(in_progress_meta, f, indent=2)

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

    def stop(self, termination_reason: str = "completed") -> SessionMetadata:
        """Finalize the recording, write WAV, session.json, and manifest.json sidecar.

        Guarantees exact accepted-sample accounting between recorder memory, WAV file, and metadata.
        """
        if not self._active:
            raise RecordingStateError("Cannot stop session: no session is currently active.")

        self._active = False
        ended_at = datetime.now(timezone.utc)

        if self._total_samples == 0 or len(self._chunks) == 0:
            raise ValueError("No audio samples were recorded in session.")

        assert self._sample_rate_hz is not None
        assert self._session_id is not None
        assert self._started_at is not None

        # 1. Concatenate audio and verify exact sample count accounting
        full_audio = np.concatenate(self._chunks)
        if len(full_audio) != self._total_samples:
            raise SessionCorruptedError(
                f"Sample accounting discrepancy: recorder counted {self._total_samples} samples, "
                f"but concatenated audio contains {len(full_audio)} samples."
            )

        duration_s = float(len(full_audio) / self._sample_rate_hz)

        # 2. Ensure session directory exists
        session_dir = self.output_root / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 3. Write raw unfiltered audio to disk
        wav_path = session_dir / "raw.wav"
        if self.wav_format == "float32":
            wavfile.write(str(wav_path), self._sample_rate_hz, full_audio.astype(np.float32))
        else:
            # 16-bit integer PCM
            scaled = np.clip(full_audio, -1.0, 1.0) * 32767.0
            wavfile.write(str(wav_path), self._sample_rate_hz, scaled.astype(np.int16))

        # 4. Read back serialized WAV to mathematically confirm exact sample accounting on disk
        read_fs, read_samples = wavfile.read(str(wav_path))
        if read_fs != self._sample_rate_hz or len(read_samples) != self._total_samples:
            raise SessionCorruptedError(
                f"WAV serialization accounting failure: expected {self._total_samples} samples at {self._sample_rate_hz} Hz, "
                f"disk WAV contains {len(read_samples)} samples at {read_fs} Hz."
            )

        # 5. Compute SHA-256 of the written WAV file
        wav_sha256 = compute_file_sha256(wav_path)

        # 6. Stream quality report
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

        # 7. Environment details
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
            acquisition_mode=self._acquisition_mode,
            termination_reason=termination_reason,
            device_info=self._device_info,
            app_version="2.0.0",
            schema_version="2.0.0",
            storage_format=f"normalized_{self.wav_format}",
            wire_format=self._wire_format,
            processing_profile=self._processing_profile,
            status="finalized",
            manifest_version="2.0.0",
        )

        # 8. Atomic metadata write via temporary file
        json_path = session_dir / "session.json"
        tmp_json_path = session_dir / "session.json.tmp"
        with open(tmp_json_path, "w", encoding="utf-8") as f:
            f.write(metadata.to_json(indent=2))
        tmp_json_path.replace(json_path)

        # 9. Write exportable laboratory manifest
        manifest_data = export_session_manifest(self._session_id, self.output_root)
        manifest_path = session_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return metadata

    def cancel(self) -> None:
        """Cancel and discard the active recording, cleaning up partial files on disk."""
        self._active = False
        if self._session_id:
            session_dir = self.output_root / self._session_id
            if session_dir.exists():
                try:
                    shutil.rmtree(session_dir)
                except Exception:
                    pass
        self._chunks = []
        self._total_samples = 0
        self._total_blocks = 0


def verify_session_integrity(
    session_id: str,
    sessions_dir: str | Path = "experiments/sessions",
) -> dict[str, Any]:
    """Verify cryptographic hash and sample-level accounting integrity of a recorded session.

    Performs deep inspection:
    1. Validates session ID path safety.
    2. Confirms session directory and session.json sidecar existence and syntax.
    3. Confirms raw.wav audio file existence and readable header.
    4. Computes SHA-256 of raw.wav on disk and compares against recorded raw_wav_sha256.
    5. Confirms exact sample count in raw.wav matches total_samples in metadata.
    6. Confirms sample rate matches sample_rate_hz in metadata.
    7. Evaluates termination reason (flags interrupted or incomplete sessions).
    """
    valid_id = validate_session_id(session_id, sessions_dir)
    root = Path(sessions_dir).resolve()
    session_dir = root / valid_id
    if not session_dir.exists() or not session_dir.is_dir():
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "missing_session_dir",
            "sha256_match": False,
            "expected_sha256": "",
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": 0,
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": 0,
            "wav_sample_rate": 0,
            "termination_reason": "unknown",
            "details": f"Session directory does not exist: {session_dir}",
        }

    # Load session.json
    json_path = session_dir / "session.json"
    if not json_path.exists():
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "missing_metadata",
            "sha256_match": False,
            "expected_sha256": "",
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": 0,
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": 0,
            "wav_sample_rate": 0,
            "termination_reason": "unknown",
            "details": "session.json metadata sidecar is missing.",
        }

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
    except Exception as e:
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "corrupted_metadata",
            "sha256_match": False,
            "expected_sha256": "",
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": 0,
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": 0,
            "wav_sample_rate": 0,
            "termination_reason": "corrupted",
            "details": f"session.json is malformed or invalid JSON: {e}",
        }

    # Check incomplete recording status
    if meta_data.get("status") == "recording" or meta_data.get("termination_reason") == "incomplete":
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "incomplete",
            "sha256_match": False,
            "expected_sha256": meta_data.get("raw_wav_sha256", ""),
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": int(meta_data.get("total_samples", 0)),
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": int(meta_data.get("sample_rate_hz", 0)),
            "wav_sample_rate": 0,
            "termination_reason": "incomplete",
            "details": "Session recording was interrupted before finalization.",
        }

    # Inspect raw.wav
    wav_rel = meta_data.get("raw_wav_relpath", "raw.wav")
    wav_path = session_dir / wav_rel
    if not wav_path.exists():
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "missing_audio",
            "sha256_match": False,
            "expected_sha256": meta_data.get("raw_wav_sha256", ""),
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": int(meta_data.get("total_samples", 0)),
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": int(meta_data.get("sample_rate_hz", 0)),
            "wav_sample_rate": 0,
            "termination_reason": meta_data.get("termination_reason", "completed"),
            "details": f"Audio file not found: {wav_path}",
        }

    # Compute actual SHA-256
    try:
        actual_sha256 = compute_file_sha256(wav_path)
    except Exception as e:
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": "unreadable_audio",
            "sha256_match": False,
            "expected_sha256": meta_data.get("raw_wav_sha256", ""),
            "actual_sha256": "",
            "sample_count_match": False,
            "metadata_samples": int(meta_data.get("total_samples", 0)),
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": int(meta_data.get("sample_rate_hz", 0)),
            "wav_sample_rate": 0,
            "termination_reason": meta_data.get("termination_reason", "completed"),
            "details": f"Failed reading audio file for SHA-256 calculation: {e}",
        }

    expected_sha256 = meta_data.get("raw_wav_sha256", "")
    sha256_match = (actual_sha256 == expected_sha256 and bool(expected_sha256))

    # Read WAV structure and sample count
    try:
        wav_fs, wav_data = wavfile.read(str(wav_path))
        wav_samples = len(wav_data)
    except Exception as e:
        status = "hash_mismatch" if (expected_sha256 and not sha256_match) else "malformed_wav"
        return {
            "session_id": valid_id,
            "is_valid": False,
            "status": status,
            "sha256_match": sha256_match,
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "sample_count_match": False,
            "metadata_samples": int(meta_data.get("total_samples", 0)),
            "wav_samples": 0,
            "sample_rate_match": False,
            "metadata_sample_rate": int(meta_data.get("sample_rate_hz", 0)),
            "wav_sample_rate": 0,
            "termination_reason": meta_data.get("termination_reason", "completed"),
            "details": (
                f"Cryptographic mismatch (expected {expected_sha256}, actual {actual_sha256}); "
                f"WAV structure error: {e}"
                if status == "hash_mismatch"
                else f"WAV file header or content corrupted: {e}"
            ),
        }

    meta_samples = int(meta_data.get("total_samples", 0))
    sample_count_match = (wav_samples == meta_samples)

    meta_fs = int(meta_data.get("sample_rate_hz", 0))
    sample_rate_match = (wav_fs == meta_fs)

    term_reason = meta_data.get("termination_reason", "completed")

    # Evaluate overall validity
    is_valid = sha256_match and sample_count_match and sample_rate_match

    if not sha256_match:
        status = "hash_mismatch"
        details = f"Cryptographic mismatch: expected {expected_sha256}, actual {actual_sha256}."
    elif not sample_count_match:
        status = "sample_count_mismatch"
        details = f"Sample count mismatch: metadata recorded {meta_samples}, WAV file contains {wav_samples}."
    elif not sample_rate_match:
        status = "sample_rate_mismatch"
        details = f"Sample rate mismatch: metadata recorded {meta_fs} Hz, WAV header declares {wav_fs} Hz."
    elif term_reason in ("device_disconnected", "stream_interrupted", "error"):
        status = "interrupted_valid"
        details = f"Integrity verified (SHA-256 and samples match), but session ended with reason {term_reason!r}."
    else:
        status = "verified"
        details = "Session passed cryptographic SHA-256 and exact sample accounting validation."

    return {
        "session_id": valid_id,
        "is_valid": is_valid,
        "status": status,
        "sha256_match": sha256_match,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "sample_count_match": sample_count_match,
        "metadata_samples": meta_samples,
        "wav_samples": wav_samples,
        "sample_rate_match": sample_rate_match,
        "metadata_sample_rate": meta_fs,
        "wav_sample_rate": wav_fs,
        "termination_reason": term_reason,
        "details": details,
    }


def export_session_manifest(
    session_id: str,
    sessions_dir: str | Path = "experiments/sessions",
) -> dict[str, Any]:
    """Generate a standardized, machine-readable laboratory session manifest for phantom experiments.

    Produces an audit-ready JSON manifest detailing:
    - Experiment identity and timestamp
    - Data specification (storage format: normalized float32, wire format, sample bounds)
    - Hardware provenance (device identity, firmware, profile; strictly None for synthetic/offline)
    - DSP provenance (active filter preset and passband during acquisition)
    - Integrity and stream quality metrics (SHA-256 hash, dropped blocks, termination reason)
    - Host execution environment (OS, Python, NumPy, SciPy, Git commit SHA)
    """
    valid_id = validate_session_id(session_id, sessions_dir)
    meta_dict = get_session(valid_id, sessions_dir)
    if meta_dict is None:
        raise SessionNotFoundError(f"Session not found: {valid_id}")

    integrity = verify_session_integrity(valid_id, sessions_dir)

    is_hardware = (meta_dict.get("acquisition_mode") == "hardware")
    dev_info = meta_dict.get("device_info") if is_hardware else None

    manifest = {
        "manifest_version": "2.0.0",
        "manifest_type": "ausculta_forge_session_manifest",
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "session_id": valid_id,
        "acquisition": {
            "source": meta_dict.get("source", "unknown"),
            "acquisition_mode": meta_dict.get("acquisition_mode", "offline"),
            "started_at_utc": meta_dict.get("started_at_utc"),
            "ended_at_utc": meta_dict.get("ended_at_utc"),
            "duration_s": meta_dict.get("duration_s", 0.0),
            "sample_rate_hz": meta_dict.get("sample_rate_hz", 48000),
            "total_samples": meta_dict.get("total_samples", 0),
            "total_blocks": meta_dict.get("total_blocks", 0),
            "termination_reason": meta_dict.get("termination_reason", "completed"),
        },
        "data_specification": {
            "channels": 1,
            "storage_format": meta_dict.get("storage_format", "normalized_float32"),
            "wire_format": meta_dict.get("wire_format") or ("int32_24bit_signed" if is_hardware else "float32"),
            "storage_sample_range": [-1.0, 1.0],
            "raw_wav_relpath": meta_dict.get("raw_wav_relpath", "raw.wav"),
            "disclaimer": meta_dict.get(
                "storage_disclaimer",
                "WAV file contains normalized IEEE float32 audio samples in [-1.0, 1.0], "
                "derived via linear scaling from acquisition blocks. It is not an unparsed wire bitstream copy."
            ),
        },
        "hardware_provenance": {
            "is_physical_hardware": is_hardware,
            "device_id": dev_info.get("device_id") if dev_info else None,
            "firmware_version": dev_info.get("firmware_version") if dev_info else None,
            "transport_type": dev_info.get("transport_type") if dev_info else None,
            "acquisition_profile": dev_info.get("acquisition_profile") if dev_info else None,
        },
        "dsp_provenance": {
            "processing_profile": meta_dict.get("processing_profile"),
            "note": "raw.wav contains unadulterated sensor samples prior to DSP filtering.",
        },
        "integrity": {
            "raw_wav_sha256": meta_dict.get("raw_wav_sha256"),
            "integrity_verified": integrity.get("is_valid", False),
            "integrity_status": integrity.get("status"),
            "stream_quality": meta_dict.get("stream_quality", {}),
        },
        "environment": meta_dict.get("environment", {}),
        "app_provenance": {
            "app_version": meta_dict.get("app_version", "2.0.0"),
            "schema_version": meta_dict.get("schema_version", "2.0.0"),
            "git_commit_sha": meta_dict.get("git_commit_sha"),
        },
    }
    return manifest


def delete_session(
    session_id: str,
    sessions_dir: str | Path = "experiments/sessions",
) -> bool:
    """Safely delete a recorded session directory and its contents after strict ID validation."""
    valid_id = validate_session_id(session_id, sessions_dir)
    target = Path(sessions_dir).resolve() / valid_id
    if not target.exists() or not target.is_dir():
        return False
    shutil.rmtree(target)
    return True


def list_sessions(sessions_dir: str | Path = "experiments/sessions") -> list[dict[str, Any]]:
    """Scan sessions directory and return list of session metadata summaries sorted newest first.

    Handles corrupted or unfinalized sessions gracefully without failing the entire listing.
    """
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
                        # Normalize schema version
                        if "schema_version" not in data:
                            data["schema_version"] = "1.0.0"
                        if data.get("status") == "recording":
                            data["status"] = "incomplete"
                        sessions.append(data)
                except Exception:
                    # Report corrupted metadata gracefully
                    sessions.append({
                        "session_id": item.name,
                        "status": "corrupted_metadata",
                        "termination_reason": "corrupted",
                        "source": "unknown",
                        "started_at_utc": "",
                        "duration_s": 0.0,
                        "total_samples": 0,
                        "sample_rate_hz": 0,
                        "stream_quality": {"is_healthy": False},
                        "raw_wav_sha256": "",
                        "schema_version": "unknown",
                    })

    # Sort descending by started_at_utc
    sessions.sort(key=lambda s: s.get("started_at_utc", ""), reverse=True)
    return sessions


def get_session(session_id: str, sessions_dir: str | Path = "experiments/sessions") -> Optional[dict[str, Any]]:
    """Load session metadata dictionary for a given session ID safely without escaping sessions_dir."""
    try:
        valid_id = validate_session_id(session_id, sessions_dir)
    except ValueError:
        return None

    root = Path(sessions_dir).resolve()
    target = root / valid_id / "session.json"
    if not target.exists():
        return None

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "1.0.0"
            if data.get("status") == "recording":
                data["status"] = "incomplete"
            return data
    except Exception:
        return None


def create_session_source(
    session_id: str,
    sessions_dir: str | Path = "experiments/sessions",
    block_size: int = 256,
    realtime: bool = False,
    speed_factor: float = 1.0,
) -> WavSource | RealtimeWavSource:
    """Create a WavSource or RealtimeWavSource directly from a recorded session safely."""
    valid_id = validate_session_id(session_id, sessions_dir)
    root = Path(sessions_dir).resolve()
    wav_path = root / valid_id / "raw.wav"
    if not wav_path.exists():
        raise FileNotFoundError(f"Session raw audio not found: {wav_path}")

    # Validate that WAV file is readable and non-corrupt
    try:
        fs, data = wavfile.read(str(wav_path))
        if len(data) == 0:
            raise SessionCorruptedError(f"Session audio file is empty (0 samples): {wav_path}")
    except Exception as e:
        if isinstance(e, SessionCorruptedError):
            raise
        raise SessionCorruptedError(f"Session audio file is corrupted or unreadable: {wav_path} ({e})") from e

    if realtime:
        return RealtimeWavSource(
            wav_path,
            block_size=block_size,
            realtime=True,
            speed_factor=speed_factor,
        )
    return WavSource(wav_path, block_size=block_size)
