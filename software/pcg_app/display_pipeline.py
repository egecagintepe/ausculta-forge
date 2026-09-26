"""AuscultaForge — Host Display Pipeline & Peak-Preserving Decimation.

Provides decoupled display frame aggregation and backpressure-isolated publication.

CORE ARCHITECTURE RULE:
Full-rate physical acquisition (48 kHz mono), DSP filtering, and session recording
are strictly independent from UI rendering cadence.
The display aggregator consumes full-rate processed SampleBlocks and periodically
produces display-oriented frames at a controlled, configurable display cadence
(e.g., 20–30 display updates/second).

Peak-preserving decimation (min/max bucket aggregation) preserves local
extrema/peaks better than naive periodic subsampling when
downsampling for UI display.
"""

from dataclasses import dataclass, field
import math
import time
from typing import Any, Optional

import numpy as np

from pcg_core.models import SampleBlock
from pcg_core.streaming import compute_spectral_frame, SpectralFrame


@dataclass(slots=True)
class DisplayPipelineConfig:
    """Centralized configuration for host display aggregation and publication.

    NOTE: Display rates are engineering defaults for smooth UI rendering and
    responsive host operation. They are NOT described as medical or clinically optimized.
    """
    target_display_hz: float = 25.0
    points_per_frame: int = 128
    max_rolling_window_s: float = 10.0
    spectral_update_hz: float = 5.0
    spectral_nperseg: int = 256
    enable_spectral: bool = True
    client_queue_size: int = 2
    emit_legacy_signal_frames: bool = False  # Legacy compatibility only; disabled by default


def decimate_min_max(samples: np.ndarray, target_points: int) -> np.ndarray:
    """Downsample signal using min/max bucket aggregation (peak-preserving decimation).

    Unlike naive subsampling (taking every N-th sample), min/max bucket aggregation
    divides the signal into target_points / 2 bins and extracts both the minimum and
    maximum values in each bin (in the chronological order in which they appear).
    This preserves local extrema/peaks better than naive periodic subsampling
    for visual display.

    Parameters
    ----------
    samples : np.ndarray
        1D array of audio/PCG samples.
    target_points : int
        Desired number of output display points (must be >= 2).

    Returns
    -------
    np.ndarray
        Decimated 1D float32 array of length <= target_points.
    """
    n = len(samples)
    if n <= target_points or target_points < 2:
        return np.asarray(samples, dtype=np.float32)

    # Each bucket produces 2 points: min and max in chronological order
    num_buckets = target_points // 2
    bucket_size = n / num_buckets

    out = np.empty(num_buckets * 2, dtype=np.float32)

    for i in range(num_buckets):
        start_idx = int(i * bucket_size)
        end_idx = int((i + 1) * bucket_size) if i < num_buckets - 1 else n
        if start_idx >= end_idx:
            start_idx = max(0, end_idx - 1)

        bucket = samples[start_idx:end_idx]
        if len(bucket) == 0:
            val = float(samples[min(start_idx, n - 1)])
            out[2 * i] = val
            out[2 * i + 1] = val
            continue

        min_rel_idx = int(np.argmin(bucket))
        max_rel_idx = int(np.argmax(bucket))

        min_val = float(bucket[min_rel_idx])
        max_val = float(bucket[max_rel_idx])

        # Preserve chronological ordering of extrema within the bucket
        if min_rel_idx <= max_rel_idx:
            out[2 * i] = min_val
            out[2 * i + 1] = max_val
        else:
            out[2 * i] = max_val
            out[2 * i + 1] = min_val

    return out


@dataclass(slots=True)
class DisplayFrame:
    """Display-oriented snapshot emitted at UI cadence.

    Represents an aggregated time-slice of full-rate data, decimated for
    visual rendering and packaged with instantaneous metrics and health summaries.
    """
    source_seq_start: int
    source_seq_end: int
    window_start_ts: float
    window_end_ts: float
    sample_rate_hz: int
    source_sample_count: int
    raw_points: list[float]
    filtered_points: list[float]
    rms: float
    peak: float
    crest_factor: float
    stream_quality: dict[str, Any]
    recording_active: bool
    dropped_display_frames: int = 0
    spectral_frame: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": "display_frame",
            "source_seq_start": self.source_seq_start,
            "source_seq_end": self.source_seq_end,
            "window_start_ts": round(self.window_start_ts, 4),
            "window_end_ts": round(self.window_end_ts, 4),
            "sample_rate_hz": self.sample_rate_hz,
            "source_sample_count": self.source_sample_count,
            "raw_points": self.raw_points,
            "filtered_points": self.filtered_points,
            "metrics": {
                "rms": round(self.rms, 5),
                "peak": round(self.peak, 5),
                "crest_factor": round(self.crest_factor, 3),
            },
            "stream_quality": self.stream_quality,
            "recording_active": self.recording_active,
            "dropped_display_frames": self.dropped_display_frames,
        }
        if self.spectral_frame is not None:
            d["spectral_frame"] = self.spectral_frame
        return d


class DisplayAggregator:
    """Accumulates full-rate processed blocks and periodically produces DisplayFrames.

    Operates on a configured display interval (e.g. 1/25 s = 40 ms). Full-rate
    blocks are appended to an internal rolling accumulator. When the display interval
    has elapsed, a DisplayFrame is generated via peak-preserving decimation.
    """

    def __init__(self, config: Optional[DisplayPipelineConfig] = None) -> None:
        self.config = config or DisplayPipelineConfig()
        self.display_interval_s: float = 1.0 / max(1.0, self.config.target_display_hz)
        self.spectral_interval_s: float = 1.0 / max(1.0, self.config.spectral_update_hz)

        # Accumulator for current display window
        self._raw_accum: list[np.ndarray] = []
        self._filt_accum: list[np.ndarray] = []
        self._accum_samples: int = 0
        self._seq_start: Optional[int] = None
        self._seq_end: Optional[int] = None
        self._ts_start: Optional[float] = None
        self._ts_end: Optional[float] = None
        self._fs: int = 48000

        # Timing tracking for cadence control (acquisition time based)
        self._last_display_ts: float = 0.0
        self._last_spectral_ts: float = 0.0

        # Bounded buffer for spectral calculation (max 4096 samples ~ 85ms at 48kHz)
        self._recent_filt: list[np.ndarray] = []
        self._recent_filt_count: int = 0

        # Telemetry counters
        self.total_display_frames_produced: int = 0
        self.total_display_frames_dropped: int = 0

    def reset(self) -> None:
        """Reset internal accumulators and timing state."""
        self._raw_accum.clear()
        self._filt_accum.clear()
        self._accum_samples = 0
        self._seq_start = None
        self._seq_end = None
        self._ts_start = None
        self._ts_end = None
        self._last_display_ts = 0.0
        self._last_spectral_ts = 0.0
        self._recent_filt.clear()
        self._recent_filt_count = 0

    def add_block(
        self,
        raw_block: SampleBlock,
        filtered_block: SampleBlock,
        quality_summary: dict[str, Any],
        recording_active: bool,
    ) -> Optional[DisplayFrame]:
        """Ingest a full-rate block and return a DisplayFrame if display cadence tick is due.

        Parameters
        ----------
        raw_block : SampleBlock
            Unfiltered acquisition block.
        filtered_block : SampleBlock
            DSP-filtered block.
        quality_summary : dict[str, Any]
            Stream health summary from StreamQualityMonitor.
        recording_active : bool
            Current SessionRecorder state.

        Returns
        -------
        Optional[DisplayFrame]
            A DisplayFrame if the display interval has elapsed; None otherwise.
        """
        raw_samples = raw_block.samples
        filt_samples = filtered_block.samples
        n_samples = len(raw_samples)
        self._fs = raw_block.sample_rate_hz

        # Sequence tracking
        if self._seq_start is None:
            self._seq_start = raw_block.sequence
            self._ts_start = raw_block.timestamp_s
        self._seq_end = raw_block.sequence

        # End timestamp: start of block + block duration
        block_dur = n_samples / max(1, self._fs)
        self._ts_end = raw_block.timestamp_s + block_dur

        # Accumulate
        self._raw_accum.append(raw_samples)
        self._filt_accum.append(filt_samples)
        self._accum_samples += n_samples

        # Bounded rolling buffer for spectral calculation (max 4096 samples)
        self._recent_filt.append(filt_samples)
        self._recent_filt_count += n_samples
        while self._recent_filt_count > 4096 and len(self._recent_filt) > 1:
            dropped = self._recent_filt.pop(0)
            self._recent_filt_count -= len(dropped)

        # Check cadence: has display interval elapsed since last emitted display frame?
        current_ts = raw_block.timestamp_s
        if self._last_display_ts == 0.0:
            self._last_display_ts = current_ts

        elapsed = current_ts - self._last_display_ts
        if elapsed < self.display_interval_s and self._accum_samples < (self._fs * 0.1):
            # Not yet time to emit display frame
            return None

        # Build DisplayFrame
        frame = self._build_frame(quality_summary, recording_active)
        self._last_display_ts = current_ts
        return frame

    def force_flush(
        self,
        quality_summary: dict[str, Any],
        recording_active: bool,
    ) -> Optional[DisplayFrame]:
        """Force generation of a DisplayFrame from any remaining accumulated samples."""
        if self._accum_samples == 0:
            return None
        return self._build_frame(quality_summary, recording_active)

    def _build_frame(
        self,
        quality_summary: dict[str, Any],
        recording_active: bool,
    ) -> DisplayFrame:
        """Construct DisplayFrame with peak-preserving decimation."""
        raw_concat = np.concatenate(self._raw_accum) if self._raw_accum else np.zeros(0, dtype=np.float32)
        filt_concat = np.concatenate(self._filt_accum) if self._filt_accum else np.zeros(0, dtype=np.float32)

        # Peak-preserving decimation to target points
        raw_dec = decimate_min_max(raw_concat, self.config.points_per_frame)
        filt_dec = decimate_min_max(filt_concat, self.config.points_per_frame)

        # Calculate metrics on recent filtered audio
        if len(filt_concat) > 0:
            cur_rms = float(np.sqrt(np.mean(filt_concat ** 2)))
            cur_peak = float(np.max(np.abs(filt_concat)))
            cur_cf = float(cur_peak / (cur_rms + 1e-9))
        else:
            cur_rms = 0.0
            cur_peak = 0.0
            cur_cf = 1.0

        # Periodic spectral frame computation (bounded to recent <=4096 samples)
        spectral_dict: Optional[dict[str, Any]] = None
        if self.config.enable_spectral and self._recent_filt_count >= 32:
            spec_elapsed = (self._ts_end or 0.0) - self._last_spectral_ts
            if spec_elapsed >= self.spectral_interval_s or self._last_spectral_ts == 0.0:
                spec_samples = np.concatenate(self._recent_filt)
                spec_frame = compute_spectral_frame(
                    spec_samples,
                    fs=self._fs,
                    nperseg=min(self.config.spectral_nperseg, len(spec_samples)),
                )
                spectral_dict = {
                    "frequencies_hz": spec_frame.frequencies_hz,
                    "power_db": spec_frame.power_db,
                    "peak_frequency_hz": spec_frame.peak_frequency_hz,
                    "dominant_band": spec_frame.dominant_band,
                }
                self._last_spectral_ts = self._ts_end or 0.0

        raw_list = [round(float(v), 5) for v in raw_dec]
        filt_list = [round(float(v), 5) for v in filt_dec]

        display_frame = DisplayFrame(
            source_seq_start=self._seq_start if self._seq_start is not None else 0,
            source_seq_end=self._seq_end if self._seq_end is not None else 0,
            window_start_ts=self._ts_start if self._ts_start is not None else 0.0,
            window_end_ts=self._ts_end if self._ts_end is not None else 0.0,
            sample_rate_hz=self._fs,
            source_sample_count=self._accum_samples,
            raw_points=raw_list,
            filtered_points=filt_list,
            rms=cur_rms,
            peak=cur_peak,
            crest_factor=cur_cf,
            stream_quality=quality_summary,
            recording_active=recording_active,
            dropped_display_frames=self.total_display_frames_dropped,
            spectral_frame=spectral_dict,
        )

        self.total_display_frames_produced += 1

        # Clear accumulation for next window
        self._raw_accum.clear()
        self._filt_accum.clear()
        self._accum_samples = 0
        self._seq_start = None
        self._seq_end = None
        self._ts_start = None
        self._ts_end = None

        return display_frame
