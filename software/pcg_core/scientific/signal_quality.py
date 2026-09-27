"""AuscultaForge — Scientific Signal Quality Characterization.

Implements deterministic scalar signal characterization on full-rate analysis sequences.

Critical Metrological Distinctions:
1. Digital Saturation / Full-Scale Hits != Physical Acoustic Overload:
   Samples near +/-1.0 indicate digital full-scale utilization in normalized float representation.
   Physical microphone overload cannot be inferred from normalized digital audio alone without
   a verified acoustic calibration chain and transducer AOP (Acoustic Overload Point) documentation.
2. Zero-Crossing Rate (ZCR):
   A generic statistical waveform metric. It is NOT a reliable heart-sound quality classifier or S1/S2 detector.
3. No Composite "Quality Score":
   Arbitrary composite numbers (e.g. 85/100) mask distinct physical failure modes (DC drift, clipping, drops).
"""

from __future__ import annotations

import math
from typing import Optional
import numpy as np

from .models import SignalQualityConfig, SignalCharacterizationResult


def compute_signal_quality(
    signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[SignalQualityConfig] = None,
) -> SignalCharacterizationResult:
    """Compute deterministic signal quality metrics on full-rate analysis arrays.
    
    Parameters
    ----------
    signal : np.ndarray
        1D floating-point audio sequence (normalized [-1.0, +1.0] expected for full-scale stats).
    sample_rate_hz : float
        Sampling frequency in Hertz (must be > 0).
    config : Optional[SignalQualityConfig]
        Configuration specifying clipping threshold and optional metrics.
        
    Returns
    -------
    SignalCharacterizationResult
        Deterministic scalar metrics with provenance.
        
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
        raise ValueError("Cannot characterize empty signal array (length is 0).")
        
    if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
        raise ValueError("Signal contains NaN or infinite values; cannot compute valid scientific metrics.")

    cfg = config or SignalQualityConfig()
    sample_count = len(signal)
    duration_s = float(sample_count) / float(sample_rate_hz)
    
    mean_dc = float(np.mean(signal))
    rms_val = float(np.sqrt(np.mean(signal ** 2)))
    peak_abs = float(np.max(np.abs(signal)))
    peak_to_peak = float(np.ptp(signal))
    
    crest_factor = float(peak_abs / rms_val) if rms_val > 1e-12 else 0.0
    digital_fs_util = float(peak_abs / 1.0)
    
    threshold = float(cfg.clipping_threshold)
    sat_mask = np.abs(signal) >= threshold
    sat_count = int(np.sum(sat_mask))
    sat_fraction = float(sat_count) / float(sample_count)
    
    zcr: Optional[float] = None
    if cfg.compute_zcr:
        if sample_count > 1:
            # Computed on mean-centered AC signal to prevent DC bias from suppressing true crossings
            centered = signal - mean_dc
            # Count sign changes
            crossings = np.sum(centered[:-1] * centered[1:] < 0)
            zcr = float(crossings) / float(sample_count - 1)
        else:
            zcr = 0.0

    provenance = {
        "analysis_type": "signal_quality",
        "sample_rate_hz": float(sample_rate_hz),
        "clipping_threshold": threshold,
        "clipping_definition": "digital_full_scale_hits_only_not_acoustic_overload",
    }
    if zcr is not None:
        provenance["zcr_metrology_note"] = (
            "Generic waveform statistic; NOT a reliable heart-sound quality or pathology classifier."
        )

    return SignalCharacterizationResult(
        schema_version="1.0.0",
        sample_count=sample_count,
        duration_s=duration_s,
        sample_rate_hz=float(sample_rate_hz),
        mean_dc=mean_dc,
        rms=rms_val,
        peak_absolute=peak_abs,
        peak_to_peak=peak_to_peak,
        crest_factor=crest_factor,
        digital_full_scale_utilization=digital_fs_util,
        digital_saturation_count=sat_count,
        digital_saturation_fraction=sat_fraction,
        zero_crossing_rate=zcr,
        provenance=provenance,
    )
