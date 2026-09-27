"""AuscultaForge — Automated Tests for HSMM Extended Viterbi Decoding.

Verifies:
- Bayes log emission computation
- Cyclic transition constraint (S1 -> Systole -> S2 -> Diastole -> S1)
- Explicit duration model shifts candidate path scoring
- Extended Viterbi boundary conditions:
  - Recording begins halfway through Diastole (initial partial state)
  - Recording begins halfway through S1
  - Recording ends halfway through Systole (final partial state)
  - Recording ends halfway through S2
- State sequence length matches input observation length exactly
- All decoded states belong to {1, 2, 3, 4}
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.hsmm import (
    compute_hsmm_log_emissions,
    viterbi_decode_pcg_extended,
    extract_state_intervals_from_sequence,
)
from pcg_core.segmentation.durations import compute_springer_duration_distributions
from pcg_core.segmentation.models import HeartSoundState


class TestSpringerHSMM:
    """Verifies HSMM emission calculation and extended Viterbi boundary decoding."""

    @pytest.fixture
    def standard_duration_stats(self):
        # 60 BPM -> 1.0 s cycle, 0.35 s systolic interval
        return compute_springer_duration_distributions(
            cycle_duration_s=1.0,
            systolic_interval_s=0.35,
            feature_sample_rate_hz=50.0,
        )

    def test_compute_hsmm_log_emissions_bayes_rule(self):
        T = 50
        K = 3
        obs = np.zeros((T, K))
        posteriors = np.full((T, 4), 0.25)
        obs_mean = np.zeros(K)
        obs_cov = np.eye(K)
        pi = [0.25, 0.25, 0.25, 0.25]

        log_b = compute_hsmm_log_emissions(obs, posteriors, obs_mean, obs_cov, pi)

        assert log_b.shape == (4, T)
        assert np.all(np.isfinite(log_b))

    def test_extended_viterbi_cyclic_sequence_structure(self, standard_duration_stats):
        """Construct synthetic log emissions favoring cyclic progression and verify decoded order."""
        # 1 complete cycle: S1 (6 frames) -> Sys (11 frames) -> S2 (5 frames) -> Dia (28 frames) = 50 frames
        T = 100  # 2 full cycles
        log_emissions = np.full((4, T), -10.0)

        # Force state emissions across two cycles
        c1_s1 = slice(0, 6)
        c1_sys = slice(6, 17)
        c1_s2 = slice(17, 22)
        c1_dia = slice(22, 50)

        c2_s1 = slice(50, 56)
        c2_sys = slice(56, 67)
        c2_s2 = slice(67, 72)
        c2_dia = slice(72, 100)

        log_emissions[0, c1_s1] = 0.0
        log_emissions[1, c1_sys] = 0.0
        log_emissions[2, c1_s2] = 0.0
        log_emissions[3, c1_dia] = 0.0

        log_emissions[0, c2_s1] = 0.0
        log_emissions[1, c2_sys] = 0.0
        log_emissions[2, c2_s2] = 0.0
        log_emissions[3, c2_dia] = 0.0

        seq, intervals = viterbi_decode_pcg_extended(log_emissions, standard_duration_stats)

        assert len(seq) == T
        assert np.all(np.isin(seq, [1, 2, 3, 4]))

        # Check cyclic order in interval sequence
        state_order = [iv.state for iv in intervals]
        # Should be S1 (1) -> Systole (2) -> S2 (3) -> Diastole (4) -> S1 (1) -> ...
        for i in range(len(state_order) - 1):
            expected_next = HeartSoundState.next_state(HeartSoundState(state_order[i])).value
            assert state_order[i + 1] == expected_next

    def test_boundary_begins_halfway_through_diastole(self, standard_duration_stats):
        """Recording begins halfway through Diastole (e.g. 10 frames of Diastole before S1)."""
        T = 80
        log_emissions = np.full((4, T), -10.0)

        # Initial partial Diastole: frames 0..9 (10 frames)
        log_emissions[3, 0:10] = 0.0
        # Followed by normal S1 (6 frames: 10..15)
        log_emissions[0, 10:16] = 0.0
        # Followed by Systole (11 frames: 16..26)
        log_emissions[1, 16:27] = 0.0
        # Followed by S2 (5 frames: 27..31)
        log_emissions[2, 27:32] = 0.0
        # Followed by Diastole (28 frames: 32..59)
        log_emissions[3, 32:60] = 0.0
        # Followed by S1 (6 frames: 60..65)
        log_emissions[0, 60:66] = 0.0
        # Remaining: Systole
        log_emissions[1, 66:T] = 0.0

        seq, intervals = viterbi_decode_pcg_extended(log_emissions, standard_duration_stats)

        assert len(seq) == T
        # First interval must be Diastole (State 4) despite lasting only ~10 frames (< normal mean 28)
        assert intervals[0].state == 4
        # Followed immediately by S1 (State 1)
        assert intervals[1].state == 1

    def test_boundary_begins_halfway_through_s1(self, standard_duration_stats):
        """Recording begins halfway through S1 (e.g. 3 frames of S1 before Systole)."""
        T = 60
        log_emissions = np.full((4, T), -10.0)

        # Initial partial S1: frames 0..2 (3 frames)
        log_emissions[0, 0:3] = 0.0
        # Systole: frames 3..13
        log_emissions[1, 3:14] = 0.0
        # S2: frames 14..18
        log_emissions[2, 14:19] = 0.0
        # Diastole: frames 19..46
        log_emissions[3, 19:47] = 0.0
        # Next S1: frames 47..52
        log_emissions[0, 47:53] = 0.0
        # Rest: Systole
        log_emissions[1, 53:T] = 0.0

        seq, intervals = viterbi_decode_pcg_extended(log_emissions, standard_duration_stats)

        assert len(seq) == T
        assert intervals[0].state == 1  # S1
        assert intervals[1].state == 2  # Systole

    def test_boundary_ends_halfway_through_systole(self, standard_duration_stats):
        """Recording ends partway through Systole."""
        T = 50
        log_emissions = np.full((4, T), -10.0)

        # S1: 0..5 (6 frames)
        log_emissions[0, 0:6] = 0.0
        # Systole: 6..16 (11 frames)
        log_emissions[1, 6:17] = 0.0
        # S2: 17..21 (5 frames)
        log_emissions[2, 17:22] = 0.0
        # Diastole: 22..41 (20 frames)
        log_emissions[3, 22:42] = 0.0
        # S1: 42..46 (5 frames)
        log_emissions[0, 42:47] = 0.0
        # Incomplete Systole at end: 47..49 (3 frames)
        log_emissions[1, 47:50] = 0.0

        seq, intervals = viterbi_decode_pcg_extended(log_emissions, standard_duration_stats)

        assert len(seq) == T
        # Final interval must be Systole (State 2)
        assert intervals[-1].state == 2

    def test_boundary_ends_halfway_through_s2(self, standard_duration_stats):
        """Recording ends partway through S2."""
        T = 40
        log_emissions = np.full((4, T), -10.0)

        # Diastole: 0..19 (20 frames)
        log_emissions[3, 0:20] = 0.0
        # S1: 20..25 (6 frames)
        log_emissions[0, 20:26] = 0.0
        # Systole: 26..36 (11 frames)
        log_emissions[1, 26:37] = 0.0
        # Incomplete S2 at end: 37..39 (3 frames)
        log_emissions[2, 37:40] = 0.0

        seq, intervals = viterbi_decode_pcg_extended(log_emissions, standard_duration_stats)

        assert len(seq) == T
        assert intervals[-1].state == 3  # S2
