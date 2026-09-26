"""Tests for AuscultaForge Session Recording & Replay Module.

Verifies:
- session directory creation and file structure
- exact sample preservation (float32 bit-exact)
- metadata schema and field population
- WAV SHA-256 hash integrity
- empty session failure rejection
- mid-session sample rate change rejection
- replay compatibility through WavSource and RealtimeWavSource
- session listing and retrieval APIs
"""

import json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import wavfile

from pcg_core.models import SampleBlock
from pcg_core.recording import (
    SessionMetadata,
    SessionRecorder,
    RecordingSampleRateError,
    RecordingStateError,
    list_sessions,
    get_session,
    create_session_source,
    validate_session_id,
)
from pcg_core.sources import MockPCGSource, WavSource, RealtimeWavSource
from pcg_core.experiment import compute_file_sha256


class TestSessionRecording:
    """Unit tests for SessionRecorder lifecycle and metadata integrity."""

    def test_record_and_save_session_exact_samples(self, tmp_path: Path):
        rec = SessionRecorder(output_dir=tmp_path, wav_format="float32")
        sid = rec.start(source="test_synthetic")
        assert sid.startswith("session_")
        assert rec.is_recording is True

        # Generate sample blocks
        fs = 4000
        block1_data = np.array([0.1, -0.2, 0.35, -0.4], dtype=np.float32)
        block2_data = np.array([0.5, 0.6, -0.7, 0.85], dtype=np.float32)

        b1 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=fs, samples=block1_data, source="test")
        b2 = SampleBlock(sequence=1, timestamp_s=4 / fs, sample_rate_hz=fs, samples=block2_data, source="test")

        rec.record_block(b1)
        rec.record_block(b2)

        meta = rec.stop()
        assert rec.is_recording is False

        # Verify SessionMetadata
        assert meta.session_id == sid
        assert meta.source == "test_synthetic"
        assert meta.sample_rate_hz == fs
        assert meta.total_blocks == 2
        assert meta.total_samples == 8
        assert pytest.approx(meta.duration_s, abs=1e-4) == 8 / fs
        assert meta.first_sequence == 0
        assert meta.last_sequence == 1
        assert meta.raw_wav_relpath == "raw.wav"

        # Verify filesystem output
        session_dir = tmp_path / sid
        assert session_dir.exists()
        assert (session_dir / "raw.wav").exists()
        assert (session_dir / "session.json").exists()

        # Verify exact sample preservation
        read_fs, read_samples = wavfile.read(session_dir / "raw.wav")
        assert read_fs == fs
        expected = np.concatenate([block1_data, block2_data])
        assert np.array_equal(read_samples, expected)

        # Verify SHA-256 matches actual file bytes
        calc_sha = compute_file_sha256(session_dir / "raw.wav")
        assert meta.raw_wav_sha256 == calc_sha

    def test_empty_session_rejected(self, tmp_path: Path):
        rec = SessionRecorder(output_dir=tmp_path)
        rec.start(session_id="empty_sess")
        with pytest.raises(ValueError, match="No audio samples were recorded"):
            rec.stop()

    def test_mid_session_sample_rate_change_rejected(self, tmp_path: Path):
        rec = SessionRecorder(output_dir=tmp_path)
        rec.start(session_id="rate_change_sess")

        b1 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=np.zeros(10, dtype=np.float32))
        b2 = SampleBlock(sequence=1, timestamp_s=0.01, sample_rate_hz=2000, samples=np.zeros(10, dtype=np.float32))

        rec.record_block(b1)
        with pytest.raises(RecordingSampleRateError, match="Sample rate mismatch mid-session"):
            rec.record_block(b2)

        assert rec.is_recording is False

    def test_invalid_lifecycle_state_errors(self, tmp_path: Path):
        rec = SessionRecorder(output_dir=tmp_path)
        # Cannot record when not active
        b = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=np.zeros(10, dtype=np.float32))
        with pytest.raises(RecordingStateError):
            rec.record_block(b)

        # Cannot stop when not active
        with pytest.raises(RecordingStateError):
            rec.stop()

        # Cannot start twice
        rec.start()
        with pytest.raises(RecordingStateError):
            rec.start()

    def test_replay_compatibility_with_sources(self, tmp_path: Path):
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="replay_sess")

        # Record mock PCG stream
        src = MockPCGSource(sample_rate_hz=4000, block_size=128, duration_s=0.5)
        recorded_blocks = list(src.blocks())
        for b in recorded_blocks:
            rec.record_block(b)
        rec.stop()

        # Replay with WavSource
        replay_src = create_session_source(sid, sessions_dir=tmp_path, block_size=128)
        assert isinstance(replay_src, WavSource)
        replayed_blocks = list(replay_src.blocks())
        assert len(replayed_blocks) == len(recorded_blocks)
        assert replayed_blocks[0].sample_rate_hz == 4000

        # Replay with RealtimeWavSource
        rt_src = create_session_source(sid, sessions_dir=tmp_path, block_size=128, realtime=False)
        assert isinstance(rt_src, WavSource)

    def test_list_and_get_sessions(self, tmp_path: Path):
        rec1 = SessionRecorder(output_dir=tmp_path)
        rec1.start(session_id="sess_1", source="mic1")
        rec1.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=np.ones(10, dtype=np.float32)))
        rec1.stop()

        rec2 = SessionRecorder(output_dir=tmp_path)
        rec2.start(session_id="sess_2", source="mic2")
        rec2.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=np.ones(20, dtype=np.float32)))
        rec2.stop()

        sessions = list_sessions(tmp_path)
        assert len(sessions) == 2
        sids = [s["session_id"] for s in sessions]
        assert "sess_1" in sids
        assert "sess_2" in sids

        retrieved = get_session("sess_1", tmp_path)
        assert retrieved is not None
        assert retrieved["session_id"] == "sess_1"
        assert retrieved["source"] == "mic1"
        assert retrieved["total_samples"] == 10

        assert get_session("non_existent", tmp_path) is None

    def test_session_id_validation_and_path_containment(self, tmp_path: Path):
        # Valid session IDs
        assert validate_session_id("session_123_abc", tmp_path) == "session_123_abc"
        assert validate_session_id("sess-test-456", tmp_path) == "sess-test-456"

        # Invalid characters or traversal
        invalid_ids = [
            "../escaped",
            "..\\escaped",
            "../../etc/passwd",
            "folder/sub",
            "folder\\sub",
            "",
            "   ",
            "sess with space",
            "sess@bad!",
        ]
        for bad_id in invalid_ids:
            with pytest.raises(ValueError):
                validate_session_id(bad_id, tmp_path)

        # get_session returns None safely on traversal attempt
        assert get_session("../escaped", tmp_path) is None
        assert get_session("bad/id", tmp_path) is None

        # create_session_source rejects traversal attempt with ValueError
        with pytest.raises(ValueError):
            create_session_source("../escaped", sessions_dir=tmp_path)

        # SessionRecorder.start rejects traversal session_id
        rec = SessionRecorder(output_dir=tmp_path)
        with pytest.raises(ValueError):
            rec.start(session_id="../escaped")
