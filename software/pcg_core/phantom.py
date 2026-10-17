"""AuscultaForge — Acoustic Phantom Validation & Reproducible System Identification Engine.

Orchestrates characterization of the physical and virtual acoustic phantom pipeline:
    PC audio output -> PAM8403 amplifier -> 12-ohm exciter -> silicone phantom ->
    chestpiece -> INMP441 microphone -> ESP32-S3 -> PC host.

Engineering Responsibilities:
1. Reusable phantom experiment templates for Kaan's laboratory measurements.
2. Robust reference-versus-capture alignment, cross-correlation, and visual overlays.
3. Separation of playback pipeline delay, acoustic propagation lag, and end-to-end latency.
4. Classical SISO H1 frequency response and magnitude-squared coherence evaluation.
5. Detection of missing synchronization, clipping, and insufficient excitation coverage.
6. Metrological honesty: uncalibrated relative transfers only, non-flat acoustic transducer disclaimers,
   and explicit 'PENDING' status for unverified physical hardware states.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple
import uuid

import numpy as np
import scipy.signal

from .metrics import rms, peak_abs, crest_factor
from .scientific.models import SystemIdConfig, SystemIdentificationResult
from .scientific.system_id import estimate_siso_system_id
from .stimulus import StimulusRecord, generate_100hz_sine, generate_multitone, generate_log_sweep, generate_impulse_train


@dataclass(slots=True)
class PhantomTemplate:
    """Standardized configuration template for an acoustic phantom trial."""
    template_id: str
    name: str
    description: str
    stimulus_type: str
    target_frequency_band_hz: list[float]
    default_output_gain_dbfs: float
    recommended_duration_s: float
    checklist: list[str]
    expected_excitation_bandwidth_hz: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Catalog of standard phantom experiment templates for Kaan's setup
STANDARD_PHANTOM_TEMPLATES: dict[str, PhantomTemplate] = {
    "PHANTOM_SINE_100HZ_V1": PhantomTemplate(
        template_id="PHANTOM_SINE_100HZ_V1",
        name="100 Hz Single-Frequency Characterization",
        description="Narrowband 100 Hz calibration tone to verify fundamental acoustic coupling, gain scaling, and phase lag.",
        stimulus_type="sine_100hz",
        target_frequency_band_hz=[20.0, 500.0],
        default_output_gain_dbfs=-6.0,
        recommended_duration_s=5.0,
        checklist=[
            "Verify PAM8403 amplifier is powered (5V USB/bench supply).",
            "Ensure 12-ohm exciter is seated against silicone phantom surface with acoustic coupling gel.",
            "Verify chestpiece diaphragm is firmly coupled to phantom opposite face.",
            "Confirm INMP441 microphone is aligned and sealed in chestpiece acoustic chamber.",
            "Set PC output volume to calibrated unity level (0 dB attenuation).",
        ],
        expected_excitation_bandwidth_hz=[95.0, 105.0],
    ),
    "PHANTOM_MULTITONE_PCG_V1": PhantomTemplate(
        template_id="PHANTOM_MULTITONE_PCG_V1",
        name="Cardiac Passband Schroeder Multitone",
        description="Multi-frequency excitation (50, 100, 150, 200, 250, 300, 350, 400 Hz) with Schroeder phase optimization for low crest factor.",
        stimulus_type="multitone",
        target_frequency_band_hz=[20.0, 500.0],
        default_output_gain_dbfs=-6.0,
        recommended_duration_s=5.0,
        checklist=[
            "Check for thermal stability of PAM8403 under multi-frequency drive.",
            "Verify silicone phantom temperature and acoustic gel coverage.",
            "Ensure chestpiece contact pressure is maintained without air gaps.",
            "Check for digital clipping indicators on ESP32-S3 stream.",
        ],
        expected_excitation_bandwidth_hz=[25.0, 420.0],
    ),
    "PHANTOM_LOG_SWEEP_20_500HZ_V1": PhantomTemplate(
        template_id="PHANTOM_LOG_SWEEP_20_500HZ_V1",
        name="Logarithmic Sine Sweep (20–500 Hz Mandatory Band)",
        description="Continuous 20–500 Hz logarithmic sweep providing equal energy per fractional octave for broadband SISO H1 and coherence.",
        stimulus_type="log_sweep",
        target_frequency_band_hz=[20.0, 500.0],
        default_output_gain_dbfs=-6.0,
        recommended_duration_s=5.0,
        checklist=[
            "Confirm audio output DAC supports unclipped playback down to 20 Hz.",
            "Check exciter mechanical resonance behavior near 150–250 Hz.",
            "Ensure chestpiece mechanical clamp does not transmit structural vibrations directly around phantom.",
            "Trigger recording on ESP32-S3 host acquisition workstation before playing sweep.",
        ],
        expected_excitation_bandwidth_hz=[20.0, 500.0],
    ),
    "PHANTOM_IMPULSE_TRAIN_V1": PhantomTemplate(
        template_id="PHANTOM_IMPULSE_TRAIN_V1",
        name="Periodic Impulse Train (1 Hz Pulse)",
        description="Discrete pulses spaced 1 second apart to evaluate acoustic propagation time-of-flight, group delay, and impulse response.",
        stimulus_type="impulse_train",
        target_frequency_band_hz=[20.0, 500.0],
        default_output_gain_dbfs=-6.0,
        recommended_duration_s=5.0,
        checklist=[
            "Check that exciter displacement does not bottom out on peak impulse voltage.",
            "Observe acoustic reverberation time in silicone phantom medium.",
            "Verify silence between impulses remains below -40 dBFS noise floor.",
        ],
        expected_excitation_bandwidth_hz=[20.0, 500.0],
    ),
    "PHANTOM_PCG_REPLAY_V1": PhantomTemplate(
        template_id="PHANTOM_PCG_REPLAY_V1",
        name="Clinical PCG Reference Replay",
        description="Acoustic replay of authentic recorded or synthetic heart sound through the phantom chain to evaluate morphological fidelity.",
        stimulus_type="reference_pcg_wav",
        target_frequency_band_hz=[20.0, 500.0],
        default_output_gain_dbfs=-6.0,
        recommended_duration_s=10.0,
        checklist=[
            "Select reference PCG WAV asset with confirmed S1/S2 heart sound morphology.",
            "Check that low-frequency S1 fundamental (30–60 Hz) is audible and transmits through silicone.",
            "Verify absence of mechanical rattling or loose chestpiece artifacts.",
        ],
        expected_excitation_bandwidth_hz=[20.0, 500.0],
    ),
}


@dataclass(slots=True)
class LatencyDecomposition:
    """Decomposition of software, driver, acoustic, and hardware latency."""
    estimated_acoustic_lag_ms: float
    playback_pipeline_buffer_delay_ms: float
    total_end_to_end_latency_estimate_ms: float
    delay_samples: int
    effective_sample_rate_hz: int
    is_hardware_synchronized: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PhantomAlignmentResult:
    """Quantitative alignment and signal integrity evaluation between stimulus and capture."""
    sync_status: str  # "SYNCHRONIZED", "MARGINAL_SYNC", "SYNC_FAILED"
    normalized_cross_correlation: float
    estimated_delay_samples: int
    estimated_delay_ms: float
    overlap_samples: int
    overlap_duration_s: float
    least_squares_gain: float
    rms_gain_ratio: float
    peak_gain_ratio: float
    rmse: float
    normalized_rmse: float
    signal_to_error_ratio_db: float
    reference_clipping: dict[str, Any]
    capture_clipping: dict[str, Any]
    excitation_coverage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PhantomExperimentRecord:
    """Complete reproducible phantom characterization record."""
    schema_version: str
    trial_id: str
    template_id: str
    created_at_utc: str
    intended_device: str
    intended_chain: str
    hardware_status: str  # "PENDING_PHYSICAL_MEASUREMENT", "SIMULATED_BENCH_TEST", "PHYSICAL_VERIFIED"
    output_gain_dbfs: float
    operator_notes: str
    stimulus: dict[str, Any]
    capture: dict[str, Any]
    latency: LatencyDecomposition
    alignment: PhantomAlignmentResult
    system_id: dict[str, Any]
    display: dict[str, Any]
    metrological_disclaimer: str
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def detect_clipping(signal: np.ndarray, threshold: float = 0.999) -> dict[str, Any]:
    """Inspect signal for digital saturation clipping events and duration."""
    sig_abs = np.abs(np.asarray(signal, dtype=np.float32))
    clipped_mask = sig_abs >= threshold
    clipped_samples = int(np.sum(clipped_mask))
    total_samples = len(sig_abs)
    clipped_fraction = float(clipped_samples / total_samples) if total_samples > 0 else 0.0

    # Count contiguous clipping events
    events = 0
    in_event = False
    for val in clipped_mask:
        if val and not in_event:
            events += 1
            in_event = True
        elif not val:
            in_event = False

    return {
        "clipped_samples_count": clipped_samples,
        "clipped_fraction": round(clipped_fraction, 6),
        "clipped_events_count": events,
        "clipping_detected": bool(clipped_samples > 0),
        "threshold": threshold,
    }


def estimate_phantom_alignment(
    reference: np.ndarray,
    captured: np.ndarray,
    sample_rate_hz: int,
    pipeline_buffer_delay_ms: float = 30.0,
    target_band_hz: tuple[float, float] = (20.0, 500.0),
) -> Tuple[np.ndarray, np.ndarray, PhantomAlignmentResult, LatencyDecomposition]:
    """Align reference stimulus and captured response via cross-correlation and evaluate latency.
    
    Returns:
        (aligned_ref, aligned_cap, alignment_result, latency_decomposition)
    """
    if len(reference) == 0 or len(captured) == 0:
        raise ValueError("Reference and capture signals must be non-empty.")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")

    ref = np.asarray(reference, dtype=np.float32)
    cap = np.asarray(captured, dtype=np.float32)

    # Cross-correlation: correlate(cap, ref) produces peak at positive lag if cap lags ref
    corr = scipy.signal.correlate(cap, ref, mode="full", method="auto")
    lags = scipy.signal.correlation_lags(len(cap), len(ref), mode="full")

    best_idx = int(np.argmax(corr))
    max_corr = float(corr[best_idx])
    delay_samples = int(lags[best_idx])
    delay_ms = float((delay_samples / float(sample_rate_hz)) * 1000.0)

    # Slice overlapping segments based on estimated delay
    if delay_samples >= 0:
        ref_start = 0
        cap_start = delay_samples
    else:
        ref_start = -delay_samples
        cap_start = 0

    overlap_len = min(len(ref) - ref_start, len(cap) - cap_start)
    if overlap_len < 16:
        # Fallback to direct truncation if overlap is insufficient
        overlap_len = min(len(ref), len(cap))
        aligned_ref = ref[:overlap_len]
        aligned_cap = cap[:overlap_len]
        delay_samples = 0
        delay_ms = 0.0
    else:
        aligned_ref = ref[ref_start : ref_start + overlap_len]
        aligned_cap = cap[cap_start : cap_start + overlap_len]

    overlap_dur_s = float(len(aligned_ref) / sample_rate_hz)

    # Normalized Cross-Correlation (NCC) over aligned region
    ref_cent = aligned_ref - float(np.mean(aligned_ref))
    cap_cent = aligned_cap - float(np.mean(aligned_cap))
    ref_std = float(np.std(aligned_ref))
    cap_std = float(np.std(aligned_cap))

    if ref_std > 1e-12 and cap_std > 1e-12:
        ncc = float(np.mean(ref_cent * cap_cent) / (ref_std * cap_std))
        ncc = float(np.clip(ncc, -1.0, 1.0))
    else:
        ncc = 1.0 if np.allclose(aligned_ref, aligned_cap) else 0.0

    # Determine synchronization classification
    if ncc >= 0.35:
        sync_status = "SYNCHRONIZED"
    elif ncc >= 0.15:
        sync_status = "MARGINAL_SYNC"
    else:
        sync_status = "SYNC_FAILED"

    # Amplitude scaling metrics
    ref_rms = float(rms(aligned_ref))
    cap_rms = float(rms(aligned_cap))
    rms_ratio = float(cap_rms / (ref_rms + 1e-12))
    ref_pk = float(peak_abs(aligned_ref))
    cap_pk = float(peak_abs(aligned_cap))
    pk_ratio = float(cap_pk / (ref_pk + 1e-12))

    ref_energy = float(np.dot(aligned_ref, aligned_ref))
    ls_gain = float(np.dot(aligned_ref, aligned_cap) / ref_energy) if ref_energy > 1e-15 else 0.0

    # Error metrics
    err = aligned_cap - aligned_ref
    rmse_val = float(np.sqrt(np.mean(err ** 2)))
    nrmse_val = float(rmse_val / (ref_rms + 1e-12))
    err_energy = float(np.sum(err ** 2))
    if err_energy <= 1e-15:
        ser_db = 100.0
    elif ref_energy <= 1e-15:
        ser_db = 0.0
    else:
        ser_db = float(10.0 * np.log10(ref_energy / err_energy))

    # Clipping detection
    ref_clip = detect_clipping(aligned_ref)
    cap_clip = detect_clipping(aligned_cap)

    # Excitation coverage over target band (Welch PSD of reference)
    nperseg = min(512, len(aligned_ref))
    if nperseg >= 32:
        f_welch, p_ref = scipy.signal.welch(aligned_ref, fs=sample_rate_hz, nperseg=nperseg)
        f_mask = (f_welch >= target_band_hz[0]) & (f_welch <= target_band_hz[1])
        p_band = p_ref[f_mask]
        max_p = float(np.max(p_ref)) if len(p_ref) > 0 else 0.0
        if max_p > 1e-20:
            rel_band_db = 10.0 * np.log10(np.maximum(p_band, 1e-30) / max_p)
            excited_bins = int(np.sum(rel_band_db >= -30.0))
            total_band_bins = len(p_band)
            cov_fraction = float(excited_bins / total_band_bins) if total_band_bins > 0 else 0.0
        else:
            excited_bins = 0
            cov_fraction = 0.0
    else:
        cov_fraction = 1.0 if ref_rms > 1e-6 else 0.0

    if cov_fraction >= 0.75:
        cov_status = "FULL_COVERAGE"
    elif cov_fraction >= 0.25:
        cov_status = "PARTIAL_COVERAGE"
    else:
        cov_status = "INSUFFICIENT_EXCITATION"

    cov_info = {
        "status": cov_status,
        "coverage_fraction": round(cov_fraction, 4),
        "target_band_hz": list(target_band_hz),
    }

    # Latency decomposition
    acoustic_lag_ms = max(0.0, delay_ms)
    total_latency_ms = acoustic_lag_ms + float(pipeline_buffer_delay_ms)
    lat_notes = (
        "Estimated acoustic lag is calculated via cross-correlation peak alignment through the phantom medium. "
        "Playback pipeline buffer delay represents host soundcard/driver output latency. "
        "Single-ended cross-correlation does NOT establish true absolute electrical DAC-to-ADC transit time "
        "without dedicated hardware loopback pulse synchronization."
    )

    latency = LatencyDecomposition(
        estimated_acoustic_lag_ms=round(acoustic_lag_ms, 3),
        playback_pipeline_buffer_delay_ms=round(pipeline_buffer_delay_ms, 3),
        total_end_to_end_latency_estimate_ms=round(total_latency_ms, 3),
        delay_samples=delay_samples,
        effective_sample_rate_hz=sample_rate_hz,
        is_hardware_synchronized=False,
        notes=lat_notes,
    )

    alignment = PhantomAlignmentResult(
        sync_status=sync_status,
        normalized_cross_correlation=round(ncc, 5),
        estimated_delay_samples=delay_samples,
        estimated_delay_ms=round(delay_ms, 3),
        overlap_samples=len(aligned_ref),
        overlap_duration_s=round(overlap_dur_s, 4),
        least_squares_gain=round(ls_gain, 4),
        rms_gain_ratio=round(rms_ratio, 4),
        peak_gain_ratio=round(pk_ratio, 4),
        rmse=round(rmse_val, 6),
        normalized_rmse=round(nrmse_val, 5),
        signal_to_error_ratio_db=round(ser_db, 2),
        reference_clipping=ref_clip,
        capture_clipping=cap_clip,
        excitation_coverage=cov_info,
    )

    return aligned_ref, aligned_cap, alignment, latency


METROLOGICAL_DISCLAIMER_PHANTOM = (
    "RESEARCH & LABORATORY METROLOGY NOTICE: "
    "The frequency response H1(f) and ordinary coherence gamma_xy^2(f) characterize the cumulative "
    "end-to-end electro-acoustic system under test (PC DAC -> PAM8403 amplifier -> 12-ohm exciter -> "
    "silicone phantom acoustic propagation -> chestpiece acoustic cavity -> INMP441 microphone -> ESP32-S3). "
    "Neither the exciter nor the microphone is assumed to have a flat frequency response. "
    "All quantities are uncalibrated relative Full Scale (FS) values. No absolute sound pressure levels (Pa, dB SPL) "
    "are claimed without physical primary calibration evidence. This system identification record is intended "
    "strictly for engineering characterization and must NOT be used for clinical diagnostic purposes."
)


def run_phantom_characterization(
    stimulus: StimulusRecord,
    capture_samples: np.ndarray,
    capture_fs: int,
    template_id: str = "PHANTOM_LOG_SWEEP_20_500HZ_V1",
    trial_id: Optional[str] = None,
    output_gain_dbfs: float = -6.0,
    operator_notes: str = "",
    hardware_status: str = "PENDING_PHYSICAL_MEASUREMENT",
    pipeline_buffer_delay_ms: float = 30.0,
    max_display_points: int = 300,
) -> PhantomExperimentRecord:
    """Execute complete reproducible phantom characterization on reference stimulus and captured response."""
    now_utc = datetime.now(timezone.utc)
    tid = trial_id or f"phantom_trial_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Validate template
    template = STANDARD_PHANTOM_TEMPLATES.get(template_id)
    target_band = tuple(template.target_frequency_band_hz) if template else (20.0, 500.0)

    # Rational polyphase resampling of capture to match stimulus sample rate if needed
    stim_samples = stimulus.samples
    stim_fs = stimulus.sample_rate_hz
    cap = np.asarray(capture_samples, dtype=np.float32)

    resampled = False
    working_fs = stim_fs
    if capture_fs != stim_fs:
        gcd = math.gcd(int(capture_fs), int(stim_fs))
        up = int(stim_fs) // gcd
        down = int(capture_fs) // gcd
        cap = scipy.signal.resample_poly(cap, up, down).astype(np.float32)
        resampled = True

    # 1. Alignment and Latency Decomposition
    aligned_ref, aligned_cap, alignment_res, latency_decomp = estimate_phantom_alignment(
        reference=stim_samples,
        captured=cap,
        sample_rate_hz=working_fs,
        pipeline_buffer_delay_ms=pipeline_buffer_delay_ms,
        target_band_hz=target_band,
    )

    # 2. SISO System Identification (H1 & Coherence)
    sysid_cfg = SystemIdConfig(
        nperseg=min(1024, len(aligned_ref)),
        excited_band_hz=target_band,
        energy_threshold_db_rel_max=-30.0,
        analysis_profile="BROADBAND_SYSTEM_ID_V1",
    )
    sysid_result = estimate_siso_system_id(
        input_signal=aligned_ref,
        output_signal=aligned_cap,
        sample_rate_hz=working_fs,
        config=sysid_cfg,
        input_name=stimulus.stimulus_id,
        output_name=f"capture_{tid}",
    )

    # 3. Decimated display curves
    n_pts = min(len(aligned_ref), max_display_points)
    step = len(aligned_ref) / float(n_pts) if n_pts > 0 else 1.0
    disp_indices = [min(len(aligned_ref) - 1, int(i * step)) for i in range(n_pts)]
    time_ms = [round(float(idx / working_fs) * 1000.0, 2) for idx in disp_indices]
    disp_ref = [round(float(aligned_ref[i]), 5) for i in disp_indices]
    disp_cap = [round(float(aligned_cap[i]), 5) for i in disp_indices]
    disp_err = [round(float(aligned_cap[i] - aligned_ref[i]), 5) for i in disp_indices]

    # Subsample frequency response curves (H1 mag, phase, coherence)
    f_arr = np.array(sysid_result.frequencies_hz)
    mask_eval = f_arr <= 1000.0
    f_sub = f_arr[mask_eval]
    mag_sub = np.array(sysid_result.h1_magnitude_db)[mask_eval]
    phase_sub = np.array(sysid_result.h1_phase_deg)[mask_eval]
    coh_sub = np.array(sysid_result.coherence)[mask_eval]

    if len(f_sub) > max_display_points:
        sub_indices = np.round(np.linspace(0, len(f_sub) - 1, max_display_points)).astype(int)
        sub_indices = np.unique(sub_indices)
        disp_freqs = [round(float(f_sub[i]), 1) for i in sub_indices]
        disp_h1_mag = [round(float(mag_sub[i]), 2) for i in sub_indices]
        disp_h1_phase = [round(float(phase_sub[i]), 1) for i in sub_indices]
        disp_coh = [round(float(coh_sub[i]), 4) for i in sub_indices]
    else:
        disp_freqs = [round(float(f), 1) for f in f_sub]
        disp_h1_mag = [round(float(m), 2) for m in mag_sub]
        disp_h1_phase = [round(float(p), 1) for p in phase_sub]
        disp_coh = [round(float(c), 4) for c in coh_sub]

    display_dict = {
        "time_ms": time_ms,
        "aligned_reference": disp_ref,
        "aligned_capture": disp_cap,
        "aligned_error": disp_err,
        "frequency_hz": disp_freqs,
        "h1_magnitude_db": disp_h1_mag,
        "h1_phase_deg": disp_h1_phase,
        "coherence": disp_coh,
    }

    provenance = {
        "engine": "AuscultaForge Phantom System Identification",
        "version": "1.0.0",
        "created_at_utc": now_utc.isoformat(),
        "template_id": template_id,
        "sample_rate_hz": working_fs,
        "resampled": resampled,
        "target_band_hz": list(target_band),
        "checklist": template.checklist if template else [],
    }

    return PhantomExperimentRecord(
        schema_version="1.0.0",
        trial_id=tid,
        template_id=template_id,
        created_at_utc=now_utc.isoformat(),
        intended_device="PC_AUDIO_OUT_PAM8403_EXCITER",
        intended_chain="PC audio output -> PAM8403 amplifier -> 12-ohm exciter -> silicone phantom -> chestpiece -> INMP441 -> ESP32-S3 -> PC",
        hardware_status=hardware_status,
        output_gain_dbfs=output_gain_dbfs,
        operator_notes=operator_notes,
        stimulus=stimulus.to_dict(),
        capture={
            "original_sample_rate_hz": capture_fs,
            "resampled": resampled,
            "working_sample_rate_hz": working_fs,
            "total_samples": len(cap),
            "duration_s": round(float(len(cap) / working_fs), 4),
            "rms_fs": round(float(rms(cap)), 5),
            "peak_fs": round(float(peak_abs(cap)), 5),
        },
        latency=latency_decomp,
        alignment=alignment_res,
        system_id=sysid_result.to_dict(),
        display=display_dict,
        metrological_disclaimer=METROLOGICAL_DISCLAIMER_PHANTOM,
        provenance=provenance,
    )
