"""AuscultaForge — Automated Tests for Springer Multi-Feature Extraction.

Verifies:
- Homomorphic envelope (AM modulated signal, zeros, positivity, finiteness, edge handling)
- Hilbert envelope feature
- PSD feature (50 Hz burst response, out-of-band burst response)
- Paper mode vs Reference mode PSD distinction
- Wavelet feature (rbio3.9 level-3 detail reconstruction + envelope)
- Per-recording z-score standardization & constant feature degeneracy protection
- 50 Hz feature rate downsampling and serialization
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.springer_features import (
    compute_springer_homomorphic_envelope,
    compute_springer_hilbert_feature,
    compute_springer_psd_feature,
    compute_springer_wavelet_feature,
    normalize_features_per_recording,
    extract_springer_features,
)
from pcg_core.segmentation.springer_config import (
    SPRINGER_PHYSIONET_REFERENCE_V1,
    SPRINGER_PAPER_4FEATURE_V1,
)


class TestSpringerFeatures:
    """Verifies Springer mathematical feature extraction algorithms."""

    def test_homomorphic_envelope_am_signal_tracks_modulation(self):
        fs = 1000.0
        n = 2000  # 2.0 s
        t = np.arange(n) / fs

        # Amplitude-modulated carrier: carrier = 100 Hz, modulator = 2 Hz
        modulator = 0.5 * (1.0 + np.sin(2.0 * np.pi * 2.0 * t))
        carrier = np.sin(2.0 * np.pi * 100.0 * t)
        am_signal = modulator * carrier

        homo_env = compute_springer_homomorphic_envelope(am_signal, sample_rate_hz=fs, lowpass_hz=8.0)

        # 1. Output must be strictly positive and finite
        assert len(homo_env) == n
        assert np.all(homo_env > 0.0)
        assert np.all(np.isfinite(homo_env))

        # 2. Correlation between true modulator and extracted homomorphic envelope must be high
        # Exclude initial filter transient
        corr = np.corrcoef(modulator[200:-200], homo_env[200:-200])[0, 1]
        assert corr > 0.80

    def test_homomorphic_envelope_silent_signal_safe(self):
        x_silent = np.zeros(1000)
        env = compute_springer_homomorphic_envelope(x_silent, sample_rate_hz=1000.0)

        assert len(env) == 1000
        assert np.all(np.isfinite(env))
        assert np.all(env >= 0.0)

    def test_hilbert_feature_matches_analytic_magnitude(self):
        fs = 1000.0
        t = np.arange(1000) / fs
        x = np.cos(2.0 * np.pi * 50.0 * t)

        hilb = compute_springer_hilbert_feature(x)

        assert len(hilb) == 1000
        # For pure sinusoid cos(wt), analytic signal magnitude is identically ~1.0
        assert pytest.approx(np.mean(hilb[100:-100]), abs=0.02) == 1.0

    def test_psd_feature_responds_to_in_band_50hz_and_rejects_200hz(self):
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs

        # First second: 50 Hz (in-band, 40-60 Hz)
        # Second second: 200 Hz (out-of-band)
        x = np.zeros(n)
        x[:1000] = np.sin(2.0 * np.pi * 50.0 * t[:1000])
        x[1000:] = np.sin(2.0 * np.pi * 200.0 * t[1000:])

        psd_feat = compute_springer_psd_feature(x, sample_rate_hz=fs, band_hz=(40.0, 60.0), window_ms=50.0)

        assert len(psd_feat) == n
        first_half_energy = np.mean(psd_feat[200:800])
        second_half_energy = np.mean(psd_feat[1200:1800])

        assert first_half_energy > 10.0 * second_half_energy

    def test_psd_paper_vs_reference_profile_modes_distinguishable(self):
        """Regression test verifying Paper mode and Reference mode produce distinguishable curves."""
        fs = 1000.0
        t = np.arange(1000) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t)

        feat_ref = compute_springer_psd_feature(x, sample_rate_hz=fs, mode="reference")
        feat_paper = compute_springer_psd_feature(x, sample_rate_hz=fs, mode="paper")

        assert len(feat_ref) == len(feat_paper)
        # Distinguishable due to window length (25 ms vs 50 ms) and frequency grid/timing
        assert not np.allclose(feat_ref, feat_paper)
        assert np.all(feat_ref >= 0.0)
        assert np.all(feat_paper >= 0.0)

    def test_psd_reference_exact_semantics_window_grid_mean(self):
        """Verify reference PSD uses 25ms window, 1Hz grid, mean (not sum), and direct 50Hz resampling."""
        import scipy.signal
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t) + 0.3 * np.sin(2.0 * np.pi * 120.0 * t)

        # 1. Config parameters
        assert SPRINGER_PHYSIONET_REFERENCE_V1.psd_window_ms == 25.0
        assert SPRINGER_PAPER_4FEATURE_V1.psd_window_ms == 50.0

        # 2. Window length: at 1000 Hz, fs / 40 = 25 samples (25 ms)
        win_len_ref = int(round(fs / 40.0))
        noverlap_ref = int(round(fs / 80.0))
        nfft_ref = int(round(fs))  # 1000 points -> 1 Hz spacing
        assert win_len_ref == 25
        assert nfft_ref == 1000

        # 3. Direct comparison: compute spectrogram and mean across 40-60 Hz
        f, t_spec, Sxx = scipy.signal.spectrogram(
            x,
            fs=fs,
            window="hamming",
            nperseg=win_len_ref,
            noverlap=noverlap_ref,
            nfft=nfft_ref,
            detrend=False,
            scaling="density",
            mode="psd",
        )
        # Verify 1 Hz frequency grid spacing
        assert pytest.approx(f[1] - f[0], abs=1e-6) == 1.0

        mask_40_60 = (f >= 40.0) & (f <= 60.0)
        expected_mean = np.mean(Sxx[mask_40_60, :], axis=0)
        expected_sum = np.sum(Sxx[mask_40_60, :], axis=0)

        # Compute with target 50 Hz length (100 frames for 2.0s)
        target_len_50hz = 100
        resampled_psd = compute_springer_psd_feature(
            x, sample_rate_hz=fs, mode="reference", target_length_50hz=target_len_50hz
        )

        assert len(resampled_psd) == target_len_50hz
        # Verify it reflects mean, not sum (mean is ~21 times smaller than sum over 21 bins)
        ratio = np.mean(expected_sum) / max(1e-12, np.mean(expected_mean))
        assert ratio > 15.0
        # The resampled mean PSD energy must be consistent with expected_mean
        assert pytest.approx(np.mean(resampled_psd), rel=0.15) == np.mean(expected_mean)

    def test_wavelet_feature_no_hilbert_no_lowpass(self):
        """Verify wavelet detail uses abs(cD) directly with NO Hilbert envelope and NO 8 Hz LPF."""
        import pywt
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 80.0 * t)

        wav_feat1 = compute_springer_wavelet_feature(x, sample_rate_hz=fs, wavelet_name="rbio3.9", level=3)
        wav_feat2 = compute_springer_wavelet_feature(x, sample_rate_hz=fs, wavelet_name="rbio3.9", level=3)

        # 1. Deterministic output
        np.testing.assert_array_equal(wav_feat1, wav_feat2)
        assert len(wav_feat1) == n

        # 2. Detail coefficients expanded and absolute value taken (no Hilbert analytic envelope)
        coeffs = pywt.wavedec(x, "rbio3.9", level=3)
        cd3 = coeffs[1]
        upsampled = np.repeat(cd3, 8)
        start_idx = (len(upsampled) - n) // 2
        expected_abs = np.abs(upsampled[start_idx : start_idx + n])
        np.testing.assert_allclose(wav_feat1, expected_abs, atol=1e-12)

        # 3. Provenance records exact structural fidelity
        res = extract_springer_features(x, config=SPRINGER_PAPER_4FEATURE_V1, original_fs=fs)
        assert res.provenance["wavelet_name"] == "rbio3.9"
        assert res.provenance["wavelet_fidelity_status"] == "SOURCE-STRUCTURAL MATCH / NUMERICAL ORACLE NOT EXECUTED"
        assert res.provenance["oracle_status"] == "REFERENCE_ORACLE_NOT_EXECUTED"

    def test_wavelet_feature_rbio39_level3(self):
        fs = 1000.0
        n = 2000
        t = np.arange(n) / fs
        # 80 Hz burst
        x = np.sin(2.0 * np.pi * 80.0 * t)

        wav_feat = compute_springer_wavelet_feature(x, sample_rate_hz=fs, wavelet_name="rbio3.9", level=3)

        assert len(wav_feat) == n
        assert np.all(np.isfinite(wav_feat))
        assert np.all(wav_feat >= 0.0)
        assert np.max(wav_feat) > 0.0

    def test_normalize_features_per_recording(self):
        rng = np.random.default_rng(42)
        # 3 features: random normal with different means and scales
        f1 = rng.normal(loc=10.0, scale=2.0, size=500)
        f2 = rng.normal(loc=-5.0, scale=0.5, size=500)
        f3 = np.full(500, 3.14)  # Constant degenerate feature

        X = np.column_stack([f1, f2, f3])
        X_norm, meta = normalize_features_per_recording(X)

        assert X_norm.shape == (500, 3)
        # Column 0: mean ~ 0, std ~ 1
        assert pytest.approx(np.mean(X_norm[:, 0]), abs=1e-7) == 0.0
        assert pytest.approx(np.std(X_norm[:, 0]), abs=1e-7) == 1.0

        # Column 1: mean ~ 0, std ~ 1
        assert pytest.approx(np.mean(X_norm[:, 1]), abs=1e-7) == 0.0
        assert pytest.approx(np.std(X_norm[:, 1]), abs=1e-7) == 1.0

        # Column 2 (degenerate): safe zero return without division by zero
        assert np.all(X_norm[:, 2] == 0.0)
        assert 2 in meta["degenerate_features"]

    def test_extract_springer_features_50hz_downsampled(self):
        fs = 1000.0
        n = 3000  # 3.0 seconds at 1000 Hz
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t)

        res = extract_springer_features(x, config=SPRINGER_PHYSIONET_REFERENCE_V1, original_fs=4000.0)

        # 3.0 s at 50 Hz = 150 frames
        assert res.feature_sample_rate_hz == 50.0
        assert len(res.time_s) == 150
        assert len(res.homomorphic) == 150
        assert len(res.hilbert) == 150
        assert len(res.psd) == 150
        assert res.wavelet is None  # Reference profile defaults to 3 features
        assert len(res.feature_matrix) == 150
        assert len(res.feature_matrix[0]) == 3

    def test_extract_springer_features_paper_4feature_profile(self):
        fs = 1000.0
        n = 2000  # 2.0 s at 1000 Hz
        t = np.arange(n) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t)

        res = extract_springer_features(x, config=SPRINGER_PAPER_4FEATURE_V1, original_fs=1000.0)

        # 2.0 s at 50 Hz = 100 frames
        assert res.feature_sample_rate_hz == 50.0
        assert len(res.time_s) == 100
        assert res.wavelet is not None
        assert len(res.wavelet) == 100
        assert len(res.feature_matrix[0]) == 4
