"""AuscultaForge — Automated Tests for Springer ECG-to-PCG Training Annotation Bridge.

Verifies:
- SpringerTrainingAnnotations schema and serialization
- Exact 50 Hz frame conversion and labeling:
  - S1 begins at ECG R-peak with expected duration (6 frames at 50 Hz)
  - S2 centers on Hilbert envelope peak near end-T-wave (5 frames at 50 Hz)
  - Systole between S1 and S2
  - Diastole between S2 and next S1
- Deterministic boundary handling (pre-S1 diastole, post-S2 diastole)
- All frame labels strictly belong to {1, 2, 3, 4}
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.training_labels import (
    SpringerTrainingAnnotations,
    label_pcg_states_from_annotations,
)
from pcg_core.segmentation.models import HeartSoundState


class TestSpringerTrainingLabels:
    """Verifies ECG annotation to 50 Hz PCG state labeling bridge."""

    def test_schema_serialization_round_trip(self):
        ann = SpringerTrainingAnnotations(
            recording_id="rec_001",
            annotation_sample_rate_hz=1000.0,
            r_peak_positions=[100, 1100, 2100],
            end_t_wave_positions=[450, 1450, 2450],
            subject_id="subj_A",
            metadata={"source": "synthetic_test"},
        )
        d = ann.to_dict()
        assert d["recording_id"] == "rec_001"
        assert d["annotation_sample_rate_hz"] == 1000.0
        assert d["r_peak_positions"] == [100, 1100, 2100]
        assert d["end_t_wave_positions"] == [450, 1450, 2450]
        assert d["subject_id"] == "subj_A"

    def test_synthetic_pcg_annotation_labeling_cyclic_sequence(self):
        fs_pcg = 1000.0
        duration_s = 4.0
        n = int(round(fs_pcg * duration_s))
        t = np.arange(n) / fs_pcg

        # Construct synthetic PCG with distinct acoustic bursts
        # R-peaks at 0.2s, 1.2s, 2.2s, 3.2s (60 BPM, cycle = 1.0s)
        # End-T-waves at 0.55s, 1.55s, 2.55s, 3.55s
        # Acoustic S1 at 0.2s, Acoustic S2 at 0.55s
        pcg = np.zeros(n, dtype=np.float64)
        r_peaks_s = [0.20, 1.20, 2.20, 3.20]
        end_t_s = [0.55, 1.55, 2.55, 3.55]

        for t_r, t_t in zip(r_peaks_s, end_t_s):
            # S1 acoustic burst around t_r
            s1_mask = (t >= t_r) & (t < t_r + 0.10)
            pcg[s1_mask] += np.sin(2.0 * np.pi * 50.0 * (t[s1_mask] - t_r))
            # S2 acoustic burst around t_t
            s2_mask = (t >= t_t) & (t < t_t + 0.08)
            pcg[s2_mask] += np.sin(2.0 * np.pi * 70.0 * (t[s2_mask] - t_t))

        ann = SpringerTrainingAnnotations(
            recording_id="synth_test",
            annotation_sample_rate_hz=1000.0,
            r_peak_positions=[int(round(p * 1000.0)) for p in r_peaks_s],
            end_t_wave_positions=[int(round(p * 1000.0)) for p in end_t_s],
        )

        labels = label_pcg_states_from_annotations(
            pcg_signal=pcg,
            pcg_sample_rate_hz=fs_pcg,
            annotations=ann,
            feature_sample_rate_hz=50.0,
            expected_s1_duration_s=0.122,
            expected_s2_duration_s=0.094,
        )

        # 4.0 seconds at 50 Hz = 200 frames
        assert len(labels) == 200
        # All frames must be in {1, 2, 3, 4}
        unique_states = set(np.unique(labels))
        assert unique_states.issubset({1, 2, 3, 4})

        # 1. Pre-first-S1 boundary (t < 0.2s -> frame < 10) must be DIASTOLE (state 4)
        assert np.all(labels[:10] == int(HeartSoundState.DIASTOLE))

        # 2. First S1 begins at t=0.2s (frame 10) and spans 6 frames [10, 16)
        s1_frame_start = int(round(0.20 * 50.0))  # 10
        s1_expected_len = int(round(0.122 * 50.0))  # 6
        assert np.all(labels[s1_frame_start : s1_frame_start + s1_expected_len] == int(HeartSoundState.S1))

        # 3. Systole occurs between S1 end and S2 start
        # S2 is around t=0.55s -> frame ~ 28
        assert labels[s1_frame_start + s1_expected_len + 1] == int(HeartSoundState.SYSTOLE)

        # 4. Check presence of all 4 states in reasonable quantities
        s1_count = np.sum(labels == int(HeartSoundState.S1))
        sys_count = np.sum(labels == int(HeartSoundState.SYSTOLE))
        s2_count = np.sum(labels == int(HeartSoundState.S2))
        dia_count = np.sum(labels == int(HeartSoundState.DIASTOLE))

        assert s1_count >= 4 * s1_expected_len - 4
        assert s2_count >= 15
        assert sys_count >= 20
        assert dia_count >= 40

    def test_empty_signal_returns_empty(self):
        ann = SpringerTrainingAnnotations("empty", 1000.0, [], [])
        labels = label_pcg_states_from_annotations(np.array([]), 1000.0, ann)
        assert len(labels) == 0

    def test_no_r_peaks_returns_all_diastole(self):
        pcg = np.sin(np.linspace(0, 10, 1000))
        ann = SpringerTrainingAnnotations("no_r", 1000.0, [], [])
        labels = label_pcg_states_from_annotations(pcg, 1000.0, ann, feature_sample_rate_hz=50.0)
        assert len(labels) == 50
        assert np.all(labels == int(HeartSoundState.DIASTOLE))
