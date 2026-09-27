"""AuscultaForge — One-to-One Cardiac Event Matching and Timing Error Analysis.

Guarantees:
- Strict one-to-one matching: No duplicate prediction can match a single reference.
- No reference event can match multiple predictions.
- Deterministic nearest-time greedy assignment under tolerance window.
- Evaluates at explicit tolerances: 20 ms, 40 ms, 60 ms, 80 ms, 100 ms.
- Computes signed and absolute timing errors exclusively on matched true positives.
"""

from __future__ import annotations

from typing import Sequence
import numpy as np

from .models import EventToleranceMetrics, TimingErrorMetrics


def match_events_one_to_one(
    predicted_times_s: Sequence[float],
    reference_times_s: Sequence[float],
    tolerance_s: float,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Perform deterministic one-to-one event matching within a tolerance window.
    
    Parameters
    ----------
    predicted_times_s : Sequence[float]
        Predicted event timestamps in seconds.
    reference_times_s : Sequence[float]
        Reference event timestamps in seconds.
    tolerance_s : float
        Maximum allowable absolute time difference in seconds.
        
    Returns
    -------
    tuple[list[tuple[int, int, float]], list[int], list[int]]
        matches: list of (pred_idx, ref_idx, signed_error_s)
        unmatched_preds: list of pred_idx that did not match any reference
        unmatched_refs: list of ref_idx that were not detected
    """
    n_preds = len(predicted_times_s)
    n_refs = len(reference_times_s)

    if n_preds == 0 or n_refs == 0:
        return [], list(range(n_preds)), list(range(n_refs))

    # Build all candidate pairs within tolerance
    candidates: list[tuple[float, int, int]] = []
    for p_idx, p_t in enumerate(predicted_times_s):
        for r_idx, r_t in enumerate(reference_times_s):
            dt = abs(p_t - r_t)
            if dt <= tolerance_s:
                candidates.append((dt, p_idx, r_idx))

    # Sort ascending by distance, breaking ties deterministically by indices
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))

    matched_p: set[int] = set()
    matched_r: set[int] = set()
    matches: list[tuple[int, int, float]] = []

    for dt, p_idx, r_idx in candidates:
        if p_idx not in matched_p and r_idx not in matched_r:
            matched_p.add(p_idx)
            matched_r.add(r_idx)
            signed_err = predicted_times_s[p_idx] - reference_times_s[r_idx]
            matches.append((p_idx, r_idx, signed_err))

    unmatched_preds = [p_idx for p_idx in range(n_preds) if p_idx not in matched_p]
    unmatched_refs = [r_idx for r_idx in range(n_refs) if r_idx not in matched_r]

    return matches, unmatched_preds, unmatched_refs


def compute_event_metrics_at_tolerance(
    predicted_times_s: Sequence[float],
    reference_times_s: Sequence[float],
    tolerance_ms: float,
) -> tuple[EventToleranceMetrics, list[float]]:
    """Compute event TP/FP/FN/precision/recall/F1 and collect signed errors at given tolerance.
    
    Returns
    -------
    tuple[EventToleranceMetrics, list[float]]
        (metrics, signed_errors_ms)
    """
    tol_s = tolerance_ms / 1000.0
    matches, _, _ = match_events_one_to_one(predicted_times_s, reference_times_s, tolerance_s=tol_s)

    tp = len(matches)
    fp = max(0, len(predicted_times_s) - tp)
    fn = max(0, len(reference_times_s) - tp)

    sens = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
    prec = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2.0 * prec * sens / (prec + sens) if (prec + sens) > 0 else 0.0

    signed_errors_ms = [signed_s * 1000.0 for _, _, signed_s in matches]

    metrics = EventToleranceMetrics(
        tolerance_ms=tolerance_ms,
        tp=tp,
        fp=fp,
        fn=fn,
        sensitivity=sens,
        precision=prec,
        f1=f1,
    )
    return metrics, signed_errors_ms


def compute_timing_error_metrics(signed_errors_ms: Sequence[float]) -> TimingErrorMetrics:
    """Compute signed and absolute timing statistics from a list of matched errors in ms."""
    if not signed_errors_ms:
        return TimingErrorMetrics(
            mean_signed_ms=0.0,
            median_signed_ms=0.0,
            mean_abs_ms=0.0,
            median_abs_ms=0.0,
            p25_abs_ms=0.0,
            p75_abs_ms=0.0,
            p95_abs_ms=0.0,
            count=0,
        )

    arr_signed = np.asarray(signed_errors_ms, dtype=np.float64)
    arr_abs = np.abs(arr_signed)

    return TimingErrorMetrics(
        mean_signed_ms=float(np.mean(arr_signed)),
        median_signed_ms=float(np.median(arr_signed)),
        mean_abs_ms=float(np.mean(arr_abs)),
        median_abs_ms=float(np.median(arr_abs)),
        p25_abs_ms=float(np.percentile(arr_abs, 25)),
        p75_abs_ms=float(np.percentile(arr_abs, 75)),
        p95_abs_ms=float(np.percentile(arr_abs, 95)),
        count=len(arr_signed),
    )
