"""AuscultaForge — Metrology Report Formatting & Multi-Format Exporters.

Produces:
1. Versioned machine-readable JSON reports.
2. Tabular CSV summaries suitable for spreadsheet analysis, defense presentations, and lab notebooks.
3. Clean, human-readable GitHub-style Markdown summaries with metrological disclaimers.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any
from .models import AdvisorMetrologyReport


def export_report_to_json(report: AdvisorMetrologyReport, target_path: str | Path) -> Path:
    """Serialize full report to formatted JSON."""
    out = Path(target_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    return out


def export_summary_to_csv(report: AdvisorMetrologyReport, target_path: str | Path) -> Path:
    """Export tabular 6-workflow executive summary to CSV."""
    out = Path(target_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        ["Workflow_ID", "Measurement_Name", "Status", "Primary_Metric", "Primary_Value", "Unit", "Uncertainty_or_Dispersion", "Notes"],
        [
            "W1",
            "Phantom Frequency Response (20-500 Hz)",
            report.workflow_1_frequency_response.status,
            "Mean Coherence (Excited Band)",
            str(report.workflow_1_frequency_response.mean_coherence_target_band or "N/A"),
            "Dimensionless (0-1)",
            f"Ripple: {report.workflow_1_frequency_response.passband_ripple_db or 'N/A'} dB",
            "End-to-end electro-acoustic chain transfer function (H1)"
        ],
        [
            "W2",
            "Active-to-Quiescent Level Ratio (SNR)",
            report.workflow_2_snr_level_ratio.status,
            "SNR_conv (20-500 Hz)",
            str(report.workflow_2_snr_level_ratio.active_to_quiescent_ratio_db),
            "dB",
            f"Active: {report.workflow_2_snr_level_ratio.active_rms_fs:.5f} FS | Quiescent: {report.workflow_2_snr_level_ratio.quiescent_rms_fs:.5f} FS",
            report.workflow_2_snr_level_ratio.room_acoustic_condition
        ],
        [
            "W3",
            "Measurement Repeatability (>= 10 Runs)",
            report.workflow_3_repeatability.status,
            "Mean Metric Value",
            str(report.workflow_3_repeatability.mean),
            report.workflow_3_repeatability.metric_name,
            f"StdDev: {report.workflow_3_repeatability.std_dev:.4f} | CV: {report.workflow_3_repeatability.coefficient_of_variation_pct:.2f}% | N={report.workflow_3_repeatability.run_count}",
            f"95% CI: [{report.workflow_3_repeatability.confidence_interval_95[0]}, {report.workflow_3_repeatability.confidence_interval_95[1]}]"
        ],
        [
            "W4",
            "50 Hz Mains Interference & Harmonics",
            report.workflow_4_mains_interference.status,
            "Total Mains Harmonic Power",
            str(report.workflow_4_mains_interference.total_mains_harmonic_power_dbfs),
            "dBFS",
            f"Mains Ratio: {report.workflow_4_mains_interference.mains_to_total_power_ratio_pct:.4f}% | delta_f={report.workflow_4_mains_interference.frequency_resolution_hz:.3f} Hz",
            f"50Hz: {report.workflow_4_mains_interference.harmonic_powers_dbfs[0] if len(report.workflow_4_mains_interference.harmonic_powers_dbfs) > 0 else 'N/A'} dBFS"
        ],
        [
            "W5",
            "End-to-End Latency & Synchronization",
            report.workflow_5_latency.status,
            "Hardware Transit Latency",
            str(report.workflow_5_latency.end_to_end_latency_ms if report.workflow_5_latency.end_to_end_latency_ms is not None else "UNSYNCHRONIZED"),
            "ms",
            f"Jitter: {report.workflow_5_latency.jitter_ms or 0.0:.2f} ms | Relative Acoustic Lag: {report.workflow_5_latency.acoustic_relative_lag_ms:.2f} ms",
            report.workflow_5_latency.synchronization_method
        ],
        [
            "W6",
            "Dropped-Sample Rate (30-Minute Gate)",
            report.workflow_6_dropped_samples.status,
            "Dropped Sample Rate",
            f"{report.workflow_6_dropped_samples.drop_rate_pct:.6f}%",
            "Percent",
            f"Dropped: {report.workflow_6_dropped_samples.dropped_samples_count:,} of {report.workflow_6_dropped_samples.expected_samples_count:,} | Duration: {report.workflow_6_dropped_samples.total_elapsed_seconds:.1f} s",
            f"30-Min Gate Met: {report.workflow_6_dropped_samples.is_30_minute_gate_met}"
        ],
    ]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return out


def format_human_readable_summary(report: AdvisorMetrologyReport) -> str:
    """Format an extensive Markdown summary report with tables and metrological callouts."""
    w1 = report.workflow_1_frequency_response
    w2 = report.workflow_2_snr_level_ratio
    w3 = report.workflow_3_repeatability
    w4 = report.workflow_4_mains_interference
    w5 = report.workflow_5_latency
    w6 = report.workflow_6_dropped_samples

    md = f"""# AUSCULTAFORGE — ADVISOR METROLOGY REPORT
## Empirical Physical Characterization & Signal Integrity Assessment

- **Report ID:** `{report.report_id}`
- **Execution Date (UTC):** {report.created_at_utc}
- **Author:** {report.author}
- **Apparatus ID:** `{report.apparatus_id}`
- **Overall Hardware Status:** `{report.overall_hardware_status}`

---

### Executive Summary: The Six Mandatory Measurements

| # | Measurement Workflow | Status | Primary Result | Dispersion / Uncertainty | Key Finding / Observation |
|---|----------------------|--------|----------------|--------------------------|---------------------------|
| **1** | **Phantom Frequency Response (20–500 Hz)** | `{w1.status}` | Mean Coherence: **{w1.mean_coherence_target_band if w1.mean_coherence_target_band is not None else 'N/A'}** | Ripple: {w1.passband_ripple_db or 'N/A'} dB | {w1.excited_bins_count} excited bins in 20–500 Hz |
| **2** | **Active-to-Quiescent Level Ratio (SNR)** | `{w2.status}` | **{w2.active_to_quiescent_ratio_db:.2f} dB** | Active RMS: {w2.active_rms_fs:.5f} FS | Room: {w2.room_acoustic_condition} |
| **3** | **Repeatability (>= 10 Runs)** | `{w3.status}` | Mean: **{w3.mean:.4f}** | StdDev: {w3.std_dev:.4f} (CV: {w3.coefficient_of_variation_pct:.2f}%) | 95% CI: [{w3.confidence_interval_95[0]}, {w3.confidence_interval_95[1]}] (N={w3.run_count}) |
| **4** | **50 Hz Mains Interference & Harmonics** | `{w4.status}` | Total Mains: **{w4.total_mains_harmonic_power_dbfs:.2f} dBFS** | Mains Ratio: {w4.mains_to_total_power_ratio_pct:.4f}% | delta_f = {w4.frequency_resolution_hz:.3f} Hz (Welch PSD) |
| **5** | **End-to-End Latency** | `{w5.status}` | Hardware Delay: **{f'{w5.end_to_end_latency_ms:.2f} ms' if w5.end_to_end_latency_ms is not None else 'UNSYNCHRONIZED'}** | Jitter: {f'{w5.jitter_ms:.2f} ms' if w5.jitter_ms is not None else 'N/A'} | Sync Method: {w5.synchronization_method} |
| **6** | **Dropped-Sample Continuity** | `{w6.status}` | Drop Rate: **{w6.drop_rate_pct:.6f}%** | Dropped: {w6.dropped_samples_count:,} / {w6.expected_samples_count:,} | 30-Min Gate Met: **{w6.is_30_minute_gate_met}** ({w6.total_elapsed_seconds:.1f} s) |

---

### Detailed Workflow Analysis

#### 1. Phantom Frequency Response (20–500 Hz)
- **Metrological Model:** Classical Single-Input Single-Output (SISO) best-linear estimator (H1(f) = Sxy/Sxx) and ordinary magnitude-squared coherence (gamma_xy^2).
- **Excited Frequency Range:** {w1.target_band_hz[0]:.1f} Hz to {w1.target_band_hz[1]:.1f} Hz.
- **-3 dB Passband Bandwidth:** {f'{w1.bandwidth_3db_hz[0]:.1f} Hz - {w1.bandwidth_3db_hz[1]:.1f} Hz' if w1.bandwidth_3db_hz else 'Bandwidth not isolated'}.
- **Passband Ripple:** {f'{w1.passband_ripple_db:.2f} dB' if w1.passband_ripple_db is not None else 'N/A'}.
> [!NOTE]
> *{w1.disclaimer}*

#### 2. Active-to-Quiescent Level Ratio (SNR Convention)
- **Acoustic / Room Condition:** {w2.room_acoustic_condition}
- **Exciter Drive Amplitude:** {w2.exciter_drive_level}
- **Filter Bandpass:** {w2.filter_band_hz[0]:.1f} to {w2.filter_band_hz[1]:.1f} Hz (4th-order Butterworth).
- **Active Signal RMS:** {w2.active_rms_fs:.6f} FS
- **Quiescent Noise Floor RMS:** {w2.quiescent_rms_fs:.6f} FS
- **Active-to-Quiescent Level Ratio:** **{w2.active_to_quiescent_ratio_db:.2f} dB**
- **Sensor Declared Configuration:** Model `{w2.sensor_config.sensor_model}` ({w2.sensor_config.interface_type}), Sensitivity `{w2.sensor_config.nominal_sensitivity_declared}`.

#### 3. Measurement Repeatability (>= 10 Runs)
- **Target Metric Evaluated:** `{w3.metric_name}`
- **Sample Count:** N = {w3.run_count} (Requirement: >= 10 runs — **{'SATISFIED' if w3.meets_minimum_runs_requirement else 'NOT MET'}**).
- **Sample Mean (mu):** {w3.mean:.4f}
- **Sample Standard Deviation (sigma):** {w3.std_dev:.4f}
- **Coefficient of Variation (c_v):** {w3.coefficient_of_variation_pct:.2f}%
- **Range (Max - Min):** [{w3.min_value:.4f}, {w3.max_value:.4f}] (Delta = {w3.range_value:.4f})
- **95% Confidence Interval:** [{w3.confidence_interval_95[0]:.4f}, {w3.confidence_interval_95[1]:.4f}]
- **Documented Outliers / Apparatus Failures:** {len(w3.outliers_documented)} documented events.
- **Run Values:** {', '.join(f'{v:.3f}' for v in w3.run_values[:12])}{'...' if len(w3.run_values) > 12 else ''}

#### 4. 50 Hz Mains Power Interference & Harmonics
- **Power Grid Standard:** Turkey 50 Hz AC Grid.
- **Welch PSD Frequency Resolution (delta_f):** {w4.frequency_resolution_hz:.4f} Hz (<= 0.5 Hz requirement met).
- **Harmonic Powers (dBFS):**
  - **50 Hz (Fundamental):** {w4.harmonic_powers_dbfs[0] if len(w4.harmonic_powers_dbfs) > 0 else 'N/A'} dBFS
  - **100 Hz (2nd Harmonic):** {w4.harmonic_powers_dbfs[1] if len(w4.harmonic_powers_dbfs) > 1 else 'N/A'} dBFS
  - **150 Hz (3rd Harmonic):** {w4.harmonic_powers_dbfs[2] if len(w4.harmonic_powers_dbfs) > 2 else 'N/A'} dBFS
  - **200 Hz (4th Harmonic):** {w4.harmonic_powers_dbfs[3] if len(w4.harmonic_powers_dbfs) > 3 else 'N/A'} dBFS
  - **250 Hz (5th Harmonic):** {w4.harmonic_powers_dbfs[4] if len(w4.harmonic_powers_dbfs) > 4 else 'N/A'} dBFS
- **Total Integrated Mains Power:** {w4.total_mains_harmonic_power_dbfs:.2f} dBFS ({w4.mains_to_total_power_ratio_pct:.4f}% of 20–500 Hz passband energy).
- **Operating Conditions:** {w4.power_source_condition} | {w4.shielding_condition}.

#### 5. End-to-End Latency & Synchronization
- **Synchronization Method:** `{w5.synchronization_method}`
- **Hardware Synchronization Evidence:** **{'VALID HARDWARE SYNC VERIFIED' if w5.has_valid_hardware_sync else 'SYNCHRONIZATION EVIDENCE MISSING (Acoustic lag only)'}**
- **Measured Transit Latency:** {f'{w5.end_to_end_latency_ms:.2f} ms' if w5.end_to_end_latency_ms is not None else 'N/A (Awaiting hardware pulse loopback)'}
- **Latency Jitter (1 sigma):** {f'{w5.jitter_ms:.2f} ms' if w5.jitter_ms is not None else 'N/A'}
- **Relative Acoustic Wave Lag:** {w5.acoustic_relative_lag_ms:.2f} ms
- **Estimated Playback Pipeline Delay:** {w5.playback_buffer_delay_ms:.2f} ms
> [!WARNING]
> *{w5.notes}*

#### 6. Dropped-Sample Rate & Continuous Acquisition (30-Minute Gate)
- **Total Stream Elapsed Time:** {w6.total_elapsed_seconds:.2f} seconds ({w6.total_elapsed_seconds / 60.0:.2f} minutes).
- **Total Expected Samples:** {w6.expected_samples_count:,} samples.
- **Total Ingested Samples:** {w6.ingested_samples_count:,} samples.
- **Dropped Samples Count:** {w6.dropped_samples_count:,} samples.
- **Drop Rate Percentage:** **{w6.drop_rate_pct:.6f}%**
- **Discontinuity Gap Events:** {w6.gap_events_count} gap events recorded.
- **Longest Gap-Free Continuous Run:** {w6.longest_continuous_run_seconds:.2f} s.
- **Week-8 30-Minute Continuous Gate (>= 1,800 s with 0 drops):** **{'GATE REQUIREMENT SATISFIED' if w6.is_30_minute_gate_met else 'GATE NOT MET'}**.

---

### Metrological Disclaimers & Sensor Declarations

1. **Uncalibrated Sensor Output:** Sensor comparisons are conducted under declared electrical and digital configurations. INMP441 (I2S digital) and ECM (analog preamplifier) are **NOT** calibrated equivalents and shall not be treated as inter-calibrated without certified acoustic sound level meter measurements.
2. **Dimensionless Quantities:** All reported amplitudes and spectral densities are expressed in Full Scale (FS) units. Pascals (Pa) and acoustic sound pressure levels (dB SPL) are strictly prohibited.
3. **Hardware Readiness:** In adherence to the Week-02 Measurement Plan, physical measurements remain marked `NOT_YET_MEASURED` until executed on physical bench hardware.
"""
    return md

