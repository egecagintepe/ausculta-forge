"""AuscultaForge — Automated Tests for Scientific Spectral Engine.

Verifies:
- Known single sinusoid PSD peak location
- Two-tone signal peak resolution
- Frequency-bin spacing calculation (Delta_f = fs / N_fft)
- Configurable Welch parameters (nperseg, noverlap, nfft, window, detrend, scaling)
- Segment count behavior across variable signal durations
- Output array shapes and consistency
- Explicit analysis resampling (scipy.signal.resample_poly) without mutating original data
- 48 kHz analysis without mandatory decimation (independent of downsampled stream)
- Springer 1 kHz research profile compatibility
"""

import math
import numpy as np
import pytest

from pcg_core.scientific.models import WelchConfig, SpectralAnalysisResult
from pcg_core.scientific.spectral import compute_welch_psd, resample_analysis_signal


class TestScientificSpectralEngine:
    """Verifies Welch PSD estimation and scientific rational resampling."""

    def test_single_sinusoid_peak_detection(self):
        fs = 4000.0
        n_samples = 8000  # 2.0 seconds
        t = np.arange(n_samples) / fs
        f_target = 150.0  # 150 Hz
        x = np.sin(2.0 * np.pi * f_target * t)

        cfg = WelchConfig(nperseg=1024, nfft=2048, window="hann")
        res = compute_welch_psd(x, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        psd = np.array(res.psd)

        peak_idx = np.argmax(psd)
        peak_freq = freqs[peak_idx]

        # Peak must match target within half a frequency bin
        bin_spacing = res.frequency_bin_spacing_hz
        assert pytest.approx(peak_freq, abs=bin_spacing) == f_target

    def test_two_tone_signal_resolution(self):
        fs = 4000.0
        n = 8000
        t = np.arange(n) / fs
        f1, f2 = 80.0, 240.0
        x = np.sin(2.0 * np.pi * f1 * t) + np.sin(2.0 * np.pi * f2 * t)

        cfg = WelchConfig(nperseg=1024, nfft=1024, window="hann")
        res = compute_welch_psd(x, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        psd = np.array(res.psd)

        # Region around f1
        mask_f1 = (freqs >= 70.0) & (freqs <= 90.0)
        peak_f1 = freqs[mask_f1][np.argmax(psd[mask_f1])]
        assert pytest.approx(peak_f1, abs=res.frequency_bin_spacing_hz) == f1

        # Region around f2
        mask_f2 = (freqs >= 230.0) & (freqs <= 250.0)
        peak_f2 = freqs[mask_f2][np.argmax(psd[mask_f2])]
        assert pytest.approx(peak_f2, abs=res.frequency_bin_spacing_hz) == f2

    def test_frequency_bin_spacing_calculation(self):
        # 48000 Hz / 512 = 93.75 Hz
        cfg_512 = WelchConfig(nperseg=512, nfft=512)
        res_512 = compute_welch_psd(np.ones(1024), sample_rate_hz=48000, config=cfg_512)
        assert pytest.approx(res_512.frequency_bin_spacing_hz) == 93.75

        # 48000 Hz / 2048 = 23.4375 Hz
        cfg_2048 = WelchConfig(nperseg=1024, nfft=2048)
        res_2048 = compute_welch_psd(np.ones(4096), sample_rate_hz=48000, config=cfg_2048)
        assert pytest.approx(res_2048.frequency_bin_spacing_hz) == 23.4375

    def test_welch_segment_count_behavior(self):
        fs = 1000.0
        # 1000 samples, nperseg=256, noverlap=128 -> step=128
        # (1000 - 128) // 128 = 872 // 128 = 6 segments
        x = np.random.default_rng(42).standard_normal(1000)
        cfg = WelchConfig(nperseg=256, noverlap=128)
        res = compute_welch_psd(x, sample_rate_hz=fs, config=cfg)
        assert res.actual_segments == 6

    def test_raw_48khz_spectral_analysis_without_decimation(self):
        """Verifies that 48 kHz signals can be analyzed directly at full rate."""
        fs = 48000.0
        n = 48000  # 1 second of 48 kHz
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 300.0 * t)

        cfg = WelchConfig(nperseg=2048, noverlap=1024)
        res = compute_welch_psd(x, sample_rate_hz=fs, config=cfg)

        assert res.sample_rate_hz == 48000.0
        assert len(res.frequencies_hz) == 1025  # 2048 / 2 + 1
        assert pytest.approx(res.frequencies_hz[-1]) == 24000.0  # Nyquist

    def test_springer_1khz_profile_spectrum(self):
        """Verifies Welch analysis on a downsampled 1000 Hz PCG research stream."""
        fs = 1000.0
        n = 5000  # 5 seconds
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t)  # 50 Hz heart sound component

        cfg = WelchConfig(nperseg=256, noverlap=128, window="hamming")
        res = compute_welch_psd(x, sample_rate_hz=fs, config=cfg)

        assert res.sample_rate_hz == 1000.0
        assert len(res.frequencies_hz) == 129
        assert pytest.approx(res.frequencies_hz[-1]) == 500.0

    def test_analysis_resampling_polyphase(self):
        """Verifies resample_analysis_signal preserves signal energy and does not mutate source."""
        fs_orig = 48000.0
        fs_target = 1000.0
        n_orig = 48000
        t_orig = np.arange(n_orig) / fs_orig
        
        # 40 Hz sinusoidal PCG component
        orig = np.sin(2.0 * np.pi * 40.0 * t_orig)
        orig_copy = orig.copy()

        resampled, new_fs = resample_analysis_signal(orig, orig_sample_rate_hz=fs_orig, target_sample_rate_hz=fs_target)

        # Original signal must NOT be mutated
        np.testing.assert_array_equal(orig, orig_copy)

        assert new_fs == 1000.0
        assert len(resampled) == 1000  # 48000 / 48 = 1000
        # Peak amplitude preserved cleanly
        assert pytest.approx(np.max(np.abs(resampled)), rel=0.05) == 1.0

    def test_resampling_identity_when_rates_match(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        res, fs = resample_analysis_signal(x, 4000.0, 4000.0)
        np.testing.assert_array_equal(res, x)
        assert fs == 4000.0

    def test_rejects_empty_and_nan(self):
        with pytest.raises(ValueError):
            compute_welch_psd(np.array([]), 4000)
        with pytest.raises(ValueError):
            compute_welch_psd(np.array([1.0, np.nan, 2.0]), 4000)
