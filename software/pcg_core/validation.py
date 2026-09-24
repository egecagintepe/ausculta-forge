"""AuscultaForge — Reference-vs-Capture Signal Validation Module.

Provides hardware-independent quantitative metrics to compare a known reference PCG
signal against a recorded/captured counterpart (e.g. from an acoustic phantom, bench test,
or simulated channel).

Strictly reports objective engineering measurements (delay, cross-correlation, gain ratio,
RMSE, NRMSE, SER, spectral differences, coherence). No clinical diagnoses or subjective labels.
"""

from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
import scipy.signal
from scipy.io import wavfile

from .analysis import compute_spectrogram_data
from .metrics import rms, peak_abs


@dataclass(slots=True)
class ValidationResult:
    """Comprehensive quantitative comparison result between reference and captured PCG signals."""
    reference_name: str
    captured_name: str
    reference_fs: int
    captured_fs: int
    effective_fs: int
    resampled: bool
    overlap_samples: int
    overlap_duration_s: float
    delay_samples: int
    delay_ms: float
    normalized_cross_correlation: float
    gain_ratio_rms: float
    gain_ratio_peak: float
    rmse: float
    normalized_rmse: float
    signal_to_error_ratio_db: float
    reference_dominant_hz: float
    captured_dominant_hz: float
    dominant_frequency_diff_hz: float
    band_energy_ratio_diffs: dict[str, float]
    mean_coherence_pcg_band: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def load_wav_as_float32(path: str | Path) -> Tuple[np.ndarray, int]:
    """Read a WAV file and return mono 1D float32 samples in range [-1.0, 1.0] and sample rate."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"WAV file not found: {file_path}")

    fs, data = wavfile.read(str(file_path))

    # Convert multichannel to mono
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Normalize integer PCM to [-1.0, 1.0]
    if np.issubdtype(data.dtype, np.integer):
        max_val = float(np.iinfo(data.dtype).max)
        samples = (data.astype(np.float32) / max_val)
    elif np.issubdtype(data.dtype, np.floating):
        samples = data.astype(np.float32)
    else:
        raise ValueError(f"Unsupported audio data type: {data.dtype}")

    return samples, int(fs)


def simulate_distorted_capture(
    reference_samples: np.ndarray,
    fs: int,
    delay_ms: float = 0.0,
    gain: float = 1.0,
    noise_std: float = 0.0,
    lowpass_cutoff_hz: Optional[float] = None,
    seed: Optional[int] = 42,
) -> np.ndarray:
    """Produce a deterministic synthetic captured version of a reference signal.
    
    Used strictly for software validation of alignment and metric algorithms before
    physical acoustic phantom hardware is available.
    """
    if len(reference_samples) == 0:
        raise ValueError("reference_samples cannot be empty.")
    if fs <= 0:
        raise ValueError("fs must be positive.")

    out = reference_samples.copy()

    # 1. Apply Gain
    out = out * float(gain)

    # 2. Apply Optional Lowpass Filter
    if lowpass_cutoff_hz is not None:
        nyquist = fs / 2.0
        if 0.0 < lowpass_cutoff_hz < nyquist:
            sos = scipy.signal.butter(4, lowpass_cutoff_hz, btype="low", fs=fs, output="sos")
            out = scipy.signal.sosfilt(sos, out).astype(np.float32)

    # 3. Apply Additive Gaussian Noise
    if noise_std > 0.0:
        rng = np.random.RandomState(seed)
        noise = rng.normal(0.0, noise_std, size=len(out)).astype(np.float32)
        out = out + noise

    # 4. Apply Time Delay (prepend zeros)
    delay_samples = int(round((delay_ms / 1000.0) * fs))
    if delay_samples > 0:
        padding = np.zeros(delay_samples, dtype=np.float32)
        out = np.concatenate([padding, out])
    elif delay_samples < 0:
        # Negative delay (trim start)
        shift = abs(delay_samples)
        out = out[shift:] if shift < len(out) else np.zeros(1, dtype=np.float32)

    return out.astype(np.float32)


def estimate_delay_and_align(
    ref: np.ndarray,
    cap: np.ndarray,
    fs: int,
) -> Tuple[np.ndarray, np.ndarray, int, float]:
    """Estimate relative delay between reference and capture via cross-correlation and align.
    
    Returns:
        (aligned_ref, aligned_cap, delay_samples, delay_ms)
        where delay_samples > 0 indicates captured signal lags behind reference.
    """
    if len(ref) == 0 or len(cap) == 0:
        raise ValueError("Signals must be non-empty for delay estimation.")

    # Cross-correlation: correlate(cap, ref) produces peak at positive lag if cap lags ref
    corr = scipy.signal.correlate(cap, ref, mode="full", method="auto")
    lags = scipy.signal.correlation_lags(len(cap), len(ref), mode="full")

    best_idx = int(np.argmax(corr))
    delay_samples = int(lags[best_idx])
    delay_ms = float((delay_samples / float(fs)) * 1000.0)

    # Align overlapping regions based on estimated delay
    if delay_samples >= 0:
        # cap is delayed: cap[n + delay] corresponds to ref[n]
        ref_start = 0
        cap_start = delay_samples
    else:
        # cap is advanced: cap[n] corresponds to ref[n - delay]
        ref_start = -delay_samples
        cap_start = 0

    overlap_len = min(len(ref) - ref_start, len(cap) - cap_start)
    if overlap_len < 16:
        raise ValueError(
            f"Insufficient signal overlap ({overlap_len} samples) after alignment at delay {delay_samples} samples."
        )

    aligned_ref = ref[ref_start : ref_start + overlap_len]
    aligned_cap = cap[cap_start : cap_start + overlap_len]

    return aligned_ref, aligned_cap, delay_samples, delay_ms


def validate_signals(
    reference: np.ndarray,
    captured: np.ndarray,
    reference_fs: int,
    captured_fs: int,
    reference_name: str = "reference",
    captured_name: str = "captured",
) -> ValidationResult:
    """Compare a reference PCG signal with a captured/replayed signal and compute objective metrics."""
    if len(reference) == 0:
        raise ValueError("Reference signal is empty.")
    if len(captured) == 0:
        raise ValueError("Captured signal is empty.")
    if reference_fs <= 0 or captured_fs <= 0:
        raise ValueError("Sample rates must be positive integers.")

    ref = np.asarray(reference, dtype=np.float32)
    cap = np.asarray(captured, dtype=np.float32)

    # 1. Sample-rate matching with explicit resampling documentation
    resampled = False
    effective_fs = reference_fs

    if reference_fs != captured_fs:
        gcd = math.gcd(reference_fs, captured_fs)
        up = reference_fs // gcd
        down = captured_fs // gcd
        cap = scipy.signal.resample_poly(cap, up, down).astype(np.float32)
        resampled = True

    # 2. Time Alignment
    aligned_ref, aligned_cap, delay_samples, delay_ms = estimate_delay_and_align(
        ref, cap, effective_fs
    )

    n_samples = len(aligned_ref)
    overlap_duration_s = float(n_samples / effective_fs)

    # 3. Amplitude & Gain Relationship
    ref_rms = float(rms(aligned_ref))
    cap_rms = float(rms(aligned_cap))
    gain_ratio_rms = float(cap_rms / (ref_rms + 1e-12))

    ref_pk = float(peak_abs(aligned_ref))
    cap_pk = float(peak_abs(aligned_cap))
    gain_ratio_peak = float(cap_pk / (ref_pk + 1e-12))

    # 4. Normalized Cross-Correlation (Shape Similarity)
    ref_centered = aligned_ref - float(np.mean(aligned_ref))
    cap_centered = aligned_cap - float(np.mean(aligned_cap))
    ref_std = float(np.std(aligned_ref))
    cap_std = float(np.std(aligned_cap))

    if ref_std > 1e-12 and cap_std > 1e-12:
        ncc = float(np.mean(ref_centered * cap_centered) / (ref_std * cap_std))
        ncc = float(np.clip(ncc, -1.0, 1.0))
    else:
        ncc = 1.0 if np.allclose(aligned_ref, aligned_cap) else 0.0

    # 5. Error Metrics (RMSE, Normalized RMSE, SER)
    error = aligned_cap - aligned_ref
    mse = float(np.mean(error ** 2))
    rmse_val = float(np.sqrt(mse))

    nrmse_val = float(rmse_val / (ref_rms + 1e-12))

    ref_energy = float(np.sum(aligned_ref ** 2))
    err_energy = float(np.sum(error ** 2))
    if err_energy <= 1e-15:
        ser_db = 100.0  # Cap perfect reconstruction at 100 dB
    elif ref_energy <= 1e-15:
        ser_db = 0.0
    else:
        ser_db = float(10.0 * np.log10(ref_energy / err_energy))

    # 6. Spectral Comparisons
    ref_spec = compute_spectrogram_data(aligned_ref, fs=effective_fs)
    cap_spec = compute_spectrogram_data(aligned_cap, fs=effective_fs)

    ref_dom = ref_spec.peak_frequency_hz
    cap_dom = cap_spec.peak_frequency_hz
    dom_diff = float(abs(cap_dom - ref_dom))

    band_diffs: dict[str, float] = {}
    for band, r_val in ref_spec.band_energy_ratios.items():
        c_val = cap_spec.band_energy_ratios.get(band, 0.0)
        band_diffs[band] = round(float(abs(c_val - r_val)), 4)

    # 7. Magnitude-Squared Coherence in PCG Passband (20 - 600 Hz)
    nperseg = min(256, n_samples)
    if nperseg >= 32:
        f_coh, cxy = scipy.signal.coherence(
            aligned_ref, aligned_cap, fs=effective_fs, nperseg=nperseg
        )
        pcg_mask = (f_coh >= 20.0) & (f_coh <= 600.0)
        if np.any(pcg_mask):
            mean_coh = float(np.mean(cxy[pcg_mask]))
        else:
            mean_coh = float(np.mean(cxy))
    else:
        mean_coh = 1.0 if np.allclose(aligned_ref, aligned_cap) else 0.0

    return ValidationResult(
        reference_name=str(reference_name),
        captured_name=str(captured_name),
        reference_fs=int(reference_fs),
        captured_fs=int(captured_fs),
        effective_fs=int(effective_fs),
        resampled=bool(resampled),
        overlap_samples=int(n_samples),
        overlap_duration_s=round(overlap_duration_s, 4),
        delay_samples=int(delay_samples),
        delay_ms=round(delay_ms, 3),
        normalized_cross_correlation=round(ncc, 5),
        gain_ratio_rms=round(gain_ratio_rms, 4),
        gain_ratio_peak=round(gain_ratio_peak, 4),
        rmse=round(rmse_val, 6),
        normalized_rmse=round(nrmse_val, 5),
        signal_to_error_ratio_db=round(ser_db, 2),
        reference_dominant_hz=round(ref_dom, 2),
        captured_dominant_hz=round(cap_dom, 2),
        dominant_frequency_diff_hz=round(dom_diff, 2),
        band_energy_ratio_diffs=band_diffs,
        mean_coherence_pcg_band=round(mean_coh, 4),
    )


def validate_wav_files(
    reference_path: str | Path,
    captured_path: str | Path,
) -> ValidationResult:
    """Convenience function to compare two WAV files on disk."""
    ref_path = Path(reference_path)
    cap_path = Path(captured_path)

    ref_samples, ref_fs = load_wav_as_float32(ref_path)
    cap_samples, cap_fs = load_wav_as_float32(cap_path)

    return validate_signals(
        reference=ref_samples,
        captured=cap_samples,
        reference_fs=ref_fs,
        captured_fs=cap_fs,
        reference_name=ref_path.name,
        captured_name=cap_path.name,
    )
