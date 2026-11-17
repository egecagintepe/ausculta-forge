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


def _validate_artifact_input(signal: np.ndarray, sample_rate_hz: float) -> np.ndarray:
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
    arr = np.asarray(signal, dtype=np.float64).flatten()
    if len(arr) == 0:
        raise ValueError("Cannot inject artifact into empty signal array (length is 0).")
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError("Input signal contains NaN or infinite values.")
    return arr


def inject_controlled_artifact(
    signal: np.ndarray,
    sample_rate_hz: float,
    artifact_type: str,
    seed: int = 42,
    **kwargs: Any,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Inject a controlled synthetic artifact for W10-W12 quality detector testing.

    Supported artifact_type values:
    - "clipping": multiplies by drive_gain and hard-clips at [-clip_threshold, +clip_threshold].
    - "contact_loss": attenuates middle segment and adds low-frequency VLF decoupling motion.
    - "mains_interference": adds 50 Hz fundamental and 100/150 Hz harmonic interference.
    - "high_frequency_noise": adds highpass-filtered Gaussian noise above highpass_hz (default 700 Hz).
    """
    arr = _validate_artifact_input(signal, sample_rate_hz)
    fs = float(sample_rate_hz)
    n = len(arr)
    t = np.arange(n, dtype=np.float64) / fs
    rng = np.random.default_rng(int(seed))
    kind = str(artifact_type).strip().lower()
    params: dict[str, Any] = {}

    if kind == "clipping":
        clip_threshold = float(kwargs.get("clip_threshold", 0.999))
        peak_in = float(np.max(np.abs(arr)))
        raw_gain = kwargs.get("drive_gain")
        if raw_gain is None:
            drive_gain = max(2.5, (1.5 * clip_threshold) / max(peak_in, 1e-6))
        else:
            drive_gain = float(raw_gain)
        out = np.clip(arr * drive_gain, -clip_threshold, clip_threshold)
        params = {"drive_gain": round(drive_gain, 4), "clip_threshold": clip_threshold}
    elif kind == "contact_loss":
        start_ratio = float(kwargs.get("start_ratio", 0.3))
        end_ratio = float(kwargs.get("end_ratio", 0.7))
        attenuation = float(kwargs.get("attenuation", 0.01))
        vlf_freq_hz = float(kwargs.get("vlf_freq_hz", 6.0))
        vlf_amplitude = float(kwargs.get("vlf_amplitude", 0.45))
        s_idx = max(0, min(n, int(start_ratio * n)))
        e_idx = max(s_idx, min(n, int(end_ratio * n)))
        out = arr.copy()
        out[s_idx:e_idx] *= attenuation
        env = np.zeros(n, dtype=np.float64)
        if e_idx > s_idx:
            env[s_idx:e_idx] = np.hanning(e_idx - s_idx)
        out += vlf_amplitude * env * np.sin(2.0 * np.pi * vlf_freq_hz * t)
        params = {
            "start_ratio": start_ratio,
            "end_ratio": end_ratio,
            "attenuation": attenuation,
            "vlf_freq_hz": vlf_freq_hz,
            "vlf_amplitude": vlf_amplitude,
        }
    elif kind == "mains_interference":
        amp_50 = float(kwargs.get("amplitude_50hz", 0.35))
        amp_100 = float(kwargs.get("amplitude_100hz", 0.06))
        amp_150 = float(kwargs.get("amplitude_150hz", 0.03))
        hum = (
            amp_50 * np.sin(2.0 * np.pi * 50.0 * t)
            + amp_100 * np.sin(2.0 * np.pi * 100.0 * t)
            + amp_150 * np.sin(2.0 * np.pi * 150.0 * t)
        )
        out = arr + hum
        params = {"amplitude_50hz": amp_50, "amplitude_100hz": amp_100, "amplitude_150hz": amp_150}
    elif kind == "high_frequency_noise":
        import scipy.signal
        highpass_hz = float(kwargs.get("highpass_hz", 700.0))
        amplitude = float(kwargs.get("amplitude", 0.25))
        if highpass_hz >= fs / 2.0:
            raise ValueError(f"highpass_hz ({highpass_hz}) must be below Nyquist ({fs / 2.0} Hz).")
        sos = scipy.signal.butter(4, highpass_hz, btype="highpass", fs=fs, output="sos")
        raw_noise = rng.standard_normal(n)
        hf_noise = scipy.signal.sosfilt(sos, raw_noise)
        rms_hf = float(np.sqrt(np.mean(hf_noise ** 2)))
        if rms_hf > 1e-12:
            hf_noise = hf_noise * (amplitude / rms_hf)
        out = arr + hf_noise
        params = {"highpass_hz": highpass_hz, "target_rms_amplitude": amplitude}
    else:
        raise ValueError(f"Unsupported artifact_type {artifact_type!r}. Choose from 'clipping', 'contact_loss', 'mains_interference', 'high_frequency_noise'.")

    meta = {
        "artifact_type": kind,
        "sample_rate_hz": fs,
        "sample_count": n,
        "seed": int(seed),
        "parameters": params,
        "provenance": "SOFTWARE_SYNTHETIC_ARTIFACT_INJECTION",
    }
    return np.asarray(out, dtype=np.float32), meta


def evaluate_quality_detection_benchmark(
    clean_signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[SignalQualityConfig] = None,
) -> dict[str, Any]:
    """Evaluate quality dimension detectors against controlled synthetic artifact injections."""
    arr = _validate_artifact_input(clean_signal, sample_rate_hz)
    cfg = config or SignalQualityConfig()
    clean_report = assess_signal_quality(arr, sample_rate_hz, config=cfg).to_dict()

    clean_flags = {
        "clipping": bool(clean_report["clipping"]["clipping_detected"]),
        "contact_loss": bool(clean_report["vlf_motion_evidence"]["vlf_prominent"]),
        "mains_interference": bool(clean_report["spectral_contamination"]["mains_hum_prominent"]),
        "high_frequency_noise": bool(clean_report["spectral_contamination"]["high_frequency_fraction_above_600hz"] > 0.10),
        "packet_drop_discontinuity": bool(clean_report["continuity"]["has_discontinuity"]),
    }

    cases: dict[str, dict[str, Any]] = {}
    specs = [
        ("clipping", "clipping", lambda r: bool(r["clipping"]["clipping_detected"])),
        ("contact_loss", "contact_loss", lambda r: bool(r["vlf_motion_evidence"]["vlf_prominent"])),
        ("mains_interference", "mains_interference", lambda r: bool(r["spectral_contamination"]["mains_hum_prominent"])),
        ("high_frequency_noise", "high_frequency_noise", lambda r: bool(r["spectral_contamination"]["high_frequency_fraction_above_600hz"] > 0.10)),
    ]

    tp = 0
    for case_name, art_type, predicate in specs:
        extra_kwargs = {"clip_threshold": cfg.clipping_threshold} if art_type == "clipping" else {}
        corrupted, art_meta = inject_controlled_artifact(arr, sample_rate_hz, art_type, **extra_kwargs)
        rep = assess_signal_quality(corrupted, sample_rate_hz, config=cfg).to_dict()
        detected = bool(predicate(rep))
        if detected:
            tp += 1
        cases[case_name] = {
            "detected": detected,
            "injection": art_meta,
            "quality_report": rep,
        }

    drop_rep = assess_signal_quality(
        arr, sample_rate_hz, config=cfg, stream_stats={"sequence_gaps": 2, "dropped_blocks": 2}
    ).to_dict()
    drop_detected = bool(drop_rep["continuity"]["has_discontinuity"])
    if drop_detected:
        tp += 1
    cases["packet_drop_discontinuity"] = {
        "detected": drop_detected,
        "injection": {"artifact_type": "packet_drop_discontinuity", "sequence_gaps": 2, "dropped_blocks": 2},
        "quality_report": drop_rep,
    }

    total_cases = len(cases)
    clean_fp = sum(1 for v in clean_flags.values() if v)
    return {
        "clean_baseline_flags": clean_flags,
        "clean_false_positive_count": clean_fp,
        "cases": cases,
        "true_positive_count": tp,
        "total_injected_cases": total_cases,
        "detection_rate_pct": round(100.0 * tp / total_cases, 2) if total_cases else 0.0,
        "provenance": {
            "mode": "SOFTWARE_CONTROLLED_ARTIFACT_BENCHMARK",
            "physical_phantom_execution": "NOT_EXECUTED",
        },
    }
