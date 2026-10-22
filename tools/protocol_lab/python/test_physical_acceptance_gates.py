"""AuscultaForge — Strict Physical Acceptance & Negative Fault Injection Tests (Gate 6).

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

MISSION:
Verify that the physical G1 acceptance flow implemented in verify_g1_bringup.py
strictly rejects any defect, timeout, configuration error, corruption, or counter discrepancy.
Tests all 17 negative failure modes + positive simulated transport test.
"""

from pathlib import Path
import sys
import time
import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_B_DIR = SCRIPT_DIR.parent / "module_b_package"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(MODULE_B_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_B_DIR))

from simulated_device import SimulatedEsp32Device
from usb_adapter import DuplexLoopbackAdapter, BaseTransportAdapter, TransportState
from verify_g1_bringup import execute_physical_g1_protocol


class DisconnectingLoopbackAdapter(DuplexLoopbackAdapter):
    """Adapter that simulates transport disconnect after N frames."""

    def __init__(self, device: SimulatedEsp32Device, disconnect_after_reads: int = 5) -> None:
        super().__init__(device=device)
        self.disconnect_after_reads = disconnect_after_reads
        self.reads_count = 0

    def read(self, max_bytes: int = 1024) -> bytes:
        self.reads_count += 1
        if self.reads_count > self.disconnect_after_reads:
            self.device.disconnect()
            self.state = TransportState.DISCONNECTED
            return b""
        return super().read(max_bytes)


class TestPhysicalAcceptanceGates:
    """Rigorous acceptance gate tests verifying that all defects result in FAIL."""

    def test_positive_simulated_transport_acceptance(self):
        """Positive test: 100% clean loopback must PASS simulated transport gates."""
        device = SimulatedEsp32Device(initial_session_id=0xCAFE000000000001)
        transport = DuplexLoopbackAdapter(device=device, max_chunk_size=2048)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport,
            duration_s=10.0,
            is_physical=False,
            handshake_timeout_s=1.0,
        )
        transport.close()

        assert passed is True
        assert verdict == "SOFTWARE_SIMULATION_PASS"
        assert metrics["host_samples_accepted"] == 480000
        assert metrics["host_frames_accepted"] == 1875
        assert metrics["sample_value_errors"] == 0
        assert metrics["crc_corrupted_frames"] == 0
        assert metrics["sequence_gaps"] == 0
        assert metrics["duplicate_frames"] == 0
        assert metrics["active_session_id"] == hex(0xCAFE000000000002)

    def test_negative_1_missing_hello_ack(self):
        """Negative Gate 1: Missing HELLO_ACK must fail."""
        device = SimulatedEsp32Device()
        device.missing_hello_ack = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert any("HELLO_ACK" in r for r in metrics["failure_reasons"])

    def test_negative_2_wrong_nonce(self):
        """Negative Gate 2: Nonce mismatch in HELLO_ACK must fail."""
        device = SimulatedEsp32Device()
        device.corrupt_nonce = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert any("ERROR" in r or "nonce" in r for r in metrics["failure_reasons"])

    def test_negative_3_start_rejection(self):
        """Negative Gate 3: Device rejects START_REQ with ERROR packet."""
        device = SimulatedEsp32Device()
        device.reject_config = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert any("START" in r or "ERROR" in r for r in metrics["failure_reasons"])

    def test_negative_4_wrong_accepted_encoding(self):
        """Negative Gate 4: START_ACK specifies wrong encoding."""
        device = SimulatedEsp32Device()
        device.wrong_start_encoding = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_5_zero_session_id(self):
        """Negative Gate 5: START_ACK returns invalid session_id = 0."""
        device = SimulatedEsp32Device()
        device.zero_session_id = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_6_stale_session_id(self):
        """Negative Gate 6: Device fails or returns error due to stale session ID on STOP."""
        device = SimulatedEsp32Device()
        device.stale_session_id = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_7_corrupted_audio_frame_crc(self):
        """Negative Gate 7: Frame 100 has corrupted CRC-32."""
        device = SimulatedEsp32Device()
        device.corrupt_crc_frames.add(100)
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert metrics["crc_corrupted_frames"] > 0

    def test_negative_8_dropped_frame(self):
        """Negative Gate 8: Frame 200 is dropped by transmitter."""
        device = SimulatedEsp32Device()
        device.drop_frames.add(200)
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert metrics["sequence_gaps"] > 0 or metrics["index_discontinuities"] > 0

    def test_negative_9_duplicated_frame(self):
        """Negative Gate 9: Frame 300 is duplicated by transport."""
        device = SimulatedEsp32Device()
        device.duplicate_frames.add(300)
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert metrics["duplicate_frames"] > 0

    def test_negative_10_incorrect_deterministic_sample(self):
        """Negative Gate 10: Deterministic sample at index 2561 is corrupted."""
        device = SimulatedEsp32Device()
        device.corrupt_sample_indices.add(2561)
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert metrics["sample_value_errors"] > 0

    def test_negative_11_partial_samples_cap(self):
        """Negative Gate 11: Exactly 479,999 received samples (one sample short)."""
        device = SimulatedEsp32Device()
        device.cap_samples = 479999
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2, streaming_inactivity_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert metrics["host_samples_accepted"] != 480000

    def test_negative_12_missing_stop_ack(self):
        """Negative Gate 12: Device does not reply to STOP_REQ."""
        device = SimulatedEsp32Device()
        device.missing_stop_ack = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert not metrics["stop_ack_received"]

    def test_negative_13_wrong_stop_session_id(self):
        """Negative Gate 13: STOP_ACK contains mismatched session_id."""
        device = SimulatedEsp32Device()
        device.wrong_stop_session_id = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_14_falsified_mcu_counters(self):
        """Negative Gate 14: Telemetry counters claim generated_samples = 480001."""
        device = SimulatedEsp32Device()
        device.falsify_telemetry = {"generated_samples": 480001}
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_15_nonzero_dropped_samples(self):
        """Negative Gate 15: Telemetry reports dropped_samples = 256."""
        device = SimulatedEsp32Device()
        device.falsify_telemetry = {"dropped_samples": 256}
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_16_unexpected_disconnect(self):
        """Negative Gate 16: Transport disconnects during streaming."""
        device = SimulatedEsp32Device()
        transport = DisconnectingLoopbackAdapter(device=device, disconnect_after_reads=10)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2, streaming_inactivity_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"

    def test_negative_17_stalled_streaming_timeout(self):
        """Negative Gate 17: Streaming stalls mid-run, triggering inactivity timeout."""
        device = SimulatedEsp32Device()
        device.stall_streaming = True
        transport = DuplexLoopbackAdapter(device=device)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport, duration_s=10.0, is_physical=True, handshake_timeout_s=0.2, streaming_inactivity_timeout_s=0.1
        )
        transport.close()

        assert passed is False
        assert verdict == "PHYSICAL_G1_FAIL"
        assert any("inactivity timeout" in r for r in metrics["failure_reasons"])

    def test_partial_reads_and_defragmentation(self):
        """Test stream defragmentation over small partial reads (e.g. 17-byte chunks)."""
        device = SimulatedEsp32Device(initial_session_id=0x1234567890ABCDEF)
        # Force very small read chunks to heavily stress defragmentation
        transport = DuplexLoopbackAdapter(device=device, max_chunk_size=17)
        transport.open()

        passed, verdict, metrics = execute_physical_g1_protocol(
            transport,
            duration_s=10.0,
            is_physical=False,
            handshake_timeout_s=1.0,
        )
        transport.close()

        assert passed is True
        assert verdict == "SOFTWARE_SIMULATION_PASS"
        assert metrics["host_samples_accepted"] == 480000
        assert metrics["host_frames_accepted"] == 1875
        assert metrics["sample_value_errors"] == 0
        assert metrics["crc_corrupted_frames"] == 0
