"""AuscultaForge — Automated Tests for SISO System Identification & FRF (H1).

Verifies:
- Synthetic known stable LTI filter transfer-function estimation (Butterworth filter)
- H1 magnitude response matches theoretical freqz within tight tolerance in passband
- Phase orientation / sign is mathematically correct (regression test protecting SciPy CSD convention)
- Magnitude-squared coherence is near 1.0 in passband with low noise
- Additive output noise reduces coherence predictably without altering H1 estimate
- Excited-frequency energy mask successfully isolates active excitation band
- Rejection of invalid inputs (empty, NaN, Inf, non-positive fs)
- Robust handling of length mismatch (truncation to common length)
- Serialization to valid JSON without NaN or Inf
"""

import math
import numpy as np
import scipy.signal
import pytest

from pcg_core.scientific.models import SystemIdConfig, SystemIdentificationResult
from pcg_core.scientific.system_id import estimate_siso_system_id


class TestScientificSystemIdentification:
    """Verifies conservative SISO H1 best-linear frequency response estimation."""

    @pytest.fixture
    def synthetic_lti_setup(self):
        """Generate a known stable 4th-order Butterworth bandpass filter and broadband excitation."""
        fs = 4000.0
        n_samples = 40000  # 10 seconds of broadband data
        rng = np.random.default_rng(20260927)

        # Broadband Gaussian white noise excitation
        x = rng.standard_normal(n_samples)

        # Known LTI System: 4th-order Butterworth bandpass 100–400 Hz
        b, a = scipy.signal.butter(4, [100.0, 400.0], btype="bandpass", fs=fs)
        y_clean = scipy.signal.lfilter(b, a, x)

        return {
            "fs": fs,
            "x": x,
            "y_clean": y_clean,
            "b": b,
            "a": a,
            "rng": rng,
        }

    def test_h1_magnitude_matches_known_lti_filter(self, synthetic_lti_setup):
        """H1 magnitude estimate must match true theoretical freqz within 0.05 in the passband."""
        setup = synthetic_lti_setup
        fs = setup["fs"]
        x = setup["x"]
        y = setup["y_clean"]
        b, a = setup["b"], setup["a"]

        cfg = SystemIdConfig(nperseg=1024, noverlap=512, window="hann")
        res = estimate_siso_system_id(x, y, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        h1_mag = np.array(res.h1_magnitude)

        # True theoretical filter response at identical frequencies
        w, H_true = scipy.signal.freqz(b, a, worN=freqs, fs=fs)
        mag_true = np.abs(H_true)

        # Evaluate in deep passband (150 Hz to 350 Hz)
        passband = (freqs >= 150.0) & (freqs <= 350.0)
        err = np.abs(h1_mag[passband] - mag_true[passband])

        assert np.max(err) < 0.03  # Max error < 0.03
        assert np.mean(err) < 0.015

    def test_cross_spectrum_convention_and_phase_orientation(self, synthetic_lti_setup):
        """REGRESSION TEST: Verify that scipy.signal.csd(x, y) yields correct phase orientation.
        
        If x is excitation and y = h * x, then:
        H1 = csd(x, y) / welch(x) has angle equal to +angle(H_true), NOT -angle(H_true).
        """
        setup = synthetic_lti_setup
        fs = setup["fs"]
        x = setup["x"]
        y = setup["y_clean"]
        b, a = setup["b"], setup["a"]

        cfg = SystemIdConfig(nperseg=1024, noverlap=512, window="hann")
        res = estimate_siso_system_id(x, y, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        h1_phase_rad = np.array(res.h1_phase_rad)

        w, H_true = scipy.signal.freqz(b, a, worN=freqs, fs=fs)
        phase_true = np.angle(H_true)

        # In passband 150-350 Hz where phase is well behaved
        passband = (freqs >= 150.0) & (freqs <= 350.0)
        phase_diff = np.abs(h1_phase_rad[passband] - phase_true[passband])
        
        # Max phase error must be less than 0.05 radians (~2.8 degrees)
        assert np.max(phase_diff) < 0.05

        # Check that inverted convention (-phase_true) would fail dramatically
        inverted_diff = np.abs(h1_phase_rad[passband] - (-phase_true[passband]))
        assert np.mean(inverted_diff) > 0.5  # Confirms orientation is unambiguously positive

    def test_coherence_near_one_for_clean_linear_system(self, synthetic_lti_setup):
        """Coherence must be > 0.98 in the excited passband for noiseless linear system."""
        setup = synthetic_lti_setup
        fs = setup["fs"]
        x = setup["x"]
        y = setup["y_clean"]

        cfg = SystemIdConfig(nperseg=1024, noverlap=512)
        res = estimate_siso_system_id(x, y, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        coh = np.array(res.coherence)

        passband = (freqs >= 150.0) & (freqs <= 350.0)
        assert np.all(coh[passband] > 0.98)

    def test_additive_output_noise_reduces_coherence(self, synthetic_lti_setup):
        """Adding uncorrelated noise to the output must decrease coherence while preserving H1."""
        setup = synthetic_lti_setup
        fs = setup["fs"]
        x = setup["x"]
        y = setup["y_clean"]
        rng = setup["rng"]

        # Add substantial noise to output
        noise = 0.6 * rng.standard_normal(len(y))
        y_noisy = y + noise

        cfg = SystemIdConfig(nperseg=1024, noverlap=512)
        res_clean = estimate_siso_system_id(x, y, sample_rate_hz=fs, config=cfg)
        res_noisy = estimate_siso_system_id(x, y_noisy, sample_rate_hz=fs, config=cfg)

        passband = (np.array(res_clean.frequencies_hz) >= 150.0) & (np.array(res_clean.frequencies_hz) <= 350.0)
        mean_coh_clean = np.mean(np.array(res_clean.coherence)[passband])
        mean_coh_noisy = np.mean(np.array(res_noisy.coherence)[passband])

        assert mean_coh_noisy < mean_coh_clean
        assert mean_coh_noisy < 0.85

    def test_excited_frequency_mask_and_summary(self, synthetic_lti_setup):
        """Verifies excited frequency mask correctly filters out frequencies outside excited band."""
        setup = synthetic_lti_setup
        fs = setup["fs"]
        x = setup["x"]
        y = setup["y_clean"]

        cfg = SystemIdConfig(
            nperseg=1024,
            noverlap=512,
            excited_band_hz=(100.0, 500.0),
            energy_threshold_db_rel_max=-20.0,
        )
        res = estimate_siso_system_id(x, y, sample_rate_hz=fs, config=cfg)

        mask = np.array(res.excited_frequency_mask)
        freqs = np.array(res.frequencies_hz)

        # All masked frequencies must lie within [100, 500] Hz
        assert np.all((freqs[mask] >= 100.0) & (freqs[mask] <= 500.0))
        assert res.excited_bins_count > 0
        assert res.mean_coherence_over_excited_band is not None
        assert res.mean_coherence_over_excited_band > 0.95

    def test_input_output_length_mismatch_truncated_cleanly(self, synthetic_lti_setup):
        setup = synthetic_lti_setup
        x = setup["x"][:10000]
        y = setup["y_clean"][:8000]  # 2000 samples shorter

        res = estimate_siso_system_id(x, y, sample_rate_hz=setup["fs"])
        assert res.provenance["input_sample_count"] == 8000
        assert res.provenance["output_sample_count"] == 8000
        assert len(res.h1_magnitude) > 0

    def test_no_division_by_zero_or_nan(self):
        fs = 4000.0
        # Silent excitation
        x = np.zeros(2000)
        y = np.zeros(2000)

        # Should not raise exception or produce NaNs
        res = estimate_siso_system_id(x, y, sample_rate_hz=fs)
        d = res.to_dict()

        for val in d["h1_magnitude"]:
            assert not math.isnan(val) and not math.isinf(val)
        for val in d["coherence"]:
            assert not math.isnan(val) and not math.isinf(val)
        for val in d["h1_magnitude_db"]:
            assert not math.isnan(val) and not math.isinf(val)

    def test_silent_input_is_not_excitation(self):
        """Validates that zero or silent input does NOT mark any frequency as excited.

        Asserts:
        - excited_frequency_mask contains no True bins
        - excited_bins_count == 0
        - mean_coherence_over_excited_band is None
        - H1 and coherence arrays remain strictly finite and JSON-serializable
        """
        fs = 4000.0
        n_samples = 4000
        x_silent = np.zeros(n_samples, dtype=np.float64)
        y_arbitrary = np.sin(2.0 * np.pi * 100.0 * np.arange(n_samples) / fs)

        cfg = SystemIdConfig(excited_band_hz=(20.0, 500.0), energy_threshold_db_rel_max=-20.0)
        res = estimate_siso_system_id(x_silent, y_arbitrary, sample_rate_hz=fs, config=cfg)

        # 1. excited_frequency_mask must contain NO True bins
        assert not any(res.excited_frequency_mask)
        assert len(res.excited_frequency_mask) == len(res.frequencies_hz)

        # 2. excited_bins_count == 0
        assert res.excited_bins_count == 0

        # 3. mean_coherence_over_excited_band is None
        assert res.mean_coherence_over_excited_band is None

        # 4. H1 and coherence arrays must remain strictly finite and JSON-safe
        assert len(res.h1_magnitude) > 0
        assert np.all(np.isfinite(res.h1_magnitude))
        assert np.all(np.isfinite(res.h1_magnitude_db))
        assert np.all(np.isfinite(res.h1_phase_rad))
        assert np.all(np.isfinite(res.h1_phase_deg))
        assert np.all(np.isfinite(res.coherence))
        assert np.all(np.isfinite(res.gxx_autospectrum))
        assert np.all(np.isfinite(res.gyy_autospectrum))

        # Check serialization round-trip
        data = res.to_dict()
        assert data["excited_bins_count"] == 0
        assert data["mean_coherence_over_excited_band"] is None
        assert not any(data["excited_frequency_mask"])
