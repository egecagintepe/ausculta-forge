"""Test that macro-subject aggregation weights subjects equally regardless of recording count."""

import pytest
from pcg_core.segmentation.validation.models import EventToleranceMetrics
from pcg_core.segmentation.validation.metrics import (
    RecordEvaluationOutcome,
    compute_macro_subject_metrics,
    aggregate_event_metrics_view,
)


def _make_outcome(rec_id: str, subj_id: str, perfect: bool) -> RecordEvaluationOutcome:
    if perfect:
        # TP=1, FP=0, FN=0 for S1; TP=1, FP=0, FN=0 for S2
        s1_m = EventToleranceMetrics(tolerance_ms=100.0, tp=1, fp=0, fn=0, sensitivity=1.0, precision=1.0, f1=1.0)
        s2_m = EventToleranceMetrics(tolerance_ms=100.0, tp=1, fp=0, fn=0, sensitivity=1.0, precision=1.0, f1=1.0)
        comb_m = EventToleranceMetrics(tolerance_ms=100.0, tp=2, fp=0, fn=0, sensitivity=1.0, precision=1.0, f1=1.0)
    else:
        # TP=0, FP=1, FN=1 for S1; TP=0, FP=1, FN=1 for S2
        s1_m = EventToleranceMetrics(tolerance_ms=100.0, tp=0, fp=1, fn=1, sensitivity=0.0, precision=0.0, f1=0.0)
        s2_m = EventToleranceMetrics(tolerance_ms=100.0, tp=0, fp=1, fn=1, sensitivity=0.0, precision=0.0, f1=0.0)
        comb_m = EventToleranceMetrics(tolerance_ms=100.0, tp=0, fp=2, fn=2, sensitivity=0.0, precision=0.0, f1=0.0)

    return RecordEvaluationOutcome(
        record_id=rec_id,
        subject_id=subj_id,
        auscultation_location="AV",
        duration_s=2.0,
        segmentation_status="SUCCESS",
        is_success=True,
        reference_s1_events=[1.0],
        reference_s2_events=[1.5],
        predicted_s1_events=[1.0] if perfect else [5.0],
        predicted_s2_events=[1.5] if perfect else [5.5],
        event_results={100.0: (s1_m, s2_m, comb_m)},
        signed_errors_s1_100ms=[0.0] if perfect else [],
        signed_errors_s2_100ms=[0.0] if perfect else [],
    )


def test_macro_subject_weights_subjects_equally():
    # Subject A has 4 recordings: ALL 4 are PERFECT (F1 = 1.0 each)
    # Subject B has 1 recording: FAILED MATCHING (F1 = 0.0)
    outcomes = [
        _make_outcome("A_1", "SUBJ_A", perfect=True),
        _make_outcome("A_2", "SUBJ_A", perfect=True),
        _make_outcome("A_3", "SUBJ_A", perfect=True),
        _make_outcome("A_4", "SUBJ_A", perfect=True),
        _make_outcome("B_1", "SUBJ_B", perfect=False),
    ]

    tolerances_ms = [100.0]

    # 1. Micro Aggregation (pools all records):
    # Total reference events: 5 records * 2 events = 10 events.
    # 4 records perfect (8 TP), 1 record 0 TP (2 FN, 2 FP).
    # Micro F1 = 2 * 8 / (2*8 + 2 + 2) = 16 / 20 = 0.800
    micro = aggregate_event_metrics_view(outcomes, tolerances_ms)
    assert pytest.approx(micro["100ms"].combined.f1, 0.001) == 0.800

    # 2. Macro Subject Aggregation:
    # Subject A score: mean of 4 perfect recordings = 1.0
    # Subject B score: 1 recording = 0.0
    # True Macro Subject F1 = (1.0 + 0.0) / 2 = 0.500
    macro_subj = compute_macro_subject_metrics(outcomes, tolerance_ms=100.0)
    assert macro_subj["subject_count"] == 2
    assert pytest.approx(macro_subj["macro_subject_combined_f1_100ms"], 0.001) == 0.500

    # Critical Assertion: Micro F1 (0.80) does NOT equal Macro Subject F1 (0.50)
    assert micro["100ms"].combined.f1 != macro_subj["macro_subject_combined_f1_100ms"]
