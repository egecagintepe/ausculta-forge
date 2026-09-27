"""AuscultaForge — Interval Annotation to 50 Hz Feature Timebase Converter.

Converts reference state intervals into:
- 50 Hz reference state labels: reference_state_50hz
- 50 Hz boolean evaluation mask: evaluation_mask_50hz

Strict Invariants:
- State 0 (UNANNOTATED / IGNORE) is NEVER converted to Diastole.
- Any unannotated gaps receive state 0 and evaluation_mask = False.
- Event extraction supports both exact ONSET and SPRINGER_CONTEXT (S2 center).
"""

from __future__ import annotations

import bisect
from typing import Any, Sequence
import numpy as np

from .models import ReferenceStateInterval


def convert_intervals_to_50hz_labels(
    intervals: Sequence[ReferenceStateInterval],
    total_frames_50hz: Optional[int] = None,
    duration_s: Optional[float] = None,
    feature_sample_rate_hz: float = 50.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert reference interval sequence into frame labels and evaluation mask on the feature timebase."""
    fs = float(feature_sample_rate_hz)
    if fs <= 0.0:
        raise ValueError(f"feature_sample_rate_hz must be positive, got {feature_sample_rate_hz}")

    if total_frames_50hz is None:
        if duration_s is not None:
            total_frames_50hz = int(round(duration_s * fs))
        else:
            raise ValueError("Must provide either total_frames_50hz or duration_s.")

    if total_frames_50hz <= 0:
        return np.array([], dtype=np.int32), np.array([], dtype=bool)

    reference_state_50hz = np.zeros(total_frames_50hz, dtype=np.int32)
    evaluation_mask_50hz = np.zeros(total_frames_50hz, dtype=bool)

    if not intervals:
        return reference_state_50hz, evaluation_mask_50hz

    # Prepare search arrays for fast lookup
    starts = [iv.start_s for iv in intervals]
    ends = [iv.end_s for iv in intervals]
    states = [iv.state for iv in intervals]

    # For each frame, check the state at the exact frame-center time
    for i in range(total_frames_50hz):
        t_center = (float(i) + 0.5) / fs

        # Find the interval candidate using bisect on start times
        idx = bisect.bisect_right(starts, t_center) - 1
        if 0 <= idx < len(intervals):
            if starts[idx] <= t_center < ends[idx]:
                st = states[idx]
                if st in (1, 2, 3, 4):
                    reference_state_50hz[i] = st
                    evaluation_mask_50hz[i] = True
                else:
                    # State 0 (UNANNOTATED) -> Explicitly ignored
                    reference_state_50hz[i] = 0
                    evaluation_mask_50hz[i] = False
                continue

        # If not contained in any valid interval: unannotated
        reference_state_50hz[i] = 0
        evaluation_mask_50hz[i] = False

    return reference_state_50hz, evaluation_mask_50hz


def extract_events_from_reference_intervals(
    intervals: Sequence[ReferenceStateInterval],
    event_anchor: str = "ONSET",
) -> dict[str, list[float]]:
    """Extract reference S1 and S2 event timestamps in seconds from interval annotations.

    Anchors:
    - 'ONSET' (Primary Stage-C standard):
      S1 event = S1 interval start_s
      S2 event = S2 interval start_s
    - 'SPRINGER_CONTEXT' (Historical contextual comparison):
      S1 event = S1 interval start_s
      S2 event = S2 interval center (start_s + 0.5 * duration_s)

    State 0 intervals NEVER produce events.
    """
    s1_events: list[float] = []
    s2_events: list[float] = []

    is_springer_context = event_anchor.upper() == "SPRINGER_CONTEXT"

    for iv in intervals:
        if iv.state == 1:  # S1
            s1_events.append(float(iv.start_s))
        elif iv.state == 3:  # S2
            if is_springer_context:
                s2_events.append(float(iv.start_s + 0.5 * iv.duration_s))
            else:
                s2_events.append(float(iv.start_s))

    return {
        "S1": s1_events,
        "S2": s2_events,
    }


def extract_events_from_predictions(
    state_intervals: Sequence[Any],
    event_anchor: str = "ONSET",
) -> dict[str, list[float]]:
    """Extract predicted S1 and S2 event timestamps in seconds from StateInterval items or dicts.

    Supports both:
    - StateInterval-like objects (with .state, .start_s, .duration_s / .end_s)
    - Serialized dictionaries (with 'state', 'start_s', 'duration_s' / 'end_s')

    Validates required fields and raises ValueError on malformed interval entries.
    """
    s1_events: list[float] = []
    s2_events: list[float] = []

    is_springer_context = event_anchor.upper() == "SPRINGER_CONTEXT"

    for idx, iv in enumerate(state_intervals):
        if isinstance(iv, dict):
            if "state" not in iv:
                raise ValueError(f"Interval dictionary at index {idx} missing required 'state' field: {iv}")
            if "start_s" not in iv:
                raise ValueError(f"Interval dictionary at index {idx} missing required 'start_s' field: {iv}")
            try:
                state = int(iv["state"])
                start_s = float(iv["start_s"])
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid numeric values in interval dict at index {idx}: {iv} ({e})")

            if "duration_s" in iv and iv["duration_s"] is not None:
                duration_s = float(iv["duration_s"])
            elif "end_s" in iv and iv["end_s"] is not None:
                duration_s = max(0.0, float(iv["end_s"]) - start_s)
            else:
                duration_s = 0.0
        elif hasattr(iv, "state") and hasattr(iv, "start_s"):
            try:
                state = int(iv.state)
                start_s = float(iv.start_s)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid numeric values in interval object at index {idx}: {iv} ({e})")

            if hasattr(iv, "duration_s") and iv.duration_s is not None:
                duration_s = float(iv.duration_s)
            elif hasattr(iv, "end_s") and iv.end_s is not None:
                duration_s = max(0.0, float(iv.end_s) - start_s)
            else:
                duration_s = 0.0
        else:
            raise ValueError(f"Interval at index {idx} is neither a dict nor a valid interval object: {type(iv)!r}")

        if state not in (1, 2, 3, 4):
            raise ValueError(f"Interval at index {idx} has invalid cardiac state {state}. Must be in {{1, 2, 3, 4}}.")

        if state == 1:  # S1
            s1_events.append(float(start_s))
        elif state == 3:  # S2
            if is_springer_context:
                s2_events.append(float(start_s + 0.5 * duration_s))
            else:
                s2_events.append(float(start_s))

    return {
        "S1": s1_events,
        "S2": s2_events,
    }
