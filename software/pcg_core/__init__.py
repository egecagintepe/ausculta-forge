from .models import SampleBlock
from .sources import MockPCGSource, WavSource, RealtimeWavSource
from .dsp import StreamingBandpass
from .buffers import RollingBuffer
from .streaming import (
    StreamQualityMonitor,
    QualityReport,
    LiveMetrics,
    SpectralFrame,
    LiveStreamFrame,
    LiveStreamingPipeline,
    compute_spectral_frame,
    compute_rolling_spectrogram,
)
from .analysis import analyze_source, analyze_wav, PCGAnalysisResult, SpectrogramData, SignalMetrics
from .recording import (
    SessionMetadata,
    SessionRecorder,
    RecordingSampleRateError,
    RecordingStateError,
    list_sessions,
    get_session,
    create_session_source,
)
from .scientific_config import (
    SignalRepresentation,
    SignalUnit,
    validate_unit_usage,
    DetrendMode,
    SpectralScaling,
    SpectralAnalysisConfig,
    AnalysisProfile,
    get_analysis_profile,
    list_analysis_profiles,
    RAW_INTEGRITY_V1,
    GENERAL_PCG_V1,
    PHANTOM_VALIDATION_V1,
    PCG_EVENT_FEATURES_V1,
    SPRINGER_SEGMENTATION_RESEARCH_V1,
    BROADBAND_SYSTEM_ID_V1,
)

def __getattr__(name: str):
    if name in ("ExperimentConfig", "run_experiment", "run_single_experiment"):
        from . import experiment
        return getattr(experiment, name)
    if name in (
        "ValidationResult",
        "validate_signals",
        "validate_wav_files",
        "simulate_distorted_capture",
        "estimate_delay_and_align",
        "compute_least_squares_gain",
    ):
        from . import validation
        return getattr(validation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
