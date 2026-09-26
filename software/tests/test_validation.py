"""Tests for AuscultaForge Reference-vs-Capture Signal Validation module.

Verifies delay recovery, correlation metrics, gain measurements, noise impacts,
sample-rate resampling, deterministic simulation, and input validation without
any network or external hardware dependency.
"""

from pathlib import Path
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from pcg_core.validation import (
    ValidationResult,
    estimate_delay_and_align,
    load_wav_as_float32,
    simulate_distorted_capture,
    validate_signals,
    validate_wav_files,
)


def _generate_synthetic_pcg(
    duration_s: float = 2.0,
    fs: int = 2000,
    seed: int = 123,
) -> np.ndarray:
    """Generate a reproducible synthetic PCG-like signal with S1/S2 heart sound transients."""
    t = np.linspace(0, duration_s, int(fs * duration_s), endpoint=False, dtype=np.float32)
    # Fundamental components in PCG passband (50 Hz, 120 Hz) with envelope modulation
    envelope = np.zeros_like(t)
    heart_rate_bps = 1.2  # 72 bpm -> ~0.833s period
    period_samples = int(fs / heart_rate_bps)
    
    for start in range(0, len(t), period_samples):
        # S1 transient (~50ms)
        s1_len = int(0.05 * fs)
        if start + s1_len < len(t):
            envelope[start : start + s1_len] += np.hanning(s1_len)
        # S2 transient (~40ms, ~300ms after S1)
        s2_start = start + int(0.3 * fs)
        s2_len = int(0.04 * fs)
        if s2_start + s2_len < len(t):
            envelope[s2_start : s2_start + s2_len] += 0.7 * np.hanning(s2_len)

    carrier = 0.6 * np.sin(2 * np.pi * 50 * t) + 0.4 * np.sin(2 * np.pi * 120 * t)
    sig = (carrier * envelope).astype(np.float32)
    return sig


class TestSignalValidation:
    """Unit tests for validation algorithms and metric computations."""

    def test_identical_signals_perfect_match(self):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=2.0, fs=fs)
        cap = ref.copy()

        result = validate_signals(ref, cap, reference_fs=fs, captured_fs=fs)

        assert isinstance(result, ValidationResult)
        assert result.resampled is False
        assert result.delay_samples == 0
        assert pytest.approx(result.delay_ms, abs=1e-3) == 0.0
        assert pytest.approx(result.normalized_cross_correlation, abs=1e-4) == 1.0
        assert pytest.approx(result.gain_ratio_rms, abs=1e-3) == 1.0
        assert pytest.approx(result.gain_ratio_peak, abs=1e-3) == 1.0
        assert pytest.approx(result.rmse, abs=1e-5) == 0.0
        assert pytest.approx(result.normalized_rmse, abs=1e-5) == 0.0
        assert result.signal_to_error_ratio_db >= 99.0
        assert pytest.approx(result.dominant_frequency_diff_hz, abs=1e-2) == 0.0
        assert pytest.approx(result.mean_coherence_pcg_band, abs=1e-2) == 1.0

    def test_known_delay_recovery(self):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=3.0, fs=fs)
        known_delay_ms = 45.0  # 45 ms at 2000 Hz = exactly 90 samples
        expected_samples = 90

        cap = simulate_distorted_capture(
            ref,
            fs=fs,
            delay_ms=known_delay_ms,
            gain=1.0,
            noise_std=0.0,
            seed=42,
        )

        aligned_ref, aligned_cap, delay_samples, delay_ms = estimate_delay_and_align(
            ref, cap, fs
        )

        assert delay_samples == expected_samples
        assert pytest.approx(delay_ms, abs=0.1) == known_delay_ms
        assert len(aligned_ref) == len(aligned_cap)

        result = validate_signals(ref, cap, reference_fs=fs, captured_fs=fs)
        assert result.delay_samples == expected_samples
        assert pytest.approx(result.delay_ms, abs=0.1) == known_delay_ms
        assert pytest.approx(result.normalized_cross_correlation, abs=1e-3) == 1.0

    def test_known_gain_measurement(self):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=2.0, fs=fs)
        known_gain = 0.65

        cap = simulate_distorted_capture(
            ref,
            fs=fs,
            delay_ms=0.0,
            gain=known_gain,
            noise_std=0.0,
        )

        result = validate_signals(ref, cap, reference_fs=fs, captured_fs=fs)

        assert pytest.approx(result.gain_ratio_rms, abs=1e-3) == known_gain
        assert pytest.approx(result.gain_ratio_peak, abs=1e-3) == known_gain
        # Shape correlation should remain ~1.0 despite linear scaling
        assert pytest.approx(result.normalized_cross_correlation, abs=1e-3) == 1.0
        # RMSE reflects amplitude mismatch
        assert result.rmse > 0.0


    def test_least_squares_gain_recovery_under_additive_noise(self):
        """Demonstrate that least-squares gain accurately estimates true scaling under additive noise,
        whereas RMS gain ratio is positively biased by noise energy.
        """
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=4.0, fs=fs)
        known_gain = 0.70
        noise_std = 0.05  # moderate additive noise

        # Scaled signal + additive noise
        cap = simulate_distorted_capture(
            ref,
            fs=fs,
            delay_ms=0.0,
            gain=known_gain,
            noise_std=noise_std,
            seed=42,
        )

        result = validate_signals(ref, cap, reference_fs=fs, captured_fs=fs)

        # Least squares gain is an unbiased estimator: closely tracks known_gain
        assert pytest.approx(result.least_squares_gain, abs=0.03) == known_gain
        # RMS gain ratio is positively biased by the noise energy (RMS_cap = sqrt(g^2 * RMS_ref^2 + noise^2))
        assert result.gain_ratio_rms > known_gain
        assert result.gain_ratio_rms > result.least_squares_gain

    def test_least_squares_gain_zero_energy_handles_safely(self):
        from pcg_core.validation import compute_least_squares_gain
        zeros = np.zeros(100, dtype=np.float32)
        sig = np.ones(100, dtype=np.float32)
        assert compute_least_squares_gain(zeros, sig) == 0.0

    def test_additive_noise_lowers_correlation_and_increases_error(self):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=2.0, fs=fs)

        clean_cap = simulate_distorted_capture(ref, fs=fs, noise_std=0.0)
        noisy_cap = simulate_distorted_capture(ref, fs=fs, noise_std=0.05, seed=123)

        clean_res = validate_signals(ref, clean_cap, reference_fs=fs, captured_fs=fs)
        noisy_res = validate_signals(ref, noisy_cap, reference_fs=fs, captured_fs=fs)

        assert noisy_res.normalized_cross_correlation < clean_res.normalized_cross_correlation
        assert noisy_res.rmse > clean_res.rmse
        assert noisy_res.signal_to_error_ratio_db < clean_res.signal_to_error_ratio_db

    def test_different_sample_rates_explicit_resampling(self):
        fs_ref = 2000
        fs_cap = 4000
        t_ref = np.linspace(0, 2.0, int(fs_ref * 2.0), endpoint=False, dtype=np.float32)
        t_cap = np.linspace(0, 2.0, int(fs_cap * 2.0), endpoint=False, dtype=np.float32)

        # 80 Hz sinusoid sampled at both 2000 Hz and 4000 Hz
        ref = (0.8 * np.sin(2 * np.pi * 80 * t_ref)).astype(np.float32)
        cap = (0.8 * np.sin(2 * np.pi * 80 * t_cap)).astype(np.float32)

        result = validate_signals(ref, cap, reference_fs=fs_ref, captured_fs=fs_cap)

        assert result.resampled is True
        assert result.reference_fs == fs_ref
        assert result.captured_fs == fs_cap
        assert result.effective_fs == fs_ref
        assert pytest.approx(result.normalized_cross_correlation, abs=0.02) == 1.0
        assert pytest.approx(result.gain_ratio_rms, abs=0.02) == 1.0

    def test_invalid_and_empty_inputs_fail(self):
        fs = 2000
        valid_sig = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        empty_sig = np.array([], dtype=np.float32)

        with pytest.raises(ValueError, match="Reference signal is empty"):
            validate_signals(empty_sig, valid_sig, reference_fs=fs, captured_fs=fs)

        with pytest.raises(ValueError, match="Captured signal is empty"):
            validate_signals(valid_sig, empty_sig, reference_fs=fs, captured_fs=fs)

        with pytest.raises(ValueError, match="Sample rates must be positive integers"):
            validate_signals(valid_sig, valid_sig, reference_fs=-1, captured_fs=fs)

        with pytest.raises(FileNotFoundError):
            load_wav_as_float32("non_existent_pcg_file_xyz123.wav")

    def test_deterministic_simulation_repeatability(self):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=1.0, fs=fs)

        sim1 = simulate_distorted_capture(
            ref, fs=fs, delay_ms=25.0, gain=0.9, noise_std=0.02, seed=99
        )
        sim2 = simulate_distorted_capture(
            ref, fs=fs, delay_ms=25.0, gain=0.9, noise_std=0.02, seed=99
        )
        sim3 = simulate_distorted_capture(
            ref, fs=fs, delay_ms=25.0, gain=0.9, noise_std=0.02, seed=100
        )

        assert np.array_equal(sim1, sim2)
        assert not np.array_equal(sim1, sim3)

    def test_wav_file_validation(self, tmp_path: Path):
        fs = 2000
        ref = _generate_synthetic_pcg(duration_s=1.5, fs=fs)
        cap = simulate_distorted_capture(ref, fs=fs, delay_ms=10.0, gain=0.75, seed=42)

        ref_file = tmp_path / "ref.wav"
        cap_file = tmp_path / "cap.wav"

        # Save as 16-bit PCM WAV
        wavfile.write(ref_file, fs, (ref * 32767).astype(np.int16))
        wavfile.write(cap_file, fs, (cap * 32767).astype(np.int16))

        result = validate_wav_files(ref_file, cap_file)

        assert isinstance(result, ValidationResult)
        assert result.reference_name == "ref.wav"
        assert result.captured_name == "cap.wav"
        assert pytest.approx(result.gain_ratio_rms, abs=0.02) == 0.75
        assert result.delay_samples == 20  # 10 ms at 2000 Hz = 20 samples

        d = result.to_dict()
        assert d["reference_name"] == "ref.wav"
        j = result.to_json()
        assert "normalized_cross_correlation" in j
