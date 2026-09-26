"""AuscultaForge — Scientific Analysis Configuration & Research Foundations.

Provides typed, declarative models for signal representations, unit systems,
spectral analysis parameters, and versioned analysis profiles.

Enforces:
1. Strict separation of Acquisition, Analysis, and Display signal representations.
2. Prohibition of uncalibrated physical units (Pa, dB SPL) without certified calibration metadata.
3. Explicit parameterization of spectral estimation (Welch, window, ENBW, detrending).
4. Traceable, versioned analysis profiles grounded in peer-reviewed literature.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
import math
from typing import Any, Optional

import numpy as np
import scipy.signal


class SignalRepresentation(str, Enum):
    """The three fundamental signal representations in AuscultaForge."""

    ACQUISITION = "acquisition"
    """Truthful, unadulterated master stream directly ingested from hardware or raw file."""

    ANALYSIS = "analysis"
    """Explicitly processed/filtered representation used for a declared engineering task."""

    DISPLAY = "display"
    """Bounded, peak-preserving decimated representation strictly used for visualization."""


class SignalUnit(str, Enum):
    """Permitted engineering units in AuscultaForge.

    Absolute physical acoustic units (PASCAL, DB_SPL) are strictly disallowed
    unless supported by a certified physical acoustic calibration chain.
    """

    RAW_PCM_CODE = "raw_pcm_code"
    """Discrete integer codes from ADC / I2S word (e.g., signed 24-bit integer)."""

    NORMALIZED_FS = "normalized_fs"
    """Dimensionless amplitude normalized to full scale, strictly within [-1.0, +1.0]."""

    FS_SQUARED_PER_HZ = "fs_squared_per_hz"
    """Power spectral density scaled to full scale squared per Hertz (FS^2 / Hz)."""

    FS_SQUARED = "fs_squared"
    """Power spectrum scaled to full scale squared (FS^2)."""

    DBFS = "dbfs"
    """Decibels relative to digital full scale: 20 * log10(|x| / 1.0) or 10 * log10(P / 1.0)."""

    RELATIVE_DB = "relative_db"
    """Relative power or amplitude ratio expressed in decibels against an explicit reference."""

    DIMENSIONLESS = "dimensionless"
    """Normalized correlation coefficients, gain ratios, coherence, or crest factors."""

    VOLTS_UNSPECIFIED = "volts_unspecified"
    """Electrical transducer voltage before acoustic calibration."""

    # Restricted acoustic physical units
    PASCAL = "pascal"
    """Acoustic pressure in Pascals (N/m^2). Requires calibrated microphone sensitivity."""

    DB_SPL = "db_spl"
    """Sound Pressure Level in dB re 20 uPa. Requires end-to-end calibrated measurement chain."""


def validate_unit_usage(unit: SignalUnit | str, has_calibration_certificate: bool = False) -> None:
    """Validate that uncalibrated physical units are not asserted without calibration metadata."""
    u_str = unit.value if isinstance(unit, SignalUnit) else str(unit).lower()
    if u_str in (SignalUnit.PASCAL.value, SignalUnit.DB_SPL.value, "pascal", "db_spl"):
        if not has_calibration_certificate:
            raise ValueError(
                f"Unit {u_str!r} requires certified physical acoustic calibration. "
                "AuscultaForge operates in uncalibrated digital full scale (normalized_fs / dBFS) "
                "until hardware sensor sensitivity (mV/Pa or dBFS/Pa) is calibrated."
            )


class DetrendMode(str, Enum):
    """Preprocessing detrending policies prior to spectral estimation."""

    NONE = "none"
    """No detrending; DC offset and drift pass into spectral bins."""

    CONSTANT = "constant"
    """Subtract the sample mean (removes DC component). Standard for stationary segments."""

    LINEAR = "linear"
    """Subtract the best-fit least-squares line (removes DC and linear drift)."""


class SpectralScaling(str, Enum):
    """Scaling mode for spectral estimation (Heinzel et al., 2002)."""

    DENSITY = "density"
    """Power Spectral Density (PSD) in V^2/Hz or FS^2/Hz. Normalizes by ENBW * fs."""

    SPECTRUM = "spectrum"
    """Power Spectrum in V^2 or FS^2. Normalizes by coherent gain squared."""


@dataclass(frozen=True)
class SpectralAnalysisConfig:
    """Typed, declarative configuration for Welch power spectral estimation.

    Directly traces to Welch (1967) and Heinzel, Rüdiger, & Schilling (2002).
    """

    window: str = "hann"
    nperseg: int = 512
    noverlap: Optional[int] = 256
    nfft: Optional[int] = None
    detrend: DetrendMode = DetrendMode.CONSTANT
    scaling: SpectralScaling = SpectralScaling.DENSITY
    frequency_min_hz: float = 0.0
    frequency_max_hz: Optional[float] = None

    def __post_init__(self) -> None:
        if self.nperseg < 8:
            raise ValueError(f"nperseg must be at least 8, got {self.nperseg}")

        effective_noverlap = self.effective_noverlap()
        if effective_noverlap < 0:
            raise ValueError(f"noverlap cannot be negative, got {effective_noverlap}")
        if effective_noverlap >= self.nperseg:
            raise ValueError(
                f"noverlap must be strictly less than nperseg ({self.nperseg}), got {effective_noverlap}"
            )

        effective_nfft = self.effective_nfft()
        if effective_nfft < self.nperseg:
            raise ValueError(
                f"nfft must be greater than or equal to nperseg ({self.nperseg}), got {effective_nfft}"
            )

        if self.frequency_min_hz < 0.0:
            raise ValueError(f"frequency_min_hz must be non-negative, got {self.frequency_min_hz}")

        if self.frequency_max_hz is not None and self.frequency_max_hz <= self.frequency_min_hz:
            raise ValueError(
                f"frequency_max_hz ({self.frequency_max_hz}) must be greater than "
                f"frequency_min_hz ({self.frequency_min_hz})"
            )

    def effective_noverlap(self) -> int:
        """Return explicit noverlap or default nperseg // 2."""
        return self.nperseg // 2 if self.noverlap is None else self.noverlap

    def effective_nfft(self) -> int:
        """Return explicit nfft or default nperseg."""
        return self.nperseg if self.nfft is None else self.nfft

    def frequency_bin_spacing(self, sample_rate_hz: float) -> float:
        """Calculate discrete frequency bin width: Delta_f = f_s / N_fft."""
        if sample_rate_hz <= 0:
            raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
        return float(sample_rate_hz) / float(self.effective_nfft())

    def enbw(self, sample_rate_hz: float) -> float:
        """Compute Equivalent Noise Bandwidth (ENBW) in Hertz.

        Equation (Heinzel et al., 2002, Eq. 17):
            ENBW = f_s * (sum(w[n]^2) / (sum(w[n]))^2)
        """
        if sample_rate_hz <= 0:
            raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")

        win = scipy.signal.get_window(self.window, self.nperseg, fftbins=True)
        s1 = float(np.sum(win))
        s2 = float(np.sum(win**2))
        if s1 == 0.0:
            raise ValueError(f"Window {self.window!r} has zero sum; ENBW undefined.")
        enbw_bins = s2 / (s1**2)
        return float(sample_rate_hz) * enbw_bins

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to JSON-safe dictionary."""
        return {
            "window": self.window,
            "nperseg": self.nperseg,
            "noverlap": self.effective_noverlap(),
            "nfft": self.effective_nfft(),
            "detrend": self.detrend.value,
            "scaling": self.scaling.value,
            "frequency_min_hz": self.frequency_min_hz,
            "frequency_max_hz": self.frequency_max_hz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpectralAnalysisConfig:
        """Deserialize from dictionary."""
        return cls(
            window=data.get("window", "hann"),
            nperseg=int(data.get("nperseg", 512)),
            noverlap=int(data["noverlap"]) if "noverlap" in data and data["noverlap"] is not None else None,
            nfft=int(data["nfft"]) if "nfft" in data and data["nfft"] is not None else None,
            detrend=DetrendMode(data.get("detrend", "constant")),
            scaling=SpectralScaling(data.get("scaling", "density")),
            frequency_min_hz=float(data.get("frequency_min_hz", 0.0)),
            frequency_max_hz=float(data["frequency_max_hz"]) if data.get("frequency_max_hz") is not None else None,
        )


@dataclass(frozen=True)
class AnalysisProfile:
    """Versioned scientific configuration profile for PCG processing and validation.

    Guarantees deterministic, reproducible parameterization traceable to literature sources.
    """

    profile_id: str
    profile_version: str
    purpose: str
    sample_rate_policy: str
    filter_policy: str
    spectral_policy: SpectralAnalysisConfig
    feature_policy: dict[str, Any] = field(default_factory=dict)
    segmentation_policy: Optional[str] = None
    calibration_requirement: str = "uncalibrated_relative_only"
    literature_sources: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to JSON-safe dictionary."""
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "purpose": self.purpose,
            "sample_rate_policy": self.sample_rate_policy,
            "filter_policy": self.filter_policy,
            "spectral_policy": self.spectral_policy.to_dict(),
            "feature_policy": dict(self.feature_policy),
            "segmentation_policy": self.segmentation_policy,
            "calibration_requirement": self.calibration_requirement,
            "literature_sources": list(self.literature_sources),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisProfile:
        """Deserialize profile from dictionary."""
        return cls(
            profile_id=data["profile_id"],
            profile_version=data.get("profile_version", "1.0.0"),
            purpose=data.get("purpose", ""),
            sample_rate_policy=data.get("sample_rate_policy", "native"),
            filter_policy=data.get("filter_policy", "none"),
            spectral_policy=SpectralAnalysisConfig.from_dict(data.get("spectral_policy", {})),
            feature_policy=data.get("feature_policy", {}),
            segmentation_policy=data.get("segmentation_policy"),
            calibration_requirement=data.get("calibration_requirement", "uncalibrated_relative_only"),
            literature_sources=tuple(data.get("literature_sources", ())),
        )


# =============================================================================
# Predefined Standard Analysis Profiles
# =============================================================================

RAW_INTEGRITY_V1 = AnalysisProfile(
    profile_id="RAW_INTEGRITY_V1",
    profile_version="1.0.0",
    purpose="Hardware packet ingestion integrity, drop counting, and bit-exact raw capture.",
    sample_rate_policy="native_48000_hz",
    filter_policy="none",
    spectral_policy=SpectralAnalysisConfig(
        window="hann",
        nperseg=2048,
        noverlap=1024,
        scaling=SpectralScaling.DENSITY,
        detrend=DetrendMode.NONE,
    ),
    feature_policy={"compute_clipping": True, "bit_depth": 24},
    calibration_requirement="uncalibrated_raw_code",
    literature_sources=("R002", "R003"),
)

GENERAL_PCG_V1 = AnalysisProfile(
    profile_id="GENERAL_PCG_V1",
    profile_version="1.0.0",
    purpose="Engineering live monitoring using 20–600 Hz 4th-order Butterworth bandpass filter.",
    sample_rate_policy="native_or_resampled",
    filter_policy="butterworth_bandpass_20_600_hz_order4_causal",
    spectral_policy=SpectralAnalysisConfig(
        window="hann",
        nperseg=512,
        noverlap=256,
        scaling=SpectralScaling.DENSITY,
        detrend=DetrendMode.CONSTANT,
    ),
    feature_policy={"compute_rms": True, "compute_crest_factor": True, "band_energy_ratios": True},
    calibration_requirement="normalized_full_scale",
    literature_sources=("R001", "R002", "R004"),
)

PHANTOM_VALIDATION_V1 = AnalysisProfile(
    profile_id="PHANTOM_VALIDATION_V1",
    profile_version="1.0.0",
    purpose="Quantitative reference-vs-capture alignment, delay estimation, and least-squares gain.",
    sample_rate_policy="resample_capture_to_reference",
    filter_policy="pre_comparison_matching_filter",
    spectral_policy=SpectralAnalysisConfig(
        window="hann",
        nperseg=512,
        noverlap=256,
        nfft=512,
        scaling=SpectralScaling.DENSITY,
        detrend=DetrendMode.CONSTANT,
        frequency_max_hz=1000.0,
    ),
    feature_policy={
        "cross_correlation": True,
        "least_squares_gain": True,
        "rmse": True,
        "nrmse": True,
        "ser_db": True,
        "coherence": True,
    },
    calibration_requirement="relative_comparison_only",
    literature_sources=("R001", "R002", "R003", "R004"),
)

PCG_EVENT_FEATURES_V1 = AnalysisProfile(
    profile_id="PCG_EVENT_FEATURES_V1",
    profile_version="1.0.0",
    purpose="Deterministic envelope extraction (Hilbert, homomorphic, energy) for acoustic event candidates.",
    sample_rate_policy="decimate_to_1000_hz",
    filter_policy="butterworth_bandpass_25_400_hz_order4",
    spectral_policy=SpectralAnalysisConfig(
        window="hamming",
        nperseg=256,
        noverlap=128,
        detrend=DetrendMode.CONSTANT,
    ),
    feature_policy={
        "hilbert_envelope": True,
        "homomorphic_envelope": True,
        "energy_envelope": True,
        "candidate_peaks_only": True,
    },
    calibration_requirement="normalized_full_scale",
    literature_sources=("R001", "R005", "R006"),
)

SPRINGER_SEGMENTATION_RESEARCH_V1 = AnalysisProfile(
    profile_id="SPRINGER_SEGMENTATION_RESEARCH_V1",
    profile_version="1.0.0",
    purpose="Research reproduction profile for Springer et al. (2016) 4-feature downsampled stream.",
    sample_rate_policy="downsample_to_1000_hz_then_features_to_50_hz",
    filter_policy="butterworth_bandpass_25_400_hz_order4",
    spectral_policy=SpectralAnalysisConfig(
        window="hann",
        nperseg=128,
        noverlap=64,
        detrend=DetrendMode.CONSTANT,
    ),
    feature_policy={
        "homomorphic_envelope": True,
        "hilbert_envelope": True,
        "wavelet_envelope": True,
        "psd_envelope": True,
        "feature_sampling_rate_hz": 50.0,
    },
    segmentation_policy="lr_hsmm_modified_viterbi_planned",
    calibration_requirement="dimensionless_features",
    literature_sources=("R005", "R006", "R007"),
)

STANDARD_PROFILES: dict[str, AnalysisProfile] = {
    RAW_INTEGRITY_V1.profile_id: RAW_INTEGRITY_V1,
    GENERAL_PCG_V1.profile_id: GENERAL_PCG_V1,
    PHANTOM_VALIDATION_V1.profile_id: PHANTOM_VALIDATION_V1,
    PCG_EVENT_FEATURES_V1.profile_id: PCG_EVENT_FEATURES_V1,
    SPRINGER_SEGMENTATION_RESEARCH_V1.profile_id: SPRINGER_SEGMENTATION_RESEARCH_V1,
}


def get_analysis_profile(profile_id: str, version: Optional[str] = None) -> AnalysisProfile:
    """Retrieve standard profile by ID. Raises KeyError if unrecognized."""
    clean_id = profile_id.strip()
    if clean_id not in STANDARD_PROFILES:
        raise KeyError(
            f"Unknown analysis profile {profile_id!r}. Supported profiles: {list(STANDARD_PROFILES.keys())}"
        )
    profile = STANDARD_PROFILES[clean_id]
    if version and profile.profile_version != version:
        raise KeyError(
            f"Profile {profile_id} version mismatch: requested {version}, available {profile.profile_version}"
        )
    return profile


def list_analysis_profiles() -> list[AnalysisProfile]:
    """Return all registered standard analysis profiles."""
    return list(STANDARD_PROFILES.values())
