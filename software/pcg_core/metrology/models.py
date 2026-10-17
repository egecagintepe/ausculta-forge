"""AuscultaForge — Models & Schemas for the Six Mandatory Advisor Measurements.

Defines schemas and serialization for:
1. Phantom Frequency Response (20–500 Hz H1 & Coherence)
2. Active-to-Quiescent Level Ratio / Declared SNR Convention
3. Repeatability Study (>= 10 Independent Runs)
4. Mains Interference (50 Hz and Harmonics)
5. End-to-End Latency & Synchronization
6. Dropped-Sample / Drop-Packet Rate (including 30-Minute Gate Test)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Optional


class MeasurementStatus(str, Enum):
    """Execution status of an experimental measurement."""
    NOT_YET_MEASURED = "NOT_YET_MEASURED"
    SYNTHETIC_VERIFIED = "SYNTHETIC_VERIFIED"
    BENCH_MEASURED = "BENCH_MEASURED"
    FAILED = "FAILED"


@dataclass(slots=True)
class SensorConfiguration:
    """Declared physical transducer configuration (never assumed equivalent without calibration)."""
    sensor_model: str  # e.g., "INMP441", "ECM_GENERIC", "SIMULATED"
    interface_type: str  # e.g., "I2S_DIGITAL", "ANALOG_PREAMP", "SYNTHETIC"
    nominal_sensitivity_declared: str  # e.g., "-26 dBFS @ 94 dB SPL (datasheet nominal)"
    preamp_gain_db: float = 0.0
    analog_filter_notes: str = "None"
    notes: str = "Declared hardware configuration; not calibrated physical acoustic equivalent."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PhantomFrequencyResponseResult:
    """Workflow 1: 20–500 Hz Phantom Frequency Response with H1 and Coherence."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    target_band_hz: list[float] = field(default_factory=lambda: [20.0, 500.0])
    frequencies_hz: list[float] = field(default_factory=list)
    h1_magnitude_db: list[float] = field(default_factory=list)
    h1_phase_deg: list[float] = field(default_factory=list)
    coherence: list[float] = field(default_factory=list)
    mean_coherence_target_band: Optional[float] = None
    bandwidth_3db_hz: Optional[list[float]] = None
    passband_ripple_db: Optional[float] = None
    excited_bins_count: int = 0
    disclaimer: str = (
        "Estimates cumulative end-to-end electro-acoustic transfer function. "
        "Neither exciter nor microphone has a flat response; uncalibrated relative FS quantities only."
    )
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SnrLevelRatioResult:
    """Workflow 2: Band-Limited Active-to-Quiescent Level Ratio / Declared SNR Convention."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    active_rms_fs: float = 0.0
    quiescent_rms_fs: float = 0.0
    active_to_quiescent_ratio_db: float = 0.0
    filter_band_hz: list[float] = field(default_factory=lambda: [20.0, 500.0])
    room_acoustic_condition: str = "Unspecified room condition"
    exciter_drive_level: str = "Unspecified drive level"
    sensor_config: SensorConfiguration = field(default_factory=lambda: SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS nominal"))
    notes: str = (
        "Calculated as 20*log10(RMS_active / RMS_quiescent) over 20–500 Hz. "
        "Represents active-to-quiescent level ratio under declared gain and acoustic conditions."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepeatabilityStudyResult:
    """Workflow 3: Repeatability Over >= 10 Independent Physical Runs."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    run_count: int = 0
    metric_name: str = "active_to_quiescent_ratio_db"
    run_values: list[float] = field(default_factory=list)
    run_labels: list[str] = field(default_factory=list)
    mean: float = 0.0
    std_dev: float = 0.0
    variance: float = 0.0
    coefficient_of_variation_pct: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    range_value: float = 0.0
    confidence_interval_95: list[float] = field(default_factory=lambda: [0.0, 0.0])
    outliers_documented: list[dict[str, Any]] = field(default_factory=list)
    meets_minimum_runs_requirement: bool = False
    notes: str = (
        "Statistical dispersion across mechanically invariant repeated runs. "
        "No outlier may be omitted without documented physical apparatus failure."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MainsInterferenceResult:
    """Workflow 4: 50 Hz Mains Interference and Relevant Harmonics."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    grid_frequency_hz: float = 50.0
    harmonics_hz: list[float] = field(default_factory=lambda: [50.0, 100.0, 150.0, 200.0, 250.0])
    harmonic_powers_dbfs: list[float] = field(default_factory=list)
    harmonic_powers_linear: list[float] = field(default_factory=list)
    total_mains_harmonic_power_dbfs: float = -300.0
    mains_to_total_power_ratio_pct: float = 0.0
    frequency_resolution_hz: float = 0.0
    power_source_condition: str = "Unspecified (AC mains adapter vs Battery)"
    shielding_condition: str = "Unspecified (Shielded vs Unshielded)"
    notes: str = (
        "Evaluated via high-resolution Welch PSD (delta_f <= 0.5 Hz) integrating energy within +-1 Hz of each harmonic."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LatencyMeasurementResult:
    """Workflow 5: End-to-End Stimulus-to-Host Latency."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    synchronization_method: str = "UNSYNCHRONIZED_ACOUSTIC_LAG_ONLY"
    has_valid_hardware_sync: bool = False
    end_to_end_latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    acoustic_relative_lag_ms: float = 0.0
    playback_buffer_delay_ms: float = 0.0
    trial_measurements_ms: list[float] = field(default_factory=list)
    notes: str = (
        "Physical latency requires simultaneous electrical trigger or loopback sync marker. "
        "Acoustic cross-correlation alone measures relative wave arrival lag, not true electrical transit time."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PacketDropContinuityResult:
    """Workflow 6: Dropped-Sample / Drop-Packet Rate for Extended Acquisition (30-Minute Gate)."""
    status: str = MeasurementStatus.NOT_YET_MEASURED.value
    total_elapsed_seconds: float = 0.0
    expected_samples_count: int = 0
    ingested_samples_count: int = 0
    dropped_samples_count: int = 0
    drop_rate_pct: float = 0.0
    gap_events_count: int = 0
    longest_continuous_run_seconds: float = 0.0
    is_30_minute_gate_met: bool = False
    gap_event_log: list[dict[str, Any]] = field(default_factory=list)
    notes: str = (
        "Monotonic sequence counter verification. "
        "Week-8 gate requires continuous acquisition for >= 30 minutes (1,800 s) without unrecoverable stalls."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdvisorMetrologyReport:
    """Consolidated Comprehensive Laboratory Report for all Six Advisor Measurements."""
    schema_version: str
    report_id: str
    created_at_utc: str
    author: str
    apparatus_id: str
    overall_hardware_status: str  # "NOT_YET_MEASURED", "PARTIAL_MEASURED", "ALL_MEASURED"
    workflow_1_frequency_response: PhantomFrequencyResponseResult
    workflow_2_snr_level_ratio: SnrLevelRatioResult
    workflow_3_repeatability: RepeatabilityStudyResult
    workflow_4_mains_interference: MainsInterferenceResult
    workflow_5_latency: LatencyMeasurementResult
    workflow_6_dropped_samples: PacketDropContinuityResult
    sensor_declarations: list[SensorConfiguration]
    environment_notes: str
    limitations_and_uncertainties: list[str]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
