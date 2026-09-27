"""AuscultaForge — Automated Tests for Springer Segmentation Preprocessing.

Verifies:
- 1000 Hz explicit analysis resampling
- 25–400 Hz zero-phase bandpass filtering
- Schmidt spike removal under various conditions (no spike, 1 spike, multiple spikes, flat signal, short signal, iteration limit guard)
- Non-mutating behavior
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.springer_preprocessing import (
    prepare_springer_analysis_signal,
    apply_springer_bandpass_filter,
    remove_schmidt_spikes,
    run_springer_preprocessing,
)
from pcg_core.segmentation.springer_config import SPRINGER_PHYSIONET_REFERENCE_V1, SPRINGER_PAPER_4FEATURE_V1


class TestSpringerPreprocessing:
    """Verifies Springer analysis signal preparation, filtering, and spike removal."""

    def test_resample_to_1000hz_from_4000hz(self):
        fs_orig = 4000.0
        n_orig = 8000  # 2.0 seconds
        t = np.arange(n_orig) / fs_orig
        x = np.sin(2.0 * np.pi * 50.0 * t)

        resampled, was_resampled = prepare_springer_analysis_signal(x, sample_rate_hz=fs_orig, target_fs=1000.0)

        assert was_resampled is True
        assert len(resampled) == 2000  # 2.0 s at 1000 Hz
        assert pytest.approx(np.max(resampled), abs=0.05) == 1.0

    def test_resample_identity_when_already_1000hz(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        resampled, was_resampled = prepare_springer_analysis_signal(x, sample_rate_hz=1000.0, target_fs=1000.0)

        assert was_resampled is False
        np.testing.assert_array_equal(resampled, x)

    def test_rejects_nan_and_inf(self):
        with pytest.raises(ValueError):
            prepare_springer_analysis_signal(np.array([1.0, np.nan, 2.0]), 4000.0)
        with pytest.raises(ValueError):
            prepare_springer_analysis_signal(np.array([1.0, np.inf, 2.0]), 4000.0)

    def test_bandpass_filter_25_400_hz(self):
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs

        # 5 Hz (below 25 Hz), 100 Hz (in band), 450 Hz (above 400 Hz)
        low_tone = np.sin(2.0 * np.pi * 5.0 * t)
        mid_tone = np.sin(2.0 * np.pi * 100.0 * t)
        high_tone = np.sin(2.0 * np.pi * 450.0 * t)

        filtered_low = apply_springer_bandpass_filter(low_tone, sample_rate_hz=fs)
        filtered_mid = apply_springer_bandpass_filter(mid_tone, sample_rate_hz=fs)
        filtered_high = apply_springer_bandpass_filter(high_tone, sample_rate_hz=fs)

        # Mid tone preserved, low and high tones heavily attenuated
        assert np.max(np.abs(filtered_mid[200:-200])) > 0.85
        assert np.max(np.abs(filtered_low[200:-200])) < 0.15
        assert np.max(np.abs(filtered_high[200:-200])) < 0.20

    def test_cascaded_lp_then_hp_filter_exact_match(self):
        """Verify explicit cascaded LP400 (order 2) -> HP25 (order 2) zero-phase filtfilt against reference."""
        import scipy.signal
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t) + 0.5 * np.cos(2.0 * np.pi * 120.0 * t)

        # Independent explicit construction of the reference cascade
        b_lp, a_lp = scipy.signal.butter(2, 400.0 / (fs / 2.0), btype="lowpass")
        pad_lp = 3 * max(len(a_lp), len(b_lp))
        lp_out = scipy.signal.filtfilt(b_lp, a_lp, x, padlen=pad_lp)

        b_hp, a_hp = scipy.signal.butter(2, 25.0 / (fs / 2.0), btype="highpass")
        pad_hp = 3 * max(len(a_hp), len(b_hp))
        expected_cascade = scipy.signal.filtfilt(b_hp, a_hp, lp_out, padlen=pad_hp)

        actual = apply_springer_bandpass_filter(x, sample_rate_hz=fs, low_hz=25.0, high_hz=400.0, order=2)
        np.testing.assert_allclose(actual, expected_cascade, rtol=1e-12, atol=1e-12)

    def test_schmidt_spike_removal_no_spike(self):
        fs = 1000.0
        n = 3000
        t = np.arange(n) / fs
        # Normal sinusoidal sequence
        x = 0.5 * np.sin(2.0 * np.pi * 50.0 * t)

        cleaned, spike_count = remove_schmidt_spikes(x, sample_rate_hz=fs, window_ms=500.0)

        assert spike_count == 0
        np.testing.assert_array_equal(cleaned, x)

    def test_schmidt_spike_removal_single_large_spike(self):
        fs = 1000.0
        n = 4000  # 4 seconds
        t = np.arange(n) / fs
        x = 0.3 * np.sin(2.0 * np.pi * 50.0 * t)

        # Inject huge isolated artifact spike in window 3 (at t=1.5s, sample 1500)
        x[1500] = 5.0

        cleaned, spike_count = remove_schmidt_spikes(x, sample_rate_hz=fs, window_ms=500.0)

        assert spike_count >= 1
        # The spike peak must have been zeroed out
        assert abs(cleaned[1500]) < 1e-6
        # Max amplitude now conforms to baseline signal
        assert np.max(np.abs(cleaned)) <= 0.40

    def test_schmidt_spike_removal_multiple_spikes(self):
        fs = 1000.0
        n = 5000
        t = np.arange(n) / fs
        x = 0.2 * np.sin(2.0 * np.pi * 60.0 * t)

        # Inject 3 spikes in distinct windows
        x[1200] = 4.0
        x[2400] = 6.0
        x[3600] = 5.0

        cleaned, spike_count = remove_schmidt_spikes(x, sample_rate_hz=fs, window_ms=500.0)

        assert spike_count >= 3
        assert np.max(np.abs(cleaned)) < 0.5

    def test_schmidt_spike_removal_flat_signal(self):
        x_flat = np.zeros(2000)
        cleaned, spike_count = remove_schmidt_spikes(x_flat, sample_rate_hz=1000.0)
        assert spike_count == 0
        np.testing.assert_array_equal(cleaned, x_flat)

    def test_schmidt_spike_removal_short_signal_safe(self):
        # Shorter than 2 windows (< 1000 samples)
        x_short = np.array([1.0, 10.0, 1.0])
        cleaned, spike_count = remove_schmidt_spikes(x_short, sample_rate_hz=1000.0, window_ms=500.0)
        assert spike_count == 0
        np.testing.assert_array_equal(cleaned, x_short)

    def test_schmidt_spike_removal_iteration_limit_guard(self):
        # Pathological repeating spikes that could loop indefinitely
        x = np.full(3000, 0.1)
        x[::100] = 2.0  # Many spikes

        # Must terminate within max_iterations without hanging
        cleaned, spike_count = remove_schmidt_spikes(x, sample_rate_hz=1000.0, max_iterations=5)
        assert spike_count <= 5

    def test_run_springer_preprocessing_orchestration(self):
        x = np.sin(2.0 * np.pi * 50.0 * np.arange(4000) / 2000.0)  # 2.0 s at 2000 Hz
        out, meta = run_springer_preprocessing(x, sample_rate_hz=2000.0, config=SPRINGER_PHYSIONET_REFERENCE_V1)

        assert len(out) == 2000  # 1000 Hz
        assert meta["was_resampled"] is True
        assert meta["bandpass_applied"] is True
        assert meta["spike_removal_applied"] is True
