"""Hand-computed verification of event-level metrics at 20, 40, 60, 80, 100 ms."""

import pytest
from pcg_core.segmentation.validation.matching import compute_event_metrics_at_tolerance


def test_hand_computed_metric_matrix_all_tolerances():
    # References: 2 events at 1.000s, 2.000s
    refs = [1.000, 2.000]

    # Predictions:
    # 1.025 (+25 ms error)
    # 2.065 (+65 ms error)
    # 3.000 (false positive)
    preds = [1.025, 2.065, 3.000]

    # 1. 20 ms tolerance
    m20, err20 = compute_event_metrics_at_tolerance(preds, refs, tolerance_ms=20)
    assert m20.tp == 0
    assert m20.fp == 3
    assert m20.fn == 2
    assert m20.precision == 0.0
    assert m20.recall == 0.0
    assert m20.f1 == 0.0
    assert len(err20) == 0

    # 2. 40 ms tolerance
    m40, err40 = compute_event_metrics_at_tolerance(preds, refs, tolerance_ms=40)
    assert m40.tp == 1
    assert m40.fp == 2
    assert m40.fn == 1
    assert pytest.approx(m40.precision, 0.001) == 1.0 / 3.0
    assert pytest.approx(m40.recall, 0.001) == 0.5
    assert pytest.approx(m40.f1, 0.001) == 0.4
    assert len(err40) == 1
    assert pytest.approx(err40[0], 0.01) == 25.0

    # 3. 60 ms tolerance
    m60, err60 = compute_event_metrics_at_tolerance(preds, refs, tolerance_ms=60)
    assert m60.tp == 1
    assert m60.fp == 2
    assert m60.fn == 1
    assert pytest.approx(m60.precision, 0.001) == 1.0 / 3.0
    assert pytest.approx(m60.recall, 0.001) == 0.5
    assert pytest.approx(m60.f1, 0.001) == 0.4

    # 4. 80 ms tolerance
    m80, err80 = compute_event_metrics_at_tolerance(preds, refs, tolerance_ms=80)
    assert m80.tp == 2
    assert m80.fp == 1
    assert m80.fn == 0
    assert pytest.approx(m80.precision, 0.001) == 2.0 / 3.0
    assert pytest.approx(m80.recall, 0.001) == 1.0
    assert pytest.approx(m80.f1, 0.001) == 0.8
    assert len(err80) == 2
    assert pytest.approx(err80[0], 0.01) == 25.0
    assert pytest.approx(err80[1], 0.01) == 65.0

    # 5. 100 ms tolerance
    m100, err100 = compute_event_metrics_at_tolerance(preds, refs, tolerance_ms=100)
    assert m100.tp == 2
    assert m100.fp == 1
    assert m100.fn == 0
    assert pytest.approx(m100.precision, 0.001) == 2.0 / 3.0
    assert pytest.approx(m100.recall, 0.001) == 1.0
    assert pytest.approx(m100.f1, 0.001) == 0.8
