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
    window_ms: float = 25.0,
    overlap_fraction: float = 0.5,
    window_type: str = "hamming",
    mode: str = "reference",
    target_length_50hz: Optional[int] = None,
) -> np.ndarray:
    """Compute short-time PSD band feature aligned with Springer pipeline.
    
    Modes:
    - 'reference' (SPRINGER_PHYSIONET_REFERENCE_V1):
      Reproduces PhysioNet get_PSD_feature_Springer_HMM.m:
      window = Fs / 40 (25 ms at 1000 Hz Fs)
      noverlap = round(Fs / 80) (12 or 13 samples)
      nfft = Fs (1000) yielding 1 Hz frequency grid spacing (1:1:500 Hz)
      mean PSD over 40–60 Hz (mean across frequency bins, NOT sum)
      direct frame sequence resampling to target 50 Hz length.

    - 'paper' (SPRINGER_PAPER_4FEATURE_V1):
      Follows Springer et al. (2016) paper description:
      window = 50 ms Hamming window
      overlap = 50%
      mean PSD over 40–60 Hz
    """
    if len(signal) == 0:
        if target_length_50hz is not None:
            return np.array([], dtype=np.float64)
        return np.array([], dtype=np.float64)

    n_samples = len(signal)
    fs = float(sample_rate_hz)

    if mode == "reference":
        win_len = max(8, int(round(fs / 40.0)))       # 25 samples at 1000 Hz (25 ms)
        noverlap = max(1, int(round(fs / 80.0)))      # 12 samples at 1000 Hz (approx 12.5 ms)
        nfft = max(win_len, int(round(fs)))           # 1000 points -> 1 Hz frequency spacing
    else:  # paper mode
        win_len = max(8, int(round(fs * (window_ms / 1000.0))))  # 50 samples at 1000 Hz (50 ms)
        noverlap = max(1, int(round(win_len * overlap_fraction))) # 25 samples
        nfft = max(win_len, 256)

    # Ensure signal has enough samples for at least one segment
    if len(signal) < win_len:
        if target_length_50hz is not None:
            return np.zeros(target_length_50hz, dtype=np.float64)
        return np.zeros(n_samples, dtype=np.float64)

    # Use scipy.signal.spectrogram with mode='psd' and scaling='density'
    f, t_spec, Sxx = scipy.signal.spectrogram(
        signal,
        fs=fs,
        window=window_type,
        nperseg=win_len,
        noverlap=noverlap,
        nfft=nfft,
        detrend=False,
        scaling="density",
        mode="psd",
    )

    f_low, f_high = band_hz
    band_mask = (f >= f_low) & (f <= f_high)

    if not np.any(band_mask) or Sxx.size == 0:
        band_power_frames = np.zeros(Sxx.shape[1] if Sxx.ndim > 1 else 0, dtype=np.float64)
    else:
        # Both reference code and paper compute MEAN PSD over the 40-60 Hz region
        band_power_frames = np.mean(Sxx[band_mask, :], axis=0)

    # If target 50 Hz length is requested (direct frame-series resampling per reference code)
    if target_length_50hz is not None:
        if len(band_power_frames) < 2:
            val = float(band_power_frames[0]) if len(band_power_frames) > 0 else 0.0
            return np.full(target_length_50hz, val, dtype=np.float64)
        # Resample frame sequence directly to target_length_50hz
        resampled_psd = np.interp(
            np.linspace(0.0, 1.0, target_length_50hz),
            np.linspace(0.0, 1.0, len(band_power_frames)),
            band_power_frames,
        )
        return np.maximum(0.0, np.asarray(resampled_psd, dtype=np.float64))

    # Fallback / continuous 1000 Hz interpolation
    frame_times = t_spec
    full_times = np.arange(n_samples) / fs
    if len(frame_times) < 2:
        val = float(band_power_frames[0]) if len(band_power_frames) > 0 else 0.0
        return np.full(n_samples, val, dtype=np.float64)

    interp_psd = np.interp(full_times, frame_times, band_power_frames)
    return np.maximum(0.0, np.asarray(interp_psd, dtype=np.float64))


def compute_springer_wavelet_feature(
    signal: np.ndarray,
    sample_rate_hz: float = 1000.0,
    wavelet_name: str = "rbio3.9",
    level: int = 3,
) -> np.ndarray:
    """Compute DWT detail envelope matching Springer reference structure.

    Structure:
    - Discrete wavelet decomposition via pywt.wavedec(signal, wavelet_name, level=3).
    - Select level-3 detail coefficients cD3 (at index len(coeffs) - level or index 1).
    - Expand / upsample detail coefficients toward original input length.
    - Absolute value: abs(cD3_expanded).
    - NO Hilbert transform, and NO 8 Hz low-pass filter (per reference getDWT.m).

    Fidelity status:
    SOURCE-STRUCTURAL MATCH / NUMERICAL ORACLE NOT EXECUTED
    """
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    if not HAS_PYWT:
        raise RuntimeError("PyWavelets (pywt) is required to compute the Springer wavelet feature.")

    n_samples = len(signal)
    max_level = pywt.dwt_max_level(n_samples, pywt.Wavelet(wavelet_name))
    actual_level = min(level, max_level)
    if actual_level < 1:
        return np.zeros(n_samples, dtype=np.float64)

    coeffs = pywt.wavedec(signal, wavelet_name, level=actual_level)
    # pywt.wavedec returns [cA_n, cD_n, cD_{n-1}, ..., cD_1]
    # For actual_level, cD_level is at index 1
    detail_idx = 1 if len(coeffs) > 1 else 0
    cd = coeffs[detail_idx]

    # Expand/upsample detail coefficients according to level (2^actual_level)
    upsample_factor = 2 ** actual_level
    upsampled = np.repeat(cd, upsample_factor)

    # Center crop / pad deterministically to original signal length
    if len(upsampled) >= n_samples:
        start_idx = (len(upsampled) - n_samples) // 2
        expanded = upsampled[start_idx : start_idx + n_samples]
    else:
        pad_total = n_samples - len(upsampled)
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        expanded = np.pad(upsampled, (pad_left, pad_right), mode="edge")

    # Reference behavior: absolute value of detail coefficients
    # NO Hilbert envelope, NO 8 Hz low-pass filter
    wav_feature = np.abs(expanded)
    return np.asarray(wav_feature, dtype=np.float64)


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

    # 1. Homomorphic envelope at 1000 Hz & downsample to 50 Hz
    homo_1000 = compute_springer_homomorphic_envelope(
        x,
        sample_rate_hz=fs_analysis,
        lowpass_hz=config.homomorphic_lowpass_hz,
        filter_order=config.homomorphic_filter_order,
    )
    homo_50, _ = resample_analysis_signal(homo_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)
    target_50hz_len = len(homo_50)

    # 2. Hilbert envelope at 1000 Hz & downsample to 50 Hz
    hilb_1000 = compute_springer_hilbert_feature(x)
    hilb_50, _ = resample_analysis_signal(hilb_1000, orig_sample_rate_hz=fs_analysis, target_sample_rate_hz=fs_feature)

    # 3. PSD band feature directly resampled to target 50 Hz length (matching reference code)
    psd_50 = compute_springer_psd_feature(
        x,
        sample_rate_hz=fs_analysis,
        band_hz=config.psd_band_hz,
        window_ms=config.psd_window_ms,
        overlap_fraction=config.psd_overlap_fraction,
        window_type=config.psd_window_type,
        mode=config.psd_mode,
        target_length_50hz=target_50hz_len,
    )
    psd_1000 = np.interp(np.linspace(0.0, 1.0, len(x)), np.linspace(0.0, 1.0, len(psd_50)), psd_50)

    # 4. Wavelet feature at 1000 Hz if enabled & downsample to 50 Hz
    wav_1000: Optional[np.ndarray] = None
    wav_50: Optional[np.ndarray] = None
    if config.include_wavelet:
        wav_1000 = compute_springer_wavelet_feature(
            x,
            sample_rate_hz=fs_analysis,
            wavelet_name=config.wavelet_name,
            level=config.wavelet_level,
        )
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
        "source_fidelity": getattr(config, "source_fidelity", "PHYSIONET_REFERENCE_CODE_DERIVED"),
        "oracle_status": "REFERENCE_ORACLE_NOT_EXECUTED",
        "input_sample_count": len(x),
        "feature_frames_count": min_len,
        "feature_sample_rate_hz": fs_feature,
        "features_extracted": config.feature_names,
        "wavelet_enabled": config.include_wavelet,
        "wavelet_name": config.wavelet_name if config.include_wavelet else None,
        "wavelet_fidelity_status": "SOURCE-STRUCTURAL MATCH / NUMERICAL ORACLE NOT EXECUTED" if config.include_wavelet else "DISABLED",
        "psd_mode": config.psd_mode,
        "psd_band_hz": list(config.psd_band_hz),
        "psd_window_ms": config.psd_window_ms,
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
