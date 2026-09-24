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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
