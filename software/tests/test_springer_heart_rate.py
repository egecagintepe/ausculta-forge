"""AuscultaForge — Automated Tests for Schmidt/Springer Heart-Rate Estimation.

Verifies:
- Synthetic periodic PCG envelopes at 60 BPM, 75 BPM, and 100 BPM
- Systolic time interval estimation
- Rejection of too-short recordings (< 2.0 s)
- Rejection of silent or flat signals
- Guard against signals without meaningful autocorrelation peaks
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.heart_rate import (
    estimate_heart_rate_schmidt,
    estimate_systolic_interval,
    run_cardiac_timing_estimation,
)


def _make_synthetic_pcg_envelope(fs: float = 1000.0, duration_s: float = 6.0, bpm: float = 60.0) -> np.ndarray:
    """Generate synthetic periodic envelope with S1 and S2 peaks."""
    cycle_s = 60.0 / bpm
    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    env = np.zeros(n, dtype=np.float64)

    # For each cycle, insert S1 at t_start and S2 at t_start + 0.35 * cycle_s
    t_start = 0.1
    while t_start + 0.4 < duration_s:
        # S1: Gaussian peak at t_start
        env += 1.0 * np.exp(-0.5 * ((t - t_start) / 0.04) ** 2)
        # S2: Gaussian peak at t_start + 0.35 * cycle_s
        t_s2 = t_start + 0.35 * cycle_s
        env += 0.8 * np.exp(-0.5 * ((t - t_s2) / 0.03) ** 2)

        t_start += cycle_s

    # Add baseline offset so envelope is non-negative
    return np.maximum(0.01, env)


class TestSpringerHeartRate:
    """Verifies autocorrelation-based cardiac cycle and systolic interval estimation."""

    def test_estimate_heart_rate_60_bpm(self):
        fs = 1000.0
        env = _make_synthetic_pcg_envelope(fs=fs, duration_s=6.0, bpm=60.0)

        bpm, cycle_s = estimate_heart_rate_schmidt(env, sample_rate_hz=fs)

        assert pytest.approx(bpm, rel=0.05) == 60.0
        assert pytest.approx(cycle_s, rel=0.05) == 1.0

    def test_estimate_heart_rate_75_bpm(self):
        fs = 1000.0
        env = _make_synthetic_pcg_envelope(fs=fs, duration_s=6.0, bpm=75.0)

        bpm, cycle_s = estimate_heart_rate_schmidt(env, sample_rate_hz=fs)

        assert pytest.approx(bpm, rel=0.05) == 75.0
        assert pytest.approx(cycle_s, rel=0.05) == 0.80

    def test_estimate_heart_rate_100_bpm(self):
        fs = 1000.0
        env = _make_synthetic_pcg_envelope(fs=fs, duration_s=6.0, bpm=100.0)

        bpm, cycle_s = estimate_heart_rate_schmidt(env, sample_rate_hz=fs)

        assert pytest.approx(bpm, rel=0.05) == 100.0
        assert pytest.approx(cycle_s, rel=0.05) == 0.60

    def test_estimate_systolic_interval_bounds(self):
        fs = 1000.0
        env = _make_synthetic_pcg_envelope(fs=fs, duration_s=6.0, bpm=60.0)
        cycle_s = 1.0

        sys_s = estimate_systolic_interval(env, cycle_duration_s=cycle_s, sample_rate_hz=fs)

        # Systolic interval must be strictly positive and physiologically bounded [0.2s, 0.5 * cycle_s]
        assert 0.20 <= sys_s <= 0.50 * cycle_s
        assert pytest.approx(sys_s, abs=0.08) == 0.35

    def test_rejects_too_short_recording(self):
        fs = 1000.0
        short_env = np.ones(1000)  # 1.0 second (< 2.0 s)
        with pytest.raises(ValueError, match="too short"):
            estimate_heart_rate_schmidt(short_env, sample_rate_hz=fs)

    def test_rejects_silent_or_flat_envelope(self):
        fs = 1000.0
        flat_env = np.full(3000, 0.5)
        with pytest.raises(ValueError, match="silent or constant"):
            estimate_heart_rate_schmidt(flat_env, sample_rate_hz=fs)

    def test_run_cardiac_timing_estimation_safe_return(self):
        fs = 1000.0
        env = _make_synthetic_pcg_envelope(fs=fs, duration_s=5.0, bpm=72.0)
        timing = run_cardiac_timing_estimation(env, sample_rate_hz=fs)

        assert timing["is_valid"] is True
        assert timing["heart_rate_bpm"] is not None
        assert pytest.approx(timing["heart_rate_bpm"], rel=0.08) == 72.0
        assert timing["cycle_duration_s"] is not None
        assert timing["systolic_interval_s"] is not None

    def test_run_cardiac_timing_estimation_invalid_returns_safe_dict(self):
        # Silent signal
        timing = run_cardiac_timing_estimation(np.zeros(2000), sample_rate_hz=1000.0)
        assert timing["is_valid"] is False
        assert timing["heart_rate_bpm"] is None
        assert timing["error"] is not None
