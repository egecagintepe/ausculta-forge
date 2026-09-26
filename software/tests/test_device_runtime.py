"""Tests for AuscultaForge Device Runtime Foundation & Physical Transport Readiness.

Verifies:
- Explicit device lifecycle state machine transitions and invalid transition rejection
- Centralized AcquisitionProfile configuration model (Rev-A 48 kHz mono signed PCM baseline)
- Semantic DeviceCapabilities validation against active acquisition profiles
- Explicit successful 48 kHz mono capability handshake
- Rejection of incompatible protocol versions, channels, formats, and rate mismatches
- Semantic DeviceSamplePacket raw sample preservation and SampleBlock conversion:
  - Zero maps to 0.0
  - Positive and negative full-scale normalization for 24-bit data words in wider containers
  - No silent overflow or integer wraparound
  - 48 kHz sample rate and timestamp metadata preservation
- Runtime integrity telemetry counters (packets, samples, gaps, duplicates, regressions, CRC failures, malformed frames)
- Hardware disconnect while streaming (transition to INTERRUPTED)
- Hardware disconnect during recording (safe finalization with termination_reason='device_disconnected')
- Reconnect lifecycle accounting (INTERRUPTED -> DETECTED -> OPENING -> HANDSHAKING -> READY)
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
    AcquisitionProfile,
    REV_A_BASELINE_PROFILE,
    DEV_LEGACY_PROFILE,
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
        assert "acquisition_profile" in st
        assert st["acquisition_profile"]["preferred_sample_rate_hz"] == 48000

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

        # 3. HANDSHAKING -> READY (validating Rev-A 48 kHz mono capabilities)
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v0.1.0-alpha",
            device_id="ESP32S3-DEV-001",
            sample_rate_hz=48000,
            sample_format="signed_pcm",
            channels=1,
            max_block_size=512,
            sample_container_bits=32,
            meaningful_data_bits=24,
        )
        runtime.complete_handshake(caps)
        assert runtime.state == DeviceState.READY
        assert runtime.get_state_dict()["connected"] is True
        assert runtime.get_state_dict()["device_id"] == "ESP32S3-DEV-001"
        assert runtime.get_state_dict()["sample_rate_hz"] == 48000

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
# Acquisition Profile & Generalized Capabilities Tests
# ==============================================================================

class TestAcquisitionProfileAndCapabilities:
    """Tests capability validation against centralized acquisition profiles."""

    def test_rev_a_baseline_profile_definition(self):
        profile = REV_A_BASELINE_PROFILE
        assert profile.preferred_sample_rate_hz == 48000
        assert profile.channels == 1
        assert profile.sample_container_bits == 32
        assert profile.meaningful_data_bits == 24
        assert profile.sample_encoding == "signed_pcm"
        d = profile.to_dict()
        assert d["preferred_sample_rate_hz"] == 48000

    def test_successful_48khz_mono_handshake(self):
        runtime = DeviceRuntime(acquisition_profile=REV_A_BASELINE_PROFILE)
        runtime.attach_candidate(DeviceCandidate("REV_A_DEV", "USB Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())
        assert runtime.state == DeviceState.HANDSHAKING

        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0.0",
            device_id="REV_A_DEV",
            sample_rate_hz=48000,
            sample_format="signed_pcm",
            channels=1,
            sample_container_bits=32,
            meaningful_data_bits=24,
            max_block_size=512,
        )
        runtime.complete_handshake(caps)
        assert runtime.state == DeviceState.READY
        assert runtime.capabilities is not None
        assert runtime.capabilities.sample_rate_hz == 48000
        assert runtime.capabilities.meaningful_data_bits == 24

    def test_incompatible_protocol_version_rejected(self):
        caps = DeviceCapabilities(
            protocol_version="2.0",
            firmware_version="v1.0",
            device_id="DEV_BAD_PROTO",
            sample_rate_hz=48000,
        )
        with pytest.raises(ValueError, match="Unsupported protocol version"):
            caps.validate_compatibility(REV_A_BASELINE_PROFILE)

    def test_incompatible_sample_rate_rejected_against_profile(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_WRONG_RATE",
            sample_rate_hz=44100,  # Audio CD rate unsupported
        )
        with pytest.raises(ValueError, match="Sample rate mismatch"):
            caps.validate_compatibility(REV_A_BASELINE_PROFILE)

    def test_stereo_channel_rejected_when_mono_required(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_STEREO",
            sample_rate_hz=48000,
            channels=2,
        )
        with pytest.raises(ValueError, match="Channel count mismatch"):
            caps.validate_compatibility(REV_A_BASELINE_PROFILE)

    def test_invalid_bit_representation_rejected(self):
        caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="DEV_BAD_BITS",
            sample_rate_hz=48000,
            sample_container_bits=16,
            meaningful_data_bits=24,  # Meaningful bits cannot exceed container bits
        )
        with pytest.raises(ValueError, match="cannot exceed sample_container_bits"):
            caps.validate_compatibility(REV_A_BASELINE_PROFILE)

    def test_legacy_4khz_dev_profile_compatibility(self):
        # A dev-configured runtime can validate a 4 kHz test signal profile
        runtime = DeviceRuntime(acquisition_profile=DEV_LEGACY_PROFILE)
        runtime.attach_candidate(DeviceCandidate("LEGACY_DEV", "Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())

        legacy_caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v0.1",
            device_id="LEGACY_DEV",
            sample_rate_hz=4000,
            sample_format="signed_pcm",
            channels=1,
            sample_container_bits=16,
            meaningful_data_bits=16,
            max_block_size=128,
        )
        runtime.complete_handshake(legacy_caps)
        assert runtime.state == DeviceState.READY
        assert runtime.capabilities.sample_rate_hz == 4000

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
# Semantic Sample Representation & Adapter Tests
# ==============================================================================

class TestSemanticSampleRepresentation:
    """Verifies integer container sample preservation and normalized float adapter."""

    def test_packet_preserves_raw_integer_samples(self):
        raw_ints = np.array([0, 1000, -2000, 8388607], dtype=np.int32)
        packet = DeviceSamplePacket(
            sequence=1,
            timestamp_s=0.01,
            raw_samples=raw_ints,
            meaningful_bits=24,
            sample_rate_hz=48000,
        )
        # Raw integers must NOT be silently converted to float32 inside DeviceSamplePacket
        assert packet.raw_samples.dtype == np.int32
        assert np.array_equal(packet.raw_samples, raw_ints)
        assert packet.samples.dtype == np.int32

    def test_zero_maps_to_zero(self):
        raw_zero = np.array([0, 0, 0], dtype=np.int32)
        packet = DeviceSamplePacket(
            sequence=1,
            timestamp_s=0.0,
            raw_samples=raw_zero,
            meaningful_bits=24,
            sample_rate_hz=48000,
        )
        block = packet_to_sample_block(packet)
        assert block.samples.dtype == np.float32
        np.testing.assert_allclose(block.samples, [0.0, 0.0, 0.0], atol=1e-7)

    def test_positive_and_negative_full_scale_normalization_24bit(self):
        # 24-bit signed PCM in 32-bit container:
        # Full scale negative: -2^(24-1) = -8,388,608 -> -1.0
        # Full scale positive: +2^(24-1) - 1 = +8,388,607 -> ~ +0.99999988
        neg_full = -(1 << 23)        # -8388608
        pos_full = (1 << 23) - 1      # +8388607
        raw = np.array([neg_full, 0, pos_full], dtype=np.int32)

        packet = DeviceSamplePacket(
            sequence=2,
            timestamp_s=0.05,
            raw_samples=raw,
            meaningful_bits=24,
            sample_rate_hz=48000,
        )
        block = packet_to_sample_block(packet)

        assert block.samples[0] == -1.0
        assert block.samples[1] == 0.0
        assert pytest.approx(block.samples[2], rel=1e-5) == 1.0
        assert -1.0 <= block.samples[2] <= 1.0

    def test_normalization_16bit(self):
        # 16-bit signed PCM normalization check:
        # -32768 -> -1.0, 0 -> 0.0, +32767 -> ~ +1.0
        raw = np.array([-32768, 0, 32767], dtype=np.int16)
        packet = DeviceSamplePacket(
            sequence=3,
            timestamp_s=0.1,
            raw_samples=raw,
            meaningful_bits=16,
            sample_rate_hz=4000,
        )
        block = packet_to_sample_block(packet)
        assert block.samples[0] == -1.0
        assert block.samples[1] == 0.0
        assert pytest.approx(block.samples[2], rel=1e-4) == 1.0

    def test_no_silent_overflow_or_wraparound(self):
        # Check boundary values do not wrap around
        raw = np.array([-8388608, 8388607], dtype=np.int32)
        packet = DeviceSamplePacket(
            sequence=4,
            timestamp_s=0.2,
            raw_samples=raw,
            meaningful_bits=24,
            sample_rate_hz=48000,
        )
        block = packet_to_sample_block(packet)
        assert not np.isnan(block.samples).any()
        assert not np.isinf(block.samples).any()
        assert block.samples[0] == -1.0
        assert block.samples[1] > 0.999

    def test_48khz_metadata_survives_conversion(self):
        raw = np.zeros(512, dtype=np.int32)
        packet = DeviceSamplePacket(
            sequence=99,
            timestamp_s=12.3456,
            raw_samples=raw,
            meaningful_bits=24,
            sample_rate_hz=48000,
        )
        block = packet_to_sample_block(packet)
        assert isinstance(block, SampleBlock)
        assert block.sequence == 99
        assert block.timestamp_s == 12.3456
        assert block.sample_rate_hz == 48000
        assert len(block.samples) == 512

    def test_packet_with_crc_failure_rejected_by_adapter(self):
        packet = DeviceSamplePacket(
            sequence=10,
            timestamp_s=0.5,
            raw_samples=np.zeros(4, dtype=np.int32),
            crc_ok=False,
        )
        with pytest.raises(ValueError, match="CRC failure"):
            packet_to_sample_block(packet)


# ==============================================================================
# Runtime Integrity Telemetry Tests
# ==============================================================================

class TestIntegrityTelemetry:
    """Tests runtime integrity telemetry counters without decorative items."""

    def test_integrity_stats_tracking(self):
        stats = DeviceIntegrityStats()

        # In-order packets
        p0 = DeviceSamplePacket(0, 0.0, np.ones(10, dtype=np.int32))
        p1 = DeviceSamplePacket(1, 0.01, np.ones(10, dtype=np.int32))
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
        p4 = DeviceSamplePacket(4, 0.04, np.ones(10, dtype=np.int32))
        stats.record_packet(p4)
        assert stats.sequence_gaps == 2

        # Out-of-order packet (sequence 3 received after 4, monotonic timestamp 0.05)
        p3 = DeviceSamplePacket(3, 0.05, np.ones(10, dtype=np.int32))
        stats.record_packet(p3)
        assert stats.out_of_order_packets == 1
        assert stats.timestamp_regressions == 0

        # Timestamp regression (sequence 5 with earlier timestamp 0.02 < 0.05)
        p_regr = DeviceSamplePacket(5, 0.02, np.ones(10, dtype=np.int32))
        stats.record_packet(p_regr)
        assert stats.timestamp_regressions == 1

        # CRC failure
        bad_crc = DeviceSamplePacket(6, 0.06, np.ones(10, dtype=np.int32), crc_ok=False)
        stats.record_packet(bad_crc)
        assert stats.crc_failures == 1

        # Malformed frame event
        stats.record_malformed_frame()
        assert stats.malformed_frames == 1

        # Output dict matches exact 10 required counters
        d = stats.to_dict()
        expected_keys = {
            "packets_received",
            "samples_received",
            "sequence_gaps",
            "repeated_packets",
            "out_of_order_packets",
            "crc_failures",
            "malformed_frames",
            "timestamp_regressions",
            "disconnect_count",
            "reconnect_count",
        }
        assert set(d.keys()) == expected_keys


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
            DeviceCapabilities("1.0", "v1.0", "ESP1", sample_rate_hz=48000)
        )
        runtime.start_streaming()
        assert runtime.state == DeviceState.STREAMING

        # Physical disconnect occurs
        runtime.handle_disconnect("USB cord unplugged")
        assert runtime.state == DeviceState.INTERRUPTED
        assert runtime.stats.disconnect_count == 1

        # Re-attach and re-handshake (INTERRUPTED -> DETECTED -> OPENING -> HANDSHAKING -> READY)
        runtime.attach_candidate(DeviceCandidate("ESP1", "Desc", "now_reconnect"))
        assert runtime.state == DeviceState.DETECTED
        runtime.attach_transport(InMemoryFakeTransport())
        assert runtime.state == DeviceState.HANDSHAKING
        runtime.complete_handshake(
            DeviceCapabilities("1.0", "v1.0", "ESP1", sample_rate_hz=48000)
        )
        assert runtime.state == DeviceState.READY
        assert runtime.stats.reconnect_count == 1

    def test_disconnect_during_recording_finalizes_with_device_disconnected_reason(self, tmp_path: Path):
        runtime = DeviceRuntime()
        manager = StreamManager(sessions_dir=tmp_path, device_runtime=runtime)

        # Prepare device into READY with 48 kHz Rev-A capabilities
        runtime.attach_candidate(DeviceCandidate("ESP1", "Desc", "now"))
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(
            DeviceCapabilities("1.0", "v1.0", "ESP1", sample_rate_hz=48000)
        )

        # Select hardware as active source
        manager.select_source("hardware")
        assert manager.is_streaming is True
        assert manager.source_type == "hardware"
        assert manager.sample_rate_hz == 48000

        # Start recording
        sid = manager.start_recording()
        assert manager.recorder.is_recording is True

        # Record at least one 48 kHz block
        block = SampleBlock(0, 0.0, 48000, np.ones(512, dtype=np.float32))
        manager.recorder.record_block(block)

        # Physical disconnect happens during recording
        manager.handle_device_disconnect("USB unplugged mid-recording")

        # Recording must be aborted/finalized cleanly
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
        """Verifies reconnect behavior:
        STREAMING -> INTERRUPTED -> DETECTED -> OPENING -> HANDSHAKING -> READY -> STREAMING.
        """
        runtime = DeviceRuntime()
        candidate = DeviceCandidate("ESP1", "Desc", "now")
        runtime.attach_candidate(candidate)
        runtime.attach_transport(InMemoryFakeTransport())
        runtime.complete_handshake(DeviceCapabilities("1.0", "v1.0", "ESP1", 48000))
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

        runtime.complete_handshake(DeviceCapabilities("1.0", "v1.0", "ESP1", 48000))
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
        # Oldest entries rotate out
        assert recent[-1]["code"] == "CODE_9"
        assert recent[0]["code"] == "CODE_5"
