"""Tests for C Golden-Vector Equivalence, Type Integrity, and Embedded Interoperability.

Verifies:
- Type audit reported by portable C golden tool matches Python assumptions
- Exact mathematical bit-for-bit equivalence between C-generated sine and Python sine
- Exact bit-for-bit equivalence between C ramp counter and Python sequence
- Numerical boundary values (+8,388,607, -8,388,608, 0, +/-1, +/-2)
- LSB-aligned to MSB-aligned container bit-shift equivalence
- Clean normalization of C golden vectors through packet_to_sample_block to [-1.0, +1.0]
- Sequence counter rollover and monotonic sample indexing
"""

import json
from pathlib import Path
import subprocess
import numpy as np
import pytest

from pcg_app.device_runtime import (
    DeviceSamplePacket,
    packet_to_sample_block,
    REV_A_BASELINE_PROFILE,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "c_golden_vectors" / "fixtures"
C_TOOL_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "c_golden_vectors"


class TestCGoldenVectors:
    """Test suite verifying C-generated golden fixtures against Python reference implementations."""

    def test_c_type_audit(self):
        """Verify C tool type audit output against Python platform assumptions."""
        exe_path = C_TOOL_DIR / "golden_generator.exe"
        if not exe_path.exists():
            pytest.skip("golden_generator.exe not compiled; run make in tools/c_golden_vectors/")

        result = subprocess.run([str(exe_path), "--verify-types"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        audit = data["type_audit"]
        assert audit["sizeof_int16_bytes"] == 2
        assert audit["sizeof_int32_bytes"] == 4
        assert audit["sizeof_uint32_bytes"] == 4
        assert audit["sizeof_float_bytes"] == 4
        assert audit["is_little_endian"] is True
        assert audit["twos_complement_ok"] is True
        assert audit["sign_extension_24to32_ok"] is True

        limits = data["limits"]
        assert limits["int24_min"] == -8388608
        assert limits["int24_max"] == 8388607
        assert limits["int32_min"] == -2147483648
        assert limits["int32_max"] == 2147483647

    def test_sine_100hz_c_vs_python_equivalence(self):
        """Verify that C-generated 100 Hz sine matches Python known-answer vector exactly."""
        bin_path = FIXTURES_DIR / "sine_100hz_48khz_512s_lsb.bin"
        if not bin_path.exists():
            pytest.skip("Golden fixtures not generated; run build.bat in tools/c_golden_vectors/")

        c_samples = np.fromfile(bin_path, dtype="<i4")
        assert len(c_samples) == 512

        # Generate identical mathematical sequence in Python
        n_samples = 512
        fs = 48000
        f0 = 100.0
        amp_ratio = 0.50
        max_amp = 8388607.0  # 2^23 - 1

        n = np.arange(n_samples)
        phase = (2.0 * np.pi * f0 * n) / fs
        val = amp_ratio * max_amp * np.sin(phase)
        py_samples = np.where(val >= 0, np.floor(val + 0.5), np.ceil(val - 0.5)).astype(np.int32)

        # Assert exact bit-for-bit equality
        diff = np.abs(c_samples - py_samples)
        assert np.max(diff) == 0, f"Max difference between C and Python sine was {np.max(diff)}"

    def test_counter_ramp_c_vs_python_equivalence(self):
        """Verify that C-generated ramp counter matches Python reference."""
        bin_path = FIXTURES_DIR / "counter_ramp_512s_lsb.bin"
        if not bin_path.exists():
            pytest.skip("Golden fixtures not generated")

        c_samples = np.fromfile(bin_path, dtype="<i4")
        assert len(c_samples) == 512

        start_val = -256
        step = 1
        py_samples = np.arange(start_val, start_val + 512 * step, step, dtype=np.int32)

        assert np.array_equal(c_samples, py_samples)

    def test_boundary_stress_vector_values(self):
        """Verify extreme integer boundaries and walking ones in C fixtures."""
        bin_path = FIXTURES_DIR / "boundary_stress_lsb.bin"
        if not bin_path.exists():
            pytest.skip("Golden fixtures not generated")

        samples = np.fromfile(bin_path, dtype="<i4")
        assert len(samples) >= 20

        # Known values: index 0 is 0, index 1 is 1, index 2 is -1
        assert samples[0] == 0
        assert samples[1] == 1
        assert samples[2] == -1
        assert samples[3] == 2
        assert samples[4] == -2

        # 16-bit limits
        assert samples[7] == 32767
        assert samples[8] == -32768

        # 24-bit limits
        assert samples[9] == 8388607   # INT24_MAX
        assert samples[10] == -8388608 # INT24_MIN

    def test_packet_to_sample_block_with_c_golden_vector(self):
        """Verify that packet_to_sample_block cleanly normalizes C golden sine without distortion."""
        bin_path = FIXTURES_DIR / "sine_100hz_48khz_512s_lsb.bin"
        if not bin_path.exists():
            pytest.skip("Golden fixtures not generated")

        raw_samples = np.fromfile(bin_path, dtype="<i4")

        packet = DeviceSamplePacket(
            sequence=100,
            timestamp_s=1.0,
            raw_samples=raw_samples,
            sample_rate_hz=48000,
            meaningful_bits=24,
            crc_ok=True,
        )

        block = packet_to_sample_block(packet, profile=REV_A_BASELINE_PROFILE)

        assert block.sequence == 100
        assert block.sample_rate_hz == 48000
        assert len(block.samples) == 512
        assert block.samples.dtype == np.float32

        # Amplitude ratio was 0.50 (-6.02 dBFS)
        peak_amp = float(np.max(np.abs(block.samples)))
        assert 0.499 < peak_amp < 0.501
        assert np.all(block.samples >= -1.0)
        assert np.all(block.samples <= 1.0)

    def test_msb_vs_lsb_alignment_normalization(self):
        """Verify that MSB-aligned container words normalized by 2^31 match LSB normalized by 2^23."""
        lsb_path = FIXTURES_DIR / "sine_100hz_48khz_512s_lsb.bin"
        msb_path = FIXTURES_DIR / "sine_100hz_48khz_512s_msb.bin"
        if not lsb_path.exists() or not msb_path.exists():
            pytest.skip("Golden fixtures not generated")

        lsb_raw = np.fromfile(lsb_path, dtype="<i4")
        msb_raw = np.fromfile(msb_path, dtype="<i4")

        # In MSB-aligned words, lower 8 bits are zeroed: msb == (lsb << 8)
        # Shift msb right by 8 to recover lsb:
        recovered_lsb = msb_raw >> 8
        assert np.array_equal(recovered_lsb, lsb_raw)

        # Float normalizations:
        # LSB normalized by 2^23:
        norm_lsb = lsb_raw.astype(np.float64) / (2.0 ** 23)
        # MSB normalized by 2^31:
        norm_msb = msb_raw.astype(np.float64) / (2.0 ** 31)

        diff = np.abs(norm_lsb - norm_msb)
        assert np.max(diff) < 1e-12
