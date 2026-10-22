"""Comprehensive Canonical B/C Protocol Test Suite (v0.1).

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)
"""

from pathlib import Path
import random
import struct
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from protocol_codec import (
    StreamingProtocolDecoder,
    DecodedPacket,
    StatusTelemetry,
    StartReq,
    StartAck,
    StopReq,
    HelloReq,
    HelloAck,
    ErrorNotification,
    build_profile_a_packet,
    build_profile_b_packet,
    build_hello_req_packet,
    build_hello_ack_packet,
    build_start_req_packet,
    build_start_ack_packet,
    build_stop_req_packet,
    build_stop_ack_packet,
    build_status_packet,
    build_error_packet,
    crc16_ccitt,
    crc32_ieee,
    encode_status_telemetry,
    decode_status_telemetry,
    encode_start_req,
    decode_start_req,
    encode_start_ack,
    decode_start_ack,
    encode_stop_req,
    decode_stop_req,
    encode_hello_req,
    decode_hello_req,
    encode_hello_ack,
    decode_hello_ack,
    encode_error,
    decode_error,
    MSG_TYPE_AUDIO_DATA,
    MSG_TYPE_HEARTBEAT_STATUS,
    MSG_TYPE_STREAM_START_REQ,
    MSG_TYPE_STREAM_START_ACK,
    MSG_TYPE_STREAM_STOP_REQ,
    MSG_TYPE_STREAM_STOP_ACK,
    MSG_TYPE_ERROR_NOTIFICATION,
    MSG_TYPE_HELLO_REQ,
    MSG_TYPE_HELLO_ACK,
    PROFILE_B_HEADER_SIZE,
    PROFILE_B_TRAILER_SIZE,
    FRAME_FLAG_TIMESTAMP_VALID,
    FRAME_FLAG_SIMULATED_SOURCE,
    FRAME_FLAG_SESSION_ACTIVE,
    FRAME_FLAG_CLIPPING_DETECTED,
)
from protocol_session import HostProtocolSession, SessionState
from simulated_device import SimulatedEsp32Device, compute_deterministic_sample
from usb_adapter import DuplexLoopbackAdapter, UsbCdcAcmAdapter, TransportState


class TestCanonicalProtocolGoldenVectors:
    """Golden test vectors for every message type on the wire."""

    def test_audio_frame_golden_vector(self):
        samples = np.array([100, -200, 300, -400], dtype=np.int32)
        wire = build_profile_b_packet(
            sequence_id=42,
            timestamp_us=1000000,
            sample_index_start=1024,
            samples=samples,
            sample_rate_hz=48000,
            meaningful_bits=24,
            flags=0x8041,  # 16-bit flags
            encoding=1,
            mcu_drops=3,
        )
        assert len(wire) == 40 + len(samples) * 4 + 4
        # Verify 40-byte header offsets
        assert wire[0:4] == b"\x31\x43\x53\xaf"  # Magic
        assert wire[4] == 1                       # Version
        assert wire[5] == MSG_TYPE_AUDIO_DATA     # Opcode 0x01
        assert struct.unpack("<H", wire[6:8])[0] == 0x8041  # Flags
        assert struct.unpack("<I", wire[8:12])[0] == 42     # Sequence
        assert struct.unpack("<I", wire[12:16])[0] == 48000 # Rate
        assert struct.unpack("<Q", wire[16:24])[0] == 1000000 # Timestamp
        assert struct.unpack("<Q", wire[24:32])[0] == 1024    # Index start
        assert struct.unpack("<H", wire[32:34])[0] == 4       # Sample count
        assert wire[34] == 24                                # Bits
        assert wire[35] == 32                                # Container
        assert wire[36] == 1                                 # Channels
        assert wire[37] == 1                                 # Encoding
        assert struct.unpack("<H", wire[38:40])[0] == 3       # Drops

        # Verify CRC trailer
        crc_expected = crc32_ieee(wire[:-4])
        crc_actual = struct.unpack("<I", wire[-4:])[0]
        assert crc_actual == crc_expected

        # Verify decoder
        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_AUDIO_DATA
        assert p.flags == 0x8041
        assert p.sample_count == 4
        np.testing.assert_array_equal(p.raw_samples, samples)

    def test_hello_req_golden_vector(self):
        wire = build_hello_req_packet(host_nonce=0xCAFE1234)
        assert len(wire) == 40 + 4 + 4  # 48 bytes
        assert wire[0:4] == b"\x31\x43\x53\xaf"
        assert wire[5] == MSG_TYPE_HELLO_REQ
        assert struct.unpack("<H", wire[32:34])[0] == 0  # sample_count MUST be 0!
        nonce = struct.unpack("<I", wire[40:44])[0]
        assert nonce == 0xCAFE1234

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        assert pkts[0].msg_type == MSG_TYPE_HELLO_REQ
        assert pkts[0].sample_count == 0
        assert pkts[0].control_payload.host_nonce == 0xCAFE1234

    def test_hello_ack_golden_vector(self):
        ack = HelloAck(
            nonce_echo=0xCAFE1234,
            protocol_version_major=1,
            protocol_version_minor=0,
            supported_profiles_mask=0x02,
            supported_encodings_mask=0x01,
            hardware_sample_rate_hz=48000,
            firmware_version_major=1,
            firmware_version_minor=0,
            firmware_version_patch=0,
            reserved=0,
            max_frame_samples=256,
            capability_flags=0x0007,
            device_uid_low=0xAABBCCDD,
        )
        wire = build_hello_ack_packet(ack)
        assert len(wire) == 40 + 24 + 4  # 68 bytes
        assert wire[5] == MSG_TYPE_HELLO_ACK
        assert struct.unpack("<H", wire[32:34])[0] == 0  # sample_count MUST be 0

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_HELLO_ACK
        assert p.control_payload.nonce_echo == 0xCAFE1234
        assert p.control_payload.device_uid_low == 0xAABBCCDD

    def test_start_req_golden_vector(self):
        req = StartReq(
            sample_rate_hz=48000,
            target_samples=480000,
            source_mode=1,
            encoding=1,
            channels=1,
            profile_id=2,
        )
        wire = build_start_req_packet(req)
        assert len(wire) == 40 + 16 + 4  # 60 bytes
        assert wire[5] == MSG_TYPE_STREAM_START_REQ
        assert struct.unpack("<H", wire[32:34])[0] == 0

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_STREAM_START_REQ
        assert p.control_payload.target_samples == 480000

    def test_start_ack_golden_vector(self):
        ack = StartAck(
            session_id=0x1234567890ABCDEF,
            session_reference_time_us=5000000,
            accepted_sample_rate_hz=48000,
            accepted_target_samples=480000,
            accepted_source_mode=1,
            encoding=1,
            channels=1,
            profile_id=2,
        )
        wire = build_start_ack_packet(ack)
        assert len(wire) == 40 + 32 + 4  # 76 bytes
        assert wire[5] == MSG_TYPE_STREAM_START_ACK

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_STREAM_START_ACK
        assert p.control_payload.session_id == 0x1234567890ABCDEF

    def test_stop_req_golden_vector(self):
        wire = build_stop_req_packet(session_id=0x1234567890ABCDEF)
        assert len(wire) == 40 + 8 + 4  # 52 bytes
        assert wire[5] == MSG_TYPE_STREAM_STOP_REQ

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_STREAM_STOP_REQ
        assert p.control_payload.session_id == 0x1234567890ABCDEF

    def test_status_and_stop_ack_72byte_telemetry_golden_vector(self):
        telem = StatusTelemetry(
            session_id=0x1234567890ABCDEF,
            generated_samples=480000,
            fully_queued_samples=480000,
            dropped_samples=0,
            audio_frames_queued=1875,
            dma_overflow_events=0,
            ring_overflow_events=0,
            usb_partial_write_events=0,
            usb_timeout_events=0,
            usb_disconnect_events=0,
            audio_bytes_queued=2002500,
            stop_reason=1,
            error_code=0,
        )
        # Test STATUS
        status_wire = build_status_packet(telem, sequence_id=100, timestamp_us=2000000)
        assert len(status_wire) == 40 + 72 + 4  # 116 bytes
        assert status_wire[5] == MSG_TYPE_HEARTBEAT_STATUS

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(status_wire)
        assert len(pkts) == 1
        p = pkts[0]
        assert p.msg_type == MSG_TYPE_HEARTBEAT_STATUS
        assert p.telemetry.generated_samples == 480000
        assert p.telemetry.audio_frames_queued == 1875

        # Test STOP_ACK
        stop_ack_wire = build_stop_ack_packet(telem)
        assert len(stop_ack_wire) == 40 + 72 + 4  # 116 bytes
        assert stop_ack_wire[5] == MSG_TYPE_STREAM_STOP_ACK

        pkts2 = decoder.feed_bytes(stop_ack_wire)
        assert len(pkts2) == 1
        assert pkts2[0].msg_type == MSG_TYPE_STREAM_STOP_ACK
        assert pkts2[0].telemetry.session_id == 0x1234567890ABCDEF

    def test_error_golden_vector(self):
        wire = build_error_packet(error_code=0x00000005, error_context=0x0000002A)
        assert len(wire) == 40 + 8 + 4  # 52 bytes
        assert wire[5] == MSG_TYPE_ERROR_NOTIFICATION

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(wire)
        assert len(pkts) == 1
        assert pkts[0].msg_type == MSG_TYPE_ERROR_NOTIFICATION
        assert pkts[0].control_payload.error_code == 5
        assert pkts[0].control_payload.error_context == 0x2A


class TestParserRobustnessAndEdgeCases:
    """Streaming parser fragmentation, concatenation, noise, and error recovery."""

    def test_unknown_opcode_rejected_safely(self):
        wire = bytearray(build_hello_req_packet(host_nonce=123))
        wire[5] = 0xAA  # Invalid opcode
        # Recompute CRC
        crc = crc32_ieee(wire[:-4])
        wire[-4:] = struct.pack("<I", crc)

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(bytes(wire))
        assert len(pkts) == 0
        assert decoder.malformed_headers == 1

    def test_control_frame_with_nonzero_sample_count_rejected(self):
        # A control frame with sample_count != 0 must be rejected
        wire = bytearray(build_hello_req_packet(host_nonce=123))
        wire[32:34] = struct.pack("<H", 10)  # Illegal non-zero sample count
        crc = crc32_ieee(wire[:-4])
        wire[-4:] = struct.pack("<I", crc)

        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(bytes(wire))
        assert len(pkts) == 0
        assert decoder.malformed_headers == 1

    def test_crc_corruption_recovery(self):
        samples = np.array([1, 2, 3, 4], dtype=np.int32)
        wire_good1 = build_profile_b_packet(1, 1000, 0, samples)
        wire_corrupt = bytearray(build_profile_b_packet(2, 2000, 4, samples))
        wire_corrupt[-1] ^= 0xFF  # Corrupt trailer
        wire_good2 = build_profile_b_packet(3, 3000, 8, samples)

        stream = wire_good1 + bytes(wire_corrupt) + wire_good2
        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(stream)

        # Corrupted frame was flagged
        assert decoder.total_frames_corrupted == 1
        # Valid frames decoded
        valid_pkts = [p for p in pkts if p.crc_ok]
        assert len(valid_pkts) == 2
        assert valid_pkts[0].sequence_id == 1
        assert valid_pkts[1].sequence_id == 3

    def test_fragmented_byte_stream_delivery(self):
        wire = build_hello_ack_packet(HelloAck(
            nonce_echo=0x9999, protocol_version_major=1, protocol_version_minor=0,
            supported_profiles_mask=2, supported_encodings_mask=1,
            hardware_sample_rate_hz=48000, firmware_version_major=1,
            firmware_version_minor=0, firmware_version_patch=0, reserved=0,
            max_frame_samples=256, capability_flags=7, device_uid_low=1
        ))
        decoder = StreamingProtocolDecoder()

        # Feed 3 bytes at a time
        pkts = []
        for i in range(0, len(wire), 3):
            pkts.extend(decoder.feed_bytes(wire[i:i+3]))

        assert len(pkts) == 1
        assert pkts[0].msg_type == MSG_TYPE_HELLO_ACK
        assert pkts[0].control_payload.nonce_echo == 0x9999

    def test_concatenated_mixed_frames(self):
        f_hello = build_hello_req_packet(111)
        f_start = build_start_req_packet(StartReq(48000, 1000, 1, 1, 1, 2))
        f_audio = build_profile_b_packet(0, 1000, 0, np.zeros(16, dtype=np.int32))
        f_stop = build_stop_req_packet(999)

        stream = f_hello + f_start + f_audio + f_stop
        decoder = StreamingProtocolDecoder()
        pkts = decoder.feed_bytes(stream)

        assert len(pkts) == 4
        assert pkts[0].msg_type == MSG_TYPE_HELLO_REQ
        assert pkts[1].msg_type == MSG_TYPE_STREAM_START_REQ
        assert pkts[2].msg_type == MSG_TYPE_AUDIO_DATA
        assert pkts[3].msg_type == MSG_TYPE_STREAM_STOP_REQ

        # Notice: only AUDIO frame incremented sample counters!
        assert decoder.total_samples_received == 16
        assert decoder.total_frames_received == 1


class TestHostSessionStateMachine:
    """State machine transitions, nonce verification, session continuity, and timeouts."""

    def test_nonce_mismatch_triggers_error(self):
        session = HostProtocolSession()
        req_bytes = session.initiate_handshake(host_nonce=0x11112222)
        assert session.state == SessionState.HELLO_PENDING

        # Craft HELLO_ACK with wrong nonce
        ack = HelloAck(
            nonce_echo=0x99999999,  # Mismatch!
            protocol_version_major=1, protocol_version_minor=0,
            supported_profiles_mask=2, supported_encodings_mask=1,
            hardware_sample_rate_hz=48000, firmware_version_major=1,
            firmware_version_minor=0, firmware_version_patch=0, reserved=0,
            max_frame_samples=256, capability_flags=7, device_uid_low=1
        )
        reply = build_hello_ack_packet(ack)
        session.handle_incoming_bytes(reply)

        assert session.state == SessionState.ERROR
        assert any("nonce mismatch" in e for e in session.error_log)

    def test_disconnect_invalidates_session_and_reconnection_renews(self):
        device = SimulatedEsp32Device()
        transport = DuplexLoopbackAdapter(device)
        session = HostProtocolSession()

        transport.open()

        # Session 1
        h1 = session.initiate_handshake()
        transport.write(h1)
        session.handle_incoming_bytes(transport.read())
        assert session.state == SessionState.READY

        s1 = session.request_start(target_samples=2560)
        transport.write(s1)
        session.handle_incoming_bytes(transport.read())
        assert session.state == SessionState.STREAMING
        session_id_1 = session.active_session_id

        # Stream some frames
        for _ in range(5):
            session.handle_incoming_bytes(transport.read())

        assert session.host_samples_accepted > 0

        # Simulate Disconnect
        session.handle_disconnect()
        transport.close()
        assert session.state == SessionState.DISCONNECTED
        assert session.active_session_id is None

        # Reconnect: must negotiate NEW session
        transport.open()
        h2 = session.initiate_handshake()
        transport.write(h2)
        session.handle_incoming_bytes(transport.read())

        s2 = session.request_start(target_samples=2560)
        transport.write(s2)
        session.handle_incoming_bytes(transport.read())

        session_id_2 = session.active_session_id
        assert session_id_2 is not None
        assert session_id_2 != session_id_1, "Reconnection MUST produce fresh session ID"
        assert session.host_samples_accepted == 0, "New session must reset sample counter to 0"

    def test_stale_session_id_rejected(self):
        device = SimulatedEsp32Device()
        transport = DuplexLoopbackAdapter(device)
        session = HostProtocolSession()
        transport.open()

        # Handshake & Start
        transport.write(session.initiate_handshake())
        session.handle_incoming_bytes(transport.read())
        transport.write(session.request_start(target_samples=512))
        session.handle_incoming_bytes(transport.read())

        # Now configure device to simulate stale session mismatch
        device.stale_session_id = True

        stop_req = session.request_stop()
        transport.write(stop_req)
        session.handle_incoming_bytes(transport.read())

        assert session.state == SessionState.ERROR
        assert any("Device reported ERROR" in e for e in session.error_log)


class TestTransportAdapterSafety:
    """USB adapter failure handling and parameter boundaries."""

    def test_usb_adapter_nonexistent_port(self):
        adapter = UsbCdcAcmAdapter()
        with pytest.raises((RuntimeError, ConnectionError)):
            adapter.open(port="COM999_NON_EXISTENT")
        assert adapter.get_state() == TransportState.ERROR
        telem = adapter.get_telemetry()
        assert telem["transport_type"] == "USB_CDC_ACM"
        assert telem["state"] == "ERROR"
