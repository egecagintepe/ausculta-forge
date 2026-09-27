"""AuscultaForge — Springer Segmentation Configuration & Profiles.

Defines explicit configuration structures and provenance profiles distinguishing:
1. SPRINGER_PHYSIONET_REFERENCE_V1:
   - Released PhysioNet reference implementation conventions
   - 25–400 Hz zero-phase Butterworth bandpass
   - Schmidt spike removal (500 ms window, 3x median threshold)
   - 8 Hz zero-phase homomorphic low-pass filter
   - Default 3-feature stream (wavelet disabled by default)
   - 50 Hz feature stream
2. SPRINGER_PAPER_4FEATURE_V1:
   - Primary publication (Springer et al. 2016, R006) conventions
   - 4-feature stream (Homomorphic, Hilbert, Wavelet rbio3.9, PSD 40–60 Hz)
   - Paper-documented feature timing and overlap
   - 50 Hz feature stream
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Tuple


@dataclass(slots=True)
class SpringerProfileConfig:
    """Configurable pipeline parameters for Springer LR-HSMM segmentation."""
    profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1"
    analysis_sample_rate_hz: float = 1000.0
    feature_sample_rate_hz: float = 50.0

    # Preprocessing
    apply_bandpass_25_400: bool = True
    bandpass_low_hz: float = 25.0
    bandpass_high_hz: float = 400.0
    bandpass_order: int = 2  # Design order 2 -> effective order 4 with zero-phase filtfilt

    # Schmidt Spike Removal
    apply_spike_removal: bool = True
    spike_window_ms: float = 500.0
    spike_threshold_multiplier: float = 3.0
    spike_max_iterations: int = 50

    # Homomorphic Envelope
    homomorphic_lowpass_hz: float = 8.0
    homomorphic_filter_order: int = 1  # 1st-order Butterworth design -> effective order 2 zero-phase

    # PSD Feature
    psd_band_hz: Tuple[float, float] = (40.0, 60.0)
    psd_window_ms: float = 50.0
    psd_overlap_fraction: float = 0.5
    psd_window_type: str = "hamming"
    psd_mode: str = "reference"  # "reference" or "paper"

    # Wavelet Feature
    include_wavelet: bool = False
    wavelet_name: str = "rbio3.9"
    wavelet_level: int = 3

    # Normalization & Training
    per_recording_z_score: bool = True
    random_seed: int = 42

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["psd_band_hz"] = list(self.psd_band_hz)
        return d

    @property
    def feature_names(self) -> list[str]:
        names = ["homomorphic", "hilbert", "psd"]
        if self.include_wavelet:
            names.append("wavelet")
        return names

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)


# Standard Provenance Profile: PhysioNet HSS Reference Implementation (v1.0)
SPRINGER_PHYSIONET_REFERENCE_V1 = SpringerProfileConfig(
    profile_id="SPRINGER_PHYSIONET_REFERENCE_V1",
    analysis_sample_rate_hz=1000.0,
    feature_sample_rate_hz=50.0,
    apply_bandpass_25_400=True,
    bandpass_low_hz=25.0,
    bandpass_high_hz=400.0,
    bandpass_order=2,
    apply_spike_removal=True,
    spike_window_ms=500.0,
    spike_threshold_multiplier=3.0,
    spike_max_iterations=50,
    homomorphic_lowpass_hz=8.0,
    homomorphic_filter_order=1,
    psd_band_hz=(40.0, 60.0),
    psd_window_ms=50.0,
    psd_overlap_fraction=0.5,
    psd_window_type="hamming",
    psd_mode="reference",
    include_wavelet=False,  # PhysioNet reference default
    per_recording_z_score=True,
    random_seed=42,
)

# Standard Provenance Profile: Springer et al. (2016) Paper Model (R006)
SPRINGER_PAPER_4FEATURE_V1 = SpringerProfileConfig(
    profile_id="SPRINGER_PAPER_4FEATURE_V1",
    analysis_sample_rate_hz=1000.0,
    feature_sample_rate_hz=50.0,
    apply_bandpass_25_400=False,  # Paper specifies 1000 Hz polyphase without explicit 25-400 mention in feature section
    apply_spike_removal=False,
    homomorphic_lowpass_hz=8.0,
    homomorphic_filter_order=1,
    psd_band_hz=(40.0, 60.0),
    psd_window_ms=50.0,
    psd_overlap_fraction=0.5,
    psd_window_type="hamming",
    psd_mode="paper",
    include_wavelet=True,  # Paper's best model included level 3 wavelet
    wavelet_name="rbio3.9",
    wavelet_level=3,
    per_recording_z_score=True,
    random_seed=42,
)

SUPPORTED_SPRINGER_PROFILES = {
    SPRINGER_PHYSIONET_REFERENCE_V1.profile_id: SPRINGER_PHYSIONET_REFERENCE_V1,
    SPRINGER_PAPER_4FEATURE_V1.profile_id: SPRINGER_PAPER_4FEATURE_V1,
}

SPRINGER_PROFILES = SUPPORTED_SPRINGER_PROFILES


def get_springer_profile(profile_id: str) -> SpringerProfileConfig:
    """Retrieve Springer profile configuration by ID or raise ValueError."""
    if profile_id not in SUPPORTED_SPRINGER_PROFILES:
        raise ValueError(
            f"Unknown Springer profile: {profile_id}. Available: {list(SUPPORTED_SPRINGER_PROFILES.keys())}"
        )
    return SUPPORTED_SPRINGER_PROFILES[profile_id]

