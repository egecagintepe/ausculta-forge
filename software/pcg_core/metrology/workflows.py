"""AuscultaForge — Mathematical Workflows for the Six Mandatory Advisor Measurements.

Implements rigorous, reproducible engineering algorithms for:
1. Phantom Frequency Response (20–500 Hz H1 & Coherence)
2. Band-Limited Active-to-Quiescent Level Ratio / Declared SNR Convention
3. Repeatability Study (>= 10 Independent Runs)
4. Mains Interference (50 Hz and Harmonics)
5. End-to-End Latency & Synchronization
6. Dropped-Sample / Drop-Packet Rate (including 30-Minute Gate Test)
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence, Tuple
import numpy as np
import scipy.signal

from ..metrics import rms, peak_abs
from ..scientific.models import SystemIdConfig
from ..scientific.system_id import estimate_siso_system_id
from .models import (
    MeasurementStatus,
    SensorConfiguration,
    PhantomFrequencyResponseResult,
    SnrLevelRatioResult,
    RepeatabilityStudyResult,
    MainsInterferenceResult,
    LatencyMeasurementResult,
    PacketDropContinuityResult,
)


# =============================================================================
# Workflow 1: Phantom Frequency Response (20–500 Hz)
# =============================================================================

def compute_phantom_frf(
    input_stimulus: np.ndarray,
    output_response: np.ndarray,
    sample_rate_hz: float,
    target_band_hz: tuple[float, float] = (20.0, 500.0),
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> PhantomFrequencyResponseResult:
    """Evaluate SISO best-linear H1 frequency response and ordinary coherence.
    
    Parameters
    ----------
    input_stimulus : np.ndarray
        1D floating-point excitation sequence.
    output_response : np.ndarray
        1D floating-point captured response sequence.
    sample_rate_hz : float
        Sampling frequency in Hertz.
    target_band_hz : tuple[float, float]
        Target acoustic evaluation band (default: 20–500 Hz).
    status : MeasurementStatus
        Measurement status declaration.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    if len(input_stimulus) == 0 or len(output_response) == 0:
        raise ValueError("Input stimulus and output response must be non-empty.")

    min_len = min(len(input_stimulus), len(output_response))
    nperseg = min(1024, min_len)

    cfg = SystemIdConfig(
        nperseg=nperseg,
        excited_band_hz=target_band_hz,
        energy_threshold_db_rel_max=-30.0,
        analysis_profile="BROADBAND_SYSTEM_ID_V1",
    )

    sys_res = estimate_siso_system_id(
        input_signal=input_stimulus[:min_len],
        output_signal=output_response[:min_len],
        sample_rate_hz=sample_rate_hz,
        config=cfg,
    )

    freqs = np.array(sys_res.frequencies_hz)
    h1_mag_db = np.array(sys_res.h1_magnitude_db)
    coherence = np.array(sys_res.coherence)

    # Focus on target band
    mask_target = (freqs >= target_band_hz[0]) & (freqs <= target_band_hz[1])
    f_target = freqs[mask_target]
    mag_target = h1_mag_db[mask_target]
    coh_target = coherence[mask_target]

    mean_coh: Optional[float] = None
    if len(coh_target) > 0 and sys_res.excited_bins_count > 0:
        mean_coh = float(np.mean(coh_target))

    # -3 dB bandwidth calculation within target band
    bw_3db: Optional[list[float]] = None
    passband_ripple: Optional[float] = None
    if len(mag_target) > 0:
        max_gain = float(np.max(mag_target))
        min_gain = float(np.min(mag_target))
        passband_ripple = round(max_gain - min_gain, 2)
        above_3db = f_target[mag_target >= (max_gain - 3.0)]
        if len(above_3db) >= 2:
            bw_3db = [float(above_3db[0]), float(above_3db[-1])]

    provenance = {
        "analysis_type": "siso_h1_frf",
        "sample_rate_hz": float(sample_rate_hz),
        "target_band_hz": list(target_band_hz),
        "nperseg": nperseg,
        "nfft": sys_res.provenance.get("nfft"),
        "window": "hann",
    }

    return PhantomFrequencyResponseResult(
        status=status.value,
        target_band_hz=list(target_band_hz),
        frequencies_hz=[float(f) for f in freqs],
        h1_magnitude_db=[float(m) for m in h1_mag_db],
        h1_phase_deg=[float(p) for p in sys_res.h1_phase_deg],
        coherence=[float(c) for c in coherence],
        mean_coherence_target_band=round(mean_coh, 4) if mean_coh is not None else None,
        bandwidth_3db_hz=bw_3db,
        passband_ripple_db=passband_ripple,
        excited_bins_count=sys_res.excited_bins_count,
        provenance=provenance,
    )


# =============================================================================
# Workflow 2: Active-to-Quiescent Level Ratio / Declared SNR Convention
# =============================================================================

def compute_active_quiescent_snr(
    active_signal: np.ndarray,
    quiescent_signal: np.ndarray,
    sample_rate_hz: float,
    filter_band_hz: tuple[float, float] = (20.0, 500.0),
    sensor_config: Optional[SensorConfiguration] = None,
    room_acoustic_condition: str = "Quiet laboratory room (< 40 dBA ambient)",
    exciter_drive_level: str = "0 dBFS DAC unity level into PAM8403",
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> SnrLevelRatioResult:
    """Evaluate active PCG stimulus level relative to quiescent noise floor in 20–500 Hz band.
    
    Formula:
        SNR_conv = 20 * log10( RMS_active / (RMS_quiescent + 1e-12) )
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    if len(active_signal) == 0 or len(quiescent_signal) == 0:
        raise ValueError("Signals must be non-empty.")

    act = np.asarray(active_signal, dtype=np.float32)
    qui = np.asarray(quiescent_signal, dtype=np.float32)

    # 4th-order Butterworth bandpass in 20–500 Hz
    sos = scipy.signal.butter(4, [filter_band_hz[0], filter_band_hz[1]], btype="bandpass", fs=sample_rate_hz, output="sos")
    act_filt = scipy.signal.sosfilt(sos, act)
    qui_filt = scipy.signal.sosfilt(sos, qui)

    rms_act = float(rms(act_filt))
    rms_qui = float(rms(qui_filt))

    if rms_qui > 1e-12:
        snr_db = 20.0 * math.log10(rms_act / rms_qui)
    else:
        snr_db = 100.0 if rms_act > 1e-12 else 0.0

    s_cfg = sensor_config or SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS @ 94 dB SPL")

    return SnrLevelRatioResult(
        status=status.value,
        active_rms_fs=round(rms_act, 6),
        quiescent_rms_fs=round(rms_qui, 6),
        active_to_quiescent_ratio_db=round(snr_db, 2),
        filter_band_hz=list(filter_band_hz),
        room_acoustic_condition=room_acoustic_condition,
        exciter_drive_level=exciter_drive_level,
        sensor_config=s_cfg,
    )


# =============================================================================
# Workflow 3: Repeatability Over >= 10 Independent Runs
# =============================================================================

def compute_repeatability_study(
    run_values: Sequence[float],
    metric_name: str = "active_to_quiescent_ratio_db",
    run_labels: Optional[Sequence[str]] = None,
    outliers_documented: Optional[list[dict[str, Any]]] = None,
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> RepeatabilityStudyResult:
    """Evaluate statistical dispersion across repeated runs.
    
    Calculates sample mean, sample standard deviation (N-1 degrees of freedom),
    variance, coefficient of variation (c_v = sigma / mu * 100%), range, and 95% CI.
    """
    vals = [float(v) for v in run_values]
    n = len(vals)
    if n == 0:
        raise ValueError("run_values sequence cannot be empty.")

    labels = list(run_labels) if run_labels is not None else [f"run_{i+1:02d}" for i in range(n)]

    mean_val = float(np.mean(vals))
    std_val = float(np.std(vals, ddof=1)) if n > 1 else 0.0
    var_val = float(std_val ** 2)

    cv_pct = float((std_val / (abs(mean_val) + 1e-12)) * 100.0) if abs(mean_val) > 1e-12 else 0.0
    min_v = float(np.min(vals))
    max_v = float(np.max(vals))
    rng_v = float(max_v - min_v)

    # 95% Confidence Interval for the mean using Student-t distribution
    if n > 1:
        # SciPy Student-t critical value
        t_crit = float(scipy.stats.t.ppf(0.975, df=n - 1)) if hasattr(scipy, "stats") and hasattr(scipy.stats, "t") else 2.262
        margin = t_crit * (std_val / math.sqrt(n))
        ci_95 = [round(mean_val - margin, 4), round(mean_val + margin, 4)]
    else:
        ci_95 = [round(mean_val, 4), round(mean_val, 4)]

    meets_req = bool(n >= 10)
    outliers = list(outliers_documented) if outliers_documented is not None else []

    return RepeatabilityStudyResult(
        status=status.value,
        run_count=n,
        metric_name=metric_name,
        run_values=[round(v, 4) for v in vals],
        run_labels=labels,
        mean=round(mean_val, 4),
        std_dev=round(std_val, 4),
        variance=round(var_val, 6),
        coefficient_of_variation_pct=round(cv_pct, 2),
        min_value=round(min_v, 4),
        max_value=round(max_v, 4),
        range_value=round(rng_v, 4),
        confidence_interval_95=ci_95,
        outliers_documented=outliers,
        meets_minimum_runs_requirement=meets_req,
    )


# =============================================================================
# Workflow 4: 50 Hz Mains Interference and Relevant Harmonics
# =============================================================================

def compute_mains_interference(
    quiescent_signal: np.ndarray,
    sample_rate_hz: float,
    harmonics_hz: Sequence[float] = (50.0, 100.0, 150.0, 200.0, 250.0),
    power_source_condition: str = "Laptop running on AC mains adapter",
    shielding_condition: str = "Shielded twisted-pair transducer cable",
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> MainsInterferenceResult:
    """Evaluate power grid harmonic interference pickup via high-resolution Welch PSD.
    
    Requires frequency resolution delta_f <= 0.5 Hz. Integrates spectral energy
    within +-1 Hz narrow band around 50 Hz fundamental and each harmonic.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    sig = np.asarray(quiescent_signal, dtype=np.float64)
    n_samples = len(sig)
    if n_samples < 64:
        raise ValueError(f"Signal too short for mains estimation: {n_samples} samples.")

    # Select N_fft ensuring delta_f <= 0.5 Hz (N_fft >= 2 * fs)
    min_nfft = int(math.ceil(sample_rate_hz / 0.5))
    nfft = int(2 ** math.ceil(math.log2(max(1024, min_nfft))))
    nperseg = min(nfft, n_samples)
    noverlap = nperseg // 2

    freqs, psd = scipy.signal.welch(
        sig,
        fs=sample_rate_hz,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        scaling="density",
        detrend="constant",
    )

    df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 0.5

    harmonic_powers_linear = []
    harmonic_powers_dbfs = []

    for h_freq in harmonics_hz:
        # Window of +-1.0 Hz around harmonic
        h_mask = (freqs >= (h_freq - 1.0)) & (freqs <= (h_freq + 1.0))
        if np.any(h_mask):
            p_linear = float(np.trapezoid(psd[h_mask], freqs[h_mask]))
        else:
            p_linear = 0.0
        p_linear = max(1e-30, p_linear)
        harmonic_powers_linear.append(p_linear)
        harmonic_powers_dbfs.append(round(10.0 * math.log10(p_linear), 2))

    total_mains_linear = float(np.sum(harmonic_powers_linear))
    total_mains_dbfs = round(10.0 * math.log10(max(1e-30, total_mains_linear)), 2)

    # Total power in characterization band 20–500 Hz
    band_mask = (freqs >= 20.0) & (freqs <= 500.0)
    if np.any(band_mask):
        total_band_linear = float(np.trapezoid(psd[band_mask], freqs[band_mask]))
    else:
        total_band_linear = total_mains_linear

    mains_ratio_pct = float((total_mains_linear / (total_band_linear + 1e-15)) * 100.0)
    mains_ratio_pct = min(100.0, max(0.0, mains_ratio_pct))

    return MainsInterferenceResult(
        status=status.value,
        grid_frequency_hz=50.0,
        harmonics_hz=[float(h) for h in harmonics_hz],
        harmonic_powers_dbfs=harmonic_powers_dbfs,
        harmonic_powers_linear=[round(float(p), 10) for p in harmonic_powers_linear],
        total_mains_harmonic_power_dbfs=total_mains_dbfs,
        mains_to_total_power_ratio_pct=round(mains_ratio_pct, 4),
        frequency_resolution_hz=round(df, 4),
        power_source_condition=power_source_condition,
        shielding_condition=shielding_condition,
    )


# =============================================================================
# Workflow 5: End-to-End Latency Measurement & Synchronization
# =============================================================================

def compute_latency_measurement(
    stimulus_trigger_timestamps_s: Optional[Sequence[float]] = None,
    received_timestamps_s: Optional[Sequence[float]] = None,
    dual_channel_loopback: Optional[np.ndarray] = None,
    sample_rate_hz: Optional[float] = None,
    acoustic_cross_corr_lag_ms: float = 0.0,
    playback_buffer_delay_ms: float = 30.0,
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> LatencyMeasurementResult:
    """Evaluate end-to-end latency with explicit synchronization evidence check.
    
    Distinguishes relative acoustic wave arrival from physically measured electrical/host transit delay.
    """
    trial_latencies: list[float] = []
    has_valid_sync = False
    sync_method = "UNSYNCHRONIZED_ACOUSTIC_LAG_ONLY"

    # Case A: Explicit paired trigger and received timestamps
    if (
        stimulus_trigger_timestamps_s is not None
        and received_timestamps_s is not None
        and len(stimulus_trigger_timestamps_s) > 0
        and len(stimulus_trigger_timestamps_s) == len(received_timestamps_s)
    ):
        for t_tx, t_rx in zip(stimulus_trigger_timestamps_s, received_timestamps_s):
            lat_ms = (t_rx - t_tx) * 1000.0
            if lat_ms >= 0:
                trial_latencies.append(lat_ms)

        if len(trial_latencies) > 0:
            has_valid_sync = True
            sync_method = "HARDWARE_TRIGGER_TIMESTAMPS"

    # Case B: Dual-channel synchronized loopback audio recording
    elif dual_channel_loopback is not None and sample_rate_hz is not None and sample_rate_hz > 0:
        if dual_channel_loopback.ndim == 2 and dual_channel_loopback.shape[1] >= 2:
            ch_stim = dual_channel_loopback[:, 0]
            ch_resp = dual_channel_loopback[:, 1]
            corr = scipy.signal.correlate(ch_resp, ch_stim, mode="full")
            lags = scipy.signal.correlation_lags(len(ch_resp), len(ch_stim), mode="full")
            best_lag = lags[np.argmax(corr)]
            lat_ms = float((best_lag / float(sample_rate_hz)) * 1000.0)
            if lat_ms >= 0:
                trial_latencies.append(lat_ms)
                has_valid_sync = True
                sync_method = "ELECTRICAL_LOOPBACK_CROSS_CORRELATION"

    # Evaluate summary
    if has_valid_sync and len(trial_latencies) > 0:
        mean_lat = float(np.mean(trial_latencies))
        jitter = float(np.std(trial_latencies)) if len(trial_latencies) > 1 else 0.0
        notes = (
            f"Physical end-to-end latency validated via {sync_method} over {len(trial_latencies)} trials. "
            f"Mean latency: {mean_lat:.2f} ms | Jitter (1 sigma): {jitter:.2f} ms."
        )
    else:
        mean_lat = None
        jitter = None
        notes = (
            "SYNCHRONIZATION EVIDENCE MISSING: Single-ended acoustic cross-correlation estimates "
            f"relative acoustic arrival lag ({acoustic_cross_corr_lag_ms:.2f} ms), not true electrical DAC-to-ADC transit time. "
            f"Estimated total latency including {playback_buffer_delay_ms:.1f} ms buffer delay is "
            f"{acoustic_cross_corr_lag_ms + playback_buffer_delay_ms:.2f} ms."
        )

    return LatencyMeasurementResult(
        status=status.value,
        synchronization_method=sync_method,
        has_valid_hardware_sync=has_valid_sync,
        end_to_end_latency_ms=round(mean_lat, 2) if mean_lat is not None else None,
        jitter_ms=round(jitter, 2) if jitter is not None else None,
        acoustic_relative_lag_ms=round(acoustic_cross_corr_lag_ms, 2),
        playback_buffer_delay_ms=round(playback_buffer_delay_ms, 2),
        trial_measurements_ms=[round(t, 2) for t in trial_latencies],
        notes=notes,
    )


# =============================================================================
# Workflow 6: Dropped-Sample / Drop-Packet Rate (30-Minute Gate)
# =============================================================================

def compute_continuity_drop_rate(
    sequence_numbers: Sequence[int],
    samples_per_packet: int = 128,
    sample_rate_hz: int = 48000,
    total_elapsed_seconds: Optional[float] = None,
    status: MeasurementStatus = MeasurementStatus.BENCH_MEASURED,
) -> PacketDropContinuityResult:
    """Evaluate stream packet continuity and sequence monotonicity.
    
    Tracks exact expected vs received packet count, dropped sample count, drop rate %,
    gap events, and verifies the Week-8 30-minute continuous streaming gate requirement.
    """
    seqs = list(sequence_numbers)
    n_rx_packets = len(seqs)
    if n_rx_packets == 0:
        return PacketDropContinuityResult(
            status=status.value,
            notes="Empty sequence stream; no packets evaluated."
        )

    seq_start = seqs[0]
    seq_end = seqs[-1]
    n_expected_packets = seq_end - seq_start + 1

    gap_events: list[dict[str, Any]] = []
    dropped_packets = 0
    longest_continuous_packets = 0
    current_continuous = 1

    for i in range(len(seqs) - 1):
        diff = seqs[i + 1] - seqs[i]
        if diff == 1:
            current_continuous += 1
            if current_continuous > longest_continuous_packets:
                longest_continuous_packets = current_continuous
        elif diff > 1:
            missed = diff - 1
            dropped_packets += missed
            current_continuous = 1
            gap_events.append({
                "preceding_sequence": seqs[i],
                "subsequent_sequence": seqs[i + 1],
                "missed_packets": missed,
                "missed_samples": missed * samples_per_packet,
                "approx_time_s": round(float(seqs[i] * samples_per_packet / sample_rate_hz), 3),
            })
        else:
            # Duplicate or regression
            pass

    if longest_continuous_packets == 0:
        longest_continuous_packets = current_continuous

    expected_samples = n_expected_packets * samples_per_packet
    ingested_samples = n_rx_packets * samples_per_packet
    dropped_samples = dropped_packets * samples_per_packet
    drop_rate_pct = float((dropped_samples / expected_samples) * 100.0) if expected_samples > 0 else 0.0

    elapsed_s = total_elapsed_seconds if total_elapsed_seconds is not None else float(expected_samples / sample_rate_hz)
    longest_continuous_s = float(longest_continuous_packets * samples_per_packet / sample_rate_hz)

    # 30-Minute Gate Check: continuous acquisition for >= 1800s with 0 dropped samples
    gate_met = bool(elapsed_s >= 1800.0 and dropped_samples == 0)

    notes = (
        f"Stream evaluated over {elapsed_s:.1f} s ({expected_samples:,} expected samples). "
        f"Dropped samples: {dropped_samples:,} ({drop_rate_pct:.4f}%). "
        f"Week-8 30-minute gate requirement (>= 1800s, 0 drops): {'MET' if gate_met else 'NOT MET'}."
    )

    return PacketDropContinuityResult(
        status=status.value,
        total_elapsed_seconds=round(elapsed_s, 2),
        expected_samples_count=expected_samples,
        ingested_samples_count=ingested_samples,
        dropped_samples_count=dropped_samples,
        drop_rate_pct=round(drop_rate_pct, 6),
        gap_events_count=len(gap_events),
        longest_continuous_run_seconds=round(longest_continuous_s, 2),
        is_30_minute_gate_met=gate_met,
        gap_event_log=gap_events,
        notes=notes,
    )
