"""AuscultaForge — Springer Multi-Feature Extraction & Normalization.

Implements the Stage-B feature extraction pipeline:
1. Homomorphic Envelope (Hilbert analytic magnitude -> log -> 8 Hz zero-phase lowpass -> exp)
2. Hilbert Envelope (analytic signal magnitude)
3. Short-Time PSD Band Feature (Paper mode vs PhysioNet Reference mode)
4. Wavelet Envelope (rbio3.9 level-3 detail reconstruction + analytic envelope)
5. Anti-aliased rational resampling from 1000 Hz to 50 Hz HSMM observation rate
6. Per-recording z-score normalization with constant-feature degeneracy guards
"""

from __future__ import annotations

import math
from typing import Tuple, Optional, Any
import numpy as np
import scipy.signal

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False

from ..scientific.spectral import resample_analysis_signal
from .models import SpringerFeatureResult
from .springer_config import SpringerProfileConfig


def compute_springer_homomorphic_envelope(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    lowpass_hz: float = 8.0,
    filter_order: int = 1,
) -> np.ndarray:
    """Compute the Springer/Schmidt research homomorphic envelope.
    
    Pipeline:
    1. Analytical signal z(t) = hilbert(x)
    2. Magnitude m(t) = |z(t)|
    3. Log envelope: l(t) = log(max(m(t), epsilon))
    4. Zero-phase 1st-order Butterworth low-pass filter at 8 Hz
    5. Exponentiation: env(t) = exp(l_filtered(t))
    
    Guarantees:
    - Finite, non-negative, no NaN or Inf
    - Strictly non-mutating
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)

    # 1 & 2. Analytic signal magnitude
    analytic = scipy.signal.hilbert(signal)
    mag = np.abs(analytic)

    # 3. Logarithm with float64 precision floor
    eps = 1e-12
    log_mag = np.log(np.maximum(mag, eps))

    # 4. Low-pass filter (1st-order Butterworth design, zero-phase filtfilt)
    nyq = 0.5 * sample_rate_hz
    cutoff = min(0.999, max(0.001, lowpass_hz / nyq))
    b, a = scipy.signal.butter(filter_order, cutoff, btype="low")

    min_pad = 3 * max(len(a), len(b))
    padlen = min_pad if len(signal) > min_pad else max(1, len(signal) - 1)
    filtered_log = scipy.signal.filtfilt(b, a, log_mag, padlen=padlen)

    # 5. Exponentiation
    # Clamp filtered_log before exp to avoid overflow (+700 in float64 is ~1e304)
    clamped_log = np.clip(filtered_log, -50.0, 50.0)
    homomorphic = np.exp(clamped_log)

    return np.asarray(homomorphic, dtype=np.float64)


def compute_springer_hilbert_feature(signal: np.ndarray) -> np.ndarray:
    """Compute the instantaneous amplitude feature via Hilbert transform: |hilbert(x)|."""
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)

    analytic = scipy.signal.hilbert(signal)
    return np.asarray(np.abs(analytic), dtype=np.float64)


def compute_springer_psd_feature(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    band_hz: Tuple[float, float] = (40.0, 60.0),
    window_ms: float = 50.0,
    overlap_fraction: float = 0.5,
    window_type: str = "hamming",
    mode: str = "reference",
) -> np.ndarray:
    """Compute the short-time PSD band feature aligned with the 1000 Hz analysis signal.
    
    Modes:
    - 'reference': PhysioNet reference implementation conventions (sum of band spectrogram power).
    - 'paper': Springer et al. (2016) paper conventions (mean normalized PSD spectral density).
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    n_samples = len(signal)
    win_len = max(8, int(round(sample_rate_hz * (window_ms / 1000.0))))
    hop_len = max(1, int(round(win_len * (1.0 - overlap_fraction))))

    # STFT via SciPy
    f, t_stft, Zxx = scipy.signal.stft(
        signal,
        fs=sample_rate_hz,
        window=window_type,
        nperseg=win_len,
        noverlap=win_len - hop_len,
        detrend=False,
        boundary="zeros",
        padded=True,
    )

    power = np.abs(Zxx) ** 2
    f_low, f_high = band_hz
    band_mask = (f >= f_low) & (f <= f_high)

    if not np.any(band_mask):
        band_power_frames = np.zeros(power.shape[1], dtype=np.float64)
    else:
        if mode == "paper":
            # Paper mode: mean PSD density across frequency bins
            band_power_frames = np.mean(power[band_mask, :], axis=0)
        else:
            # Reference mode: total integrated band power
            band_power_frames = np.sum(power[band_mask, :], axis=0)

    # Interpolate frame values back to the full 1000 Hz continuous time grid
    frame_times = t_stft
    full_times = np.arange(n_samples) / float(sample_rate_hz)

    if len(frame_times) < 2:
        return np.full(n_samples, float(band_power_frames[0]) if len(band_power_frames) > 0 else 0.0)

    interp_psd = np.interp(full_times, frame_times, band_power_frames)
    return np.maximum(0.0, np.asarray(interp_psd, dtype=np.float64))


def compute_springer_wavelet_feature(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    wavelet_name: str = "rbio3.9",
    level: int = 3,
) -> np.ndarray:
    """Compute the level-3 wavelet detail envelope aligned with the 1000 Hz analysis signal.
    
    Decomposes signal using discrete wavelet transform, isolates level-3 detail coefficients,
    reconstructs the detail sequence at 1000 Hz, and extracts instantaneous magnitude.
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    if not HAS_PYWT:
        raise RuntimeError("PyWavelets (pywt) is required to compute the Springer wavelet feature.")

    n_samples = len(signal)

    # Check maximum valid decomposition level for signal length
    max_level = pywt.dwt_max_level(n_samples, pywt.Wavelet(wavelet_name))
    actual_level = min(level, max_level)
    if actual_level < 1:
        return np.zeros(n_samples, dtype=np.float64)

    # Decompose
    coeffs = pywt.wavedec(signal, wavelet_name, level=actual_level)

    # Isolate detail coefficients at requested level (index -actual_level)
    zeroed_coeffs = [np.zeros_like(c) for c in coeffs]
    detail_idx = len(coeffs) - actual_level
    zeroed_coeffs[detail_idx] = coeffs[detail_idx]

    # Reconstruct isolated detail signal at 1000 Hz
    d_rec = pywt.waverec(zeroed_coeffs, wavelet_name)
    d_rec = d_rec[:n_samples]

    # Instantaneous magnitude envelope via Hilbert transform
    analytic_d = scipy.signal.hilbert(d_rec)
    env = np.abs(analytic_d)

    return np.asarray(env, dtype=np.float64)


def normalize_features_per_recording(
    feature_matrix: np.ndarray,
) -> Tuple[np.ndarray, dict[str, Any]]:
    """Per-recording, per-feature z-score normalization: z = (x - mean) / std.
    
    Guarantees:
    - Protects against division by zero for constant/degenerate features
    - Returns finite normalized matrix and explicit variance metadata
    """
    if feature_matrix.size == 0:
        return feature_matrix.copy(), {}

    norm_matrix = np.zeros_like(feature_matrix, dtype=np.float64)
    n_features = feature_matrix.shape[1]
    metadata: dict[str, Any] = {
        "means": [],
        "stds": [],
        "degenerate_features": [],
    }

    for col in range(n_features):
        feat = feature_matrix[:, col]
        mean_val = float(np.mean(feat))
        std_val = float(np.std(feat))
        metadata["means"].append(mean_val)
        metadata["stds"].append(std_val)

        if std_val < 1e-12:
            norm_matrix[:, col] = 0.0
            metadata["degenerate_features"].append(col)
        else:
            norm_matrix[:, col] = (feat - mean_val) / std_val

    return norm_matrix, metadata


def extract_springer_features(
    preprocessed_signal_1000hz: np.ndarray,
    config: SpringerProfileConfig,
    original_fs: float = 4000.0,
) -> SpringerFeatureResult:
    """Extract, downsample to 50 Hz, and normalize the Springer observation feature stream.
    
    Parameters
    ----------
    preprocessed_signal_1000hz : np.ndarray
        Audio signal preprocessed at 1000 Hz.
    config : SpringerProfileConfig
        Pipeline profile configuration.
    original_fs : float
        Original acquisition sampling frequency in Hertz.
        
    Returns
    -------
    SpringerFeatureResult
        Complete versioned 50 Hz feature result.
    """
    x = preprocessed_signal_1000hz
    fs_analysis = float(config.analysis_sample_rate_hz)  # 1000.0
    fs_feature = float(config.feature_sample_rate_hz)    # 50.0

    if len(x) == 0:
        return SpringerFeatureResult(
            profile_id=config.profile_id,
            original_sample_rate_hz=float(original_fs),
            analysis_sample_rate_hz=fs_analysis,
            feature_sample_rate_hz=fs_feature,
        )

    # 1. Homomorphic envelope at 1000 Hz
    homo_1000 = compute_springer_homomorphic_envelope(
        x,
        sample_rate_hz=fs_analysis,
        lowpass_hz=config.homomorphic_lowpass_hz,
        filter_order=config.homomorphic_filter_order,
    )

    # 2. Hilbert envelope at 1000 Hz
    hilb_1000 = compute_springer_hilbert_feature(x)

    # 3. PSD band feature at 1000 Hz
    psd_1000 = compute_springer_psd_feature(
        x,
        sample_rate_hz=fs_analysis,
        band_hz=config.psd_band_hz,
        window_ms=config.psd_window_ms,
        overlap_fraction=config.psd_overlap_fraction,
        window_type=config.psd_window_type,
        mode=config.psd_mode,
    )

    # 4. Wavelet feature at 1000 Hz if enabled
    wav_1000: Optional[np.ndarray] = None
    if config.include_wavelet:
        wav_1000 = compute_springer_wavelet_feature(
            x,
            sample_rate_hz=fs_analysis,
            wavelet_name=config.wavelet_name,
            level=config.wavelet_level,
        )

    # 5. Downsample all features from 1000 Hz to 50 Hz using rational polyphase resampling
    homo_50, _ = resample_analysis_signal(homo_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)
    hilb_50, _ = resample_analysis_signal(hilb_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)
    psd_50, _ = resample_analysis_signal(psd_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)

    wav_50: Optional[np.ndarray] = None
    if wav_1000 is not None:
        wav_50, _ = resample_analysis_signal(wav_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)

    # Harmonize lengths across features
    lengths = [len(homo_50), len(hilb_50), len(psd_50)]
    if wav_50 is not None:
        lengths.append(len(wav_50))
    min_len = min(lengths)

    homo_50 = homo_50[:min_len]
    hilb_50 = hilb_50[:min_len]
    psd_50 = psd_50[:min_len]
    if wav_50 is not None:
        wav_50 = wav_50[:min_len]

    # Build raw feature matrix
    cols = [homo_50, hilb_50, psd_50]
    if wav_50 is not None:
        cols.append(wav_50)
    raw_matrix = np.column_stack(cols)

    # 6. Per-recording z-score normalization
    norm_matrix, norm_meta = normalize_features_per_recording(raw_matrix)

    norm_homo = norm_matrix[:, 0]
    norm_hilb = norm_matrix[:, 1]
    norm_psd = norm_matrix[:, 2]
    norm_wav = norm_matrix[:, 3] if wav_50 is not None else None

    time_s = [float(t) for t in np.arange(min_len) / fs_feature]

    provenance = {
        "analysis_type": "springer_feature_extraction",
        "profile_id": config.profile_id,
        "input_sample_count": len(x),
        "feature_frames_count": min_len,
        "feature_sample_rate_hz": fs_feature,
        "features_extracted": config.feature_names,
        "wavelet_enabled": config.include_wavelet,
        "wavelet_name": config.wavelet_name if config.include_wavelet else None,
        "psd_mode": config.psd_mode,
        "psd_band_hz": list(config.psd_band_hz),
    }

    return SpringerFeatureResult(
        schema_version="1.0.0",
        profile_id=config.profile_id,
        original_sample_rate_hz=float(original_fs),
        analysis_sample_rate_hz=fs_analysis,
        feature_sample_rate_hz=fs_feature,
        time_s=time_s,
        homomorphic=[float(v) for v in norm_homo],
        hilbert=[float(v) for v in norm_hilb],
        psd=[float(v) for v in norm_psd],
        wavelet=[float(v) for v in norm_wav] if norm_wav is not None else None,
        feature_matrix=[[float(x) for x in row] for row in norm_matrix],
        normalization_metadata=norm_meta,
        preprocessing_metadata={},
        provenance=provenance,
    )
