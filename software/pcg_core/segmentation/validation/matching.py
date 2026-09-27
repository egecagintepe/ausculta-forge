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

    Optimizes with priority:
    1. Maximize number of valid matches within tolerance (TP).
    2. Among solutions with equal TP count, minimize total absolute timing error.

    Uses a dynamic-programming sequence alignment matcher on sorted event sequences,
    guaranteeing the optimal 1-to-1 matching without greedy suboptimal blocking.

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

    # Sort preserving original indices
    p_sorted = sorted(enumerate(predicted_times_s), key=lambda x: (x[1], x[0]))
    r_sorted = sorted(enumerate(reference_times_s), key=lambda x: (x[1], x[0]))

    # DP table: dp[i][j] = (max_matches: int, min_total_error: float)
    dp: list[list[tuple[int, float]]] = [
        [(0, 0.0) for _ in range(n_refs + 1)] for _ in range(n_preds + 1)
    ]
    parent: list[list[tuple[int, int, bool]]] = [
        [(0, 0, False) for _ in range(n_refs + 1)] for _ in range(n_preds + 1)
    ]

    def _is_better(cand: tuple[int, float, int, int, bool], current: tuple[int, float, int, int, bool]) -> bool:
        if cand[0] > current[0]:
            return True
        if cand[0] < current[0]:
            return False
        # Equal match count: minimize total error
        if cand[1] < current[1] - 1e-12:
            return True
        if cand[1] > current[1] + 1e-12:
            return False
        # Equal count and error: prefer matching
        if cand[4] and not current[4]:
            return True
        return False

    for i in range(n_preds + 1):
        for j in range(n_refs + 1):
            if i == 0 and j == 0:
                continue

            best: tuple[int, float, int, int, bool] | None = None

            # Option 1: Skip prediction i (if i > 0)
            if i > 0:
                cand = (dp[i - 1][j][0], dp[i - 1][j][1], i - 1, j, False)
                if best is None or _is_better(cand, best):
                    best = cand

            # Option 2: Skip reference j (if j > 0)
            if j > 0:
                cand = (dp[i][j - 1][0], dp[i][j - 1][1], i, j - 1, False)
                if best is None or _is_better(cand, best):
                    best = cand

            # Option 3: Match prediction i - 1 with reference j - 1 (if i > 0 and j > 0)
            if i > 0 and j > 0:
                p_idx, p_time = p_sorted[i - 1]
                r_idx, r_time = r_sorted[j - 1]
                dt = abs(p_time - r_time)
                if dt <= tolerance_s + 1e-12:
                    cand = (dp[i - 1][j - 1][0] + 1, dp[i - 1][j - 1][1] + dt, i - 1, j - 1, True)
                    if best is None or _is_better(cand, best):
                        best = cand

            if best is not None:
                dp[i][j] = (best[0], best[1])
                parent[i][j] = (best[2], best[3], best[4])

    # Reconstruct optimal matches via backtracking
    raw_matches: list[tuple[int, int, float]] = []
    curr_i, curr_j = n_preds, n_refs
    while curr_i > 0 or curr_j > 0:
        prev_i, prev_j, is_match = parent[curr_i][curr_j]
        if is_match:
            orig_p_idx = p_sorted[prev_i][0]
            orig_r_idx = r_sorted[prev_j][0]
            signed_err = float(predicted_times_s[orig_p_idx] - reference_times_s[orig_r_idx])
            raw_matches.append((orig_p_idx, orig_r_idx, signed_err))
        curr_i, curr_j = prev_i, prev_j

    raw_matches.reverse()
    matches = sorted(raw_matches, key=lambda m: m[0])

    matched_p = {m[0] for m in matches}
    matched_r = {m[1] for m in matches}

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
