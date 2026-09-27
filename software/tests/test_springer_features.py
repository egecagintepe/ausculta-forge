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
        # Mean scaling differs between total integrated band power and mean spectral density
        assert not np.allclose(feat_ref, feat_paper)
        assert np.all(feat_ref >= 0.0)
        assert np.all(feat_paper >= 0.0)

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
