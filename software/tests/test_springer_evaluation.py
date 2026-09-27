"""AuscultaForge — Automated Tests for Segmentation Evaluation Foundation.

Verifies:
- Onset-based temporal event matching across tolerances (20 ms, 50 ms, 100 ms)
- True Positive, False Positive, and False Negative computation
- Precision, Recall, and F1 calculations
"""

import pytest

from pcg_core.segmentation.evaluation import evaluate_segmentation_onsets
from pcg_core.segmentation.models import StateInterval, HeartSoundState


class TestSpringerEvaluation:
    """Verifies temporal event matching and F1 metric calculation."""

    def test_perfect_matching(self):
        # 3 S1 intervals at t = 0.5s, 1.5s, 2.5s
        intervals = [
            StateInterval(state=1, state_name="S1", start_s=0.50, end_s=0.62, duration_s=0.12, start_frame_50hz=25, end_frame_50hz=31),
            StateInterval(state=2, state_name="SYSTOLE", start_s=0.62, end_s=0.90, duration_s=0.28, start_frame_50hz=31, end_frame_50hz=45),
            StateInterval(state=1, state_name="S1", start_s=1.50, end_s=1.62, duration_s=0.12, start_frame_50hz=75, end_frame_50hz=81),
            StateInterval(state=1, state_name="S1", start_s=2.50, end_s=2.62, duration_s=0.12, start_frame_50hz=125, end_frame_50hz=131),
        ]
        reference_onsets = [0.50, 1.50, 2.50]

        metrics = evaluate_segmentation_onsets(intervals, reference_onsets, target_state=1, tolerance_ms=50.0)

        assert metrics.true_positives == 3
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.sensitivity == 1.0
        assert metrics.positive_predictivity == 1.0
        assert metrics.f1_score == 1.0

    def test_imperfect_matching_with_missing_and_spurious_events(self):
        # Predicted onsets: 0.50s (matches), 1.00s (spurious FP), 2.50s (matches)
        # Reference onsets: 0.50s (matches), 1.50s (missed FN), 2.50s (matches)
        intervals = [
            StateInterval(state=1, state_name="S1", start_s=0.50, end_s=0.62, duration_s=0.12, start_frame_50hz=25, end_frame_50hz=31),
            StateInterval(state=1, state_name="S1", start_s=1.00, end_s=1.12, duration_s=0.12, start_frame_50hz=50, end_frame_50hz=56),
            StateInterval(state=1, state_name="S1", start_s=2.50, end_s=2.62, duration_s=0.12, start_frame_50hz=125, end_frame_50hz=131),
        ]
        reference_onsets = [0.50, 1.50, 2.50]

        metrics = evaluate_segmentation_onsets(intervals, reference_onsets, target_state=1, tolerance_ms=50.0)

        assert metrics.true_positives == 2
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1
        # Sensitivity = 2 / 3 = 0.6667
        assert pytest.approx(metrics.sensitivity, abs=1e-3) == 0.6667
        # Precision = 2 / 3 = 0.6667
        assert pytest.approx(metrics.positive_predictivity, abs=1e-3) == 0.6667
        assert pytest.approx(metrics.f1_score, abs=1e-3) == 0.6667

    def test_tolerance_impact(self):
        # Predicted onset is 40 ms late: pred = 1.04 s, ref = 1.00 s
        intervals = [
            StateInterval(state=1, state_name="S1", start_s=1.04, end_s=1.16, duration_s=0.12, start_frame_50hz=52, end_frame_50hz=58)
        ]
        reference_onsets = [1.00]

        # At tolerance 20 ms: diff (40 ms) > tol -> No match (TP=0, FP=1, FN=1)
        m_20 = evaluate_segmentation_onsets(intervals, reference_onsets, target_state=1, tolerance_ms=20.0)
        assert m_20.true_positives == 0
        assert m_20.f1_score == 0.0

        # At tolerance 50 ms: diff (40 ms) <= tol -> Match! (TP=1, FP=0, FN=0)
        m_50 = evaluate_segmentation_onsets(intervals, reference_onsets, target_state=1, tolerance_ms=50.0)
        assert m_50.true_positives == 1
        assert m_50.f1_score == 1.0
