"""Tests for 1-to-1 event matching within tolerance windows."""

import pytest
from pcg_core.segmentation.validation.matching import (
    match_events_one_to_one,
    compute_event_metrics_at_tolerance,
)


def test_perfect_event_alignment():
    refs = [0.5, 1.5]
    preds = [0.5, 1.5]

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 2
    assert len(unmatched_p) == 0
    assert len(unmatched_r) == 0
    assert matches[0][2] == 0.0
    assert matches[1][2] == 0.0


def test_one_prediction_within_tolerance_one_outside():
    refs = [1.00]
    # Prediction at 1.03s is +30ms away -> within 50ms tolerance
    # Prediction at 1.08s is +80ms away -> outside 50ms tolerance
    preds = [1.03, 1.08]

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 1
    assert unmatched_p == [1]
    assert len(unmatched_r) == 0
    # Match error
    p_idx, r_idx, err_s = matches[0]
    assert p_idx == 0
    assert r_idx == 0
    assert pytest.approx(err_s, 0.0001) == 0.030


def test_two_predictions_near_one_reference_guarantees_1to1():
    # Only 1 true positive allowed; duplicate prediction becomes FP!
    refs = [1.00]
    preds = [1.01, 1.02]  # +10ms, +20ms

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 1
    assert matches[0][0] == 0  # matched the closer one (1.01)
    assert unmatched_p == [1]   # 1.02 is unmatched
    assert len(unmatched_r) == 0


def test_one_prediction_near_two_references_guarantees_1to1():
    # 1 prediction cannot claim both references
    refs = [1.00, 1.04]
    preds = [1.01]  # 10ms from ref 0, 30ms from ref 1

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 1
    assert matches[0][1] == 0  # matched closer ref 0
    assert len(unmatched_p) == 0
    assert unmatched_r == [1]  # ref 1 remains unmatched


def test_missing_prediction():
    refs = [1.00]
    preds = []

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 0
    assert len(unmatched_p) == 0
    assert unmatched_r == [0]


def test_extra_prediction():
    refs = []
    preds = [1.00]

    matches, unmatched_p, unmatched_r = match_events_one_to_one(preds, refs, tolerance_s=0.050)
    assert len(matches) == 0
    assert unmatched_p == [0]
    assert len(unmatched_r) == 0


def test_s1_and_s2_independent_matching():
    # S1 and S2 events evaluated separately
    s1_refs = [0.50]
    s2_refs = [0.80]

    s1_preds = [0.52]  # S1 match (+20ms)
    s2_preds = []      # S2 missing

    m_s1, err_s1 = compute_event_metrics_at_tolerance(s1_preds, s1_refs, tolerance_ms=50)
    m_s2, err_s2 = compute_event_metrics_at_tolerance(s2_preds, s2_refs, tolerance_ms=50)

    assert m_s1.tp == 1 and m_s1.fp == 0 and m_s1.fn == 0
    assert m_s2.tp == 0 and m_s2.fp == 0 and m_s2.fn == 1
