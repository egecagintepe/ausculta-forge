"""AuscultaForge — Springer Segmentation Preprocessing & Schmidt Spike Removal.

Implements the offline research preprocessing path:
1. Anti-aliased rational resampling to 1000 Hz analysis rate
2. 25–400 Hz 2nd-order Butterworth zero-phase bandpass filtering
3. Schmidt spike removal (iterative 500 ms window median thresholding)

Deterministic guards:
- Max iteration limits on spike removal
- Zero-crossing boundary protection
- Silent / flat signal safe return
- Short recording handling
"""

from __future__ import annotations

import math
from typing import Tuple, Any
import numpy as np
import scipy.signal

from ..scientific.spectral import resample_analysis_signal
from .springer_config import SpringerProfileConfig


def prepare_springer_analysis_signal(
    signal: np.ndarray,
    sample_rate_hz: float,
    target_fs: float = 1000.0,
) -> Tuple[np.ndarray, bool]:
    """Convert input sequence to the 1000 Hz Springer analysis representation.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio array.
    sample_rate_hz : float
        Current sampling frequency in Hertz.
    target_fs : float
        Target Springer analysis rate (default: 1000.0 Hz).
        
    Returns
    -------
    Tuple[np.ndarray, bool]
        (resampled_signal_1000hz, was_resampled)
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")

    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim != 1:
        signal = signal.flatten()

    if len(signal) == 0:
        return np.array([], dtype=np.float64), False

    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Input signal contains NaN or infinite values.")

    if float(sample_rate_hz) == float(target_fs):
        return signal.copy(), False

    resampled, _ = resample_analysis_signal(
        signal,
        orig_sample_rate_hz=float(sample_rate_hz),
        target_sample_rate_hz=float(target_fs),
    )
    return resampled, True


def apply_springer_bandpass_filter(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    low_hz: float = 25.0,
    high_hz: float = 400.0,
    order: int = 2,
) -> np.ndarray:
    """Apply zero-phase Butterworth bandpass filter for Springer segmentation.
    
    Design order: 2 (effective order 4 after forward-backward filtfilt).
    Band: 25–400 Hz at 1000 Hz fs.
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    nyq = 0.5 * sample_rate_hz
    low = max(0.001, low_hz / nyq)
    high = min(0.999, high_hz / nyq)

    if low >= high:
        raise ValueError(f"Invalid bandpass cutoffs: low={low_hz} Hz, high={high_hz} Hz at fs={sample_rate_hz} Hz")

    b, a = scipy.signal.butter(order, [low, high], btype="bandpass")

    # Adapt padlen for short recordings to prevent filtfilt crash
    min_pad = 3 * max(len(a), len(b))
    if len(signal) <= min_pad:
        padlen = max(1, len(signal) - 1)
    else:
        padlen = min_pad

    filtered = scipy.signal.filtfilt(b, a, signal, padlen=padlen)
    return np.asarray(filtered, dtype=np.float64)


def remove_schmidt_spikes(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    window_ms: float = 500.0,
    threshold_multiplier: float = 3.0,
    max_iterations: int = 50,
) -> Tuple[np.ndarray, int]:
    """Iteratively remove non-cardiac artifact spikes using the Schmidt/Springer algorithm.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio array at analysis rate.
    sample_rate_hz : float
        Sampling frequency in Hertz (typically 1000 Hz).
    window_ms : float
        Window duration for local maximum evaluation (default: 500 ms).
    threshold_multiplier : float
        Spike threshold multiplier relative to median window maximum (default: 3.0).
    max_iterations : int
        Maximum removal iterations to prevent infinite loop (default: 50).
        
    Returns
    -------
    Tuple[np.ndarray, int]
        (cleaned_signal, spike_count)
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64), 0

    x = signal.copy()
    n_samples = len(x)
    window_samples = max(4, int(round(sample_rate_hz * (window_ms / 1000.0))))

    # Short signal guard: fewer than 2 full windows cannot compute meaningful median
    if n_samples < 2 * window_samples:
        return x, 0

    spike_count = 0
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Calculate maximum absolute amplitude in each window
        n_windows = int(math.ceil(n_samples / window_samples))
        window_maxima = np.zeros(n_windows, dtype=np.float64)
        for w in range(n_windows):
            start = w * window_samples
            end = min(n_samples, start + window_samples)
            if start < end:
                window_maxima[w] = np.max(np.abs(x[start:end]))

        median_max = float(np.median(window_maxima))
        # Silence/flat signal guard
        if median_max < 1e-12:
            break

        spike_threshold = threshold_multiplier * median_max
        max_val = float(np.max(window_maxima))

        if max_val <= spike_threshold:
            # All window maxima within threshold; convergence reached
            break

        # Identify window with largest maximum
        largest_w = int(np.argmax(window_maxima))
        w_start = largest_w * window_samples
        w_end = min(n_samples, w_start + window_samples)

        # Locate spike peak within that window
        spike_local_idx = int(np.argmax(np.abs(x[w_start:w_end])))
        spike_global_idx = w_start + spike_local_idx

        # Find nearest preceding zero crossing
        left_bound = spike_global_idx
        while left_bound > 0:
            if (x[left_bound] * x[left_bound - 1] <= 0.0) or (left_bound < w_start - window_samples):
                break
            left_bound -= 1

        # Find nearest following zero crossing
        right_bound = spike_global_idx
        while right_bound < n_samples - 1:
            if (x[right_bound] * x[right_bound + 1] <= 0.0) or (right_bound > w_end + window_samples):
                break
            right_bound += 1

        # Zero out the spike interval
        x[left_bound:right_bound + 1] = 0.0
        spike_count += 1

    return x, spike_count


def run_springer_preprocessing(
    signal: np.ndarray,
    sample_rate_hz: float,
    config: SpringerProfileConfig,
) -> Tuple[np.ndarray, dict[str, Any]]:
    """Execute the configured Springer preprocessing pipeline.
    
    Returns
    -------
    Tuple[np.ndarray, dict[str, Any]]
        (preprocessed_1000hz_signal, metadata)
    """
    # 1. Resample to 1000 Hz analysis rate
    x_1000, was_resampled = prepare_springer_analysis_signal(
        signal,
        sample_rate_hz=sample_rate_hz,
        target_fs=config.analysis_sample_rate_hz,
    )

    metadata: dict[str, Any] = {
        "original_sample_rate_hz": float(sample_rate_hz),
        "analysis_sample_rate_hz": float(config.analysis_sample_rate_hz),
        "was_resampled": was_resampled,
        "bandpass_applied": False,
        "spike_removal_applied": False,
        "spikes_removed_count": 0,
    }

    # 2. Bandpass filtering if configured
    if config.apply_bandpass_25_400:
        x_1000 = apply_springer_bandpass_filter(
            x_1000,
            sample_rate_hz=config.analysis_sample_rate_hz,
            low_hz=config.bandpass_low_hz,
            high_hz=config.bandpass_high_hz,
            order=config.bandpass_order,
        )
        metadata["bandpass_applied"] = True
        metadata["bandpass_range_hz"] = [config.bandpass_low_hz, config.bandpass_high_hz]
        metadata["bandpass_order"] = config.bandpass_order

    # 3. Schmidt spike removal if configured
    if config.apply_spike_removal:
        x_1000, spikes_removed = remove_schmidt_spikes(
            x_1000,
            sample_rate_hz=config.analysis_sample_rate_hz,
            window_ms=config.spike_window_ms,
            threshold_multiplier=config.spike_threshold_multiplier,
            max_iterations=config.spike_max_iterations,
        )
        metadata["spike_removal_applied"] = True
        metadata["spikes_removed_count"] = spikes_removed

    return x_1000, metadata
