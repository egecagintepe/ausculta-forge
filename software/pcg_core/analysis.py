"""AuscultaForge — Offline PCG Analysis Pipeline.

Processes continuous or block-based PCG audio through the common SampleBlock
pipeline, applying provisional band-pass filtering, computing metrics, and
calculating a machine-readable spectrogram representation.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Iterator
import json
import numpy as np
from scipy.signal import spectrogram

from .models import SampleBlock
from .sources import WavSource
from .dsp import StreamingBandpass
from .metrics import rms, peak_abs, crest_factor


@dataclass(slots=True)
class SignalMetrics:
    """Statistical amplitude and crest metrics for a signal segment."""
    rms: float
    peak_abs: float
    crest_factor: float

    @classmethod
    def from_samples(cls, x: np.ndarray) -> "SignalMetrics":
        return cls(
            rms=float(rms(x)),
            peak_abs=float(peak_abs(x)),
            crest_factor=float(crest_factor(x)),
        )


@dataclass(slots=True)
class FilterConfig:
    """Filter configuration details.
    
    Note: 20-600 Hz is a provisional engineering default, not a clinical finality.
    """
    filter_type: str
    low_hz: float
    high_hz: float
    order: int
    is_provisional: bool = True


@dataclass(slots=True)
class SpectrogramData:
    """Summary and frequency breakdown of the computed spectrogram."""
    shape: list[int]  # [n_frequencies, n_time_bins]
    f_min_hz: float
    f_max_hz: float
    f_resolution_hz: float
    time_min_s: float
    time_max_s: float
    time_step_s: float
    peak_frequency_hz: float
    band_energy_ratios: dict[str, float]
    # Optionally store the full matrix if explicitly enabled
    matrix: list[list[float]] | None = None


@dataclass(slots=True)
class PCGAnalysisResult:
    """Comprehensive machine-readable PCG analysis report."""
    source_name: str
    sample_rate_hz: int
    duration_s: float
    total_samples: int
    filter_config: FilterConfig
    raw_metrics: SignalMetrics
    filtered_metrics: SignalMetrics
    spectrogram: SpectrogramData

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def compute_spectrogram_data(
    samples: np.ndarray,
    fs: int,
    nperseg: int = 256,
    noverlap: int = 128,
    include_matrix: bool = False,
) -> SpectrogramData:
    """Compute spectrogram representation and acoustic band energies."""
    if len(samples) < 16:
        return SpectrogramData(
            shape=[0, 0],
            f_min_hz=0.0,
            f_max_hz=0.0,
            f_resolution_hz=0.0,
            time_min_s=0.0,
            time_max_s=0.0,
            time_step_s=0.0,
            peak_frequency_hz=0.0,
            band_energy_ratios={},
            matrix=None,
        )

    # Adjust segment sizes if audio is shorter than default window
    actual_nperseg = min(nperseg, len(samples))
    actual_noverlap = min(noverlap, actual_nperseg // 2)

    f, t, Sxx = spectrogram(
        samples,
        fs=fs,
        nperseg=actual_nperseg,
        noverlap=actual_noverlap,
        scaling="density",
    )

    # Calculate peak dominant frequency across total power
    psd_mean = np.mean(Sxx, axis=1) if Sxx.ndim == 2 and Sxx.shape[1] > 0 else np.zeros_like(f)
    peak_idx = int(np.argmax(psd_mean)) if len(psd_mean) else 0
    peak_freq = float(f[peak_idx]) if len(f) else 0.0

    total_energy = float(np.sum(psd_mean)) if len(psd_mean) else 0.0

    # Categorize into conventional acoustic PCG frequency bands
    def band_energy(low: float, high: float) -> float:
        if total_energy <= 0.0:
            return 0.0
        mask = (f >= low) & (f < high)
        return float(np.sum(psd_mean[mask]) / total_energy) if np.any(mask) else 0.0

    energy_ratios = {
        "sub_audible_0_20hz": round(band_energy(0.0, 20.0), 4),
        "fundamental_pcg_20_150hz": round(band_energy(20.0, 150.0), 4),
        "extended_pcg_150_600hz": round(band_energy(150.0, 600.0), 4),
        "high_freq_above_600hz": round(band_energy(600.0, fs / 2.0), 4),
    }

    f_res = float(f[1] - f[0]) if len(f) > 1 else 0.0
    t_step = float(t[1] - t[0]) if len(t) > 1 else 0.0

    matrix_data = Sxx.tolist() if include_matrix else None

    return SpectrogramData(
        shape=[int(Sxx.shape[0]), int(Sxx.shape[1])],
        f_min_hz=float(f[0]) if len(f) else 0.0,
        f_max_hz=float(f[-1]) if len(f) else 0.0,
        f_resolution_hz=round(f_res, 3),
        time_min_s=float(t[0]) if len(t) else 0.0,
        time_max_s=float(t[-1]) if len(t) else 0.0,
        time_step_s=round(t_step, 4),
        peak_frequency_hz=round(peak_freq, 2),
        band_energy_ratios=energy_ratios,
        matrix=matrix_data,
    )


def analyze_source(
    source: Any,
    filter_low_hz: float = 20.0,
    filter_high_hz: float = 600.0,
    filter_order: int = 4,
    include_spectrogram_matrix: bool = False,
) -> PCGAnalysisResult:
    """Analyze stream of SampleBlocks from any source (Mock, WAV, Serial, etc.).
    
    Dynamically configures the bandpass filter using the source's detected
    sample_rate_hz.
    """
    raw_blocks: list[np.ndarray] = []
    filtered_blocks: list[np.ndarray] = []

    bp_filter: StreamingBandpass | None = None
    detected_fs: int | None = None
    source_name = getattr(source, "name", getattr(source, "source", "stream"))

    for block in source.blocks():
        if detected_fs is None:
            detected_fs = block.sample_rate_hz
            source_name = block.source

            # Validate requested provisional filter range against Nyquist
            nyquist = detected_fs / 2.0
            actual_high_hz = min(filter_high_hz, nyquist - 1.0)
            if actual_high_hz <= filter_low_hz:
                raise ValueError(
                    f"Invalid filter parameters for sample rate {detected_fs} Hz: "
                    f"low={filter_low_hz} Hz, high={actual_high_hz} Hz (Nyquist={nyquist} Hz)"
                )

            bp_filter = StreamingBandpass(
                sample_rate_hz=detected_fs,
                low_hz=filter_low_hz,
                high_hz=actual_high_hz,
                order=filter_order,
            )

        raw_blocks.append(block.samples)
        filtered_block = bp_filter.process(block)
        filtered_blocks.append(filtered_block.samples)

    if detected_fs is None or len(raw_blocks) == 0:
        raise ValueError("Source produced no SampleBlocks to analyze.")

    raw_signal = np.concatenate(raw_blocks)
    filtered_signal = np.concatenate(filtered_blocks)

    total_samples = len(raw_signal)
    duration_s = total_samples / float(detected_fs)

    raw_metrics = SignalMetrics.from_samples(raw_signal)
    filtered_metrics = SignalMetrics.from_samples(filtered_signal)

    filter_cfg = FilterConfig(
        filter_type="butterworth_bandpass",
        low_hz=filter_low_hz,
        high_hz=min(filter_high_hz, detected_fs / 2.0 - 1.0),
        order=filter_order,
        is_provisional=True,
    )

    spec_data = compute_spectrogram_data(
        filtered_signal,
        fs=detected_fs,
        include_matrix=include_spectrogram_matrix,
    )

    return PCGAnalysisResult(
        source_name=str(source_name),
        sample_rate_hz=detected_fs,
        duration_s=round(duration_s, 4),
        total_samples=total_samples,
        filter_config=filter_cfg,
        raw_metrics=raw_metrics,
        filtered_metrics=filtered_metrics,
        spectrogram=spec_data,
    )


def analyze_wav(
    path: str | Path,
    block_size: int = 256,
    filter_low_hz: float = 20.0,
    filter_high_hz: float = 600.0,
    filter_order: int = 4,
    include_spectrogram_matrix: bool = False,
) -> PCGAnalysisResult:
    """Convenience helper to analyze a WAV file using WavSource."""
    wav_path = Path(path)
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    source = WavSource(path=wav_path, block_size=block_size)
    return analyze_source(
        source=source,
        filter_low_hz=filter_low_hz,
        filter_high_hz=filter_high_hz,
        filter_order=filter_order,
        include_spectrogram_matrix=include_spectrogram_matrix,
    )
