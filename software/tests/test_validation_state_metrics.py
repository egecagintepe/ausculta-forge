"""Tests for 4-state 50 Hz frame-level evaluation with state 0 ignored."""

import pytest
import numpy as np
from pcg_core.segmentation.validation.metrics import (
    RecordEvaluationOutcome,
    aggregate_state_metrics,
)


def test_state_metrics_ignores_state_zero_and_computes_4x4_matrix():
    # Confusion matrix for 8 annotated frames:
    # Row = reference (S1, Sys, S2, Dia), Col = predicted (S1, Sys, S2, Dia)
    # Row 0 (S1): 1 predicted as S1, 1 as Sys -> [1, 1, 0, 0]
    # Row 1 (Systole): 1 predicted as Sys -> [0, 1, 0, 0]
    # Row 2 (S2): 1 predicted as S2, 1 as Dia -> [0, 0, 1, 1]
    # Row 3 (Diastole): 1 predicted as S1, 2 as Dia -> [1, 0, 0, 2]
    # Plus 2 frames of state 0 (ignored)
    cm = np.array([
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 1],
        [1, 0, 0, 2],
    ], dtype=np.int64)

    outcome = RecordEvaluationOutcome(
        record_id="REC_TEST",
        subject_id="SUBJ_1",
        auscultation_location="AV",
        duration_s=0.2,
        segmentation_status="SUCCESS",
        is_success=True,
        reference_s1_events=[],
        reference_s2_events=[],
        predicted_s1_events=[],
        predicted_s2_events=[],
        event_results={},
        signed_errors_s1_100ms=[],
        signed_errors_s2_100ms=[],
        confusion_matrix_4x4=cm,
        annotated_frames_count=8,
        ignored_frames_count=2,
    )

    state_res = aggregate_state_metrics([outcome])
    assert state_res is not None

    # Total annotated frames should be 8
    assert state_res.total_annotated_frames == 8
    assert state_res.total_ignored_frames == 2

    matrix = state_res.confusion_matrix
    assert len(matrix) == 4
    for row in matrix:
        assert len(row) == 4

    assert matrix[0] == [1, 1, 0, 0]
    assert matrix[1] == [0, 1, 0, 0]
    assert matrix[2] == [0, 0, 1, 1]
    assert matrix[3] == [1, 0, 0, 2]

    # Overall agreement: (1 + 1 + 1 + 2) / 8 = 5 / 8 = 0.625
    assert pytest.approx(state_res.annotated_frame_agreement, 0.001) == 0.625

    # Per-state checks:
    # S1: TP=1, FP=1, FN=1 -> F1=0.5
    assert pytest.approx(state_res.per_state_f1["S1"], 0.001) == 0.5
    # Systole: TP=1, FP=1, FN=0 -> Prec=0.5, Rec=1.0, F1=2*(0.5*1)/(1.5) = 2/3
    assert pytest.approx(state_res.per_state_f1["SYSTOLE"], 0.001) == 2.0 / 3.0
    # S2: TP=1, FP=0, FN=1 -> Prec=1.0, Rec=0.5, F1=2/3
    assert pytest.approx(state_res.per_state_f1["S2"], 0.001) == 2.0 / 3.0
    # Diastole: TP=2, FP=1, FN=1 -> Prec=2/3, Rec=2/3, F1=2/3
    assert pytest.approx(state_res.per_state_f1["DIASTOLE"], 0.001) == 2.0 / 3.0

    # Macro F1: mean(0.5, 2/3, 2/3, 2/3) = (0.5 + 2.0) / 4 = 2.5 / 4 = 0.625
    assert pytest.approx(state_res.macro_f1, 0.001) == 0.625
