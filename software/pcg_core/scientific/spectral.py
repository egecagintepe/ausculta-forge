"""AuscultaForge — Scientific Spectral Engine & Analysis Resampling.

Implements deterministic Welch Power Spectral Density estimation and rational multirate resampling.

Metrological Conventions:
1. PSD Scaling & Units:
   When scaling='density', PSD units are normalized_amplitude^2 / Hz (Dimensionless FS^2 / Hz).
   Relative logarithmic values are referenced explicitly to relative_db_ref (1.0 FS^2/Hz default).
2. Frequency-Bin Spacing vs. Physical Resolving Power:
   Delta_f = fs / N_fft defines the discrete grid spacing. Applying zero-padding (N_fft > nperseg)
   produces denser frequency samples via DTFT interpolation, but does NOT create new physical resolving information.
3. Analysis Resampling:
   Explicit, non-mutating polyphase rational rate conversion using scipy.signal.resample_poly.
"""

from __future__ import annotations

import fractions
from typing import Optional, Tuple
import numpy as np
import scipy.signal

from .models import WelchConfig, SpectralAnalysisResult


def compute_welch_psd(
    signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[WelchConfig] = None,
) -> SpectralAnalysisResult:
    """Compute Welch Power Spectral Density on full-rate analysis sequences.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio sequence.
    sample_rate_hz : float
        Sampling frequency in Hertz (must be > 0).
    config : Optional[WelchConfig]
        Welch estimation parameters (nperseg, noverlap, nfft, window, detrend, scaling).
        
    Returns
    -------
    SpectralAnalysisResult
        Frequencies, PSD, relative dB, bin spacing, segment count, and ENBW.
        
    Raises
    ------
    ValueError
        If signal is empty, contains NaN/Inf, or sample_rate_hz <= 0.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
        
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
        
    if signal.ndim != 1:
        signal = signal.flatten()
        
    if len(signal) == 0:
        raise ValueError("Cannot compute spectrum on empty signal array.")
        
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute valid PSD.")

    cfg = config or WelchConfig()
    n_samples = len(signal)
    
    nperseg = min(cfg.nperseg, n_samples)
    if nperseg < 4:
        raise ValueError(f"Signal length ({n_samples}) is too short for spectral estimation (minimum 4 samples required).")
        
    noverlap = cfg.noverlap if cfg.noverlap is not None else (nperseg // 2)
    if noverlap >= nperseg:
        noverlap = nperseg // 2
        
    nfft = cfg.nfft if cfg.nfft is not None else nperseg
    if nfft < nperseg:
        nfft = nperseg

    # Compute Welch PSD via SciPy
    f, psd = scipy.signal.welch(
        signal,
        fs=float(sample_rate_hz),
        window=cfg.window,
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        detrend=cfg.detrend,
        scaling=cfg.scaling,
    )

    # Frequency bin spacing Delta_f = fs / N_fft
    bin_spacing = float(sample_rate_hz) / float(nfft)
    
    # Actual Welch segment count
    step = nperseg - noverlap
    actual_segments = max(1, (n_samples - noverlap) // step) if step > 0 else 1

    # Equivalent Noise Bandwidth (ENBW) from window coefficients
    try:
        win = scipy.signal.get_window(cfg.window, nperseg, fftbins=True)
        s1 = float(np.sum(win))
        s2 = float(np.sum(win ** 2))
        enbw_hz = float(sample_rate_hz) * (s2 / (s1 ** 2)) if s1 != 0.0 else bin_spacing
    except Exception:
        enbw_hz = bin_spacing * 1.50  # Fallback approximation for standard Hann-like window

    # Explicit relative dB calculation
    ref_val = max(1e-20, float(cfg.relative_db_ref))
    psd_safe = np.maximum(psd, 1e-25)
    psd_rel_db = 10.0 * np.log10(psd_safe / ref_val)

    provenance = {
        "analysis_type": "welch_psd",
        "sample_rate_hz": float(sample_rate_hz),
        "input_sample_count": n_samples,
        "nperseg": nperseg,
        "noverlap": noverlap,
        "nfft": nfft,
        "window": cfg.window,
        "detrend": cfg.detrend,
        "scaling": cfg.scaling,
        "psd_units": "normalized_amplitude^2/Hz" if cfg.scaling == "density" else "normalized_amplitude^2",
        "relative_db_reference": ref_val,
        "bin_spacing_note": "Delta_f = fs / N_fft defines discrete sampling interval, not physical resolving power",
    }

    return SpectralAnalysisResult(
        schema_version="1.0.0",
        sample_rate_hz=float(sample_rate_hz),
        frequencies_hz=[float(x) for x in f],
        psd=[float(x) for x in psd],
        psd_relative_db=[float(x) for x in psd_rel_db],
        frequency_bin_spacing_hz=bin_spacing,
        actual_segments=actual_segments,
        enbw_hz=enbw_hz,
        config=cfg.to_dict(),
        provenance=provenance,
    )


def resample_analysis_signal(
    signal: np.ndarray,
    orig_sample_rate_hz: float,
    target_sample_rate_hz: float,
) -> Tuple[np.ndarray, float]:
    """Scientifically resample an analysis sequence using polyphase rational filtering.
    
    Guarantees:
    - Caller must explicitly invoke this helper; no silent decimation.
    - Original array is NOT mutated.
    - Anti-aliasing filter applied automatically inside resample_poly.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio array.
    orig_sample_rate_hz : float
        Current sampling frequency in Hertz.
    target_sample_rate_hz : float
        Requested target sampling frequency in Hertz.
        
    Returns
    -------
    Tuple[np.ndarray, float]
        (resampled_array, target_sample_rate_hz)
    """
    if orig_sample_rate_hz <= 0 or target_sample_rate_hz <= 0:
        raise ValueError("Sampling frequencies must be strictly positive.")
        
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
        
    if signal.ndim != 1:
        signal = signal.flatten()
        
    if len(signal) == 0:
        return np.array([], dtype=np.float64), float(target_sample_rate_hz)
        
    if float(orig_sample_rate_hz) == float(target_sample_rate_hz):
        return signal.copy(), float(orig_sample_rate_hz)

    # Compute minimal integer rational ratio up / down
    ratio = fractions.Fraction(target_sample_rate_hz / orig_sample_rate_hz).limit_denominator(1000)
    up = ratio.numerator
    down = ratio.denominator

    # Polyphase anti-aliased resampling
    resampled = scipy.signal.resample_poly(signal, up, down)
    return np.asarray(resampled, dtype=np.float64), float(target_sample_rate_hz)
