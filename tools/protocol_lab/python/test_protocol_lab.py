"""Tests for AuscultaForge Protocol Laboratory & C/Python Parity.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)
"""

from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from protocol_codec import (
    StreamingProtocolDecoder,
    build_profile_a_packet,
    build_profile_b_packet,
    crc16_ccitt,
    crc32_ieee,
    PROFILE_A_HEADER_SIZE,
    PROFILE_B_HEADER_SIZE,
    PROFILE_B_SAMPLES_PER_FRAME,
    NOMINAL_SAMPLE_RATE_HZ,
    MAX_DECODER_BUFFER_BYTES,
)
from protocol_validator import ProtocolValidator

C_DIR = Path(__file__).resolve().parent.parent / "c"
RUNNER_EXE = C_DIR / "bin" / "g1_sim_runner.exe"
if not RUNNER_EXE.exists():
    RUNNER_EXE = C_DIR / "g1_sim_runner.exe"


class TestProtocolLaboratory:
    """Test suite for protocol codecs, C/Python parity, and stress robustness."""

    def test_crc_implementations_match_known_vectors(self):
        """Verify CRC-16 and CRC-32 match standard known-answer test vectors."""
        kat = b"123456789"
        assert crc16_ccitt(kat) == 0x29B1
        assert crc32_ieee(kat) == 0xCBF43926

    def test_profile_a_roundtrip(self):
        """Verify Profile A packet serialization and deserialization."""
        samples = np.array([0, 1000, -2000, 3000, -8388608, 8388607], dtype=np.int32)
        wire_bytes = build_profile_a_packet(sequence=99, timestamp_us=500000, samples=samples)

        assert len(wire_bytes) == PROFILE_A_HEADER_SIZE + len(samples) * 4 + 2

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(wire_bytes)

        assert len(packets) == 1
        pkt = packets[0]
        assert pkt.is_profile_b is False
        assert pkt.crc_ok is True
        assert pkt.sequence_id == 99
        assert pkt.timestamp_us == 500000
        assert pkt.sample_count == len(samples)
        np.testing.assert_array_equal(pkt.raw_samples, samples)

    def test_profile_b_roundtrip(self):
        """Verify Profile B 40-byte header packet serialization and deserialization."""
        samples = np.arange(256, dtype=np.int32) * 50
        wire_bytes = build_profile_b_packet(
            sequence_id=1234,
            timestamp_us=987654321,
            sample_index_start=25600,
            samples=samples,
            sample_rate_hz=48000,
            meaningful_bits=24,
            flags=0x03,
            encoding=0x01,
            mcu_drops=5,
        )

        assert len(wire_bytes) == PROFILE_B_HEADER_SIZE + 256 * 4 + 4

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(wire_bytes)

        assert len(packets) == 1
        pkt = packets[0]
        assert pkt.is_profile_b is True
        assert pkt.crc_ok is True
        assert pkt.sequence_id == 1234
        assert pkt.timestamp_us == 987654321
        assert pkt.sample_index_start == 25600
        assert pkt.sample_count == 256
        assert pkt.sample_rate_hz == 48000
        assert pkt.meaningful_bits == 24
        assert pkt.flags == 0x03
        assert pkt.encoding == 0x01
        assert pkt.mcu_buffer_drops == 5
        np.testing.assert_array_equal(pkt.raw_samples, samples)

    def test_cross_language_explicit_field_offsets_golden_vector(self):
        """Verify Profile B 40-byte header exact byte offsets against C11 layout."""
        samples = np.zeros(256, dtype=np.int32)
        wire_packet = build_profile_b_packet(
            sequence_id=0xA1B2C3D4,
            timestamp_us=0x0102030405060708,
            sample_index_start=0x1122334455667788,
            samples=samples,
            sample_rate_hz=48000,
            meaningful_bits=24,
            flags=0x1234,
            encoding=1,
            mcu_drops=7,
        )

        hdr = wire_packet[:40]
        assert len(hdr) == 40
        # Offset 0..3: magic 0xAF534331 ("1CSA" in LE)
        assert hdr[0:4] == b"\x31\x43\x53\xaf"
        # Offset 4: version
        assert hdr[4] == 1
        # Offset 5: msg_type
        assert hdr[5] == 1
        # Offset 6..7: flags 0x1234 (LE)
        assert hdr[6:8] == b"\x34\x12"
        # Offset 8..11: sequence 0xA1B2C3D4 (LE)
        assert hdr[8:12] == b"\xd4\xc3\xb2\xa1"
        # Offset 12..15: sample_rate 48000 (LE)
        assert hdr[12:16] == b"\x80\xbb\x00\x00"
        # Offset 16..23: timestamp 0x0102030405060708 (LE)
        assert hdr[16:24] == b"\x08\x07\x06\x05\x04\x03\x02\x01"
        # Offset 24..31: sample_index 0x1122334455667788 (LE)
        assert hdr[24:32] == b"\x88\x77\x66\x55\x44\x33\x22\x11"
        # Offset 32..33: sample_count 256 (LE)
        assert hdr[32:34] == b"\x00\x01"
        # Offset 34: meaningful_bits (24)
        assert hdr[34] == 24
        # Offset 35: container_bits (32)
        assert hdr[35] == 32
        # Offset 36: channels (1)
        assert hdr[36] == 1
        # Offset 37: encoding (1)
        assert hdr[37] == 1
        # Offset 38..39: mcu_buffer_drops 7 (LE)
        assert hdr[38:40] == b"\x07\x00"

    def test_c_executable_to_python_decoder_parity(self):
        """Execute compiled C runner and verify byte-level deserialization parity."""
        if not RUNNER_EXE.exists():
            pytest.skip("g1_sim_runner.exe not compiled")

        cmd = [str(RUNNER_EXE), "--mode=stream", "--signal=ramp", "--seconds=0.1", "--profile=b"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        raw_output = res.stdout

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(raw_output)

        assert len(packets) == 18
        for i, pkt in enumerate(packets):
            assert pkt.crc_ok is True
            assert pkt.sequence_id == i
            assert pkt.sample_count == 256

        all_samples = np.concatenate([p.raw_samples for p in packets])
        diffs = np.diff(all_samples)
        assert np.all(diffs == 1), "All samples must increment by exactly 1 without gaps"

    @pytest.mark.parametrize("chunk_size", [1, 3, 7, 13, 64, 128, 512, 1024])
    def test_fragmented_chunk_feed_fuzzing(self, chunk_size: int):
        """Verify decoder reassembles identical frames across arbitrary chunk read boundaries."""
        samples1 = np.full(256, 111, dtype=np.int32)
        samples2 = np.full(256, 222, dtype=np.int32)
        wire_data = (
            build_profile_b_packet(sequence_id=1, timestamp_us=1000, sample_index_start=0, samples=samples1) +
            build_profile_b_packet(sequence_id=2, timestamp_us=2000, sample_index_start=256, samples=samples2)
        )

        decoder = StreamingProtocolDecoder()
        received_packets = []

        offset = 0
        while offset < len(wire_data):
            chunk = wire_data[offset : offset + chunk_size]
            pkts = decoder.feed_bytes(chunk)
            received_packets.extend(pkts)
            offset += len(chunk)

        assert len(received_packets) == 2
        assert received_packets[0].sequence_id == 1
        assert received_packets[1].sequence_id == 2
        np.testing.assert_array_equal(received_packets[0].raw_samples, samples1)
        np.testing.assert_array_equal(received_packets[1].raw_samples, samples2)

    def test_partial_final_frame_decoding(self):
        """Verify decoder cleanly parses a partial final frame (e.g. 100 samples)."""
        samples = np.arange(100, dtype=np.int32) * 3
        wire_data = build_profile_b_packet(
            sequence_id=5, timestamp_us=50000, sample_index_start=1000, samples=samples
        )
        assert len(wire_data) == 40 + 100 * 4 + 4

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(wire_data)
        assert len(packets) == 1
        assert packets[0].sample_count == 100
        assert packets[0].crc_ok is True
        np.testing.assert_array_equal(packets[0].raw_samples, samples)

    def test_concatenated_frames(self):
        """Verify multiple concatenated frames in a single chunk are all emitted."""
        s = np.zeros(256, dtype=np.int32)
        blob = b"".join(
            build_profile_b_packet(sequence_id=i, timestamp_us=i*1000, sample_index_start=i*256, samples=s)
            for i in range(5)
        )
        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(blob)
        assert len(packets) == 5
        for i, pkt in enumerate(packets):
            assert pkt.sequence_id == i

    def test_sequence_wraparound_rfc3550(self):
        """Verify sequence wraparound across 0xFFFFFFFF has zero sequence gaps."""
        s = np.zeros(256, dtype=np.int32)
        p1 = build_profile_b_packet(sequence_id=0xFFFFFFFF, timestamp_us=1000, sample_index_start=0, samples=s)
        p2 = build_profile_b_packet(sequence_id=0, timestamp_us=2000, sample_index_start=256, samples=s)

        decoder = StreamingProtocolDecoder()
        decoder.feed_bytes(p1)
        decoder.feed_bytes(p2)

        assert decoder.total_frames_received == 2
        assert decoder.total_sequence_gaps == 0
        assert decoder.total_duplicate_frames == 0
        assert decoder.total_reordered_frames == 0

    def test_out_of_order_frame_rfc3550(self):
        """Verify reordered frames increment total_reordered_frames and do NOT inflate gaps."""
        s = np.zeros(256, dtype=np.int32)
        p_seq15 = build_profile_b_packet(sequence_id=15, timestamp_us=15000, sample_index_start=3840, samples=s)
        p_seq10 = build_profile_b_packet(sequence_id=10, timestamp_us=10000, sample_index_start=2560, samples=s)

        decoder = StreamingProtocolDecoder()
        decoder.feed_bytes(p_seq15)
        decoder.feed_bytes(p_seq10)

        assert decoder.total_frames_received == 2
        assert decoder.total_reordered_frames == 1
        assert decoder.total_sequence_gaps == 0

    def test_decoder_memory_safety_bound(self):
        """Verify decoder buffer is strictly bounded when fed arbitrary garbage."""
        decoder = StreamingProtocolDecoder()
        huge_garbage = b"\x77" * (MAX_DECODER_BUFFER_BYTES * 2)
        decoder.feed_bytes(huge_garbage)

        assert decoder.buffer_len <= MAX_DECODER_BUFFER_BYTES
        assert decoder.garbage_bytes_discarded > 0

    def test_crc_corruption_trapped(self):
        """Verify that corrupted frames fail CRC check and update error counters."""
        samples = np.arange(256, dtype=np.int32)
        corrupted_bytes = build_profile_b_packet(
            sequence_id=10, timestamp_us=5000, sample_index_start=0, samples=samples, corrupt_crc=True
        )

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(corrupted_bytes)

        assert len(packets) == 1
        assert packets[0].crc_ok is False
        assert decoder.total_frames_corrupted == 1

    def test_noise_recovery_resynchronization(self):
        """Verify stream lock recovery after discarding line noise preceding sync magic."""
        noise = b"\x00\xFF\x42\xDE\xAD\xBE\xEF\xAA\x54\x31\x43\x53\x00\x11"
        valid_packet = build_profile_b_packet(
            sequence_id=999, timestamp_us=99999, sample_index_start=0, samples=np.zeros(256, dtype=np.int32)
        )

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(noise + valid_packet)

        assert len(packets) == 1
        assert packets[0].crc_ok is True
        assert packets[0].sequence_id == 999
        assert decoder.garbage_bytes_discarded == len(noise)

    def test_exact_data_rates_and_overhead(self):
        """Validate theoretical and practical wire framing data rates."""
        fs = 48000
        bytes_per_sample = 4
        payload_rate_bps = fs * bytes_per_sample * 8
        assert payload_rate_bps == 1536000  # 1.536 Mbps

        samples_per_frame = 256
        frames_per_sec = fs / samples_per_frame  # 187.5 fps
        header_overhead_bytes_sec = frames_per_sec * 40  # 7,500 bytes/sec
        trailer_overhead_bytes_sec = frames_per_sec * 4  # 750 bytes/sec
        total_wire_rate_bps = int(frames_per_sec * (40 + 1024 + 4) * 8)

        assert total_wire_rate_bps == 1602000  # 1.602 Mbps
        overhead_percentage = ((1602000 - 1536000) / 1536000) * 100.0
        assert abs(overhead_percentage - 4.296875) < 1e-4  # 4.30% framing overhead
