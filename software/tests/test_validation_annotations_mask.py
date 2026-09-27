"""Test strict state 0 unannotated/ignore mask semantics."""

import pytest
import numpy as np
from pcg_core.segmentation.validation.models import ReferenceStateInterval
from pcg_core.segmentation.validation.annotations import (
    convert_intervals_to_50hz_labels,
    extract_events_from_reference_intervals,
    extract_events_from_predictions,
)
from pcg_core.segmentation.validation.matching import compute_event_metrics_at_tolerance
from pcg_core.segmentation.springer import (
    segment_pcg_springer,
    build_demo_springer_model,
)
from pcg_core.segmentation.models import SegmentationStatus



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
        feature_sample_rate_hz=50.0,
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


def test_convert_intervals_non_default_feature_rate():
    # Sequence:
    # 0.0 - 0.2: State 1 (S1)
    # 0.2 - 0.5: State 2 (Systole)
    intervals = [
        ReferenceStateInterval(state=1, start_s=0.0, end_s=0.2),
        ReferenceStateInterval(state=2, start_s=0.2, end_s=0.5),
    ]
    duration_s = 0.5
    # Use 100 Hz feature rate instead of default 50 Hz
    labels, eval_mask = convert_intervals_to_50hz_labels(
        intervals,
        duration_s=duration_s,
        feature_sample_rate_hz=100.0,
    )
    # At 100 Hz, 0.5s gives 50 frames
    assert len(labels) == 50
    assert len(eval_mask) == 50
    # Frame centers: t = (i + 0.5) / 100.0
    # For i=0..19: t is in [0.005 .. 0.195] -> State 1
    for i in range(20):
        assert labels[i] == 1
        assert bool(eval_mask[i]) is True
    # For i=20..49: t is in [0.205 .. 0.495] -> State 2
    for i in range(20, 50):
        assert labels[i] == 2
        assert bool(eval_mask[i]) is True


def test_extract_events_from_serialized_dict_intervals():
    dict_intervals = [
        {"state": 1, "start_s": 0.10, "duration_s": 0.12},
        {"state": 2, "start_s": 0.22, "duration_s": 0.25},
        {"state": 3, "start_s": 0.47, "duration_s": 0.10},
        {"state": 4, "start_s": 0.57, "duration_s": 0.35},
        {"state": 1, "start_s": 0.92, "duration_s": 0.12},
    ]

    events = extract_events_from_predictions(dict_intervals, event_anchor="ONSET")
    assert len(events["S1"]) == 2
    assert events["S1"] == [0.10, 0.92]
    assert len(events["S2"]) == 1
    assert events["S2"] == [0.47]

    # Test error on missing required field
    with pytest.raises(ValueError, match="missing required 'state' field"):
        extract_events_from_predictions([{"start_s": 0.10, "duration_s": 0.10}])

    with pytest.raises(ValueError, match="missing required 'start_s' field"):
        extract_events_from_predictions([{"state": 1, "duration_s": 0.10}])

    # Test error on invalid cardiac state
    with pytest.raises(ValueError, match="invalid cardiac state"):
        extract_events_from_predictions([{"state": 5, "start_s": 0.10, "duration_s": 0.10}])


def test_real_springer_segmentation_result_event_extraction():
    # Generate 4-second synthetic PCG with clear heart beats at 60 BPM
    fs = 1000.0
    duration_s = 4.0
    t = np.linspace(0, duration_s, int(duration_s * fs), endpoint=False)
    x = 0.05 * np.sin(2 * np.pi * 30 * t)
    # Add bursts at periodic intervals: S1 at 0.0, 1.0, 2.0, 3.0; S2 at 0.35, 1.35, 2.35, 3.35
    for start in [0.0, 1.0, 2.0, 3.0]:
        idx1 = (t >= start) & (t < start + 0.12)
        x[idx1] += 0.5 * np.sin(2 * np.pi * 80 * t[idx1])
        idx2 = (t >= start + 0.35) & (t < start + 0.45)
        x[idx2] += 0.4 * np.sin(2 * np.pi * 70 * t[idx2])

    demo_model = build_demo_springer_model()
    # Real segmentation inference using segment_pcg_springer
    res = segment_pcg_springer(
        signal=x,
        sample_rate_hz=fs,
        model=demo_model,
    )

    # Must produce SUCCESS
    assert res.status == SegmentationStatus.SUCCESS
    assert len(res.state_intervals) > 0

    # res.state_intervals is a list of dicts in SpringerSegmentationResult
    events_from_dicts = extract_events_from_predictions(res.state_intervals, event_anchor="ONSET")
    assert len(events_from_dicts["S1"]) > 0
    assert len(events_from_dicts["S2"]) > 0

    # Also test with StateInterval objects
    from pcg_core.segmentation.models import StateInterval
    interval_objs = [
        StateInterval(
            state=int(iv["state"]),
            state_name=str(iv.get("state_name", f"S{iv['state']}")),
            start_s=float(iv["start_s"]),
            end_s=float(iv.get("end_s", iv["start_s"] + iv.get("duration_s", 0.0))),
            duration_s=float(iv.get("duration_s", 0.0)),
            start_frame_50hz=int(iv.get("start_frame_50hz", 0)),
            end_frame_50hz=int(iv.get("end_frame_50hz", 0)),
        )
        for iv in res.state_intervals
    ]
    events_from_objs = extract_events_from_predictions(interval_objs, event_anchor="ONSET")
    assert events_from_objs["S1"] == events_from_dicts["S1"]
    assert events_from_objs["S2"] == events_from_dicts["S2"]

    # Verify event metrics compute predictions rather than failing or treating as empty
    ref_s1 = [0.0, 1.0, 2.0, 3.0]
    metrics_s1, errs = compute_event_metrics_at_tolerance(
        predicted_times_s=events_from_dicts["S1"],
        reference_times_s=ref_s1,
        tolerance_ms=100.0,
    )
    # Must have predicted events (not empty)
    assert len(events_from_dicts["S1"]) > 0
    assert (metrics_s1.tp + metrics_s1.fp) > 0
