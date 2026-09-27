"""AuscultaForge — Schmidt/Springer Heart-Rate & Systolic-Time Estimation.

Implements the deterministic autocorrelation-based cardiac cycle and systolic interval
estimation from Schmidt et al. (2010) and Springer et al. (2016).

Strict Scientific Boundary:
Heart-rate and systolic-time estimations are model hyper-parameters used exclusively
to configure HSMM duration distributions. They are NOT diagnostic measurements.
"""

from __future__ import annotations

import math
from typing import Tuple, Optional, Any
import numpy as np
import scipy.signal

from .springer_features import compute_springer_homomorphic_envelope


def estimate_heart_rate_schmidt(
    envelope: np.ndarray,
    sample_rate_hz: float = 1000.0,
    min_bpm: float = 30.0,
    max_bpm: float = 120.0,
) -> Tuple[float, float]:
    """Estimate cardiac cycle duration and heart rate from envelope autocorrelation.
    
    Parameters
    ----------
    envelope : np.ndarray
        1D envelope sequence (typically homomorphic envelope at 1000 Hz).
    sample_rate_hz : float
        Sampling frequency of the envelope in Hertz (default: 1000 Hz).
    min_bpm : float
        Lower search boundary in beats per minute (default: 30 BPM -> 2.0 s lag).
    max_bpm : float
        Upper search boundary in beats per minute (default: 120 BPM -> 0.5 s lag).
        
    Returns
    -------
    Tuple[float, float]
        (heart_rate_bpm, cycle_duration_s)
        
    Raises
    ------
    ValueError
        If signal is too short, silent, or no meaningful autocorrelation peak exists.
    """
    if len(envelope) == 0:
        raise ValueError("Cannot estimate heart rate from empty envelope sequence.")

    fs = float(sample_rate_hz)
    duration_s = len(envelope) / fs

    # Minimum duration check: at least 2.0 seconds needed to observe one complete 30-BPM cycle
    min_required_s = 60.0 / min_bpm
    if duration_s < min_required_s:
        raise ValueError(
            f"Recording duration ({duration_s:.2f} s) is too short for heart-rate estimation "
            f"(minimum {min_required_s:.2f} s required for {min_bpm} BPM)."
        )

    # Demean envelope
    env = np.asarray(envelope, dtype=np.float64)
    env_mean = np.mean(env)
    env_centered = env - env_mean

    energy = np.sum(env_centered ** 2)
    if energy < 1e-12:
        raise ValueError("Envelope signal is silent or constant; cannot estimate heart rate.")

    # Compute unbiased / normalized autocorrelation
    # Using FFT for O(N log N) efficiency
    n = len(env_centered)
    n_fft = 2 ** int(math.ceil(math.log2(2 * n - 1)))
    fft_val = np.fft.rfft(env_centered, n=n_fft)
    autocorr = np.fft.irfft(fft_val * np.conj(fft_val), n=n_fft)[:n]
    autocorr = autocorr / autocorr[0]  # Normalize zero-lag to 1.0

    # Define lag index range [tau_min, tau_max]
    lag_min_s = 60.0 / max_bpm  # 0.5 s for 120 BPM
    lag_max_s = 60.0 / min_bpm  # 2.0 s for 30 BPM

    idx_min = int(round(lag_min_s * fs))
    idx_max = min(n - 1, int(round(lag_max_s * fs)))

    if idx_min >= idx_max:
        raise ValueError("Invalid lag search range for specified BPM bounds.")

    search_region = autocorr[idx_min:idx_max + 1]

    # Source-faithful Springer/Schmidt reference behavior: argmax in [500ms, 2000ms]
    best_peak_rel = int(np.argmax(search_region))
    if search_region[best_peak_rel] <= 0.0:
        raise ValueError("No positive autocorrelation peak found in heart-rate search band.")

    best_lag_samples = idx_min + best_peak_rel
    cycle_duration_s = float(best_lag_samples) / fs
    heart_rate_bpm = 60.0 / cycle_duration_s

    return heart_rate_bpm, cycle_duration_s


def estimate_systolic_interval(
    envelope: np.ndarray,
    cycle_duration_s: float,
    sample_rate_hz: float = 1000.0,
) -> float:
    """Estimate systolic time interval (S1-to-S2 time) from envelope autocorrelation.
    
    Source-faithful reference behavior:
    Search autocorrelation between 200 ms and half the estimated heart-cycle duration
    and choose the maximum autocorrelation value (argmax).

    No arbitrary 0.45s cap, no 0.38 fallback, no undocumented physiological fallback.
    If valid search region cannot be formed or no positive peak exists, raises ValueError.
    """
    if len(envelope) == 0:
        raise ValueError("Cannot estimate systolic interval from empty envelope.")

    fs = float(sample_rate_hz)
    env_centered = envelope - np.mean(envelope)
    n = len(env_centered)

    # Search window: between 200 ms and half the cardiac cycle (0.50 * cycle_duration_s)
    min_sys_s = 0.20
    max_sys_s = 0.50 * cycle_duration_s

    if min_sys_s >= max_sys_s:
        raise ValueError(
            f"Invalid systolic search region: min={min_sys_s}s, max={max_sys_s}s (cycle={cycle_duration_s}s)."
        )

    idx_min = int(round(min_sys_s * fs))
    idx_max = int(round(max_sys_s * fs))

    if idx_min >= idx_max or idx_max >= n:
        raise ValueError(
            f"Systolic search indices [{idx_min}, {idx_max}] exceed envelope length ({n})."
        )

    n_fft = 2 ** int(math.ceil(math.log2(2 * n - 1)))
    fft_val = np.fft.rfft(env_centered, n=n_fft)
    autocorr = np.fft.irfft(fft_val * np.conj(fft_val), n=n_fft)[:n]
    if autocorr[0] > 1e-12:
        autocorr = autocorr / autocorr[0]

    search_region = autocorr[idx_min:idx_max + 1]
    if len(search_region) == 0:
        raise ValueError("Empty systolic autocorrelation search region.")

    best_rel = int(np.argmax(search_region))
    if search_region[best_rel] <= 0.0:
        raise ValueError("No positive autocorrelation peak found in systolic interval search region.")

    systolic_time_s = float(idx_min + best_rel) / fs
    return systolic_time_s


def run_cardiac_timing_estimation(
    preprocessed_signal_1000hz: np.ndarray,
    sample_rate_hz: float = 1000.0,
) -> dict[str, Any]:
    """Execute complete cardiac cycle and systolic interval estimation.
    
    Returns
    -------
    dict[str, Any]
        Dictionary with heart_rate_bpm, cycle_duration_s, systolic_interval_s, and status.
    """
    try:
        homo_env = compute_springer_homomorphic_envelope(preprocessed_signal_1000hz, sample_rate_hz=sample_rate_hz)
        bpm, cycle_s = estimate_heart_rate_schmidt(homo_env, sample_rate_hz=sample_rate_hz)
        sys_s = estimate_systolic_interval(homo_env, cycle_duration_s=cycle_s, sample_rate_hz=sample_rate_hz)

        return {
            "heart_rate_bpm": round(bpm, 2),
            "cycle_duration_s": round(cycle_s, 4),
            "systolic_interval_s": round(sys_s, 4),
            "is_valid": True,
            "error": None,
        }
    except Exception as e:
        return {
            "heart_rate_bpm": None,
            "cycle_duration_s": None,
            "systolic_interval_s": None,
            "is_valid": False,
            "error": str(e),
        }
