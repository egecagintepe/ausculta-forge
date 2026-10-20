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

import hashlib
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
    SessionCorruptedError,
    list_sessions,
    get_session,
    create_session_source,
    validate_session_id,
    verify_session_integrity,
    export_session_manifest,
    delete_session,
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

    def test_exact_sample_accounting_across_variable_chunks(self, tmp_path: Path):
        """Verify exact sample count matching between recorder memory, WAV file, and metadata."""
        rec = SessionRecorder(output_dir=tmp_path, wav_format="float32")
        sid = rec.start(source="variable_chunks_test")
        fs = 48000

        # Feed 4 blocks of arbitrary, uneven lengths
        chunk_sizes = [127, 255, 63, 1024]
        total_expected_samples = sum(chunk_sizes)
        seq = 0
        current_sample = 0

        for size in chunk_sizes:
            samples = np.linspace(0.01, 0.99, size, dtype=np.float32)
            ts = current_sample / fs
            block = SampleBlock(sequence=seq, timestamp_s=ts, sample_rate_hz=fs, samples=samples, source="test")
            rec.record_block(block)
            seq += 1
            current_sample += size

        meta = rec.stop(termination_reason="completed")

        # 1. Check in-memory recorder metadata
        assert meta.total_samples == total_expected_samples
        assert meta.total_blocks == len(chunk_sizes)
        assert pytest.approx(meta.duration_s, abs=1e-5) == total_expected_samples / fs

        # 2. Check disk WAV file frame count
        wav_path = tmp_path / sid / "raw.wav"
        read_fs, read_data = wavfile.read(str(wav_path))
        assert read_fs == fs
        assert len(read_data) == total_expected_samples

        # 3. Check session.json sidecar on disk
        json_path = tmp_path / sid / "session.json"
        with open(json_path, "r", encoding="utf-8") as f:
            disk_meta = json.load(f)
        assert disk_meta["total_samples"] == total_expected_samples
        assert disk_meta["total_blocks"] == len(chunk_sizes)

    def test_storage_format_and_disclaimer_distinction(self, tmp_path: Path):
        """Verify explicit distinction between normalized float32 WAV and wire format."""
        rec = SessionRecorder(output_dir=tmp_path, wav_format="float32")
        rec.start(
            source="wire_format_test",
            wire_format="signed_pcm_24bit_in_32bit_slot",
        )
        rec.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.full(64, 0.5, dtype=np.float32)))
        meta = rec.stop()

        assert meta.storage_format == "normalized_float32"
        assert meta.wire_format == "signed_pcm_24bit_in_32bit_slot"
        assert "normalized IEEE float32" in meta.storage_disclaimer
        assert "not an unparsed wire bitstream copy" in meta.storage_disclaimer.lower()

    def test_acquisition_provenance_hardware_vs_non_hardware(self, tmp_path: Path):
        """Verify hardware metadata is recorded only for hardware and never fabricated for non-hardware."""
        # 1. Hardware acquisition
        rec_hw = SessionRecorder(output_dir=tmp_path)
        hw_info = {
            "device_id": "ESP32-S3-LAB-01",
            "firmware_version": "v1.2.0-rc1",
            "transport_type": "native_usb",
            "sample_rate_hz": 48000,
        }
        rec_hw.start(
            session_id="hw_sess",
            source="hardware_probe",
            acquisition_mode="hardware",
            device_info=hw_info,
        )
        rec_hw.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.zeros(32, dtype=np.float32)))
        meta_hw = rec_hw.stop()
        assert meta_hw.device_info is not None
        assert meta_hw.device_info["device_id"] == "ESP32-S3-LAB-01"

        # 2. Synthetic / non-hardware acquisition (zero fabricated hardware metadata!)
        rec_syn = SessionRecorder(output_dir=tmp_path)
        rec_syn.start(
            session_id="syn_sess",
            source="synthetic_sine",
            acquisition_mode="synthetic",
            device_info=None,
        )
        rec_syn.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.zeros(32, dtype=np.float32)))
        meta_syn = rec_syn.stop()
        assert meta_syn.device_info is None

    def test_pre_creation_and_incomplete_session_detection(self, tmp_path: Path):
        """Verify pre-creation on start() ensures aborted/crashed sessions are detected as incomplete."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="crashed_sess", source="crash_test")

        # Simulate crash: session was started, placeholder written, but stop() never called
        marker_file = tmp_path / sid / "session.json"
        assert marker_file.exists()
        with open(marker_file, "r", encoding="utf-8") as f:
            marker = json.load(f)
        assert marker["status"] == "recording"
        assert marker["termination_reason"] == "incomplete"

        # Scanner recognizes session as incomplete
        sessions = list_sessions(tmp_path)
        matching = [s for s in sessions if s["session_id"] == sid]
        assert len(matching) == 1
        assert matching[0]["status"] == "incomplete"

        # Integrity verifier recognizes session as incomplete
        check = verify_session_integrity(sid, tmp_path)
        assert check["is_valid"] is False
        assert check["status"] == "incomplete"
        assert check["termination_reason"] == "incomplete"

    def test_interrupted_session_preserves_samples_and_reasons(self, tmp_path: Path):
        """Verify sudden USB disconnect cleanly records samples up to disconnect and flags reason."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="interrupted_sess", source="esp32_cable_pull")

        samples_before_pull = np.full(512, 0.42, dtype=np.float32)
        rec.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=samples_before_pull))

        # Abrupt disconnect stop
        meta = rec.stop(termination_reason="device_disconnected")
        assert meta.termination_reason == "device_disconnected"
        assert meta.total_samples == 512

        # Verify integrity check flags interrupted status while verifying samples
        check = verify_session_integrity(sid, tmp_path)
        assert check["is_valid"] is True
        assert check["status"] == "interrupted_valid"
        assert check["sha256_match"] is True
        assert check["sample_count_match"] is True
        assert check["termination_reason"] == "device_disconnected"

    def test_backward_compatible_schema_v1_loading(self, tmp_path: Path):
        """Verify older v1.0.0 session metadata files load cleanly without missing field errors."""
        legacy_dir = tmp_path / "legacy_v1_session"
        legacy_dir.mkdir(parents=True)

        legacy_json = {
            "session_id": "legacy_v1_session",
            "started_at_utc": "2026-10-10T12:00:00Z",
            "ended_at_utc": "2026-10-10T12:00:05Z",
            "source": "old_synthetic",
            "sample_rate_hz": 4000,
            "total_blocks": 10,
            "total_samples": 1280,
            "duration_s": 0.32,
            "raw_wav_relpath": "raw.wav",
            "raw_wav_sha256": "fakehash123",
            "stream_quality": {"is_healthy": True},
            "environment": {},
            "app_version": "1.0.0",
            # schema_version, storage_format, wire_format, processing_profile all absent
        }
        with open(legacy_dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(legacy_json, f)

        # 1. from_dict succeeds
        meta = SessionMetadata.from_dict(legacy_json)
        assert meta.schema_version == "1.0.0"
        assert meta.storage_format == "normalized_float32"
        assert meta.wire_format is None
        assert meta.processing_profile is None

        # 2. get_session succeeds
        loaded = get_session("legacy_v1_session", tmp_path)
        assert loaded is not None
        assert loaded["schema_version"] == "1.0.0"

    def test_sha256_verification_and_tamper_detection(self, tmp_path: Path):
        """Verify cryptographic verification and detection of modified WAV audio."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="tamper_test")
        rec.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.arange(100, dtype=np.float32) / 100.0))
        rec.stop()

        # 1. Untampered session passes
        c1 = verify_session_integrity(sid, tmp_path)
        assert c1["is_valid"] is True
        assert c1["sha256_match"] is True
        assert c1["sample_count_match"] is True
        assert c1["status"] == "verified"

        # 2. Tamper: corrupt 1 byte in audio sample payload (near end of file)
        wav_path = tmp_path / sid / "raw.wav"
        with open(wav_path, "r+b") as f:
            f.seek(-10, 2)  # Seek relative to EOF inside float32 audio samples
            byte_val = f.read(1)[0]
            f.seek(-10, 2)
            f.write(bytes([(byte_val + 1) % 256]))

        c2 = verify_session_integrity(sid, tmp_path)
        assert c2["is_valid"] is False
        assert c2["sha256_match"] is False
        assert c2["status"] == "hash_mismatch"
        assert "Cryptographic mismatch" in c2["details"]

    def test_windows_reserved_names_rejected(self, tmp_path: Path):
        """Verify Windows reserved device names are strictly rejected."""
        reserved = ["CON", "prn", "AUX", "NUL", "com1", "COM9", "lpt1", "LPT9"]
        for name in reserved:
            with pytest.raises(ValueError, match="Reserved identifier not allowed"):
                validate_session_id(name, tmp_path)

    def test_corrupted_metadata_graceful_handling(self, tmp_path: Path):
        """Verify invalid JSON in session.json does not crash list_sessions or verifier."""
        corrupt_dir = tmp_path / "corrupt_meta_sess"
        corrupt_dir.mkdir(parents=True)
        with open(corrupt_dir / "session.json", "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON NOT CLOSED")

        # Listing does not crash
        sessions = list_sessions(tmp_path)
        corrupt_item = next((s for s in sessions if s["session_id"] == "corrupt_meta_sess"), None)
        assert corrupt_item is not None
        assert corrupt_item["status"] == "corrupted_metadata"

        # Verifier flags error cleanly
        c = verify_session_integrity("corrupt_meta_sess", tmp_path)
        assert c["is_valid"] is False
        assert c["status"] == "corrupted_metadata"

    def test_malformed_wav_handling(self, tmp_path: Path):
        """Verify corrupted or truncated WAV files raise clean errors."""
        bad_dir = tmp_path / "bad_wav_sess"
        bad_dir.mkdir(parents=True)
        bad_bytes = b"RIFF\x00\x00\x00\x00"
        meta = {
            "session_id": "bad_wav_sess",
            "started_at_utc": "2026-10-17T00:00:00Z",
            "total_samples": 100,
            "sample_rate_hz": 48000,
            "raw_wav_relpath": "raw.wav",
            "raw_wav_sha256": hashlib.sha256(bad_bytes).hexdigest(),
        }
        with open(bad_dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(meta, f)

        # Write 8 truncated garbage bytes
        with open(bad_dir / "raw.wav", "wb") as f:
            f.write(bad_bytes)

        # create_session_source raises SessionCorruptedError
        with pytest.raises(SessionCorruptedError, match="Session audio file is corrupted or unreadable"):
            create_session_source("bad_wav_sess", sessions_dir=tmp_path)

        # verify_session_integrity catches malformed WAV
        c = verify_session_integrity("bad_wav_sess", tmp_path)
        assert c["is_valid"] is False
        assert c["status"] == "malformed_wav"

    def test_manifest_export_structure(self, tmp_path: Path):
        """Verify export_session_manifest produces complete phantom-ready provenance document."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(
            session_id="phantom_test_sess",
            source="phantom_sine",
            wire_format="signed_pcm_24bit_in_32bit_container",
            processing_profile={"filter_preset": "pcg_bandpass", "low_hz": 20, "high_hz": 600},
        )
        rec.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.full(128, 0.25, dtype=np.float32)))
        rec.stop(termination_reason="completed")

        manifest = export_session_manifest(sid, tmp_path)
        assert manifest["manifest_version"] == "2.0.0"
        assert manifest["manifest_type"] == "ausculta_forge_session_manifest"
        assert manifest["session_id"] == sid
        assert manifest["acquisition"]["sample_rate_hz"] == 48000
        assert manifest["acquisition"]["total_samples"] == 128
        assert manifest["data_specification"]["storage_format"] == "normalized_float32"
        assert manifest["data_specification"]["wire_format"] == "signed_pcm_24bit_in_32bit_container"
        assert manifest["dsp_provenance"]["processing_profile"]["filter_preset"] == "pcg_bandpass"
        assert manifest["integrity"]["integrity_verified"] is True
        assert manifest["app_provenance"]["schema_version"] == "2.0.0"

    def test_session_safe_deletion(self, tmp_path: Path):
        """Verify delete_session removes session directory cleanly."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="to_delete")
        rec.record_block(SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=48000, samples=np.ones(10, dtype=np.float32)))
        rec.stop()

        assert (tmp_path / sid).exists()
        assert delete_session(sid, tmp_path) is True
        assert not (tmp_path / sid).exists()

        # Subsequent delete returns False
        assert delete_session(sid, tmp_path) is False

    def test_numerical_consistency_recording_and_replay(self, tmp_path: Path):
        """Verify that replaying a session emits samples mathematically identical to what was recorded."""
        rec = SessionRecorder(output_dir=tmp_path)
        sid = rec.start(session_id="num_consistency_sess")

        # 48 kHz 100 Hz sine wave, 2048 samples
        t = np.arange(2048) / 48000.0
        orig_samples = (0.75 * np.sin(2.0 * np.pi * 100.0 * t)).astype(np.float32)

        # Record in blocks of 256
        for i in range(0, 2048, 256):
            blk_samples = orig_samples[i : i + 256]
            rec.record_block(SampleBlock(sequence=i // 256, timestamp_s=float(t[i]), sample_rate_hz=48000, samples=blk_samples))
        rec.stop()

        # Replay through WavSource in blocks of 128
        source = create_session_source(sid, sessions_dir=tmp_path, block_size=128)
        replayed_chunks = [b.samples for b in source.blocks()]
        replayed_samples = np.concatenate(replayed_chunks)

        assert len(replayed_samples) == len(orig_samples)
        # Mathematical identity (0.0 difference)
        assert np.array_equal(replayed_samples, orig_samples)
