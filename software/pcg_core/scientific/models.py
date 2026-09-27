"""AuscultaForge — Scientific Models & Versioned Configuration Schemas.

Defines deterministic, JSON-safe data structures for:
- Signal Quality Characterization
- Spectral Analysis (Welch PSD, bin spacing, ENBW)
- Envelope Lab (Hilbert, Moving RMS, TKEO, PSD-band)
- System Identification Foundation (SISO H1 FRF, coherence, autospectra, cross-spectrum)

All floating-point lists guarantee finite JSON serialization (NaN / Inf sanitized).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import math
from typing import Any, Optional
import numpy as np


def sanitize_float(val: float | int | None, default: float = 0.0) -> float:
    """Ensure floating-point value is finite and JSON-serializable."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def sanitize_list(arr: np.ndarray | list[float] | None, default_val: float = 0.0) -> list[float]:
    """Convert array or list to a JSON-safe list of finite floats."""
    if arr is None:
        return []
    if isinstance(arr, np.ndarray):
        flat = arr.flatten()
        clean = np.where(np.isnan(flat) | np.isinf(flat), default_val, flat)
        return [float(x) for x in clean]
    return [sanitize_float(x, default_val) for x in arr]


# ============================================================================
# 1. SIGNAL QUALITY CONFIGURATION & RESULT
# ============================================================================

@dataclass(slots=True)
class SignalQualityConfig:
    """Configuration for deterministic signal quality characterization."""
    schema_version: str = "1.0.0"
    clipping_threshold: float = 0.999
    compute_zcr: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SignalCharacterizationResult:
    """Quantitative scalar signal quality metrics evaluated on full-rate analysis arrays.
    
    Digital saturation count and fraction reflect digital full-scale utilization (samples >= threshold),
    which does NOT automatically prove physical acoustic overload at the microphone diaphragm.
    Zero-crossing rate is a generic waveform statistic, NOT a heart-sound quality classifier.
    """
    schema_version: str = "1.0.0"
    sample_count: int = 0
    duration_s: float = 0.0
    sample_rate_hz: float = 0.0
    mean_dc: float = 0.0
    rms: float = 0.0
    peak_absolute: float = 0.0
    peak_to_peak: float = 0.0
    crest_factor: float = 0.0
    digital_full_scale_utilization: float = 0.0
    digital_saturation_count: int = 0
    digital_saturation_fraction: float = 0.0
    zero_crossing_rate: Optional[float] = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sample_count": self.sample_count,
            "duration_s": round(sanitize_float(self.duration_s), 4),
            "sample_rate_hz": sanitize_float(self.sample_rate_hz),
            "mean_dc": round(sanitize_float(self.mean_dc), 6),
            "rms": round(sanitize_float(self.rms), 6),
            "peak_absolute": round(sanitize_float(self.peak_absolute), 6),
            "peak_to_peak": round(sanitize_float(self.peak_to_peak), 6),
            "crest_factor": round(sanitize_float(self.crest_factor), 4),
            "digital_full_scale_utilization": round(sanitize_float(self.digital_full_scale_utilization), 4),
            "digital_saturation_count": self.digital_saturation_count,
            "digital_saturation_fraction": round(sanitize_float(self.digital_saturation_fraction), 6),
            "zero_crossing_rate": round(sanitize_float(self.zero_crossing_rate), 6) if self.zero_crossing_rate is not None else None,
            "provenance": dict(self.provenance),
        }


# ============================================================================
# 2. SPECTRAL CONFIGURATION & RESULT
# ============================================================================

@dataclass(slots=True)
class WelchConfig:
    """Configuration for scientific Welch Power Spectral Density estimation."""
    schema_version: str = "1.0.0"
    nperseg: int = 512
    noverlap: Optional[int] = None
    nfft: Optional[int] = None
    window: str = "hann"
    detrend: str = "constant"
    scaling: str = "density"
    relative_db_ref: float = 1.0

    def effective_noverlap(self) -> int:
        return self.nperseg // 2 if self.noverlap is None else self.noverlap

    def effective_nfft(self) -> int:
        return self.nperseg if self.nfft is None else self.nfft

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nperseg": self.nperseg,
            "noverlap": self.noverlap,
            "effective_noverlap": self.effective_noverlap(),
            "nfft": self.nfft,
            "effective_nfft": self.effective_nfft(),
            "window": self.window,
            "detrend": self.detrend,
            "scaling": self.scaling,
            "relative_db_ref": self.relative_db_ref,
        }


@dataclass(slots=True)
class SpectralAnalysisResult:
    """Deterministic Welch Power Spectral Density result.
    
    Units: normalized_amplitude^2 / Hz for density scaling.
    Relative dB values are referenced explicitly to relative_db_ref (1.0 FS^2/Hz by default).
    Frequency-bin spacing Delta_f = fs / N_fft defines the discrete grid spacing, not physical resolving power.
    """
    schema_version: str = "1.0.0"
    sample_rate_hz: float = 0.0
    frequencies_hz: list[float] = field(default_factory=list)
    psd: list[float] = field(default_factory=list)
    psd_relative_db: list[float] = field(default_factory=list)
    frequency_bin_spacing_hz: float = 0.0
    actual_segments: int = 0
    enbw_hz: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sample_rate_hz": sanitize_float(self.sample_rate_hz),
            "frequencies_hz": sanitize_list(self.frequencies_hz),
            "psd": sanitize_list(self.psd),
            "psd_relative_db": sanitize_list(self.psd_relative_db),
            "frequency_bin_spacing_hz": round(sanitize_float(self.frequency_bin_spacing_hz), 4),
            "actual_segments": self.actual_segments,
            "enbw_hz": round(sanitize_float(self.enbw_hz), 4),
            "config": dict(self.config),
            "provenance": dict(self.provenance),
        }


# ============================================================================
# 3. ENVELOPE LAB CONFIGURATION & RESULT
# ============================================================================

@dataclass(slots=True)
class EnvelopeLabConfig:
    """Configuration for Stage-A deterministic envelope extraction."""
    schema_version: str = "1.0.0"
    rms_window_duration_s: float = 0.02
    tkeo_boundary_policy: str = "replicate"  # 'replicate' or 'zero'
    psd_band_hz: tuple[float, float] = (40.0, 60.0)
    psd_window_duration_s: float = 0.05
    psd_overlap_fraction: float = 0.5
    psd_window_type: str = "hamming"
    profile_behavior: str = "SPRINGER_RESEARCH"
    homomorphic_status: str = "DEFERRED_STAGE_B"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rms_window_duration_s": self.rms_window_duration_s,
            "tkeo_boundary_policy": self.tkeo_boundary_policy,
            "psd_band_hz": list(self.psd_band_hz),
            "psd_window_duration_s": self.psd_window_duration_s,
            "psd_overlap_fraction": self.psd_overlap_fraction,
            "psd_window_type": self.psd_window_type,
            "profile_behavior": self.profile_behavior,
            "homomorphic_status": self.homomorphic_status,
        }


@dataclass(slots=True)
class EnvelopeSeries:
    """Single envelope extractor output stream."""
    algorithm: str
    sample_rate_hz: float
    time_s: list[float]
    values: list[float]
    parameters: dict[str, Any] = field(default_factory=dict)
    input_sample_count: int = 0
    output_sample_count: int = 0
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "sample_rate_hz": sanitize_float(self.sample_rate_hz),
            "time_s": sanitize_list(self.time_s),
            "values": sanitize_list(self.values),
            "parameters": dict(self.parameters),
            "input_sample_count": self.input_sample_count,
            "output_sample_count": self.output_sample_count,
            "provenance": dict(self.provenance),
        }


@dataclass(slots=True)
class EnvelopeLabResult:
    """Multi-envelope analysis result container."""
    schema_version: str = "1.0.0"
    input_sample_rate_hz: float = 0.0
    input_duration_s: float = 0.0
    envelopes: dict[str, EnvelopeSeries] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "input_sample_rate_hz": sanitize_float(self.input_sample_rate_hz),
            "input_duration_s": round(sanitize_float(self.input_duration_s), 4),
            "envelopes": {k: v.to_dict() for k, v in self.envelopes.items()},
            "provenance": dict(self.provenance),
        }


# ============================================================================
# 4. SYSTEM IDENTIFICATION CONFIGURATION & RESULT
# ============================================================================

@dataclass(slots=True)
class SystemIdConfig:
    """Configuration for SISO best-linear frequency response estimation (H1 model)."""
    schema_version: str = "1.0.0"
    nperseg: int = 1024
    noverlap: Optional[int] = 512
    nfft: Optional[int] = None
    window: str = "hann"
    detrend: str = "constant"
    excited_band_hz: tuple[float, float] = (20.0, 1000.0)
    energy_threshold_db_rel_max: float = -30.0
    analysis_profile: str = "BROADBAND_SYSTEM_ID_V1"

    def effective_noverlap(self) -> int:
        return self.nperseg // 2 if self.noverlap is None else self.noverlap

    def effective_nfft(self) -> int:
        return self.nperseg if self.nfft is None else self.nfft

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nperseg": self.nperseg,
            "noverlap": self.noverlap,
            "effective_noverlap": self.effective_noverlap(),
            "nfft": self.nfft,
            "effective_nfft": self.effective_nfft(),
            "window": self.window,
            "detrend": self.detrend,
            "excited_band_hz": list(self.excited_band_hz),
            "energy_threshold_db_rel_max": self.energy_threshold_db_rel_max,
            "analysis_profile": self.analysis_profile,
        }


@dataclass(slots=True)
class SystemIdentificationResult:
    """SISO Best-Linear Frequency Response Function (FRF) and Coherence Result.
    
    Model:
        Input: x[n] (measured reference excitation)
        Output: y[n] (measured capture)
        H1-style FRF: H1(f) = Sxy(f) / Sxx(f)
        Convention: scipy.signal.csd(x, y) computes <conj(X) * Y>
        Coherence: gamma_xy^2(f) = |Sxy(f)|^2 / (Sxx(f) * Syy(f))
        Coherent output: gamma_xy^2(f) * Syy(f)
        Residual output: (1 - gamma_xy^2(f)) * Syy(f)
    
    Boundary & Metrology Note:
        In phantom experiments (stimulus -> DAC -> amp -> speaker -> phantom -> coupling -> chestpiece -> sensor -> acquisition),
        this characterizes the complete END-TO-END transmission chain. It is NOT an isolated stethoscope FRF, NOT anatomical
        chest response, and magnitude-squared coherence alone does NOT establish physical causality.
    """
    schema_version: str = "1.0.0"
    sample_rate_hz: float = 0.0
    input_name: str = ""
    output_name: str = ""
    frequencies_hz: list[float] = field(default_factory=list)
    gxx_autospectrum: list[float] = field(default_factory=list)
    gyy_autospectrum: list[float] = field(default_factory=list)
    gxy_cross_spectrum_real: list[float] = field(default_factory=list)
    gxy_cross_spectrum_imag: list[float] = field(default_factory=list)
    coherence: list[float] = field(default_factory=list)
    h1_magnitude: list[float] = field(default_factory=list)
    h1_magnitude_db: list[float] = field(default_factory=list)
    h1_phase_rad: list[float] = field(default_factory=list)
    h1_phase_deg: list[float] = field(default_factory=list)
    h1_phase_unwrapped_deg: Optional[list[float]] = None
    coherent_output_spectrum: list[float] = field(default_factory=list)
    residual_output_spectrum: list[float] = field(default_factory=list)
    excited_frequency_mask: list[bool] = field(default_factory=list)
    excited_bins_count: int = 0
    mean_coherence_over_excited_band: Optional[float] = None
    frequency_bin_spacing_hz: float = 0.0
    notes: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sample_rate_hz": sanitize_float(self.sample_rate_hz),
            "input_name": self.input_name,
            "output_name": self.output_name,
            "frequencies_hz": sanitize_list(self.frequencies_hz),
            "gxx_autospectrum": sanitize_list(self.gxx_autospectrum),
            "gyy_autospectrum": sanitize_list(self.gyy_autospectrum),
            "gxy_cross_spectrum_real": sanitize_list(self.gxy_cross_spectrum_real),
            "gxy_cross_spectrum_imag": sanitize_list(self.gxy_cross_spectrum_imag),
            "coherence": sanitize_list(self.coherence),
            "h1_magnitude": sanitize_list(self.h1_magnitude),
            "h1_magnitude_db": sanitize_list(self.h1_magnitude_db),
            "h1_phase_rad": sanitize_list(self.h1_phase_rad),
            "h1_phase_deg": sanitize_list(self.h1_phase_deg),
            "h1_phase_unwrapped_deg": sanitize_list(self.h1_phase_unwrapped_deg) if self.h1_phase_unwrapped_deg is not None else None,
            "coherent_output_spectrum": sanitize_list(self.coherent_output_spectrum),
            "residual_output_spectrum": sanitize_list(self.residual_output_spectrum),
            "excited_frequency_mask": [bool(b) for b in self.excited_frequency_mask],
            "excited_bins_count": self.excited_bins_count,
            "mean_coherence_over_excited_band": round(sanitize_float(self.mean_coherence_over_excited_band), 4) if self.mean_coherence_over_excited_band is not None else None,
            "frequency_bin_spacing_hz": round(sanitize_float(self.frequency_bin_spacing_hz), 4),
            "notes": self.notes,
            "provenance": dict(self.provenance),
        }
