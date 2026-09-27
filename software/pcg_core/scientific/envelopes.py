"""AuscultaForge — Envelope Lab & Deterministic PCG Feature Methods.

Implements Stage-A deterministic envelope extraction algorithms:
1. Analytical Signal Magnitude (Hilbert Transform Envelope)
2. Moving RMS Energy Envelope
3. Discrete Teager-Kaiser Energy Operator (TKEO)
4. Short-Time Power Spectral Density (PSD) Band Envelope (Springer 40–60 Hz research feature)
5. Homomorphic Envelope (Interface declared; algorithmic execution deferred to Stage-B pending literature parameterization)

Metrological & Diagnostic Boundaries:
- Envelopes are mathematical acoustic energy descriptors, NOT diagnostic classifications.
- TKEO is an experimental nonlinear feature comparator, NOT an authoritative S1/S2 or pathology detector.
- The 40–60 Hz PSD envelope is a specific Springer et al. (2016) research configuration, NOT a universal medical standard.
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np
import scipy.signal

from .models import EnvelopeLabConfig, EnvelopeSeries, EnvelopeLabResult


def compute_hilbert_envelope(signal: np.ndarray) -> np.ndarray:
    """Compute the analytical signal magnitude envelope via Hilbert transform.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point signal sequence.
        
    Returns
    -------
    np.ndarray
        Instantaneous amplitude envelope |x(t) + j * H{x(t)}|.
    """
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if len(signal) == 0:
        return np.array([], dtype=np.float64)
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute Hilbert envelope.")
        
    analytic = scipy.signal.hilbert(signal)
    return np.abs(analytic)


def compute_moving_rms_envelope(
    signal: np.ndarray,
    sample_rate_hz: float,
    window_duration_s: float = 0.02,
) -> np.ndarray:
    """Compute the running root-mean-square (RMS) energy envelope.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point signal sequence.
    sample_rate_hz : float
        Sampling frequency in Hertz.
    window_duration_s : float
        Analysis window duration in seconds (default: 0.02 s = 20 ms).
        
    Returns
    -------
    np.ndarray
        Moving RMS envelope of identical length to the input signal.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if len(signal) == 0:
        return np.array([], dtype=np.float64)
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute RMS envelope.")

    window_len = max(1, int(round(window_duration_s * sample_rate_hz)))
    if window_len == 1:
        return np.abs(signal)

    # Boxcar sliding mean of squared sequence using convolution with 'same' boundary mode
    kernel = np.ones(window_len, dtype=np.float64) / float(window_len)
    mean_sq = scipy.signal.convolve(signal ** 2, kernel, mode="same")
    # Clip any tiny negative values caused by numerical round-off
    mean_sq = np.maximum(mean_sq, 0.0)
    return np.sqrt(mean_sq)


def compute_tkeo(
    signal: np.ndarray,
    boundary_policy: str = "replicate",
) -> np.ndarray:
    """Compute the discrete Teager-Kaiser Energy Operator (TKEO).
    
    Mathematical Formulation:
        Psi[x[n]] = x[n]^2 - x[n-1] * x[n+1]   for 1 <= n <= N - 2
        
    Theoretical Frequency Dependency:
        For a pure sinusoid x[n] = A * cos(omega_0 * n + phi),
        Psi[x[n]] = A^2 * sin^2(omega_0)
        For low discrete frequencies (omega_0 << 1), sin(omega_0) ~ omega_0,
        yielding Psi ~ A^2 * omega_0^2 (instantaneous energy proportional to amplitude^2 * frequency^2).
        
    Boundary Policies:
        - 'replicate': Psi[0] = Psi[1], Psi[N-1] = Psi[N-2]
        - 'zero': Psi[0] = 0.0, Psi[N-1] = 0.0
        
    Diagnostic Caveat:
        TKEO is an experimental feature comparator. A high TKEO peak indicates rapid energy/frequency
        transients, but is NOT definitive proof of S1, S2, or cardiovascular pathology.
    """
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    if n == 0:
        return np.array([], dtype=np.float64)
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute TKEO.")

    tkeo = np.zeros(n, dtype=np.float64)
    if n < 3:
        return tkeo

    # Vectorized core evaluation: n = 1 to n = N-2
    tkeo[1:-1] = signal[1:-1] ** 2 - signal[:-2] * signal[2:]

    # Boundary handling
    if boundary_policy == "replicate":
        tkeo[0] = tkeo[1]
        tkeo[-1] = tkeo[-2]
    elif boundary_policy == "zero":
        tkeo[0] = 0.0
        tkeo[-1] = 0.0
    else:
        raise ValueError(f"Unknown boundary_policy {boundary_policy!r}. Choose 'replicate' or 'zero'.")

    return tkeo


def compute_psd_band_envelope(
    signal: np.ndarray,
    sample_rate_hz: float,
    band_hz: Tuple[float, float] = (40.0, 60.0),
    window_duration_s: float = 0.05,
    overlap_fraction: float = 0.5,
    window_type: str = "hamming",
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute the short-time PSD band-power envelope.
    
    Supports the Springer et al. (2016) research profile:
    - Band: 40–60 Hz
    - Window duration: 50 ms
    - Overlap: 50%
    - Window: Hamming
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio array.
    sample_rate_hz : float
        Sampling frequency in Hertz.
    band_hz : Tuple[float, float]
        Lower and upper frequency integration limits [f_low, f_high] in Hertz.
    window_duration_s : float
        Analysis window duration in seconds (default: 0.05 s = 50 ms).
    overlap_fraction : float
        Fraction of overlap between consecutive frames (default: 0.5 = 50%).
    window_type : str
        Window function name (default: 'hamming').
        
    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (time_s, envelope_values)
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if len(signal) == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute PSD-band envelope.")

    f_low, f_high = band_hz
    if f_low < 0 or f_high <= f_low:
        raise ValueError(f"Invalid band_hz limits: {band_hz}. Require 0 <= f_low < f_high.")

    nperseg = max(4, int(round(window_duration_s * sample_rate_hz)))
    noverlap = int(round(nperseg * overlap_fraction))
    if noverlap >= nperseg:
        noverlap = nperseg // 2
    step = nperseg - noverlap

    n_samples = len(signal)
    if n_samples < nperseg:
        # Pad with zeros if recording is shorter than a single window
        padded = np.zeros(nperseg, dtype=np.float64)
        padded[:n_samples] = signal
        signal = padded
        n_samples = nperseg

    n_frames = (n_samples - noverlap) // step
    if n_frames < 1:
        n_frames = 1

    win = scipy.signal.get_window(window_type, nperseg, fftbins=True)
    # Window noise power normalization factor S2
    s2 = float(np.sum(win ** 2))
    if s2 == 0.0:
        s2 = 1.0

    freqs = np.fft.rfftfreq(nperseg, d=1.0 / sample_rate_hz)
    in_band = (freqs >= f_low) & (freqs <= f_high)
    df = sample_rate_hz / nperseg

    env_vals = np.zeros(n_frames, dtype=np.float64)
    time_s = np.zeros(n_frames, dtype=np.float64)

    for i in range(n_frames):
        start = i * step
        segment = signal[start : start + nperseg]
        time_s[i] = (start + nperseg / 2.0) / sample_rate_hz
        
        # Detrend constant (remove DC offset)
        seg_detrend = segment - np.mean(segment)
        windowed = seg_detrend * win
        fft_vals = np.fft.rfft(windowed)
        # One-sided PSD density in FS^2/Hz
        psd = (2.0 / (sample_rate_hz * s2)) * (np.abs(fft_vals) ** 2)
        psd[0] /= 2.0  # DC bin is not doubled
        if nperseg % 2 == 0 and len(psd) == len(freqs):
            psd[-1] /= 2.0  # Nyquist bin is not doubled

        # Mean PSD across the band in FS^2/Hz
        if np.any(in_band):
            env_vals[i] = float(np.mean(psd[in_band]))
        else:
            # Nearest bin if band is narrower than a single FFT bin
            idx = np.argmin(np.abs(freqs - (f_low + f_high) / 2.0))
            env_vals[i] = float(psd[idx])

    return time_s, env_vals


def compute_envelope_lab(
    signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[EnvelopeLabConfig] = None,
) -> EnvelopeLabResult:
    """Run Stage-A deterministic envelope extraction suite.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio array.
    sample_rate_hz : float
        Sampling frequency in Hertz.
    config : Optional[EnvelopeLabConfig]
        Configuration specifying window lengths, boundary modes, and band limits.
        
    Returns
    -------
    EnvelopeLabResult
        Multi-envelope result collection with per-envelope time axes and parameters.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim != 1:
        signal = signal.flatten()
    if len(signal) == 0:
        raise ValueError("Cannot compute envelopes on empty signal array.")

    cfg = config or EnvelopeLabConfig()
    n_samples = len(signal)
    duration_s = float(n_samples) / float(sample_rate_hz)
    native_time_s = np.linspace(0.0, duration_s, n_samples, endpoint=False, dtype=np.float64)

    # 1. Hilbert Envelope
    hilbert_vals = compute_hilbert_envelope(signal)
    hilbert_series = EnvelopeSeries(
        algorithm="hilbert",
        sample_rate_hz=float(sample_rate_hz),
        time_s=[float(t) for t in native_time_s],
        values=[float(v) for v in hilbert_vals],
        parameters={"analytic_signal": True},
        input_sample_count=n_samples,
        output_sample_count=len(hilbert_vals),
        provenance={"literature": "R001, R006"},
    )

    # 2. Moving RMS Envelope
    rms_vals = compute_moving_rms_envelope(signal, sample_rate_hz, cfg.rms_window_duration_s)
    rms_series = EnvelopeSeries(
        algorithm="moving_rms",
        sample_rate_hz=float(sample_rate_hz),
        time_s=[float(t) for t in native_time_s],
        values=[float(v) for v in rms_vals],
        parameters={"window_duration_s": cfg.rms_window_duration_s},
        input_sample_count=n_samples,
        output_sample_count=len(rms_vals),
        provenance={"literature": "R001"},
    )

    # 3. Teager-Kaiser Energy Operator (TKEO)
    tkeo_vals = compute_tkeo(signal, cfg.tkeo_boundary_policy)
    tkeo_series = EnvelopeSeries(
        algorithm="tkeo",
        sample_rate_hz=float(sample_rate_hz),
        time_s=[float(t) for t in native_time_s],
        values=[float(v) for v in tkeo_vals],
        parameters={"boundary_policy": cfg.tkeo_boundary_policy, "model": "Psi[x[n]] = x[n]^2 - x[n-1]*x[n+1]"},
        input_sample_count=n_samples,
        output_sample_count=len(tkeo_vals),
        provenance={"note": "Experimental nonlinear comparator; NOT S1/S2 truth or clinical detector"},
    )

    # 4. Short-Time PSD Band Envelope (Springer 40–60 Hz research feature)
    psd_time_s, psd_band_vals = compute_psd_band_envelope(
        signal,
        sample_rate_hz,
        band_hz=cfg.psd_band_hz,
        window_duration_s=cfg.psd_window_duration_s,
        overlap_fraction=cfg.psd_overlap_fraction,
        window_type=cfg.psd_window_type,
    )
    effective_psd_fs = float(len(psd_band_vals)) / duration_s if duration_s > 0 else 0.0
    psd_series = EnvelopeSeries(
        algorithm="psd_band",
        sample_rate_hz=round(effective_psd_fs, 2),
        time_s=[float(t) for t in psd_time_s],
        values=[float(v) for v in psd_band_vals],
        parameters={
            "band_hz": list(cfg.psd_band_hz),
            "window_duration_s": cfg.psd_window_duration_s,
            "overlap_fraction": cfg.psd_overlap_fraction,
            "window_type": cfg.psd_window_type,
            "profile_behavior": cfg.profile_behavior,
        },
        input_sample_count=n_samples,
        output_sample_count=len(psd_band_vals),
        provenance={
            "literature": "R006 (Springer et al. 2016) feature parameterization",
            "scope": "Generic 40-60 Hz PSD-band comparator (not full Springer pipeline)",
            "profile": cfg.profile_behavior,
        },
    )

    envelopes = {
        "hilbert": hilbert_series,
        "moving_rms": rms_series,
        "tkeo": tkeo_series,
        "psd_band": psd_series,
    }

    provenance = {
        "module": "pcg_core.scientific.envelopes",
        "input_sample_rate_hz": float(sample_rate_hz),
        "homomorphic_status": cfg.homomorphic_status,
        "homomorphic_note": "Homomorphic envelope deferred to Stage-B pending verified primary-source parameterization (R005/R006).",
    }

    return EnvelopeLabResult(
        schema_version="1.0.0",
        input_sample_rate_hz=float(sample_rate_hz),
        input_duration_s=duration_s,
        envelopes=envelopes,
        provenance=provenance,
    )
