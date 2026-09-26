"""AuscultaForge — Scientific Signal Characterization, Envelopes & System ID."""

from .models import (
    SignalQualityConfig,
    SignalCharacterizationResult,
    WelchConfig,
    SpectralAnalysisResult,
    EnvelopeLabConfig,
    EnvelopeSeries,
    EnvelopeLabResult,
    SystemIdConfig,
    SystemIdentificationResult,
)
from .signal_quality import compute_signal_quality
from .spectral import compute_welch_psd, resample_analysis_signal
from .envelopes import (
    compute_hilbert_envelope,
    compute_moving_rms_envelope,
    compute_tkeo,
    compute_psd_band_envelope,
    compute_envelope_lab,
)
from .system_id import estimate_siso_system_id

__all__ = [
    "SignalQualityConfig",
    "SignalCharacterizationResult",
    "WelchConfig",
    "SpectralAnalysisResult",
    "EnvelopeLabConfig",
    "EnvelopeSeries",
    "EnvelopeLabResult",
    "SystemIdConfig",
    "SystemIdentificationResult",
    "compute_signal_quality",
    "compute_welch_psd",
    "resample_analysis_signal",
    "compute_hilbert_envelope",
    "compute_moving_rms_envelope",
    "compute_tkeo",
    "compute_psd_band_envelope",
    "compute_envelope_lab",
    "estimate_siso_system_id",
]
