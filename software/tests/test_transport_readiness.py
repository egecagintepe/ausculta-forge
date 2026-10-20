"""Tests for AuscultaForge Plug-and-Play Host Transport Readiness (Sprint 03).

Verifies:
1. Layered boundary separation:
   - Byte transport (DeviceTransport)
   - Packet framing and decoding (DevicePacketDecoder)
   - Sample normalization and range checking (packet_to_sample_block)
   - DSP and session dispatch (StreamManager)
2. Fragmented byte read reassembly (partial frames are never prematurely emitted)
3. Combined / concatenated frame unpacking in a single read
4. Preamble line noise / garbage recovery via sync magic seek
5. Application CRC-16 check and corrupted frame rejection
6. TransportSupervisor lifecycle:
   - Single-reader ownership enforcement (TransportConcurrentOwnershipError)
   - Clean background thread start, stop, and join without orphan threads or leaked handles
   - Graceful TimeoutError tolerance without thread crash
   - Explicit error propagation
7. Abrupt physical cable disconnect detection and safe session finalization (termination_reason='device_disconnected')
8. Reconnect recovery and clean buffer reset
9. Transport configuration models (CDC-ACM and Vendor Bulk) and PendingHardwareTransportFactory
10. PUI Rev-A reference profile preservation
"""

import asyncio
from pathlib import Path
import time
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
    DeviceTransport,
    DevicePacketDecoder,
    TransportSupervisor,
    InjectableTestTransport,
    ReferenceFramedPacketDecoder,
    ProposedProfileBPacketDecoder,
    build_test_frame,
    crc16_ccitt,
    TransportError,
    TransportTimeoutError,
    TransportDisconnectedError,
    TransportConcurrentOwnershipError,
    TransportType,
    CdcAcmTransportConfig,
    VendorBulkTransportConfig,
    TestTransportConfig,
    PendingHardwareTransportFactory,
    packet_to_sample_block,
    REV_A_BASELINE_PROFILE,
    DEV_LEGACY_PROFILE,
)
from pcg_app.state import StreamManager
from pcg_core.recording import get_session


# ==============================================================================
# 1. Decoupled Boundary Tests (Requirement 3)
# ==============================================================================

def test_layer1_byte_transport_boundary():
    """Verify Layer 1: raw byte acquisition from transport without parsing assumptions."""
    transport = InjectableTestTransport()
    assert transport.open() is True
    assert transport.is_connected() is True

    raw_payload = b"\x01\x02\x03\x04\x05\x06"
    transport.push_bytes(raw_payload)
    chunk = transport.read(max_bytes=4)
    assert chunk == b"\x01\x02\x03\x04"
    rem = transport.read(max_bytes=4)
    assert rem == b"\x05\x06"
    transport.close()
    assert transport.is_connected() is False


def test_layer2_packet_decoder_boundary():
    """Verify Layer 2: semantic packet decoding without float conversion or DSP dispatch."""
    samples = np.array([1000, -2000, 3000, -4000], dtype=np.int32)
    frame_bytes = build_test_frame(sequence=42, timestamp_us=123456, raw_samples=samples)

    decoder = ReferenceFramedPacketDecoder(meaningful_bits=24, sample_rate_hz=48000)
    packets = decoder.feed_bytes(frame_bytes)

    assert len(packets) == 1
    pkt = packets[0]
    assert pkt.sequence == 42
    assert abs(pkt.timestamp_s - 0.123456) < 1e-6
    assert pkt.crc_ok is True
    assert pkt.sample_rate_hz == 48000
    assert pkt.meaningful_bits == 24
    assert np.array_equal(pkt.raw_samples, samples)


def test_layer3_sample_normalization_boundary():
    """Verify Layer 3: integer bounds checking and [-1.0, 1.0] scaling into SampleBlock."""
    # Max legal 24-bit positive: 8,388,607
    # Min legal 24-bit negative: -8,388,608
    samples = np.array([0, 8388607, -8388608], dtype=np.int32)
    pkt = DeviceSamplePacket(sequence=1, timestamp_s=0.0, raw_samples=samples, meaningful_bits=24, sample_rate_hz=48000)

    block = packet_to_sample_block(pkt)
    assert isinstance(block, SampleBlock)
    assert block.sequence == 1
    assert block.sample_rate_hz == 48000
    assert abs(block.samples[0] - 0.0) < 1e-6
    assert abs(block.samples[1] - 1.0) < 1e-4
    assert abs(block.samples[2] - (-1.0)) < 1e-6

    # Test out-of-range integer sample rejection
    bad_samples = np.array([8388608], dtype=np.int32)  # Exceeds 24-bit signed max
    bad_pkt = DeviceSamplePacket(sequence=2, timestamp_s=0.1, raw_samples=bad_samples, meaningful_bits=24, sample_rate_hz=48000)
    with pytest.raises(ValueError, match="out of legal 24-bit signed range"):
        packet_to_sample_block(bad_pkt)


# ==============================================================================
# 2. Fragmented Reads & Combined Reads (Requirements 4 & 9)
# ==============================================================================

def test_fragmented_byte_reads_not_prematurely_emitted():
    """Verify fragmented reads are buffered and NEVER emitted prematurely as frames."""
    samples = np.arange(128, dtype=np.int32) * 50
    frame_bytes = build_test_frame(sequence=10, timestamp_us=50000, raw_samples=samples)
    total_len = len(frame_bytes)
    assert total_len == 16 + (128 * 4) + 2  # 530 bytes

    decoder = ReferenceFramedPacketDecoder(meaningful_bits=24, sample_rate_hz=48000)

    # 1. Feed partial header (10 bytes of 16-byte header)
    p1 = decoder.feed_bytes(frame_bytes[:10])
    assert p1 == []
    assert decoder.buffer_len == 10

    # 2. Feed remainder of header + partial payload (100 bytes)
    p2 = decoder.feed_bytes(frame_bytes[10:110])
    assert p2 == []
    assert decoder.buffer_len == 110

    # 3. Feed 1-byte at a time for 20 bytes
    for i in range(110, 130):
        p_byte = decoder.feed_bytes(frame_bytes[i : i + 1])
        assert p_byte == []

    # 4. Feed almost the entire remainder, leaving 1 byte of CRC missing
    p_almost = decoder.feed_bytes(frame_bytes[130 : total_len - 1])
    assert p_almost == []
    assert decoder.buffer_len == total_len - 1

    # 5. Feed the final byte: now and ONLY now does the frame emit!
    p_final = decoder.feed_bytes(frame_bytes[total_len - 1 :])
    assert len(p_final) == 1
    assert p_final[0].sequence == 10
    assert np.array_equal(p_final[0].raw_samples, samples)
    assert decoder.buffer_len == 0


def test_combined_concatenated_frames_in_single_read():
    """Verify multiple frames packed into a single chunk read are completely unpacked."""
    f1 = build_test_frame(sequence=1, timestamp_us=10000, raw_samples=np.array([1, 2, 3], dtype=np.int32))
    f2 = build_test_frame(sequence=2, timestamp_us=20000, raw_samples=np.array([4, 5, 6], dtype=np.int32))
    f3 = build_test_frame(sequence=3, timestamp_us=30000, raw_samples=np.array([7, 8, 9], dtype=np.int32))

    combined = f1 + f2 + f3
    decoder = ReferenceFramedPacketDecoder()
    packets = decoder.feed_bytes(combined)

    assert len(packets) == 3
    assert [p.sequence for p in packets] == [1, 2, 3]
    assert np.array_equal(packets[0].raw_samples, [1, 2, 3])
    assert np.array_equal(packets[1].raw_samples, [4, 5, 6])
    assert np.array_equal(packets[2].raw_samples, [7, 8, 9])
    assert decoder.buffer_len == 0


def test_preamble_garbage_noise_recovery():
    """Verify parser seeks sync magic, discards line noise, and extracts valid frame."""
    valid_frame = build_test_frame(sequence=99, timestamp_us=99000, raw_samples=np.array([10, 20], dtype=np.int32))
    noisy_wire = b"\xff\x00\x12\xaa\x44\x55GARBAGE_NOISE" + valid_frame

    decoder = ReferenceFramedPacketDecoder()
    packets = decoder.feed_bytes(noisy_wire)

    assert len(packets) == 1
    assert packets[0].sequence == 99
    assert np.array_equal(packets[0].raw_samples, [10, 20])


def test_corrupt_crc_frame_flagged():
    """Verify frame with invalid CRC is flagged with crc_ok=False."""
    bad_frame = build_test_frame(sequence=5, timestamp_us=5000, raw_samples=np.array([100], dtype=np.int32), corrupt_crc=True)
    decoder = ReferenceFramedPacketDecoder()
    packets = decoder.feed_bytes(bad_frame)

    assert len(packets) == 1
    assert packets[0].sequence == 5
    assert packets[0].crc_ok is False
    assert decoder.crc_failure_count == 1


# ==============================================================================
# 3. TransportSupervisor Lifecycle, Concurrency & Cleanup (Requirements 2, 5, 6)
# ==============================================================================

def test_supervisor_single_reader_ownership():
    """Verify supervisor strictly prohibits concurrent reader ownership."""
    transport = InjectableTestTransport()
    transport.open()
    decoder = ReferenceFramedPacketDecoder()
    supervisor = TransportSupervisor(transport, decoder)

    supervisor.start(on_packet=lambda p: None)
    assert supervisor.is_running is True

    # Attempt second concurrent start
    with pytest.raises(TransportConcurrentOwnershipError, match="Concurrent reader ownership is prohibited"):
        supervisor.start(on_packet=lambda p: None)

    supervisor.stop()
    assert supervisor.is_running is False


def test_supervisor_clean_stop_and_join():
    """Verify supervisor stops cleanly, joins thread within timeout, and closes transport."""
    transport = InjectableTestTransport()
    transport.open()
    decoder = ReferenceFramedPacketDecoder()
    supervisor = TransportSupervisor(transport, decoder)

    received_packets = []
    supervisor.start(on_packet=lambda p: received_packets.append(p))

    # Push 3 frames
    for seq in range(3):
        f = build_test_frame(sequence=seq, timestamp_us=seq * 10000, raw_samples=np.array([seq * 10], dtype=np.int32))
        transport.push_chunk(f)

    # Wait briefly for worker thread to process
    time.sleep(0.1)
    assert len(received_packets) == 3

    # Stop supervisor
    supervisor.stop(timeout_s=1.0)
    assert supervisor.is_running is False
    assert transport.is_connected() is False  # Handle closed cleanly


def test_supervisor_read_timeout_tolerance():
    """Verify read timeouts do not crash or stall the supervisor read loop."""
    transport = InjectableTestTransport()
    transport.open()
    decoder = ReferenceFramedPacketDecoder()
    supervisor = TransportSupervisor(transport, decoder, read_timeout_s=0.01)

    received = []
    supervisor.start(on_packet=lambda p: received.append(p))

    # Enable simulated timeout on transport
    transport.simulate_timeout(True)
    time.sleep(0.05)
    assert supervisor.is_running is True  # Still alive

    # Turn off timeout and push a frame
    transport.simulate_timeout(False)
    frame = build_test_frame(sequence=1, timestamp_us=1000, raw_samples=np.array([42], dtype=np.int32))
    transport.push_chunk(frame)

    time.sleep(0.05)
    assert len(received) == 1
    assert received[0].sequence == 1

    supervisor.stop()


def test_supervisor_error_callback_propagation():
    """Verify transport errors trigger on_error callback and cleanly terminate loop."""
    transport = InjectableTestTransport()
    transport.open()
    decoder = ReferenceFramedPacketDecoder()
    supervisor = TransportSupervisor(transport, decoder)

    caught_errors = []
    supervisor.start(
        on_packet=lambda p: None,
        on_error=lambda err: caught_errors.append(err),
    )

    transport.simulate_error(IOError("Simulated USB endpoint fault"))
    time.sleep(0.08)

    assert len(caught_errors) == 1
    assert "Simulated USB endpoint fault" in str(caught_errors[0])
    assert supervisor.is_running is False
    supervisor.stop()


# ==============================================================================
# 4. Disconnect & Reconnect Recovery with Session Finalization (Requirements 2, 6, 9)
# ==============================================================================

def test_abrupt_disconnect_finalizes_session_and_preserves_samples(tmp_path: Path):
    """Verify sudden cable disconnect triggers INTERRUPTED and finalizes session cleanly."""
    transport = InjectableTestTransport()
    decoder = ReferenceFramedPacketDecoder()
    runtime = DeviceRuntime()

    manager = StreamManager(sessions_dir=tmp_path / "sessions", device_runtime=runtime)

    candidate = DeviceCandidate(
        device_id="TEST-PROBE-01",
        descriptor="ESP32-S3 Test Probe",
        detected_at_utc="2026-10-17T00:00:00Z",
    )
    runtime.attach_candidate(candidate)
    runtime.attach_transport(transport)
    runtime.attach_decoder(decoder)

    caps = DeviceCapabilities(
        protocol_version="1.0",
        firmware_version="v0.1-test",
        device_id="TEST-PROBE-01",
        sample_rate_hz=48000,
        sample_format="signed_pcm",
        channels=1,
        max_block_size=512,
        sample_container_bits=32,
        meaningful_data_bits=24,
    )
    runtime.complete_handshake(caps)
    assert runtime.state == DeviceState.READY

    # Select hardware source (starts supervisor automatically)
    manager.select_source("hardware")
    assert manager.is_streaming is True
    assert runtime.state == DeviceState.STREAMING
    assert runtime.supervisor is not None
    assert runtime.supervisor.is_running is True

    # Start recording session
    session_id = manager.start_recording("Hardware Cable Pull Test")
    assert manager.recorder.is_recording is True

    # Stream 3 valid frames (128 samples each = 384 samples)
    for seq in range(3):
        samples = np.full(128, 5000, dtype=np.int32)
        f = build_test_frame(sequence=seq, timestamp_us=seq * 2666, raw_samples=samples)
        transport.push_chunk(f)

    time.sleep(0.1)
    assert manager.recorder.total_samples == 384

    # Simulate abrupt physical cable pull!
    transport.simulate_disconnect()
    for _ in range(10):
        if runtime.state == DeviceState.INTERRUPTED:
            break
        time.sleep(0.05)

    # Verify runtime state transitioned to INTERRUPTED
    assert runtime.state == DeviceState.INTERRUPTED
    assert manager.recorder.is_recording is False

    # Verify session was cleanly finalized with termination_reason='device_disconnected'
    sess_meta = get_session(session_id, sessions_dir=tmp_path / "sessions")
    assert sess_meta is not None
    assert sess_meta["termination_reason"] == "device_disconnected"
    assert sess_meta["total_samples"] == 384


def test_reconnect_recovery_lifecycle(tmp_path: Path):
    """Verify clean recovery after disconnect: re-attach, re-handshake, and clean state."""
    runtime = DeviceRuntime()
    manager = StreamManager(sessions_dir=tmp_path / "sessions", device_runtime=runtime)

    # 1. First connection
    t1 = InjectableTestTransport()
    d1 = ReferenceFramedPacketDecoder()
    cand1 = DeviceCandidate("DEV-01", "USB Candidate", "2026-10-17T00:00:00Z")
    runtime.attach_candidate(cand1)
    runtime.attach_transport(t1)
    runtime.attach_decoder(d1)
    runtime.complete_handshake(DeviceCapabilities("1.0", "v1", "DEV-01"))
    manager.select_source("hardware")

    # Cable pull
    t1.simulate_disconnect()
    time.sleep(0.08)
    assert runtime.state == DeviceState.INTERRUPTED
    assert runtime.stats.disconnect_count == 1

    # 2. Re-plug device (Reconnection Lifecycle)
    t2 = InjectableTestTransport()
    d2 = ReferenceFramedPacketDecoder()
    cand2 = DeviceCandidate("DEV-01", "USB Candidate (Re-plugged)", "2026-10-17T00:01:00Z")
    runtime.attach_candidate(cand2)
    assert runtime.state == DeviceState.DETECTED

    runtime.attach_transport(t2)
    assert runtime.state == DeviceState.HANDSHAKING

    runtime.attach_decoder(d2)
    runtime.complete_handshake(DeviceCapabilities("1.0", "v1", "DEV-01"))
    assert runtime.state == DeviceState.READY
    assert runtime.stats.reconnect_count == 1  # Reconnection accounting

    # Stream new session cleanly
    manager.select_source("hardware")
    assert runtime.state == DeviceState.STREAMING

    rec_id = manager.start_recording("Reconnected Stream")
    frame = build_test_frame(sequence=0, timestamp_us=0, raw_samples=np.full(64, 1000, dtype=np.int32))
    t2.push_chunk(frame)
    time.sleep(0.08)

    meta = manager.stop_recording(termination_reason="completed")
    assert meta.total_samples == 64
    assert meta.termination_reason == "completed"

    manager.stop_stream()
    assert runtime.state == DeviceState.READY


# ==============================================================================
# 5. Configuration Interfaces & Factory Validation (Requirement 7)
# ==============================================================================

def test_transport_configs_validation():
    """Verify CDC-ACM and Vendor Bulk transport configuration models."""
    # CDC-ACM valid
    cdc = CdcAcmTransportConfig(port="COM5", baudrate=115200, timeout_s=0.05)
    cdc.validate()
    assert cdc.transport_type == TransportType.CDC_ACM

    # CDC-ACM invalid baudrate
    with pytest.raises(ValueError, match="Invalid baudrate"):
        CdcAcmTransportConfig(port="COM5", baudrate=0).validate()

    # Vendor Bulk valid
    bulk = VendorBulkTransportConfig(vid=0x303A, pid=0x1001, read_endpoint=0x81, write_endpoint=0x01)
    bulk.validate()
    assert bulk.transport_type == TransportType.VENDOR_BULK

    # Vendor Bulk invalid identical endpoints
    with pytest.raises(ValueError, match="endpoints cannot be identical"):
        VendorBulkTransportConfig(read_endpoint=0x01, write_endpoint=0x01).validate()


def test_pending_hardware_factory():
    """Verify production factory throws explicit error declaring DW03-12 status."""
    factory = PendingHardwareTransportFactory()
    cfg = CdcAcmTransportConfig(port="COM3")
    with pytest.raises(NotImplementedError, match="pending joint B->C protocol approval \\(DW03-12\\)"):
        factory.create_transport(cfg)


# ==============================================================================
# 6. Critical Constraint Verification
# ==============================================================================

def test_pui_reference_profile_preservation():
    """Verify PUI DMM-4026 Rev-A baseline profile is preserved and NOT replaced with INMP441."""
    assert REV_A_BASELINE_PROFILE.profile_id == "rev_a_pui_dmm4026"
    assert REV_A_BASELINE_PROFILE.preferred_sample_rate_hz == 48000
    assert REV_A_BASELINE_PROFILE.channels == 1
    assert REV_A_BASELINE_PROFILE.sample_container_bits == 32
    assert REV_A_BASELINE_PROFILE.meaningful_data_bits == 24
    assert "PUI DMM-4026" in REV_A_BASELINE_PROFILE.description


def test_proposed_profile_b_decoder_compatibility():
    """Verify ProposedProfileBPacketDecoder decodes 40-byte header Profile B frames seamlessly."""
    decoder = ProposedProfileBPacketDecoder(meaningful_bits=24, sample_rate_hz=48000)
    samples = np.full(256, 123456, dtype=np.int32)
    payload = samples.astype("<i4").tobytes()
    import binascii
    import struct
    header = struct.pack(
        "<4sBBHIIQQHBBBBH",
        b"\x31\x43\x53\xaf",  # 0xAF534331
        1, 1, 1,
        77, 48000, 1500000, 7700, 256, 24, 32, 1, 1, 0
    )
    crc = binascii.crc32(header + payload) & 0xFFFFFFFF
    wire_frame = header + payload + struct.pack("<I", crc)

    packets = decoder.feed_bytes(wire_frame)
    assert len(packets) == 1
    pkt = packets[0]
    assert pkt.sequence == 77
    assert pkt.timestamp_s == 1.5
    assert pkt.crc_ok is True
    assert len(pkt.raw_samples) == 256
    assert pkt.raw_samples[0] == 123456

