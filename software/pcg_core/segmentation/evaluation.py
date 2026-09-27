"""AuscultaForge — Segmentation Evaluation Foundation.

Provides tolerance-based temporal onset matching and standard event evaluation metrics:
- True Positives (TP)
- False Positives (FP)
- False Negatives (FN)
- Sensitivity (Recall)
- Positive Predictivity (Precision)
- F1 Score

Supports configurable tolerance bands (20, 40, 50, 60, 80, 100 ms).
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import numpy as np

from .models import StateInterval, SegmentationEvaluationMetrics, HeartSoundState


def evaluate_segmentation_onsets(
    predicted_intervals: List[StateInterval],
    reference_onset_times_s: List[float],
    target_state: int = 1,
    tolerance_ms: float = 50.0,
) -> SegmentationEvaluationMetrics:
    """Evaluate temporal onset precision/recall against reference annotations.
    
    Parameters
    ----------
    predicted_intervals : List[StateInterval]
        Model predicted segmentation intervals.
    reference_onset_times_s : List[float]
        Ground-truth reference event onset timestamps in seconds.
    target_state : int
        Cardiac state integer to evaluate (1 for S1, 3 for S2).
    tolerance_ms : float
        Matching window in milliseconds (default: 50.0 ms).
        
    Returns
    -------
    SegmentationEvaluationMetrics
        Detailed TP, FP, FN, precision, recall, and F1 metrics.
    """
    tol_s = float(tolerance_ms) / 1000.0

    # Filter predicted intervals for target state
    pred_onsets = [
        iv.start_s for iv in predicted_intervals
        if iv.state == target_state
    ]

    ref_onsets = sorted(reference_onset_times_s)
    pred_onsets = sorted(pred_onsets)

    n_ref = len(ref_onsets)
    n_pred = len(pred_onsets)

    if n_ref == 0:
        return SegmentationEvaluationMetrics(
            tolerance_ms=tolerance_ms,
            true_positives=0,
            false_positives=n_pred,
            false_negatives=0,
            sensitivity=0.0,
            positive_predictivity=0.0,
            f1_score=0.0,
            total_reference_events=0,
            total_predicted_events=n_pred,
            provenance={"target_state": target_state, "state_name": HeartSoundState(target_state).name},
        )

    matched_ref = set()
    matched_pred = set()

    # Greedy closest-timestamp matching within tolerance
    for p_idx, p_time in enumerate(pred_onsets):
        best_r_idx = None
        best_diff = tol_s + 1e-9

        for r_idx, r_time in enumerate(ref_onsets):
            if r_idx in matched_ref:
                continue
            diff = abs(p_time - r_time)
            if diff <= tol_s and diff < best_diff:
                best_diff = diff
                best_r_idx = r_idx

        if best_r_idx is not None:
            matched_ref.add(best_r_idx)
            matched_pred.add(p_idx)

    tp = len(matched_ref)
    fp = n_pred - tp
    fn = n_ref - tp

    sensitivity = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
    precision = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
    if sensitivity + precision > 0:
        f1 = 2.0 * (sensitivity * precision) / (sensitivity + precision)
    else:
        f1 = 0.0

    return SegmentationEvaluationMetrics(
        tolerance_ms=tolerance_ms,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        sensitivity=round(sensitivity, 4),
        positive_predictivity=round(precision, 4),
        f1_score=round(f1, 4),
        total_reference_events=n_ref,
        total_predicted_events=n_pred,
        provenance={
            "target_state": target_state,
            "state_name": HeartSoundState(target_state).name,
            "tolerance_ms": tolerance_ms,
        },
    )
