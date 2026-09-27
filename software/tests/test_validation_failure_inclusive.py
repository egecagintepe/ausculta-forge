"""Anti-survivorship bias regression test: End-to-End vs Conditional-on-Success views."""

import pytest
from dataclasses import dataclass
from pathlib import Path
from pcg_core.segmentation.validation.models import (
    AnnotatedPCGRecord,
    ReferenceStateInterval,
)
from pcg_core.segmentation.validation.metrics import (
    evaluate_single_record,
    aggregate_event_metrics_view,
)


@dataclass
class DummyInterval:
    state: int
    start_s: float
    end_s: float
    duration_s: float


@dataclass
class DummyPredictionResult:
    status: str
    state_intervals: list[DummyInterval]
    state_sequence_50hz: list[int]
    total_frames_50hz: int


def test_failure_inclusive_end_to_end_vs_conditional():
    # Record A: SUCCESS with 2 S1 and 2 S2 reference events, perfectly predicted
    intervals_a = [
        ReferenceStateInterval(state=1, start_s=0.2, end_s=0.35),
        ReferenceStateInterval(state=2, start_s=0.35, end_s=0.60),
        ReferenceStateInterval(state=3, start_s=0.60, end_s=0.75),
        ReferenceStateInterval(state=4, start_s=0.75, end_s=1.20),
        ReferenceStateInterval(state=1, start_s=1.20, end_s=1.35),
        ReferenceStateInterval(state=2, start_s=1.35, end_s=1.60),
        ReferenceStateInterval(state=3, start_s=1.60, end_s=1.75),
        ReferenceStateInterval(state=4, start_s=1.75, end_s=2.20),
    ]
    rec_a = AnnotatedPCGRecord(
        dataset_id="CIRCOR",
        dataset_version="1.0.3",
        record_id="REC_A",
        subject_id="SUBJ_A",
        sample_rate_hz=4000.0,
        duration_s=2.5,
        annotation_intervals=intervals_a,
        auscultation_location="AV",
        wav_path=Path("/tmp/a.wav"),
        annotation_path=Path("/tmp/a.tsv"),
    )

    pred_intervals_a = [
        DummyInterval(state=1, start_s=0.2, end_s=0.35, duration_s=0.15),
        DummyInterval(state=2, start_s=0.35, end_s=0.60, duration_s=0.25),
        DummyInterval(state=3, start_s=0.60, end_s=0.75, duration_s=0.15),
        DummyInterval(state=4, start_s=0.75, end_s=1.20, duration_s=0.45),
        DummyInterval(state=1, start_s=1.20, end_s=1.35, duration_s=0.15),
        DummyInterval(state=2, start_s=1.35, end_s=1.60, duration_s=0.25),
        DummyInterval(state=3, start_s=1.60, end_s=1.75, duration_s=0.15),
        DummyInterval(state=4, start_s=1.75, end_s=2.20, duration_s=0.45),
    ]
    pred_a = DummyPredictionResult(
        status="SUCCESS",
        state_intervals=pred_intervals_a,
        state_sequence_50hz=[1] * 125,
        total_frames_50hz=125,
    )
    outcome_a = evaluate_single_record(rec_a, pred_a, event_tolerances_ms=[100.0])
    assert outcome_a.is_success is True

    # Record B: FAILURE with 5 S1 and 5 S2 reference events
    intervals_b = []
    for i in range(5):
        t0 = float(i)
        intervals_b.append(ReferenceStateInterval(state=1, start_s=t0 + 0.1, end_s=t0 + 0.2))
        intervals_b.append(ReferenceStateInterval(state=2, start_s=t0 + 0.2, end_s=t0 + 0.5))
        intervals_b.append(ReferenceStateInterval(state=3, start_s=t0 + 0.5, end_s=t0 + 0.6))
        intervals_b.append(ReferenceStateInterval(state=4, start_s=t0 + 0.6, end_s=t0 + 1.0))

    rec_b = AnnotatedPCGRecord(
        dataset_id="CIRCOR",
        dataset_version="1.0.3",
        record_id="REC_B",
        subject_id="SUBJ_B",
        sample_rate_hz=4000.0,
        duration_s=5.0,
        annotation_intervals=intervals_b,
        auscultation_location="MV",
        wav_path=Path("/tmp/b.wav"),
        annotation_path=Path("/tmp/b.tsv"),
    )

    pred_b_failed = DummyPredictionResult(
        status="HEART_RATE_ESTIMATION_FAILED",
        state_intervals=[],
        state_sequence_50hz=[],
        total_frames_50hz=0,
    )
    outcome_b = evaluate_single_record(rec_b, pred_b_failed, event_tolerances_ms=[100.0])
    assert outcome_b.is_success is False
    # Predicted events must be empty due to failure
    assert len(outcome_b.predicted_s1_events) == 0
    assert len(outcome_b.predicted_s2_events) == 0

    # 1. CONDITIONAL ON SUCCESS: Only successful outcomes are included
    cond_outcomes = [o for o in [outcome_a, outcome_b] if o.is_success]
    cond_metrics = aggregate_event_metrics_view(cond_outcomes, tolerances_ms=[100.0])
    cond_100 = cond_metrics["100ms"]

    # Record A alone is 100% perfect
    assert cond_100.combined.tp == 4
    assert cond_100.combined.fp == 0
    assert cond_100.combined.fn == 0
    assert cond_100.combined.precision == 1.0
    assert cond_100.combined.recall == 1.0
    assert cond_100.combined.f1 == 1.0

    # 2. END-TO-END (Primary Benchmark): Evaluates both records.
    # Record B reference events (5 S1 + 5 S2 = 10 events) MUST become False Negatives!
    e2e_outcomes = [outcome_a, outcome_b]
    e2e_metrics = aggregate_event_metrics_view(e2e_outcomes, tolerances_ms=[100.0])
    e2e_100 = e2e_metrics["100ms"]

    assert e2e_100.combined.tp == 4
    assert e2e_100.combined.fp == 0
    assert e2e_100.combined.fn == 10  # 10 missed reference events from Record B!
    assert e2e_100.combined.precision == 1.0
    # Recall = 4 / (4 + 10) = 4/14 = 2/7 approx 0.2857
    assert pytest.approx(e2e_100.combined.recall, 0.001) == 4.0 / 14.0
    # F1 = 2 * (1.0 * (2/7)) / (1.0 + 2/7) = 4/9 approx 0.4444
    assert pytest.approx(e2e_100.combined.f1, 0.001) == 4.0 / 9.0

    # Critical Assertion: Conditional F1 (1.0) > End-to-End F1 (0.444)
    assert cond_100.combined.f1 > e2e_100.combined.f1
