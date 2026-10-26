"""Regression and unit tests for continuous replay EOF wrap and conscious rewind health.

Verifies:
1. Conscious EOF wrap / loop restart does not flag false sequence discontinuities or timestamp regressions.
2. Stream health remains True across loop cycles when no real data loss occurred.
3. Health counters are NOT fake-reset: legitimate dropped blocks or sequence anomalies remain recorded.
4. Mid-stream anomalies without conscious rewind notification remain properly flagged.
5. StreamManager continuous background stream loop handles EOF without degradation.
"""

import asyncio
import numpy as np
import pytest
from pathlib import Path
from scipy.io import wavfile

from pcg_core.models import SampleBlock
from pcg_core.streaming import StreamQualityMonitor, LiveStreamingPipeline
from pcg_app.state import StreamManager


def test_quality_monitor_eof_wrap_preserves_health():
    """Verify notify_rewind prevents false degradation on normal loop wrap."""
    monitor = StreamQualityMonitor(expected_sample_rate_hz=2000)

    # First cycle: blocks 0, 1, 2
    for seq in range(3):
        block = SampleBlock(
            sequence=seq,
            timestamp_s=seq * 0.128,
            sample_rate_hz=2000,
            samples=np.zeros(256, dtype=np.float32),
            source="test.wav",
        )
        issues = monitor.inspect_block(block)
        assert len(issues) == 0

    assert monitor.report.is_healthy
    assert monitor.report.sequence_discontinuities == 0
    assert monitor.report.timestamp_regressions == 0
    assert monitor.report.dropped_blocks == 0

    # Normal EOF reached: notify_rewind called
    monitor.notify_rewind()

    # Second cycle: blocks 0, 1, 2
    for seq in range(3):
        block = SampleBlock(
            sequence=seq,
            timestamp_s=seq * 0.128,
            sample_rate_hz=2000,
            samples=np.zeros(256, dtype=np.float32),
            source="test.wav",
        )
        issues = monitor.inspect_block(block)
        assert len(issues) == 0

    # Must still be completely healthy
    assert monitor.report.is_healthy
    assert monitor.report.sequence_discontinuities == 0
    assert monitor.report.timestamp_regressions == 0
    assert monitor.report.dropped_blocks == 0
    assert monitor.report.total_blocks == 6


def test_quality_monitor_no_fake_reset_on_real_error():
    """Verify notify_rewind does NOT wipe out real dropped blocks or anomalies."""
    monitor = StreamQualityMonitor(expected_sample_rate_hz=2000)

    # Cycle 1: block 0, then block 3 (dropped 2 blocks!)
    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    b3 = SampleBlock(sequence=3, timestamp_s=0.384, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    monitor.inspect_block(b0)
    monitor.inspect_block(b3)

    assert not monitor.report.is_healthy
    assert monitor.report.dropped_blocks == 2
    assert monitor.report.sequence_discontinuities == 1

    # Conscious rewind occurs
    monitor.notify_rewind()

    # Cycle 2: block 0 arrives cleanly
    b0_next = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    monitor.inspect_block(b0_next)

    # Historical dropped blocks and discontinuities MUST NOT be wiped out
    assert monitor.report.dropped_blocks == 2
    assert monitor.report.sequence_discontinuities == 1
    # is_healthy MUST still be False because real loss occurred
    assert not monitor.report.is_healthy


def test_quality_monitor_unannounced_jump_back_is_flagged():
    """Verify that an unexpected jump back to 0 without notify_rewind IS flagged as out-of-order."""
    monitor = StreamQualityMonitor(expected_sample_rate_hz=2000)

    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    b1 = SampleBlock(sequence=1, timestamp_s=0.128, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    monitor.inspect_block(b0)
    monitor.inspect_block(b1)
    assert monitor.report.is_healthy

    # Unannounced jump back to sequence 0 (e.g. data corruption or unexpected packet)
    b0_unannounced = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(256), source="test.wav")
    issues = monitor.inspect_block(b0_unannounced)

    assert not monitor.report.is_healthy
    assert monitor.report.sequence_discontinuities == 1
    assert monitor.report.timestamp_regressions == 1
    assert any("Out-of-order sequence" in s for s in issues)
    assert any("Timestamp regression" in s for s in issues)


def test_pipeline_notify_rewind_resets_filter_zi():
    """Verify pipeline.notify_rewind resets the causal filter delay state."""
    pipeline = LiveStreamingPipeline(buffer_duration_s=1.0, filter_low_hz=20, filter_high_hz=200)

    # Process blocks with DC offset to load filter state
    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.ones(256, dtype=np.float32))
    pipeline.process_block(b0)
    assert pipeline.filter is not None
    assert np.any(pipeline.filter.zi != 0.0)

    # Notify rewind
    pipeline.notify_rewind()
    assert np.all(pipeline.filter.zi == 0.0)


def test_stream_manager_eof_continuous_replay_loop(tmp_path: Path):
    """Verify that playing a WAV in StreamManager across EOF does not degrade stream health."""
    wav_path = tmp_path / "short.wav"
    fs = 2000
    # 512 samples = 2 blocks of 256
    wavfile.write(wav_path, fs, np.sin(2 * np.pi * 100 * np.arange(512) / fs).astype(np.float32))

    manager = StreamManager(sessions_dir=tmp_path / "sessions")
    state = manager.select_source("realtime_wav", path=str(wav_path))
    assert state["source_type"] == "realtime_wav"

    # Drive pass 1
    gen1 = manager._create_source_generator()
    for block in gen1:
        asyncio.run(manager._dispatch_sample_block(block))

    assert manager.pipeline.quality_monitor.report.is_healthy
    assert manager.pipeline.quality_monitor.report.sequence_discontinuities == 0
    assert manager.pipeline.quality_monitor.report.timestamp_regressions == 0

    # Simulate EOF wrap in _stream_loop
    manager.pipeline.notify_rewind()
    manager.display_aggregator.reset()

    # Drive pass 2 (the loop replay)
    gen2 = manager._create_source_generator()
    for block in gen2:
        asyncio.run(manager._dispatch_sample_block(block))

    # Must still be completely healthy
    assert manager.pipeline.quality_monitor.report.is_healthy
    assert manager.pipeline.quality_monitor.report.sequence_discontinuities == 0
    assert manager.pipeline.quality_monitor.report.timestamp_regressions == 0
    assert manager.pipeline.quality_monitor.report.dropped_blocks == 0
