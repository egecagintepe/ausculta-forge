"""AuscultaForge Independent Protocol & Signal Validator.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)
"""

from typing import Any, Dict
import numpy as np
from scipy import signal


class ProtocolValidator:
    """Independent mathematical validator for C-produced binary streams."""

    @staticmethod
    def validate_sine_100hz(
        samples: np.ndarray,
        sample_rate_hz: int = 48000,
        expected_freq_hz: float = 100.0,
    ) -> Dict[str, Any]:
        """Validate that a sample array is a pure 100 Hz sine wave."""
        if len(samples) < 480:
            raise ValueError(f"Need at least 1 period (480 samples), got {len(samples)}")

        # Convert to float64 for high-precision analytical calculations
        x = samples.astype(np.float64)
        n_samples = len(x)

        # 1. FFT Spectral Peak Search
        window = np.blackman(n_samples)
        spectrum = np.abs(np.fft.rfft(x * window))
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate_hz)

        peak_idx = int(np.argmax(spectrum[1:])) + 1
        peak_freq = float(freqs[peak_idx])

        # 2. Welch PSD for SNR & Harmonics
        f_welch, pxx = signal.welch(x, fs=sample_rate_hz, nperseg=min(n_samples, 4096))
        signal_bin = int(np.argmin(np.abs(f_welch - expected_freq_hz)))
        signal_power = float(pxx[signal_bin])

        noise_mask = np.ones(len(pxx), dtype=bool)
        noise_mask[max(0, signal_bin - 2) : min(len(pxx), signal_bin + 3)] = False
        noise_power = float(np.mean(pxx[noise_mask])) if np.any(noise_mask) else 1e-12

        snr_db = float(10.0 * np.log10(signal_power / max(noise_power, 1e-12)))

        # 3. Peak & RMS Measurements
        peak_pos = float(np.max(x))
        peak_neg = float(np.min(x))
        rms = float(np.sqrt(np.mean(x**2)))
        crest_factor = float(max(abs(peak_pos), abs(peak_neg)) / max(rms, 1e-12))

        # Expected sine crest factor is sqrt(2) ~= 1.4142
        crest_factor_err = abs(crest_factor - np.sqrt(2.0))

        freq_error = float(abs(peak_freq - expected_freq_hz))
        passed = bool((freq_error <= 0.5) and (snr_db >= 50.0) and (crest_factor_err <= 0.1))

        return {
            "passed": passed,
            "peak_freq_hz": peak_freq,
            "freq_error_hz": freq_error,
            "snr_db": snr_db,
            "peak_positive": peak_pos,
            "peak_negative": peak_neg,
            "rms": rms,
            "crest_factor": crest_factor,
            "crest_factor_error": crest_factor_err,
            "sample_count": n_samples,
            "duration_s": float(n_samples) / float(sample_rate_hz),
        }

    @staticmethod
    def validate_ramp_counter(
        samples: np.ndarray,
        meaningful_bits: int = 24,
    ) -> Dict[str, Any]:
        """Validate integer counter continuity and modulo wrapping."""
        if len(samples) < 2:
            return {"passed": True, "gaps": 0, "sample_count": len(samples)}

        diffs = np.diff(samples)
        span = 1 << meaningful_bits  # 16,777,216 for 24-bit

        # Normal step is +1, wrap step is -(span - 1)
        expected_steps = (diffs == 1) | (diffs == -(span - 1))
        invalid_steps = np.where(~expected_steps)[0]

        return {
            "passed": len(invalid_steps) == 0,
            "gaps": len(invalid_steps),
            "first_invalid_index": int(invalid_steps[0]) if len(invalid_steps) > 0 else None,
            "sample_count": len(samples),
        }

    @staticmethod
    def validate_g1_run(
        sample_count: int,
        frame_count: int,
        corrupted_frames: int,
        sequence_gaps: int,
        duplicate_frames: int,
        timestamp_regressions: int,
        garbage_bytes: int,
        expected_duration_s: float = 10.0,
        expected_rate_hz: int = 48000,
        expected_frame_size: int = 256,
    ) -> Dict[str, Any]:
        """Validate complete 10-second G1 benchmark execution metrics."""
        expected_samples = int(expected_duration_s * expected_rate_hz)
        expected_frames = expected_samples // expected_frame_size

        sample_count_ok = (sample_count == expected_samples)
        frame_count_ok = (frame_count == expected_frames)
        clean_integrity = (corrupted_frames == 0) and (sequence_gaps == 0) and (duplicate_frames == 0)

        passed = sample_count_ok and frame_count_ok and clean_integrity and (timestamp_regressions == 0)

        return {
            "passed": passed,
            "expected_samples": expected_samples,
            "actual_samples": sample_count,
            "sample_discrepancy": sample_count - expected_samples,
            "expected_frames": expected_frames,
            "actual_frames": frame_count,
            "frame_discrepancy": frame_count - expected_frames,
            "corrupted_frames": corrupted_frames,
            "sequence_gaps": sequence_gaps,
            "duplicate_frames": duplicate_frames,
            "timestamp_regressions": timestamp_regressions,
            "garbage_bytes_discarded": garbage_bytes,
        }
