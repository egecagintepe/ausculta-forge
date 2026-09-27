"""Test strict state 0 unannotated/ignore mask semantics."""

import pytest
import numpy as np
from pcg_core.segmentation.validation.models import ReferenceStateInterval
from pcg_core.segmentation.validation.annotations import (
    convert_intervals_to_50hz_labels,
    extract_events_from_reference_intervals,
)


def test_state_zero_ignore_mask_and_not_diastole():
    # Sequence:
    # 0.0 - 0.2: State 0 (unannotated)
    # 0.2 - 0.34: State 1 (S1)
    # 0.34 - 0.60: State 2 (Systole)
    # 0.60 - 0.72: State 3 (S2)
    # 0.72 - 1.10: State 4 (Diastole)
    # 1.10 - 1.30: State 0 (unannotated)
    intervals = [
        ReferenceStateInterval(state=0, start_s=0.0, end_s=0.2),
        ReferenceStateInterval(state=1, start_s=0.2, end_s=0.34),
        ReferenceStateInterval(state=2, start_s=0.34, end_s=0.60),
        ReferenceStateInterval(state=3, start_s=0.60, end_s=0.72),
        ReferenceStateInterval(state=4, start_s=0.72, end_s=1.10),
        ReferenceStateInterval(state=0, start_s=1.10, end_s=1.30),
    ]

    duration_s = 1.30
    labels_50hz, eval_mask_50hz = convert_intervals_to_50hz_labels(
        intervals,
        duration_s=duration_s,
        feature_fs_hz=50.0,
    )

    total_frames = int(round(duration_s * 50.0))  # 65 frames
    assert len(labels_50hz) == total_frames
    assert len(eval_mask_50hz) == total_frames

    # Check frame times: t = (i + 0.5) / 50.0
    # For i in [0..9] (0 to 0.2s): center times are 0.01, 0.03, ... 0.19. All in State 0!
    for i in range(10):
        assert labels_50hz[i] == 0
        assert eval_mask_50hz[i] is False or eval_mask_50hz[i] == False
        # CRITICAL: Must NEVER be converted to Diastole (state 4)
        assert labels_50hz[i] != 4

    # Frames for 1.10 - 1.30s: i in [55..64]
    for i in range(55, 65):
        assert labels_50hz[i] == 0
        assert eval_mask_50hz[i] is False or eval_mask_50hz[i] == False
        assert labels_50hz[i] != 4

    # Middle frames must be active in eval_mask
    annotated_indices = [i for i, m in enumerate(eval_mask_50hz) if m]
    assert len(annotated_indices) > 0
    for idx in annotated_indices:
        assert labels_50hz[idx] in {1, 2, 3, 4}


def test_state_zero_does_not_generate_reference_events():
    intervals = [
        ReferenceStateInterval(state=0, start_s=0.0, end_s=0.5),
        ReferenceStateInterval(state=1, start_s=0.5, end_s=0.65),
        ReferenceStateInterval(state=0, start_s=0.65, end_s=1.0),
    ]

    events = extract_events_from_reference_intervals(intervals, event_anchor="ONSET")
    s1_events = events["S1"]
    s2_events = events["S2"]
    # Only 1 S1 event, 0 S2 events, no event from state 0
    assert len(s1_events) == 1
    assert s1_events[0] == 0.5
    assert len(s2_events) == 0
