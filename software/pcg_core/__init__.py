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
    ):
        from . import validation
        return getattr(validation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
