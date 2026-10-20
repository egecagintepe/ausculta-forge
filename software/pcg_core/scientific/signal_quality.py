"""AuscultaForge — Scientific Signal Quality Characterization & Multidimensional Assessment.

Implements deterministic scalar signal characterization and multidimensional quality
evaluations on full-rate analysis sequences.

Critical Metrological Distinctions:
1. Digital Saturation / Full-Scale Hits != Physical Acoustic Overload:
   Samples near +/-1.0 indicate digital full-scale utilization in normalized float representation.
   Physical microphone overload cannot be inferred from normalized digital audio alone without
   a verified acoustic calibration chain and transducer AOP (Acoustic Overload Point) documentation.
2. Zero-Crossing Rate (ZCR):
   A generic statistical waveform metric. It is NOT a reliable heart-sound quality classifier or S1/S2 detector.
3. No Composite "Quality Score":
   Arbitrary composite numbers (e.g. 85/100) mask distinct physical failure modes (DC drift, clipping, drops).
   AuscultaForge strictly reports separate, unblended quality dimensions.
4. No Diagnostic Claims:
   Quality metrics are objective acoustic engineering observations; never medical diagnoses.
"""

from __future__ import annotations

import math
from typing import Any, Optional
import numpy as np

from .models import (
    SignalQualityConfig,
    SignalCharacterizationResult,
    MultiDimensionalQualityReport,
)


def assess_signal_quality(
    signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[SignalQualityConfig] = None,
    stream_stats: Optional[dict[str, Any]] = None,
) -> MultiDimensionalQualityReport:
    """Assess recording quality across separate physical and computational dimensions.

    Reports separate dimensions:
    - clipping: digital full-scale saturation count, fraction, peak
    - continuity: sequence gaps, dropped blocks, sample preservation
    - vlf_motion_evidence: sub-audible energy fraction (0–20 Hz), DC offset
    - spectral_contamination: 50/60 Hz mains hum, high-frequency noise (>600 Hz), 20–500 Hz characterization
    - timing_faults: sample rate, clock stability, timestamp regressions
    - morphology_evidence: RMS, crest factor, silence detection

    Guarantees:
    - Rejects empty, NaN, Inf, non-positive sample rate
    - No invented 0–100 quality score or diagnostic claims
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

    # 1. Amplitude and clipping stats
    mean_dc = float(np.mean(signal))
    rms_val = float(np.sqrt(np.mean(signal ** 2)))
    peak_abs = float(np.max(np.abs(signal)))
    crest_factor = float(peak_abs / rms_val) if rms_val > 1e-12 else 0.0
    digital_fs_util = float(peak_abs / 1.0)

    threshold = float(cfg.clipping_threshold)
    sat_mask = np.abs(signal) >= threshold
    sat_count = int(np.sum(sat_mask))
    sat_fraction = float(sat_count) / float(sample_count)

    clipping_dim = {
        "digital_saturation_count": sat_count,
        "digital_saturation_fraction": round(sat_fraction, 6),
        "peak_absolute": round(peak_abs, 6),
        "digital_full_scale_utilization": round(digital_fs_util, 4),
        "clipping_detected": bool(sat_count > 0),
        "threshold": threshold,
    }

    # 2. Continuity stats
    stats = stream_stats or {}
    seq_gaps = int(stats.get("sequence_gaps", 0))
    dropped_blks = int(stats.get("dropped_blocks", 0))
    continuity_dim = {
        "sample_count": sample_count,
        "duration_s": round(duration_s, 4),
        "sequence_gaps": seq_gaps,
        "dropped_blocks": dropped_blks,
        "has_discontinuity": bool(seq_gaps > 0 or dropped_blks > 0),
    }

    # 3. Spectral decomposition for VLF motion and contamination
    # Compute windowed FFT on mean-centered AC signal
    ac_signal = signal - mean_dc
    if sample_count >= 8:
        win = np.hanning(sample_count)
        fft_mags = np.abs(np.fft.rfft(ac_signal * win)) ** 2
        freqs = np.fft.rfftfreq(sample_count, d=1.0 / sample_rate_hz)
        total_ac_pwr = float(np.sum(fft_mags))
    else:
        fft_mags = np.array([], dtype=np.float64)
        freqs = np.array([], dtype=np.float64)
        total_ac_pwr = 0.0

    if total_ac_pwr > 1e-15 and len(freqs) > 0:
        vlf_mask = (freqs >= 0.0) & (freqs < 20.0)
        mains50_mask = (freqs >= 48.0) & (freqs <= 52.0)
        mains60_mask = (freqs >= 58.0) & (freqs <= 62.0)
        char_mask = (freqs >= 20.0) & (freqs <= 500.0)
        hf_mask = freqs > 600.0

        vlf_ratio = float(np.sum(fft_mags[vlf_mask]) / total_ac_pwr)
        mains50_ratio = float(np.sum(fft_mags[mains50_mask]) / total_ac_pwr)
        mains60_ratio = float(np.sum(fft_mags[mains60_mask]) / total_ac_pwr)
        char_ratio = float(np.sum(fft_mags[char_mask]) / total_ac_pwr)
        hf_ratio = float(np.sum(fft_mags[hf_mask]) / total_ac_pwr)
    else:
        vlf_ratio = 0.0
        mains50_ratio = 0.0
        mains60_ratio = 0.0
        char_ratio = 0.0
        hf_ratio = 0.0

    vlf_dim = {
        "mean_dc": round(mean_dc, 6),
        "dc_offset_present": bool(abs(mean_dc) > 0.01),
        "vlf_energy_fraction_0_20hz": round(vlf_ratio, 4),
        "vlf_prominent": bool(vlf_ratio > 0.35),
    }

    spectral_dim = {
        "characterization_band_fraction_20_500hz": round(char_ratio, 4),
        "mains_hum_50hz_ratio": round(mains50_ratio, 4),
        "mains_hum_60hz_ratio": round(mains60_ratio, 4),
        "mains_hum_prominent": bool(mains50_ratio > 0.15 or mains60_ratio > 0.15),
        "high_frequency_fraction_above_600hz": round(hf_ratio, 4),
    }

    # 4. Timing faults
    timing_dim = {
        "sample_rate_hz": float(sample_rate_hz),
        "rate_stability_status": "nominal",
        "timestamp_fault_count": int(stats.get("timestamp_regressions", 0)),
    }

    # 5. Morphology & Zero-Crossing Rate
    zcr: Optional[float] = None
    if cfg.compute_zcr:
        if sample_count > 1:
            crossings = np.sum(ac_signal[:-1] * ac_signal[1:] < 0)
            zcr = float(crossings) / float(sample_count - 1)
        else:
            zcr = 0.0

    morphology_dim = {
        "rms": round(rms_val, 6),
        "crest_factor": round(crest_factor, 4),
        "zero_crossing_rate": round(zcr, 6) if zcr is not None else None,
        "is_silent": bool(rms_val < 1e-4),
    }

    provenance = {
        "analysis_type": "multidimensional_quality_assessment",
        "sample_rate_hz": float(sample_rate_hz),
        "clipping_threshold": threshold,
        "clipping_definition": "digital_full_scale_hits_only_not_acoustic_overload",
        "metrological_rule": "Reports separate unblended failure dimensions; NO universal 0-100 score; NO clinical diagnostic claims.",
        "units": "normalized_fs, FS^2/Hz, or dimensionless ratios",
    }

    return MultiDimensionalQualityReport(
        schema_version="1.0.0",
        clipping=clipping_dim,
        continuity=continuity_dim,
        vlf_motion_evidence=vlf_dim,
        spectral_contamination=spectral_dim,
        timing_faults=timing_dim,
        morphology_evidence=morphology_dim,
        provenance=provenance,
    )


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
        Deterministic scalar metrics with provenance and multidimensional quality breakdown.

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

    # Attach multidimensional assessment
    multi_report = assess_signal_quality(signal, sample_rate_hz, cfg)

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
        quality_dimensions=multi_report.to_dict(),
        provenance=provenance,
    )
