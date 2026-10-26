"""Tests for Week 6 UX stabilization: recording elapsed seconds synchronization and manifest version disambiguation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import tempfile
import time
import pytest
import numpy as np

from pcg_core.models import SampleBlock
from pcg_core.recording import (
    SessionRecorder,
    SessionMetadata,
    export_session_manifest,
    get_session,
)
from pcg_app.state import StreamManager


def test_session_recorder_elapsed_seconds_and_properties(tmp_path: Path):
    """Verify that SessionRecorder computes elapsed_seconds exactly from total_samples and sample_rate."""
    rec = SessionRecorder(output_dir=tmp_path, wav_format="float32")
    assert rec.elapsed_seconds == 0.0
    assert rec.total_blocks == 0
    assert rec.total_samples == 0

    sid = rec.start(source="test_pcm", session_id="session_elapsed_test")
    assert sid == "session_elapsed_test"
    assert rec.source == "test_pcm"

    fs = 4000
    # Feed 1 block of 128 samples
    b1 = SampleBlock(
        sequence=0,
        timestamp_s=0.0,
        sample_rate_hz=fs,
        samples=np.zeros(128, dtype=np.float32),
    )
    rec.record_block(b1)
    assert rec.total_blocks == 1
    assert rec.total_samples == 128
    assert rec.elapsed_seconds == pytest.approx(128 / 4000, rel=1e-5)

    # Feed 19 more blocks (total 20 blocks = 2560 samples = 0.64s)
    for i in range(1, 20):
        b = SampleBlock(
            sequence=i,
            timestamp_s=i * 128 / fs,
            sample_rate_hz=fs,
            samples=np.zeros(128, dtype=np.float32),
        )
        rec.record_block(b)

    assert rec.total_blocks == 20
    assert rec.total_samples == 2560
    assert rec.elapsed_seconds == pytest.approx(2560 / 4000, rel=1e-5)

    meta = rec.stop()
    assert meta.total_samples == 2560
    assert meta.duration_s == pytest.approx(0.64, rel=1e-5)


def test_stream_manager_recording_elapsed_broadcast_and_pause(tmp_path: Path):
    """Verify that StreamManager broadcasts recording_state with elapsed_seconds advancing and pausing cleanly."""
    async def _run():
        manager = StreamManager(sessions_dir=tmp_path)
        # Select synthetic source
        manager.select_source("synthetic_dev")
        assert manager.is_streaming

        received_rec_messages: list[dict] = []

        class MockWebSocket:
            async def send_json(self, msg: dict) -> None:
                if msg.get("type") == "recording_state":
                    received_rec_messages.append(msg)

        ws = MockWebSocket()
        manager.register_client(ws)

        # Start recording
        sid = manager.start_recording()
        assert manager.recorder.is_recording
        assert sid is not None

        fs = manager.sample_rate_hz
        # Dispatch blocks
        for i in range(10):
            block = SampleBlock(
                sequence=i,
                timestamp_s=i * 128 / fs,
                sample_rate_hz=fs,
                samples=np.sin(np.linspace(0, 2 * np.pi, 128, dtype=np.float32)),
            )
            # Advance time so throttled broadcast fires
            manager._last_rec_broadcast_time = 0.0
            await manager._dispatch_sample_block(block)

        assert len(received_rec_messages) >= 1
        last_msg = received_rec_messages[-1]
        assert last_msg["is_recording"] is True
        assert last_msg["samples_recorded"] == 10 * 128
        assert last_msg["elapsed_seconds"] == pytest.approx((10 * 128) / fs, rel=1e-3)

        # Test Pause: elapsed time must not advance
        manager.pause_stream()
        assert manager.is_paused is True
        paused_samples = manager.recorder.total_samples
        paused_elapsed = manager.recorder.elapsed_seconds

        # Simulate loop skipping blocks while paused
        await asyncio.sleep(0.05)
        assert manager.recorder.total_samples == paused_samples
        assert manager.recorder.elapsed_seconds == paused_elapsed

        # Resume stream
        manager.resume_stream()
        assert manager.is_paused is False

        # Dispatch another block
        manager._last_rec_broadcast_time = 0.0
        b_resume = SampleBlock(
            sequence=10,
            timestamp_s=10 * 128 / fs,
            sample_rate_hz=fs,
            samples=np.zeros(128, dtype=np.float32),
        )
        await manager._dispatch_sample_block(b_resume)
        assert manager.recorder.total_samples == 11 * 128
        assert manager.recorder.elapsed_seconds == pytest.approx((11 * 128) / fs, rel=1e-3)

        # Stop recording
        meta = manager.stop_recording()
        assert meta.total_samples == 11 * 128
        assert meta.duration_s == pytest.approx((11 * 128) / fs, rel=1e-3)
        manager.unregister_client(ws)

    asyncio.run(_run())


def test_session_manifest_version_disambiguation(tmp_path: Path):
    """Verify that export_session_manifest includes dsp_engine_version, desktop_client_version, and legacy app_version."""
    rec = SessionRecorder(output_dir=tmp_path, wav_format="float32")
    sid = rec.start(source="test_provenance", session_id="session_ver_test")
    b = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=np.zeros(256, dtype=np.float32))
    rec.record_block(b)
    meta = rec.stop()

    assert meta.dsp_engine_version == "2.0.0"
    assert meta.desktop_client_version == "0.1.0-alpha.1"
    assert meta.app_version == "2.0.0"

    manifest = export_session_manifest(sid, tmp_path)
    app_prov = manifest["app_provenance"]
    assert app_prov["dsp_engine_version"] == "2.0.0"
    assert app_prov["desktop_client_version"] == "0.1.0-alpha.1"
    assert app_prov["app_version"] == "2.0.0"
    assert app_prov["schema_version"] == "2.0.0"


def test_backward_compatible_manifest_reading():
    """Verify that older v1 manifests with only app_version can still be parsed safely."""
    legacy_dict = {
        "session_id": "legacy_session_001",
        "started_at_utc": "2026-09-01T12:00:00Z",
        "ended_at_utc": "2026-09-01T12:00:10Z",
        "source": "circor_sample",
        "sample_rate_hz": 4000,
        "total_blocks": 50,
        "total_samples": 6400,
        "duration_s": 1.6,
        "raw_wav_relpath": "raw.wav",
        "raw_wav_sha256": "dummy_hash",
        "app_version": "1.0.0",
        "schema_version": "1.0.0",
    }

    meta = SessionMetadata.from_dict(legacy_dict)
    assert meta.session_id == "legacy_session_001"
    assert meta.app_version == "1.0.0"
    assert meta.dsp_engine_version == "1.0.0"
    assert meta.desktop_client_version == "0.1.0-alpha.1"
