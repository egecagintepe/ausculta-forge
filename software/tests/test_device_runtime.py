"""Tests for AuscultaForge Device Runtime Foundation & Physical Transport Readiness.

Verifies:
- Explicit device lifecycle state machine transitions and invalid transition rejection
- Semantic DeviceCapabilities validation and handshake compatibility rejection
- Semantic DeviceSamplePacket to SampleBlock conversion
- Runtime integrity telemetry counters (sequence gaps, duplicates, regressions, CRC failures)
- Hardware disconnect while streaming (transition to INTERRUPTED)
- Hardware disconnect during recording (safe finalization with termination_reason='device_disconnected')
- Reconnect lifecycle accounting
- Bounded device event history
- In-memory test double transport and discovery providers
"""

from pathlib import Path
import numpy as np
import pytest

from pcg_core.models import SampleBlock
from pcg_app.device_runtime import (
    DeviceState,
    DeviceRuntime,
    DeviceCapabilities,
    DeviceSamplePacket,
    DeviceIntegrityStats,
    DeviceEventLog,
    DeviceCandidate,
    DeviceDiscoveryProvider,
    DeviceTransport,
    InvalidStateTransitionError,
    packet_to_sample_block,
    PendingDescriptorDiscoveryProvider,
)
from pcg_app.state import StreamManager


# ==============================================================================
# Test Doubles (Explicitly Marked Test-Only)
# ==============================================================================

class InMemoryFakeTransport:
    """Test-only in-memory physical transport double."""

    def __init__(self, should_fail_open: bool = False) -> None:
        self.should_fail_open = should_fail_open
        self._connected: bool = False
        self.incoming_buffer: bytearray = bytearray()
        self.control_writes: list[bytes] = []

    def open(self) -> bool:
        if self.should_fail_open:
            return False
        self._connected = True
        return True

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read(self, max_bytes: int = 4096, timeout_s: float = 0.1) -> bytes:
        data = bytes(self.incoming_buffer[:max_bytes])
        del self.incoming_buffer[:max_bytes]
        return data

    def write_control(self, data: bytes) -> int:
        self.control_writes.append(data)
        return len(data)


class FakeDiscoveryProvider(DeviceDiscoveryProvider):
    """Test-only discovery provider reporting simulated candidates."""

    def __init__(self, candidates: list[DeviceCandidate]) -> None:
        self._candidates = candidates

    def poll_candidates(self) -> list[DeviceCandidate]:
        return list(self._candidates)

    def get_status_description(self) -> str:
        return f"Test discovery provider ({len(self._candidates)} attached)"


# ==============================================================================
# Lifecycle State Machine Tests
# ==============================================================================

class TestDeviceLifecycle:
    """Unit tests for the physical device state machine."""

    def test_initial_state_is_absent(self):
        runtime = DeviceRuntime()
        assert runtime.state == DeviceState.ABSENT
        st = runtime.get_state_dict()
        assert st["state"] == "absent"
        assert st["connected"] is False
        assert st["device_id"] is None
        assert st["firmware_version"] is None

    def test_full_valid_handshake_and_streaming_lifecycle(self):
        runtime = DeviceRuntime()
        candidate = DeviceCandidate(
            device_id="ESP32S3-DEV-001",
            descriptor="USB VID:PID test",
            detected_at_utc="2026-09-26T12:00:00Z",
        )

        # 1. ABSENT -> DETECTED
        runtime.attach_candidate(candidate)
        assert runtime.state == DeviceState.DETECTED

        # 2. DETECTED -> OPENING -> HANDSHAKING
        transport = InMemoryFakeTransport()
        runtime.attach_transport(transport)
        assert runtime.state == DeviceState.HANDSHAKING

        # 3. HANDSHAKING -> READY
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v0.1.0-alpha",
            device_id="ESP32S3-DEV-001",
            sample_rate_hz=4000,
            sample_format="float32",
            channels=1,
            max_block_size=128,
        )
        runtime.complete_handshake(caps)
        assert runtime.state == DeviceState.READY
        assert runtime.get_state_dict()["connected"] is True
        assert runtime.get_state_dict()["device_id"] == "ESP32S3-DEV-001"

        # 4. READY -> STREAMING
        runtime.start_streaming()
        assert runtime.state == DeviceState.STREAMING

        # 5. STREAMING -> READY
        runtime.stop_streaming()
        assert runtime.state == DeviceState.READY

        # 6. READY -> ABSENT (unplugged)
        runtime.handle_disconnect()
        assert runtime.state == DeviceState.ABSENT
        assert runtime.get_state_dict()["connected"] is False

    def test_invalid_state_transitions_rejected(self):
        runtime = DeviceRuntime()

        # Cannot stream directly from ABSENT
        with pytest.raises(InvalidStateTransitionError):
            runtime.transition_to(DeviceState.STREAMING)

        # Cannot complete handshake directly from ABSENT
        with pytest.raises(InvalidStateTransitionError):
            runtime.transition_to(DeviceState.READY)

        # Candidate arrives
        runtime.attach_candidate(DeviceCandidate("ID1", "Desc", "now"))
        assert runtime.state == DeviceState.DETECTED

        # Cannot jump from DETECTED directly to STREAMING
        with pytest.raises(InvalidStateTransitionError):
            runtime.transition_to(DeviceState.STREAMING)

    def test_transport_open_failure_transitions_to_error(self):
        runtime = DeviceRuntime()
        candidate = DeviceCandidate("ID1", "Desc", "now")
        runtime.attach_candidate(candidate)

        failing_transport = InMemoryFakeTransport(should_fail_open=True)
        with pytest.raises(RuntimeError):
            runtime.attach_transport(failing_transport)

        assert runtime.state == DeviceState.ERROR
        assert "Failed to open transport" in str(runtime.get_state_dict()["last_error"])

        # Resetting from ERROR to ABSENT is permitted
        runtime.handle_disconnect()
        assert runtime.state == DeviceState.ABSENT


# ==============================================================================
# Capabilities & Incompatibility Tests
# ==============================================================================

class TestDeviceCapabilities:
    """Tests capability validation rules for Phase-1."""

    def test_valid_capabilities_pass(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_OK",
            sample_rate_hz=4000,
            sample_format="float32",
            channels=1,
        )
        caps.validate()  # Should not raise

    def test_incompatible_protocol_version_rejected(self):
        caps = DeviceCapabilities(
            protocol_version="2.0",
            firmware_version="v1.0",
            device_id="DEV_BAD_PROTO",
            sample_rate_hz=4000,
        )
        with pytest.raises(ValueError, match="Unsupported protocol version"):
            caps.validate()

    def test_incompatible_sample_rate_rejected(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_BAD_RATE",
            sample_rate_hz=44100,  # Audio CD rate unsupported on Phase-1 PCG
        )
        with pytest.raises(ValueError, match="Unsupported sample rate"):
            caps.validate()

    def test_stereo_channel_rejected_for_phase1(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_STEREO",
            channels=2,
        )
        with pytest.raises(ValueError, match="Phase-1 requires mono"):
            caps.validate()

    def test_incompatible_handshake_transitions_device_to_incompatible_state(self):
        runtime = DeviceRuntime()
        runtime.attach_candidate(DeviceCandidate("BAD_DEVICE", "Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())
        assert runtime.state == DeviceState.HANDSHAKING

        bad_caps = DeviceCapabilities(
            protocol_version="9.9",
            firmware_version="v0",
            device_id="BAD_DEVICE",
        )
        with pytest.raises(ValueError):
            runtime.complete_handshake(bad_caps)

        assert runtime.state == DeviceState.INCOMPATIBLE
        assert "Device rejected during handshake" in str(runtime.get_state_dict()["last_error"])


# ==============================================================================
# Packet Framing & Integrity Telemetry Tests
# ==============================================================================

class TestPacketFramingAndIntegrity:
    """Tests semantic packet conversion and runtime telemetry accounting."""

    def test_packet_to_sample_block_conversion(self):
        samples = np.array([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
        packet = DeviceSamplePacket(
            sequence=42,
            timestamp_s=1.05,
            samples=samples,
            flags=0,
            crc_ok=True,
        )

        block = packet_to_sample_block(packet, sample_rate_hz=4000)
        assert isinstance(block, SampleBlock)
        assert block.sequence == 42
        assert block.timestamp_s == 1.05
        assert block.sample_rate_hz == 4000
        np.testing.assert_allclose(block.samples, samples)

    def test_packet_with_crc_failure_rejected_by_adapter(self):
        packet = DeviceSamplePacket(
            sequence=10,
            timestamp_s=0.5,
            samples=np.zeros(4, dtype=np.float32),
            crc_ok=False,
        )
        with pytest.raises(ValueError, match="CRC failure"):
            packet_to_sample_block(packet, sample_rate_hz=4000)

    def test_integrity_stats_tracking(self):
        stats = DeviceIntegrityStats()

        # In-order packets
        p0 = DeviceSamplePacket(0, 0.0, np.ones(10, dtype=np.float32))
        p1 = DeviceSamplePacket(1, 0.01, np.ones(10, dtype=np.float32))
        stats.record_packet(p0)
        stats.record_packet(p1)
        assert stats.packets_received == 2
        assert stats.samples_received == 20
        assert stats.sequence_gaps == 0
        assert stats.repeated_packets == 0

        # Repeated packet
        stats.record_packet(p1)
        assert stats.repeated_packets == 1

        # Gap (skipped sequence 2, 3 -> received 4)
        p4 = DeviceSamplePacket(4, 0.04, np.ones(10, dtype=np.float32))
        stats.record_packet(p4)
        assert stats.sequence_gaps == 2

        # Out-of-order packet (sequence 3 received after 4)
        p3 = DeviceSamplePacket(3, 0.03, np.ones(10, dtype=np.float32))
        stats.record_packet(p3)
        assert stats.out_of_order_packets == 1

        # CRC failure
        bad_crc = DeviceSamplePacket(5, 0.05, np.ones(10, dtype=np.float32), crc_ok=False)
        stats.record_packet(bad_crc)
        assert stats.crc_failures == 1


# ==============================================================================
# Disconnect, Interruption & Recording Abort Tests
# ==============================================================================

class TestDisconnectAndRecordingHandling:
    """Verifies disconnect handling while streaming and recording."""

    def test_disconnect_while_streaming_becomes_interrupted(self):
        runtime = DeviceRuntime()
        runtime.attach_candidate(DeviceCandidate("ESP1", "Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(
            DeviceCapabilities("1.0", "v1.0", "ESP1", sample_rate_hz=4000)
        )
        runtime.start_streaming()
        assert runtime.state == DeviceState.STREAMING

        # Physical disconnect occurs
        runtime.handle_disconnect("USB cord unplugged")
        assert runtime.state == DeviceState.INTERRUPTED
        assert runtime.stats.disconnect_count == 1

        # Re-attach and re-handshake
        runtime.attach_candidate(DeviceCandidate("ESP1", "Desc", "now_reconnect"))
        assert runtime.state == DeviceState.DETECTED
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(
            DeviceCapabilities("1.0", "v1.0", "ESP1", sample_rate_hz=4000)
        )
        assert runtime.state == DeviceState.READY
        assert runtime.stats.reconnect_count == 1

    def test_disconnect_during_recording_finalizes_with_device_disconnected_reason(self, tmp_path: Path):
        runtime = DeviceRuntime()
        manager = StreamManager(sessions_dir=tmp_path, device_runtime=runtime)

        # Prepare device into READY
        runtime.attach_candidate(DeviceCandidate("ESP1", "Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(DeviceCapabilities("1.0", "v1.0", "ESP1", 4000))

        # Select hardware as active source
        manager.select_source("hardware")
        assert manager.is_streaming is True
        assert manager.source_type == "hardware"

        # Start recording
        sid = manager.start_recording()
        assert manager.recorder.is_recording is True

        # Record at least one block so session has samples
        block = SampleBlock(0, 0.0, 4000, np.ones(128, dtype=np.float32))
        manager.recorder.record_block(block)

        # Physical disconnect happens during recording
        manager.handle_device_disconnect("USB unplugged mid-recording")

        # Recording must be aborted/finalized cleanly, not left dangling
        assert manager.recorder.is_recording is False
        assert manager.is_streaming is False
        assert manager.source_type == "none"

        # Check saved session metadata sidecar
        from pcg_core.recording import get_session
        meta_dict = get_session(sid, tmp_path)
        assert meta_dict is not None
        assert meta_dict["termination_reason"] == "device_disconnected"
        assert meta_dict["acquisition_mode"] == "hardware"
        assert meta_dict["device_info"] is not None

    def test_reconnect_lifecycle_after_interruption(self):
        """Verifies Phase-9 reconnect behavior:
        STREAMING -> INTERRUPTED -> DETECTED -> HANDSHAKING -> READY -> STREAMING.
        """
        runtime = DeviceRuntime()
        candidate = DeviceCandidate("ESP1", "Desc", "now")
        runtime.attach_candidate(candidate)
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(DeviceCapabilities("1.0", "v1.0", "ESP1", 4000))
        runtime.start_streaming()
        assert runtime.state == DeviceState.STREAMING

        # Physical link drops
        runtime.handle_disconnect("Cable dislodged")
        assert runtime.state == DeviceState.INTERRUPTED
        assert runtime.stats.disconnect_count == 1

        # Same device candidate reappears
        runtime.attach_candidate(candidate)
        assert runtime.state == DeviceState.DETECTED

        # Re-attach transport & handshake
        runtime.attach_transport(InMemoryFakeTransport())
        assert runtime.state == DeviceState.HANDSHAKING

        runtime.complete_handshake(DeviceCapabilities("1.0", "v1.0", "ESP1", 4000))
        assert runtime.state == DeviceState.READY
        assert runtime.stats.reconnect_count == 1

        # Resumes streaming on explicit user request
        runtime.start_streaming()
        assert runtime.state == DeviceState.STREAMING


# ==============================================================================
# Event Log Bounded History Tests
# ==============================================================================

class TestDeviceEventLog:
    """Verifies structured audit trail logging."""

    def test_event_log_records_and_bounds_entries(self):
        log = DeviceEventLog(max_entries=5)
        for i in range(10):
            log.log(f"CODE_{i}", f"Message {i}", severity="info")

        recent = log.get_recent(limit=10)
        assert len(recent) == 5
        # The oldest entries should have rotated out
        assert recent[-1]["code"] == "CODE_9"
        assert recent[0]["code"] == "CODE_5"
