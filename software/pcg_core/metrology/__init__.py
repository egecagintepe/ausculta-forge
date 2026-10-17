"""AuscultaForge — Advisor Metrology & Laboratory Characterization Automation.

Implements pipelines and reports for the six mandatory advisor measurements:
1. Phantom Frequency Response (20–500 Hz H1 & Coherence)
2. Band-Limited Active-to-Quiescent Level Ratio (SNR Convention)
3. Repeatability Study (>= 10 Independent Runs)
4. 50 Hz Mains Interference & Harmonics (Welch PSD delta_f <= 0.5 Hz)
5. End-to-End Latency & Synchronization Verification
6. Dropped-Sample Rate Continuity (30-Minute Hardware Gate Test)
"""

from .models import (
    MeasurementStatus,
    SensorConfiguration,
    PhantomFrequencyResponseResult,
    SnrLevelRatioResult,
    RepeatabilityStudyResult,
    MainsInterferenceResult,
    LatencyMeasurementResult,
    PacketDropContinuityResult,
    AdvisorMetrologyReport,
)
from .workflows import (
    compute_phantom_frf,
    compute_active_quiescent_snr,
    compute_repeatability_study,
    compute_mains_interference,
    compute_latency_measurement,
    compute_continuity_drop_rate,
)
from .reports import (
    export_report_to_json,
    export_summary_to_csv,
    format_human_readable_summary,
)
from .runner import (
    MetrologyExperimentConfig,
    MetrologyRunner,
    Workflow1Config,
    Workflow2Config,
    Workflow3Config,
    Workflow4Config,
    Workflow5Config,
    Workflow6Config,
    load_audio_wav,
)

__all__ = [
    "MeasurementStatus",
    "SensorConfiguration",
    "PhantomFrequencyResponseResult",
    "SnrLevelRatioResult",
    "RepeatabilityStudyResult",
    "MainsInterferenceResult",
    "LatencyMeasurementResult",
    "PacketDropContinuityResult",
    "AdvisorMetrologyReport",
    "compute_phantom_frf",
    "compute_active_quiescent_snr",
    "compute_repeatability_study",
    "compute_mains_interference",
    "compute_latency_measurement",
    "compute_continuity_drop_rate",
    "export_report_to_json",
    "export_summary_to_csv",
    "format_human_readable_summary",
    "MetrologyExperimentConfig",
    "MetrologyRunner",
    "Workflow1Config",
    "Workflow2Config",
    "Workflow3Config",
    "Workflow4Config",
    "Workflow5Config",
    "Workflow6Config",
    "load_audio_wav",
]
