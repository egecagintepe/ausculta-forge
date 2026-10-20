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
)
from protocol_validator import ProtocolValidator

C_DIR = Path(__file__).resolve().parent.parent / "c"
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

    def test_c_executable_to_python_decoder_parity(self):
        """Execute compiled C runner and verify byte-level deserialization parity."""
        if not RUNNER_EXE.exists():
            pytest.skip("g1_sim_runner.exe not compiled")

        cmd = [str(RUNNER_EXE), "--mode=stream", "--signal=ramp", "--seconds=0.1", "--profile=b"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        raw_output = res.stdout

        decoder = StreamingProtocolDecoder()
        packets = decoder.feed_bytes(raw_output)

        # 0.1s at 48 kHz = 4800 samples = 18.75 -> 18 frames of 256 samples (4608 samples)
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
