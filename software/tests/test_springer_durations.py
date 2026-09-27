"""AuscultaForge — Automated Tests for Springer Duration Distributions.

Verifies:
- Exact reference duration equations at 50 Hz
- S1, S2, Systole, and Diastole means and standard deviations
- Discrete probability mass sums to 1.0
- Rejection of invalid/impossible duration combinations
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.durations import (
    compute_springer_duration_distributions,
    get_duration_probabilities_50hz,
    SPRINGER_S1_MEAN_S,
    SPRINGER_S1_STD_S,
    SPRINGER_S2_MEAN_S,
    SPRINGER_S2_STD_S,
)
from pcg_core.segmentation.models import HeartSoundState


class TestSpringerDurations:
    """Verifies Springer/Schmidt duration distribution calculations."""

    def test_duration_equations_standard_case(self):
        # 60 BPM -> cycle = 1.0 s; systolic interval = 0.35 s
        cycle_s = 1.00
        sys_s = 0.35
        fs_feat = 50.0

        dur_stats = compute_springer_duration_distributions(
            cycle_duration_s=cycle_s,
            systolic_interval_s=sys_s,
            feature_sample_rate_hz=fs_feat,
        )

        s1 = dur_stats[HeartSoundState.S1]
        systole = dur_stats[HeartSoundState.SYSTOLE]
        s2 = dur_stats[HeartSoundState.S2]
        diastole = dur_stats[HeartSoundState.DIASTOLE]

        # 1. S1: mean 0.122 s -> ~6 frames at 50 Hz
        assert pytest.approx(s1.mean_s) == SPRINGER_S1_MEAN_S
        assert s1.mean_frames_50hz == 6

        # 2. S2: mean 0.094 s -> ~5 frames at 50 Hz
        assert pytest.approx(s2.mean_s) == SPRINGER_S2_MEAN_S
        assert s2.mean_frames_50hz == 5

        # 3. Systole: mean = sys_interval (0.35) - S1 (0.122) = 0.228 s -> ~11 frames
        expected_sys_mean = 0.35 - SPRINGER_S1_MEAN_S
        assert pytest.approx(systole.mean_s, abs=1e-3) == expected_sys_mean
        assert systole.mean_frames_50hz == int(round(expected_sys_mean * 50.0))

        # 4. Diastole: mean = cycle (1.0) - sys_interval (0.35) - S2 (0.094) = 0.556 s -> ~28 frames
        expected_dia_mean = 1.0 - 0.35 - SPRINGER_S2_MEAN_S
        assert pytest.approx(diastole.mean_s, abs=1e-3) == expected_dia_mean
        assert diastole.mean_frames_50hz == int(round(expected_dia_mean * 50.0))

        # Sum of mean state durations must equal total cycle duration
        total_mean = s1.mean_s + systole.mean_s + s2.mean_s + diastole.mean_s
        assert pytest.approx(total_mean, abs=1e-3) == cycle_s

    def test_duration_probabilities_sum_to_one(self):
        cycle_s = 0.80  # 75 BPM
        sys_s = 0.30
        dur_stats = compute_springer_duration_distributions(cycle_s, sys_s, feature_sample_rate_hz=50.0)

        for state in [HeartSoundState.S1, HeartSoundState.SYSTOLE, HeartSoundState.S2, HeartSoundState.DIASTOLE]:
            stats = dur_stats[state]
            probs, log_probs, d_min, d_max = get_duration_probabilities_50hz(stats)

            # Sum of probabilities must equal 1.0 within numerical precision
            assert pytest.approx(np.sum(probs), abs=1e-6) == 1.0
            # All log probabilities must be finite
            assert np.all(np.isfinite(log_probs))
            assert d_min >= 1
            assert d_max > d_min

    def test_rejects_physiologically_impossible_systolic_duration(self):
        # Systolic interval smaller than S1 duration -> negative systole
        with pytest.raises(ValueError, match="SEGMENTATION_PARAMETERS_INVALID"):
            compute_springer_duration_distributions(
                cycle_duration_s=1.0,
                systolic_interval_s=0.10,  # Less than S1 mean (0.122 s)
                feature_sample_rate_hz=50.0,
            )

    def test_rejects_cycle_smaller_than_systolic_interval(self):
        with pytest.raises(ValueError, match="SEGMENTATION_PARAMETERS_INVALID"):
            compute_springer_duration_distributions(
                cycle_duration_s=0.30,
                systolic_interval_s=0.35,  # Exceeds cycle
                feature_sample_rate_hz=50.0,
            )
