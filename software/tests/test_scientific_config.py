"""AuscultaForge — Automated Tests for Scientific Configuration & Foundations.

Verifies:
- SignalRepresentation boundaries (Acquisition vs Analysis vs Display)
- Unit system rules (strict prohibition of uncalibrated Pa / dB SPL without calibration)
- SpectralAnalysisConfig validation (nperseg, noverlap, nfft, frequency bounds)
- Frequency-bin spacing calculation (Delta_f = fs / N_fft)
- Equivalent Noise Bandwidth (ENBW) calculation for canonical windows
- AnalysisProfile serialization, deserialization, and registry
- Backward compatibility of AnalysisService with legacy reports lacking profile metadata
"""

import json
from pathlib import Path

import numpy as np
import pytest

from pcg_core.scientific_config import (
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
)
from pcg_app.analysis_service import AnalysisService


class TestSignalRepresentationsAndUnits:
    """Verifies architectural signal representation invariants and strict unit policies."""

    def test_signal_representation_values(self):
        assert SignalRepresentation.ACQUISITION.value == "acquisition"
        assert SignalRepresentation.ANALYSIS.value == "analysis"
        assert SignalRepresentation.DISPLAY.value == "display"

    def test_permitted_uncalibrated_units(self):
        # Permitted uncalibrated units must validate without error
        permitted = [
            SignalUnit.RAW_PCM_CODE,
            SignalUnit.NORMALIZED_FS,
            SignalUnit.FS_SQUARED_PER_HZ,
            SignalUnit.FS_SQUARED,
            SignalUnit.DBFS,
            SignalUnit.RELATIVE_DB,
            SignalUnit.DIMENSIONLESS,
            SignalUnit.VOLTS_UNSPECIFIED,
        ]
        for u in permitted:
            validate_unit_usage(u, has_acoustic_calibration=False)

    def test_restricted_acoustic_units_rejected_without_calibration(self):
        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage(SignalUnit.PASCAL, has_acoustic_calibration=False)

        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage(SignalUnit.DB_SPL, has_acoustic_calibration=False)

        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage("pascal", has_acoustic_calibration=False)

        # Legacy alias has_calibration_certificate also works
        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage(SignalUnit.PASCAL, has_calibration_certificate=False)

    def test_restricted_acoustic_units_accepted_with_explicit_calibration(self):
        # When acoustic calibration is present, validation passes
        validate_unit_usage(SignalUnit.PASCAL, has_acoustic_calibration=True)
        validate_unit_usage(SignalUnit.DB_SPL, has_acoustic_calibration=True)
        # Legacy parameter alias supported
        validate_unit_usage(SignalUnit.PASCAL, has_calibration_certificate=True)
        validate_unit_usage(SignalUnit.DB_SPL, has_calibration_certificate=True)


class TestSpectralAnalysisConfig:
    """Verifies Welch parameter validation, frequency bin spacing, and ENBW."""

    def test_default_config_valid(self):
        cfg = SpectralAnalysisConfig()
        assert cfg.window == "hann"
        assert cfg.nperseg == 512
        assert cfg.effective_noverlap() == 256
        assert cfg.effective_nfft() == 512
        assert cfg.detrend == DetrendMode.CONSTANT
        assert cfg.scaling == SpectralScaling.DENSITY

    def test_rejects_invalid_noverlap(self):
        with pytest.raises(ValueError, match="strictly less than nperseg"):
            SpectralAnalysisConfig(nperseg=256, noverlap=256)

        with pytest.raises(ValueError, match="strictly less than nperseg"):
            SpectralAnalysisConfig(nperseg=256, noverlap=300)

        with pytest.raises(ValueError, match="cannot be negative"):
            SpectralAnalysisConfig(nperseg=256, noverlap=-1)

    def test_rejects_nfft_less_than_nperseg(self):
        with pytest.raises(ValueError, match="greater than or equal to nperseg"):
            SpectralAnalysisConfig(nperseg=512, nfft=256)

    def test_rejects_invalid_frequency_bounds(self):
        with pytest.raises(ValueError, match="frequency_min_hz must be non-negative"):
            SpectralAnalysisConfig(frequency_min_hz=-10.0)

        with pytest.raises(ValueError, match="must be greater than"):
            SpectralAnalysisConfig(frequency_min_hz=100.0, frequency_max_hz=50.0)

    def test_frequency_bin_spacing(self):
        # 48000 Hz / 512 samples = 93.75 Hz
        cfg_512 = SpectralAnalysisConfig(nperseg=512)
        assert cfg_512.frequency_bin_spacing(48000) == pytest.approx(93.75)

        # 48000 Hz / 2048 FFT = 23.4375 Hz
        cfg_2048 = SpectralAnalysisConfig(nperseg=512, nfft=2048)
        assert cfg_2048.frequency_bin_spacing(48000) == pytest.approx(23.4375)

        # 4000 Hz / 512 samples = 7.8125 Hz
        assert cfg_512.frequency_bin_spacing(4000) == pytest.approx(7.8125)

    def test_enbw_canonical_windows(self):
        fs = 1000.0
        n = 1024

        # For Hann window: theoretical normalized ENBW is 1.50 bins
        cfg_hann = SpectralAnalysisConfig(window="hann", nperseg=n)
        bin_width_hann = fs / n
        expected_hann_enbw = 1.50 * bin_width_hann
        assert cfg_hann.enbw(fs) == pytest.approx(expected_hann_enbw, rel=0.01)

        # For Rectangular window (boxcar): theoretical normalized ENBW is 1.00 bin
        cfg_rect = SpectralAnalysisConfig(window="boxcar", nperseg=n)
        bin_width_rect = fs / n
        assert cfg_rect.enbw(fs) == pytest.approx(1.00 * bin_width_rect, rel=0.01)

        # For Hamming window: theoretical normalized ENBW is approx 1.36 bins
        cfg_hamming = SpectralAnalysisConfig(window="hamming", nperseg=n)
        assert cfg_hamming.enbw(fs) == pytest.approx(1.36 * bin_width_rect, rel=0.02)

    def test_config_serialization_roundtrip(self):
        cfg = SpectralAnalysisConfig(
            window="hamming",
            nperseg=256,
            noverlap=128,
            nfft=512,
            detrend=DetrendMode.LINEAR,
            scaling=SpectralScaling.SPECTRUM,
            frequency_min_hz=20.0,
            frequency_max_hz=600.0,
        )
        data = cfg.to_dict()
        restored = SpectralAnalysisConfig.from_dict(data)
        assert restored == cfg


class TestAnalysisProfiles:
    """Verifies AnalysisProfile models, standard profile registry, and serialization."""

    def test_standard_profiles_exist(self):
        profiles = list_analysis_profiles()
        assert len(profiles) >= 5

        ids = [p.profile_id for p in profiles]
        assert "RAW_INTEGRITY_V1" in ids
        assert "GENERAL_PCG_V1" in ids
        assert "PHANTOM_VALIDATION_V1" in ids
        assert "PCG_EVENT_FEATURES_V1" in ids
        assert "SPRINGER_SEGMENTATION_RESEARCH_V1" in ids

    def test_get_analysis_profile_success_and_failure(self):
        p = get_analysis_profile("GENERAL_PCG_V1")
        assert p.profile_id == "GENERAL_PCG_V1"
        assert p.profile_version == "1.0.0"

        with pytest.raises(KeyError, match="Unknown analysis profile"):
            get_analysis_profile("NON_EXISTENT_PROFILE")

        with pytest.raises(KeyError, match="version mismatch"):
            get_analysis_profile("GENERAL_PCG_V1", version="2.0.0")

    def test_profile_serialization_roundtrip(self):
        profile = PHANTOM_VALIDATION_V1
        d = profile.to_dict()
        assert d["profile_id"] == "PHANTOM_VALIDATION_V1"
        assert "spectral_policy" in d

        restored = AnalysisProfile.from_dict(d)
        assert restored.profile_id == profile.profile_id
        assert restored.profile_version == profile.profile_version
        assert restored.spectral_policy == profile.spectral_policy
        assert restored.literature_sources == profile.literature_sources

    def test_legacy_report_compatibility_without_profile(self, tmp_path: Path):
        """Verifies that an older comparison report without profile fields reloads cleanly."""
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        legacy_analysis_id = "cmp_legacy_test_01"
        rep_dir = tmp_path / "analysis" / legacy_analysis_id
        rep_dir.mkdir(parents=True, exist_ok=True)

        legacy_data = {
            "version": "1.0",
            "analysis_id": legacy_analysis_id,
            "created_at_utc": "2026-09-20T12:00:00Z",
            "reference": {"asset_id": "ref_old", "filename": "old.wav", "sha256": "abc"},
            "capture": {"session_id": "sess_old", "wav_sha256": "def"},
            "alignment": {"delay_samples": 0, "delay_ms": 0.0, "overlap_samples": 1000},
            "metrics": {"normalized_cross_correlation": 0.99},
            "provenance": {
                "app_version": "0.1.0",
                "python_version": "3.11.0",
                "numpy_version": "1.26.0",
                "scipy_version": "1.11.0",
                # Note: analysis_profile_id and analysis_profile_version are absent
            },
        }
        (rep_dir / "comparison.json").write_text(json.dumps(legacy_data), encoding="utf-8")

        # Reload report via service
        loaded = service.get_comparison_report(legacy_analysis_id)
        assert loaded is not None
        assert loaded["analysis_id"] == legacy_analysis_id
        assert "provenance" in loaded
        assert "analysis_profile_id" not in loaded["provenance"]  # Not retroactively falsified


class TestScientificConsistencyRegression:
    """Verifies that standard analysis profiles do not contradict their typed configurations."""

    def test_raw_integrity_profile_consistency(self):
        p = RAW_INTEGRITY_V1
        assert p.profile_id == "RAW_INTEGRITY_V1"
        assert p.sample_rate_policy == "native_48000_hz"
        assert p.filter_policy == "none"
        assert p.calibration_requirement == "uncalibrated_raw_code"
        assert p.spectral_policy.nperseg == 2048
        assert p.spectral_policy.effective_noverlap() == 1024
        assert p.spectral_policy.effective_nfft() == 2048
        assert p.spectral_policy.detrend == DetrendMode.NONE
        assert p.spectral_policy.scaling == SpectralScaling.DENSITY
        assert p.feature_policy["container_bits"] == 32
        assert p.feature_policy["transmitted_data_bits"] == 24

    def test_general_pcg_profile_consistency(self):
        p = GENERAL_PCG_V1
        assert p.profile_id == "GENERAL_PCG_V1"
        assert "20_600_hz" in p.filter_policy
        assert p.spectral_policy.nperseg == 512
        assert p.spectral_policy.effective_noverlap() == 256
        assert p.spectral_policy.effective_nfft() == 512
        assert p.spectral_policy.detrend == DetrendMode.CONSTANT

    def test_phantom_validation_profile_consistency(self):
        p = PHANTOM_VALIDATION_V1
        assert p.profile_id == "PHANTOM_VALIDATION_V1"
        assert p.sample_rate_policy == "resample_capture_to_reference"
        assert p.spectral_policy.nperseg == 512
        assert p.spectral_policy.effective_noverlap() == 256
        assert p.spectral_policy.effective_nfft() == 512
        assert p.spectral_policy.frequency_max_hz == 1000.0
        assert p.spectral_policy.detrend == DetrendMode.CONSTANT
        assert p.calibration_requirement == "relative_comparison_only"

    def test_pcg_event_features_profile_consistency(self):
        p = PCG_EVENT_FEATURES_V1
        assert p.profile_id == "PCG_EVENT_FEATURES_V1"
        assert p.sample_rate_policy == "decimate_to_1000_hz"
        assert p.spectral_policy.nperseg == 256
        assert p.spectral_policy.effective_noverlap() == 128
        assert p.feature_policy["candidate_peaks_only"] is True

    def test_springer_segmentation_profile_consistency(self):
        p = SPRINGER_SEGMENTATION_RESEARCH_V1
        assert p.profile_id == "SPRINGER_SEGMENTATION_RESEARCH_V1"
        assert p.sample_rate_policy == "downsample_to_1000_hz_then_features_to_50_hz"
        # Strict Springer provenance: polyphase anti-aliasing without Schmidt 25-400 Hz conflation
        assert p.filter_policy == "springer_polyphase_anti_alias_1000hz"
        assert p.literature_sources == ("R006", "R007")
        assert p.spectral_policy.window == "hamming"
        assert p.spectral_policy.nperseg == 50
        assert p.spectral_policy.effective_noverlap() == 25
        assert p.spectral_policy.nfft is None
        assert p.feature_policy["psd_envelope_band_hz"] == [40, 60]
        assert p.feature_policy["psd_envelope_window_seconds"] == 0.05
        assert p.feature_policy["psd_envelope_overlap_fraction"] == 0.5
        assert p.feature_policy["per_recording_z_normalization"] is True
        assert p.feature_policy["feature_sampling_rate_hz"] == 50.0
        assert p.calibration_requirement == "dimensionless_features"

    def test_all_standard_profiles_serialize_without_contradiction(self):
        for profile in list_analysis_profiles():
            d = profile.to_dict()
            assert d["profile_id"] == profile.profile_id
            assert d["profile_version"] == profile.profile_version
            restored = AnalysisProfile.from_dict(d)
            assert restored == profile

            # Uncalibrated profiles must not allow Pascal or dB SPL
            if profile.calibration_requirement != "calibrated_acoustic":
                with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
                    validate_unit_usage(SignalUnit.PASCAL, has_acoustic_calibration=False)
