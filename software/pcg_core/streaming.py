"""AuscultaForge — Streaming Processing, Quality Monitoring, and Live Pipeline.

Provides live streaming ingestion, stream health / quality checks,
rolling metrics computation, and spectral frames for downstream UI consumption.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
from scipy.signal import spectrogram, welch

from .models import SampleBlock
from .buffers import RollingBuffer
from .dsp import StreamingBandpass
from .metrics import rms, peak_abs, crest_factor


@dataclass(slots=True)
class QualityReport:
    """Diagnostic health summary of an active SampleBlock stream."""
    total_blocks: int = 0
    total_samples: int = 0
    dropped_blocks: int = 0
    repeated_sequences: int = 0
    sequence_discontinuities: int = 0
    timestamp_regressions: int = 0
    sample_rate_changes: int = 0
    current_fs: Optional[int] = None
    last_sequence: Optional[int] = None
    last_timestamp_s: Optional[float] = None
    is_healthy: bool = True


class StreamQualityMonitor:
    """Inspects sequential SampleBlocks for stream anomalies.
    
    Operates strictly on the SampleBlock abstraction, independent of underlying
    wire/serial protocols.
    """

    def __init__(self, expected_sample_rate_hz: Optional[int] = None):
        self.report = QualityReport(current_fs=expected_sample_rate_hz)

    def inspect_block(self, block: SampleBlock) -> list[str]:
        """Validate an incoming SampleBlock and record any stream anomalies."""
        issues: list[str] = []
        r = self.report

        r.total_blocks += 1
        r.total_samples += len(block.samples)

        # 1. Sample rate check
        if r.current_fs is None:
            r.current_fs = block.sample_rate_hz
        elif block.sample_rate_hz != r.current_fs:
            r.sample_rate_changes += 1
            issues.append(
                f"Sample rate mismatch: expected {r.current_fs} Hz, got {block.sample_rate_hz} Hz"
            )

        # 2. Sequence checks (detects skipped, repeated, and out-of-order blocks)
        if r.last_sequence is not None:
            expected_seq = r.last_sequence + 1
            if block.sequence != expected_seq:
                r.sequence_discontinuities += 1
                diff = block.sequence - expected_seq
                if diff > 0:
                    r.dropped_blocks += diff
                    issues.append(
                        f"Dropped {diff} block(s): expected seq {expected_seq}, got {block.sequence}"
                    )
                elif block.sequence == r.last_sequence:
                    r.repeated_sequences += 1
                    issues.append(
                        f"Repeated sequence block: {block.sequence}"
                    )
                else:
                    issues.append(
                        f"Out-of-order sequence: expected {expected_seq}, got {block.sequence}"
                    )

        # 3. Timestamp regression check (with numerical precision tolerance)
        if r.last_timestamp_s is not None:
            if block.timestamp_s < r.last_timestamp_s - 1e-9:
                r.timestamp_regressions += 1
                issues.append(
                    f"Timestamp regression: previous {r.last_timestamp_s:.4f}s, current {block.timestamp_s:.4f}s"
                )

        r.last_sequence = block.sequence
        r.last_timestamp_s = block.timestamp_s

        r.is_healthy = (
            r.dropped_blocks == 0
            and r.repeated_sequences == 0
            and r.sequence_discontinuities == 0
            and r.timestamp_regressions == 0
            and r.sample_rate_changes == 0
        )

        return issues

    def reset(self) -> None:
        """Reset all diagnostic counters."""
        self.report = QualityReport(current_fs=None)


@dataclass(slots=True)
class LiveMetrics:
    """Current metrics evaluated over the rolling audio window."""
    timestamp_s: float
    buffer_duration_s: float
    sample_count: int
    rms: float
    peak_abs: float
    crest_factor: float


@dataclass(slots=True)
class SpectralFrame:
    """Instantaneous or short-time power spectrum ready for UI display."""
    frequencies_hz: list[float]
    power_db: list[float]
    peak_frequency_hz: float
    dominant_band: str


def compute_spectral_frame(
    samples: np.ndarray,
    fs: int,
    nperseg: int = 256,
) -> SpectralFrame:
    """Compute recent power spectral distribution from buffer samples."""
    if len(samples) < 16 or fs <= 0:
        return SpectralFrame(
            frequencies_hz=[],
            power_db=[],
            peak_frequency_hz=0.0,
            dominant_band="unknown",
        )

    actual_nperseg = min(nperseg, len(samples))
    freqs, psd = welch(samples, fs=fs, nperseg=actual_nperseg, scaling="density")

    # Convert to dB relative to 1.0 (with numerical floor)
    psd_floor = 1e-12
    power_db = 10.0 * np.log10(np.maximum(psd, psd_floor))

    peak_idx = int(np.argmax(psd)) if len(psd) else 0
    peak_freq = float(freqs[peak_idx]) if len(freqs) else 0.0

    if peak_freq < 20.0:
        band = "sub_audible"
    elif peak_freq < 150.0:
        band = "fundamental_pcg"
    elif peak_freq < 600.0:
        band = "extended_pcg"
    else:
        band = "high_frequency"

    return SpectralFrame(
        frequencies_hz=[round(float(f), 2) for f in freqs],
        power_db=[round(float(p), 2) for p in power_db],
        peak_frequency_hz=round(peak_freq, 2),
        dominant_band=band,
    )


def compute_rolling_spectrogram(
    samples: np.ndarray,
    fs: int,
    nperseg: int = 256,
    noverlap: int = 128,
) -> dict[str, Any]:
    """Compute a 2D time-frequency spectrogram representation over the current buffer."""
    if len(samples) < 32 or fs <= 0:
        return {
            "frequencies_hz": [],
            "time_bins_s": [],
            "shape": [0, 0],
            "sxx_preview": None,
        }

    actual_nperseg = min(nperseg, len(samples))
    actual_noverlap = min(noverlap, actual_nperseg // 2)

    f, t, Sxx = spectrogram(
        samples,
        fs=fs,
        nperseg=actual_nperseg,
        noverlap=actual_noverlap,
        scaling="density",
    )

    return {
        "frequencies_hz": [round(float(val), 2) for val in f],
        "time_bins_s": [round(float(val), 3) for val in t],
        "shape": [int(Sxx.shape[0]), int(Sxx.shape[1])],
        "sxx_preview": Sxx.tolist() if Sxx.shape[1] <= 64 else None,
    }


@dataclass(slots=True)
class LiveStreamFrame:
    """Output generated for each processed streaming block."""
    block: SampleBlock
    filtered_block: SampleBlock
    metrics: LiveMetrics
    spectral_frame: Optional[SpectralFrame]
    quality_issues: list[str] = field(default_factory=list)


class LiveStreamingPipeline:
    """Coordinates streaming DSP filtering, rolling buffer storage, and quality monitoring."""

    def __init__(
        self,
        buffer_duration_s: float = 5.0,
        filter_low_hz: float = 20.0,
        filter_high_hz: float = 600.0,
        filter_order: int = 4,
        enable_spectral_frame: bool = True,
    ):
        self.buffer_duration_s = float(buffer_duration_s)
        self.filter_low_hz = float(filter_low_hz)
        self.filter_high_hz = float(filter_high_hz)
        self.filter_order = int(filter_order)
        self.enable_spectral_frame = bool(enable_spectral_frame)

        self.buffer = RollingBuffer(capacity_seconds=self.buffer_duration_s)
        self.quality_monitor = StreamQualityMonitor()
        self.filter: Optional[StreamingBandpass] = None
        self._fs: Optional[int] = None

    def process_block(self, block: SampleBlock) -> LiveStreamFrame:
        """Process an incoming SampleBlock through the streaming pipeline."""
        # 1. Quality inspection
        issues = self.quality_monitor.inspect_block(block)

        # 2. Dynamic filter & buffer initialization upon first block or sample rate change
        if self.filter is None or self._fs != block.sample_rate_hz:
            self._fs = block.sample_rate_hz
            nyquist = self._fs / 2.0
            actual_high = min(self.filter_high_hz, nyquist - 1.0)
            self.filter = StreamingBandpass(
                sample_rate_hz=self._fs,
                low_hz=self.filter_low_hz,
                high_hz=actual_high,
                order=self.filter_order,
            )
            if self.buffer.sample_rate_hz is not None and self.buffer.sample_rate_hz != self._fs:
                self.buffer.reset_sample_rate(self._fs)

        # 3. DSP filter processing
        filtered_block = self.filter.process(block)

        # 4. Append filtered audio to the rolling window buffer
        self.buffer.append(filtered_block)

        # 5. Live metrics over current buffer
        buf_samples = self.buffer.get_samples()
        current_metrics = LiveMetrics(
            timestamp_s=block.timestamp_s,
            buffer_duration_s=self.buffer.duration_s,
            sample_count=len(buf_samples),
            rms=float(rms(buf_samples)),
            peak_abs=float(peak_abs(buf_samples)),
            crest_factor=float(crest_factor(buf_samples)),
        )

        # 6. Spectral frame for UI updates
        spectral: Optional[SpectralFrame] = None
        if self.enable_spectral_frame:
            spectral = compute_spectral_frame(buf_samples, fs=self._fs)

        return LiveStreamFrame(
            block=block,
            filtered_block=filtered_block,
            metrics=current_metrics,
            spectral_frame=spectral,
            quality_issues=issues,
        )
