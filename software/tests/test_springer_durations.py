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

        # Hand-computed exact reference values at Fs_feat = 50.0:
        # S1:
        # mean_f = round(0.122 * 50) = 6
        # std_f = round(0.022 * 50) = 1
        # bounds: 6 +/- 3*1 = [3, 9]
        assert s1.mean_frames_50hz == 6
        assert s1.std_frames_50hz == 1.0
        assert s1.min_frames_50hz == 3
        assert s1.max_frames_50hz == 9
        assert s1.mean_s == 0.12
        assert s1.std_s == 0.02
        assert s1.min_s == 0.06
        assert s1.max_s == 0.18

        # S2:
        # mean_f = round(0.094 * 50) = 5
        # std_f = round(0.022 * 50) = 1
        # bounds: 5 +/- 3*1 = [2, 8]
        assert s2.mean_frames_50hz == 5
        assert s2.std_frames_50hz == 1.0
        assert s2.min_frames_50hz == 2
        assert s2.max_frames_50hz == 8
        assert s2.mean_s == 0.10
        assert s2.std_s == 0.02
        assert s2.min_s == 0.04
        assert s2.max_s == 0.16

        # Systole:
        # mean_f = round(0.35 * 50) - 6 = 18 - 6 = 12
        # std_f = 0.025 * 50 = 1.25
        # bounds: 12 +/- 3*(1.25 + 1.0) = 12 +/- 6.75 = [5.25, 18.75] -> [5, 19]
        assert systole.mean_frames_50hz == 12
        assert systole.std_frames_50hz == 1.25
        assert systole.min_frames_50hz == 5
        assert systole.max_frames_50hz == 19
        assert systole.mean_s == 0.24
        assert systole.std_s == 0.025
        assert systole.min_s == 0.10
        assert systole.max_s == 0.38

        # Diastole:
        # mean_f = (1.00 - 0.35 - 0.094) * 50 = 27.8
        # std_f = 0.07 * 27.8 + 0.006 * 50 = 1.946 + 0.3 = 2.246
        # bounds: 27.8 +/- 3*2.246 = 27.8 +/- 6.738 = [21.062, 34.538] -> [21, 35]
        assert systole.mean_frames_50hz == 12
        assert diastole.mean_frames_50hz == 28  # round(27.8) = 28
        assert pytest.approx(diastole.std_frames_50hz, abs=1e-3) == 2.246
        assert diastole.min_frames_50hz == 21
        assert diastole.max_frames_50hz == 35
        assert pytest.approx(diastole.mean_s, abs=1e-3) == 0.556
        assert pytest.approx(diastole.std_s, abs=1e-4) == 0.0449
        assert diastole.min_s == 0.42
        assert diastole.max_s == 0.70

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
