"""AuscultaForge — Segmentation Validation Metrics and Aggregations.

Computes:
1. End-to-End Metrics (anti-survivorship-bias: failed segmentations produce 0 predictions,
   causing all reference events to be counted as False Negatives).
2. Conditional-on-Success Metrics (only evaluated on SUCCESS recordings).
3. Event-level metrics at 20, 40, 60, 80, 100 ms for S1, S2, and combined.
4. State-level 4x4 confusion matrix and frame agreement on evaluation_mask == True.
5. Micro, Macro-Record, and Macro-Subject aggregations.
6. Descriptive breakdown by auscultation location.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence, Optional
import numpy as np

from .models import (
    EventToleranceMetrics,
    EventEvaluationResult,
    TimingErrorMetrics,
    StateMetrics,
    LocationMetrics,
    AnnotatedPCGRecord,
)
from .matching import (
    compute_event_metrics_at_tolerance,
    compute_timing_error_metrics,
)
from .annotations import (
    convert_intervals_to_50hz_labels,
    extract_events_from_reference_intervals,
    extract_events_from_predictions,
)


@dataclass(slots=True)
class RecordEvaluationOutcome:
    """Evaluation outcome for a single PCG record."""
    record_id: str
    subject_id: str
    auscultation_location: Optional[str]
    duration_s: float
    segmentation_status: str
    is_success: bool
    reference_s1_events: list[float]
    reference_s2_events: list[float]
    predicted_s1_events: list[float]
    predicted_s2_events: list[float]
    # Tolerance -> (s1_metrics, s2_metrics, combined_metrics)
    event_results: dict[float, tuple[EventToleranceMetrics, EventToleranceMetrics, EventToleranceMetrics]]
    signed_errors_s1_100ms: list[float]
    signed_errors_s2_100ms: list[float]
    # State-level metrics if available
    confusion_matrix_4x4: Optional[np.ndarray] = None
    annotated_frames_count: int = 0
    ignored_frames_count: int = 0


from dataclasses import dataclass


def evaluate_single_record(
    record: AnnotatedPCGRecord,
    prediction_result: Any,  # SpringerSegmentationResult
    event_tolerances_ms: Sequence[float] = (20.0, 40.0, 60.0, 80.0, 100.0),
    event_anchor: str = "ONSET",
    include_state_metrics: bool = True,
) -> RecordEvaluationOutcome:
    """Evaluate a single record against reference annotations.
    
    If prediction_result.status != SUCCESS:
    Predicted event set is empty (anti-survivorship-bias: all reference events become FNs).
    """
    status = getattr(prediction_result, "status", "FAILED")
    status_str = status.value if hasattr(status, "value") else str(status)
    is_success = (status_str == "SUCCESS")

    # Reference events
    ref_events = extract_events_from_reference_intervals(
        record.annotation_intervals, event_anchor=event_anchor
    )
    ref_s1 = ref_events["S1"]
    ref_s2 = ref_events["S2"]

    # Predicted events
    if is_success and hasattr(prediction_result, "state_intervals"):
        pred_events = extract_events_from_predictions(
            prediction_result.state_intervals, event_anchor=event_anchor
        )
        pred_s1 = pred_events["S1"]
        pred_s2 = pred_events["S2"]
    else:
        pred_s1 = []
        pred_s2 = []

    # Compute event metrics across all requested tolerances
    event_results: dict[float, tuple[EventToleranceMetrics, EventToleranceMetrics, EventToleranceMetrics]] = {}
    signed_s1_100ms: list[float] = []
    signed_s2_100ms: list[float] = []

    for tol_ms in event_tolerances_ms:
        m_s1, err_s1 = compute_event_metrics_at_tolerance(pred_s1, ref_s1, tol_ms)
        m_s2, err_s2 = compute_event_metrics_at_tolerance(pred_s2, ref_s2, tol_ms)

        # Combined S1 + S2
        comb_tp = m_s1.tp + m_s2.tp
        comb_fp = m_s1.fp + m_s2.fp
        comb_fn = m_s1.fn + m_s2.fn
        comb_sens = float(comb_tp) / float(comb_tp + comb_fn) if (comb_tp + comb_fn) > 0 else 0.0
        comb_prec = float(comb_tp) / float(comb_tp + comb_fp) if (comb_tp + comb_fp) > 0 else 0.0
        comb_f1 = 2.0 * comb_prec * comb_sens / (comb_prec + comb_sens) if (comb_prec + comb_sens) > 0 else 0.0

        m_comb = EventToleranceMetrics(
            tolerance_ms=tol_ms,
            tp=comb_tp,
            fp=comb_fp,
            fn=comb_fn,
            sensitivity=comb_sens,
            precision=comb_prec,
            f1=comb_f1,
        )

        event_results[tol_ms] = (m_s1, m_s2, m_comb)

        if tol_ms == 100.0:
            signed_s1_100ms = err_s1
            signed_s2_100ms = err_s2

    # State-level 4x4 confusion matrix
    cm_4x4: Optional[np.ndarray] = None
    annotated_frames = 0
    ignored_frames = 0

    if include_state_metrics and is_success and hasattr(prediction_result, "state_sequence_50hz"):
        pred_seq = np.asarray(prediction_result.state_sequence_50hz, dtype=np.int32)
        n_frames = len(pred_seq)

        ref_seq, eval_mask = convert_intervals_to_50hz_labels(
            record.annotation_intervals, total_frames_50hz=n_frames, feature_sample_rate_hz=50.0
        )

        annotated_frames = int(np.sum(eval_mask))
        ignored_frames = int(n_frames - annotated_frames)

        cm_4x4 = np.zeros((4, 4), dtype=np.int64)
        if annotated_frames > 0:
            valid_ref = ref_seq[eval_mask]
            valid_pred = pred_seq[eval_mask]

            for r_st, p_st in zip(valid_ref, valid_pred):
                # States in {1, 2, 3, 4} -> 0-indexed [0, 3]
                if 1 <= r_st <= 4 and 1 <= p_st <= 4:
                    cm_4x4[r_st - 1, p_st - 1] += 1

    return RecordEvaluationOutcome(
        record_id=record.record_id,
        subject_id=record.subject_id,
        auscultation_location=record.auscultation_location,
        duration_s=record.duration_s,
        segmentation_status=status_str,
        is_success=is_success,
        reference_s1_events=ref_s1,
        reference_s2_events=ref_s2,
        predicted_s1_events=pred_s1,
        predicted_s2_events=pred_s2,
        event_results=event_results,
        signed_errors_s1_100ms=signed_s1_100ms,
        signed_errors_s2_100ms=signed_s2_100ms,
        confusion_matrix_4x4=cm_4x4,
        annotated_frames_count=annotated_frames,
        ignored_frames_count=ignored_frames,
    )


def aggregate_event_metrics_view(
    outcomes: Sequence[RecordEvaluationOutcome],
    tolerances_ms: Sequence[float] = (20.0, 40.0, 60.0, 80.0, 100.0),
) -> dict[str, EventEvaluationResult]:
    """Micro-aggregate TP/FP/FN across given outcomes for all tolerances."""
    view: dict[str, EventEvaluationResult] = {}

    for tol_ms in tolerances_ms:
        tol_key = f"{int(tol_ms)}ms"

        tp_s1 = sum(o.event_results[tol_ms][0].tp for o in outcomes if tol_ms in o.event_results)
        fp_s1 = sum(o.event_results[tol_ms][0].fp for o in outcomes if tol_ms in o.event_results)
        fn_s1 = sum(o.event_results[tol_ms][0].fn for o in outcomes if tol_ms in o.event_results)

        tp_s2 = sum(o.event_results[tol_ms][1].tp for o in outcomes if tol_ms in o.event_results)
        fp_s2 = sum(o.event_results[tol_ms][1].fp for o in outcomes if tol_ms in o.event_results)
        fn_s2 = sum(o.event_results[tol_ms][1].fn for o in outcomes if tol_ms in o.event_results)

        tp_comb = tp_s1 + tp_s2
        fp_comb = fp_s1 + fp_s2
        fn_comb = fn_s1 + fn_s2

        def _calc_m(tp: int, fp: int, fn: int) -> EventToleranceMetrics:
            sens = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
            prec = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
            f1 = 2.0 * prec * sens / (prec + sens) if (prec + sens) > 0 else 0.0
            return EventToleranceMetrics(
                tolerance_ms=tol_ms,
                tp=tp,
                fp=fp,
                fn=fn,
                sensitivity=sens,
                precision=prec,
                f1=f1,
            )

        view[tol_key] = EventEvaluationResult(
            tolerance_ms=tol_ms,
            s1=_calc_m(tp_s1, fp_s1, fn_s1),
            s2=_calc_m(tp_s2, fp_s2, fn_s2),
            combined=_calc_m(tp_comb, fp_comb, fn_comb),
        )

    return view


def aggregate_timing_errors(outcomes: Sequence[RecordEvaluationOutcome]) -> dict[str, TimingErrorMetrics]:
    """Aggregate signed and absolute timing errors across all matched events at 100 ms tolerance."""
    all_s1_errs: list[float] = []
    all_s2_errs: list[float] = []

    for o in outcomes:
        all_s1_errs.extend(o.signed_errors_s1_100ms)
        all_s2_errs.extend(o.signed_errors_s2_100ms)

    comb_errs = all_s1_errs + all_s2_errs

    return {
        "s1": compute_timing_error_metrics(all_s1_errs),
        "s2": compute_timing_error_metrics(all_s2_errs),
        "combined": compute_timing_error_metrics(comb_errs),
    }


def aggregate_state_metrics(outcomes: Sequence[RecordEvaluationOutcome]) -> Optional[StateMetrics]:
    """Aggregate 4x4 confusion matrix and compute per-state and macro frame agreement."""
    total_cm = np.zeros((4, 4), dtype=np.int64)
    total_annotated = 0
    total_ignored = 0
    valid_count = 0

    for o in outcomes:
        if o.confusion_matrix_4x4 is not None:
            total_cm += o.confusion_matrix_4x4
            total_annotated += o.annotated_frames_count
            total_ignored += o.ignored_frames_count
            valid_count += 1

    if total_annotated == 0:
        return None

    state_names = ["S1", "SYSTOLE", "S2", "DIASTOLE"]
    precisions: dict[str, float] = {}
    recalls: dict[str, float] = {}
    f1s: dict[str, float] = {}

    for i, name in enumerate(state_names):
        tp = float(total_cm[i, i])
        fp = float(np.sum(total_cm[:, i]) - tp)
        fn = float(np.sum(total_cm[i, :]) - tp)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2.0 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions[name] = prec
        recalls[name] = rec
        f1s[name] = f1

    macro_f1 = float(np.mean(list(f1s.values())))
    correct_frames = float(np.trace(total_cm))
    agreement = correct_frames / float(total_annotated) if total_annotated > 0 else 0.0

    return StateMetrics(
        confusion_matrix=[[int(val) for val in row] for row in total_cm],
        per_state_precision=precisions,
        per_state_recall=recalls,
        per_state_f1=f1s,
        macro_f1=macro_f1,
        annotated_frame_agreement=agreement,
        total_annotated_frames=total_annotated,
        total_ignored_frames=total_ignored,
    )


def compute_macro_subject_metrics(
    outcomes: Sequence[RecordEvaluationOutcome],
    tolerance_ms: float = 100.0,
) -> dict[str, Any]:
    """Aggregate event metrics at subject level to prevent multi-record subjects from dominating."""
    subject_map: dict[str, list[RecordEvaluationOutcome]] = defaultdict(list)
    for o in outcomes:
        subject_map[o.subject_id].append(o)

    if not subject_map:
        return {"subject_count": 0, "macro_subject_f1_100ms": 0.0}

    subject_f1s: list[float] = []
    subject_s1_f1s: list[float] = []
    subject_s2_f1s: list[float] = []

    for sid, sub_outcomes in subject_map.items():
        # Aggregate TP/FP/FN for this subject
        tp_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].tp for o in sub_outcomes)
        fp_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].fp for o in sub_outcomes)
        fn_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].fn for o in sub_outcomes)

        tp_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].tp for o in sub_outcomes)
        fp_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].fp for o in sub_outcomes)
        fn_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].fn for o in sub_outcomes)

        def _f1(tp: int, fp: int, fn: int) -> float:
            p = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
            r = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
            return 2.0 * p * r / (p + r) if (p + r) > 0 else 0.0

        f1_1 = _f1(tp_s1, fp_s1, fn_s1)
        f1_2 = _f1(tp_s2, fp_s2, fn_s2)
        f1_c = _f1(tp_s1 + tp_s2, fp_s1 + fp_s2, fn_s1 + fn_s2)

        subject_s1_f1s.append(f1_1)
        subject_s2_f1s.append(f1_2)
        subject_f1s.append(f1_c)

    return {
        "subject_count": len(subject_map),
        "macro_subject_s1_f1_100ms": round(float(np.mean(subject_s1_f1s)), 4),
        "macro_subject_s2_f1_100ms": round(float(np.mean(subject_s2_f1s)), 4),
        "macro_subject_combined_f1_100ms": round(float(np.mean(subject_f1s)), 4),
    }


def compute_location_breakdown(
    outcomes: Sequence[RecordEvaluationOutcome],
    tolerance_ms: float = 100.0,
) -> list[LocationMetrics]:
    """Break down performance metrics descriptively by auscultation location."""
    loc_map: dict[str, list[RecordEvaluationOutcome]] = defaultdict(list)
    for o in outcomes:
        loc = o.auscultation_location or "UNKNOWN"
        loc_map[loc].append(o)

    breakdown: list[LocationMetrics] = []
    for loc, loc_outcomes in sorted(loc_map.items()):
        total = len(loc_outcomes)
        success_count = sum(1 for o in loc_outcomes if o.is_success)
        coverage = float(success_count) / float(total) if total > 0 else 0.0
        unique_subjects = len({o.subject_id for o in loc_outcomes})

        # Micro-aggregate TP/FP/FN for location
        tp_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].tp for o in loc_outcomes)
        fp_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].fp for o in loc_outcomes)
        fn_s1 = sum(o.event_results.get(tolerance_ms, (EventToleranceMetrics(100,0,0,0,0,0,0),))[0].fn for o in loc_outcomes)

        tp_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].tp for o in loc_outcomes)
        fp_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].fp for o in loc_outcomes)
        fn_s2 = sum(o.event_results.get(tolerance_ms, (None, EventToleranceMetrics(100,0,0,0,0,0,0)))[1].fn for o in loc_outcomes)

        def _f1(tp: int, fp: int, fn: int) -> float:
            p = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
            r = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
            return 2.0 * p * r / (p + r) if (p + r) > 0 else 0.0

        f1_1 = _f1(tp_s1, fp_s1, fn_s1)
        f1_2 = _f1(tp_s2, fp_s2, fn_s2)
        f1_c = _f1(tp_s1 + tp_s2, fp_s1 + fp_s2, fn_s1 + fn_s2)

        breakdown.append(
            LocationMetrics(
                location=loc,
                record_count=total,
                subject_count=unique_subjects,
                coverage=coverage,
                s1_f1_100ms=f1_1,
                s2_f1_100ms=f1_2,
                combined_f1_100ms=f1_c,
            )
        )

    return breakdown
