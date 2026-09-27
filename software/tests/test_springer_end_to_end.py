"""AuscultaForge — Automated Tests for End-to-End Springer Segmentation.

Verifies:
- Truthful MODEL_REQUIRED guard when no model is provided
- Rejection of recordings shorter than 2.0 seconds
- Demo model generation (build_demo_springer_model)
- Complete pipeline inference on synthetic PCG audio:
  resampling (4000 Hz -> 1000 Hz) -> preprocessing -> cardiac timing -> durations ->
  features (1000 Hz -> 50 Hz) -> logistic regression posteriors -> Bayes log-emissions ->
  extended Viterbi decoding -> state interval partitioning
- Serialization of SpringerSegmentationResult to valid JSON
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.springer import (
    segment_pcg_springer,
    build_demo_springer_model,
)
from pcg_core.segmentation.models import SegmentationStatus, HeartSoundState
from pcg_core.segmentation.springer_config import SPRINGER_PHYSIONET_REFERENCE_V1, SPRINGER_PAPER_4FEATURE_V1


def _generate_synthetic_pcg_wav(
    fs: float = 4000.0,
    duration_s: float = 5.0,
    bpm: float = 60.0,
) -> np.ndarray:
    """Generate synthetic 4000 Hz PCG signal with acoustic S1 and S2 bursts."""
    cycle_s = 60.0 / bpm
    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    x = np.zeros(n, dtype=np.float64)

    # Insert S1 (50 Hz burst) and S2 (70 Hz burst)
    t_start = 0.1
    while t_start + 0.4 < duration_s:
        # S1: 50 Hz burst lasting ~100 ms
        t_s1 = t_start
        s1_mask = (t >= t_s1) & (t < t_s1 + 0.10)
        t_rel_s1 = t[s1_mask] - t_s1
        x[s1_mask] += 0.8 * np.sin(2.0 * np.pi * 50.0 * t_rel_s1) * np.hanning(len(t_rel_s1))

        # S2: 70 Hz burst lasting ~80 ms at t_start + 0.35 * cycle_s
        t_s2 = t_start + 0.35 * cycle_s
        s2_mask = (t >= t_s2) & (t < t_s2 + 0.08)
        t_rel_s2 = t[s2_mask] - t_s2
        x[s2_mask] += 0.6 * np.sin(2.0 * np.pi * 70.0 * t_rel_s2) * np.hanning(len(t_rel_s2))

        t_start += cycle_s

    # Add small background noise
    rng = np.random.default_rng(42)
    x += rng.normal(0.0, 0.02, size=n)
    return np.clip(x, -1.0, 1.0)


class TestSpringerEndToEnd:
    """Verifies complete Springer LR-HSMM segmentation pipeline end-to-end."""

    def test_truthful_no_model_guard(self):
        """When model is None, must return MODEL_REQUIRED without fabricating any state sequence."""
        x = np.sin(2.0 * np.pi * 50.0 * np.arange(4000) / 1000.0)
        res = segment_pcg_springer(x, sample_rate_hz=1000.0, model=None)

        assert res.status == SegmentationStatus.MODEL_REQUIRED
        assert len(res.state_sequence_50hz) == 0
        assert len(res.state_intervals) == 0
        assert len(res.technical_warnings) > 0

    def test_rejects_signal_shorter_than_2_seconds(self):
        """Signals shorter than 2.0 seconds cannot reliably estimate cardiac timing."""
        demo_model = build_demo_springer_model()
        x_short = np.ones(1500)  # 1.5 seconds at 1000 Hz

        res = segment_pcg_springer(x_short, sample_rate_hz=1000.0, model=demo_model)

        assert res.status == SegmentationStatus.SIGNAL_TOO_SHORT
        assert len(res.state_sequence_50hz) == 0

    def test_end_to_end_synthetic_pcg_segmentation_success(self):
        """Full execution on 4000 Hz PCG signal using demo model."""
        fs = 4000.0
        duration_s = 5.0
        x_pcg = _generate_synthetic_pcg_wav(fs=fs, duration_s=duration_s, bpm=60.0)

        demo_model = build_demo_springer_model()
        res = segment_pcg_springer(
            signal=x_pcg,
            sample_rate_hz=fs,
            model=demo_model,
            config=SPRINGER_PHYSIONET_REFERENCE_V1,
        )

        # 1. Status must be SUCCESS
        assert res.status == SegmentationStatus.SUCCESS
        assert res.model_id == demo_model.model_id

        # 2. Heart rate estimate must be approximately 60 BPM (within 10%)
        assert res.heart_rate_estimate_bpm is not None
        assert pytest.approx(res.heart_rate_estimate_bpm, rel=0.10) == 60.0
        assert res.cycle_duration_estimate_s is not None
        assert res.systolic_interval_estimate_s is not None

        # 3. Decoded frame count at 50 Hz must match duration
        expected_frames = int(round(duration_s * 50.0))
        assert res.total_frames_50hz == expected_frames
        assert len(res.state_sequence_50hz) == expected_frames

        # 4. Decoded states must strictly belong to {1, 2, 3, 4}
        unique_states = set(res.state_sequence_50hz)
        assert unique_states.issubset({1, 2, 3, 4})

        # 5. State intervals must be populated and partitioned
        assert len(res.state_intervals) > 0
        assert len(res.s1_intervals) >= 3
        assert len(res.s2_intervals) >= 3
        assert len(res.systole_intervals) >= 3
        assert len(res.diastole_intervals) >= 3
        assert res.cycle_count >= 3

        # 6. JSON serialization round-trip
        data = res.to_dict()
        assert data["schema_version"] == "1.0.0"
        assert data["status"] == "SUCCESS"
        assert len(data["state_sequence_50hz"]) == expected_frames
        assert len(data["s1_intervals"]) > 0

    def test_end_to_end_paper_profile_with_wavelet(self):
        """Full execution under SPRINGER_PAPER_4FEATURE_V1 with wavelet enabled."""
        fs = 4000.0
        x_pcg = _generate_synthetic_pcg_wav(fs=fs, duration_s=4.0, bpm=75.0)

        demo_4feat_model = build_demo_springer_model(include_wavelet=True)
        res = segment_pcg_springer(
            signal=x_pcg,
            sample_rate_hz=fs,
            model=demo_4feat_model,
            config=SPRINGER_PAPER_4FEATURE_V1,
        )

        assert res.status == SegmentationStatus.SUCCESS
        assert res.profile_id == "SPRINGER_PAPER_4FEATURE_V1"
        assert res.total_frames_50hz == 200  # 4.0 s * 50 Hz
        assert len(res.s1_intervals) > 0

    def test_model_profile_mismatch_guard(self):
        """Passing a model with incompatible profile or feature names returns MODEL_PROFILE_MISMATCH."""
        fs = 4000.0
        x_pcg = _generate_synthetic_pcg_wav(fs=fs, duration_s=4.0, bpm=60.0)

        # 3-feature reference model
        ref_model = build_demo_springer_model(include_wavelet=False)
        assert ref_model.feature_profile_id == "SPRINGER_PHYSIONET_REFERENCE_V1"

        # Attempt to run under 4-feature paper profile
        res = segment_pcg_springer(
            signal=x_pcg,
            sample_rate_hz=fs,
            model=ref_model,
            config=SPRINGER_PAPER_4FEATURE_V1,
        )

        assert res.status == SegmentationStatus.MODEL_PROFILE_MISMATCH
        assert len(res.state_sequence_50hz) == 0
        assert len(res.state_intervals) == 0
        assert any("MODEL_PROFILE_MISMATCH" in w or "does not match" in w for w in res.technical_warnings)
