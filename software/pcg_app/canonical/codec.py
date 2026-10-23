"""AuscultaForge Independent Python Protocol Codec & Streaming Decoder.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)
"""

import binascii
from dataclasses import dataclass, field
import struct
from typing import Any, Dict, List, Optional
import numpy as np

# Magic sequences
PROFILE_A_MAGIC = b"\x55\xaa"           # 0xAA55 in little-endian (Historical Legacy)
PROFILE_B_MAGIC = b"\x31\x43\x53\xaf"   # "1CSA" in ASCII little-endian (0xAF534331)

PROFILE_A_HEADER_SIZE = 16
PROFILE_A_TRAILER_SIZE = 2

PROFILE_B_HEADER_SIZE = 40
PROFILE_B_TRAILER_SIZE = 4

NOMINAL_SAMPLE_RATE_HZ = 48000
NOMINAL_MEANINGFUL_BITS = 24
NOMINAL_CONTAINER_BITS = 32
NOMINAL_CHANNELS = 1
PROFILE_B_SAMPLES_PER_FRAME = 256
INT24_MAX = 8388607
INT24_MIN = -8388608
INT24_SCALE = 8388608.0

MAX_DECODER_BUFFER_BYTES = 65536  # Safety bound preventing unbounded memory accumulation

# Protocol Message Types (Opcodes)
MSG_TYPE_AUDIO_DATA         = 0x01
MSG_TYPE_HEARTBEAT_STATUS   = 0x02
MSG_TYPE_STREAM_START_REQ   = 0x03
MSG_TYPE_STREAM_START_ACK   = 0x04
MSG_TYPE_STREAM_STOP_REQ    = 0x05
MSG_TYPE_STREAM_STOP_ACK    = 0x06
MSG_TYPE_CALIBRATION_TONE   = 0x07
MSG_TYPE_ERROR_NOTIFICATION = 0x0F
MSG_TYPE_HELLO_REQ          = 0x10
MSG_TYPE_HELLO_ACK          = 0x11

# Frame Flags Bitmask (16-bit)
FRAME_FLAG_TIMESTAMP_VALID      = 1 << 0
FRAME_FLAG_SAMPLE_DISCONTINUITY = 1 << 1
FRAME_FLAG_DMA_BUFFER_OVERFLOW  = 1 << 2
FRAME_FLAG_USB_QUEUE_OVERFLOW   = 1 << 3
FRAME_FLAG_CLIPPING_DETECTED    = 1 << 4
FRAME_FLAG_SIMULATED_SOURCE     = 1 << 5
FRAME_FLAG_DIAGNOSTIC_TONE      = 1 << 6
FRAME_FLAG_SESSION_ACTIVE       = 1 << 7

# Control payload sizes (in bytes)
CONTROL_PAYLOAD_SIZES: Dict[int, int] = {
    MSG_TYPE_HEARTBEAT_STATUS:   72,
    MSG_TYPE_STREAM_START_REQ:   16,
    MSG_TYPE_STREAM_START_ACK:   32,
    MSG_TYPE_STREAM_STOP_REQ:    8,
    MSG_TYPE_STREAM_STOP_ACK:    72,
    MSG_TYPE_ERROR_NOTIFICATION: 8,
    MSG_TYPE_HELLO_REQ:          4,
    MSG_TYPE_HELLO_ACK:          24,
    MSG_TYPE_CALIBRATION_TONE:   0,
}


def crc16_ccitt(data: bytes, init: int = 0xFFFF, poly: int = 0x1021) -> int:
    """Compute CRC-16-CCITT matching C implementation."""
    crc = init
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc32_ieee(data: bytes) -> int:
    """Compute standard IEEE 802.3 CRC-32 matching C implementation."""
    return binascii.crc32(data) & 0xFFFFFFFF


# =========================================================================
# Control Payload Dataclasses & Codecs
# =========================================================================

@dataclass(slots=True)
class StatusTelemetry:
    """72-Byte Exact Hardware Telemetry Payload (STATUS and STOP_ACK)."""
    session_id: int
    generated_samples: int
    fully_queued_samples: int
    dropped_samples: int
    audio_frames_queued: int
    dma_overflow_events: int
    ring_overflow_events: int
    usb_partial_write_events: int
    usb_timeout_events: int
    usb_disconnect_events: int
    audio_bytes_queued: int
    stop_reason: int
    error_code: int


def encode_status_telemetry(t: StatusTelemetry) -> bytes:
    """Encode 72-byte telemetry payload to little-endian bytes."""
    return struct.pack(
        "<QQQQIIIIIIQII",
        t.session_id,
        t.generated_samples,
        t.fully_queued_samples,
        t.dropped_samples,
        t.audio_frames_queued,
        t.dma_overflow_events,
        t.ring_overflow_events,
        t.usb_partial_write_events,
        t.usb_timeout_events,
        t.usb_disconnect_events,
        t.audio_bytes_queued,
        t.stop_reason,
        t.error_code,
    )


def decode_status_telemetry(b: bytes) -> StatusTelemetry:
    """Decode 72-byte telemetry payload from little-endian bytes."""
    if len(b) < 72:
        raise ValueError(f"Telemetry payload requires 72 bytes, got {len(b)}")
    fields = struct.unpack("<QQQQIIIIIIQII", b[:72])
    return StatusTelemetry(*fields)


@dataclass(slots=True)
class StartReq:
    """16-Byte Stream Start Request Payload (START_REQ)."""
    sample_rate_hz: int
    target_samples: int
    source_mode: int
    encoding: int
    channels: int
    profile_id: int


def encode_start_req(r: StartReq) -> bytes:
    """Encode 16-byte start request payload to little-endian bytes."""
    return struct.pack("<IQBBBB", r.sample_rate_hz, r.target_samples, r.source_mode, r.encoding, r.channels, r.profile_id)


def decode_start_req(b: bytes) -> StartReq:
    """Decode 16-byte start request payload from little-endian bytes."""
    if len(b) < 16:
        raise ValueError(f"StartReq payload requires 16 bytes, got {len(b)}")
    fields = struct.unpack("<IQBBBB", b[:16])
    return StartReq(*fields)


@dataclass(slots=True)
class StartAck:
    """32-Byte Stream Start Acknowledge Payload (START_ACK)."""
    session_id: int
    session_reference_time_us: int
    accepted_sample_rate_hz: int
    accepted_target_samples: int
    accepted_source_mode: int
    encoding: int
    channels: int
    profile_id: int


def encode_start_ack(a: StartAck) -> bytes:
    """Encode 32-byte start acknowledge payload to little-endian bytes."""
    return struct.pack(
        "<QQIQBBBB",
        a.session_id,
        a.session_reference_time_us,
        a.accepted_sample_rate_hz,
        a.accepted_target_samples,
        a.accepted_source_mode,
        a.encoding,
        a.channels,
        a.profile_id,
    )


def decode_start_ack(b: bytes) -> StartAck:
    """Decode 32-byte start acknowledge payload from little-endian bytes."""
    if len(b) < 32:
        raise ValueError(f"StartAck payload requires 32 bytes, got {len(b)}")
    fields = struct.unpack("<QQIQBBBB", b[:32])
    return StartAck(*fields)


@dataclass(slots=True)
class StopReq:
    """8-Byte Stream Stop Request Payload (STOP_REQ)."""
    session_id: int


def encode_stop_req(r: StopReq) -> bytes:
    """Encode 8-byte stop request payload to little-endian bytes."""
    return struct.pack("<Q", r.session_id)


def decode_stop_req(b: bytes) -> StopReq:
    """Decode 8-byte stop request payload from little-endian bytes."""
    if len(b) < 8:
        raise ValueError(f"StopReq payload requires 8 bytes, got {len(b)}")
    (session_id,) = struct.unpack("<Q", b[:8])
    return StopReq(session_id=session_id)


@dataclass(slots=True)
class HelloReq:
    """4-Byte Hello Request Payload (HELLO_REQ)."""
    host_nonce: int


def encode_hello_req(r: HelloReq) -> bytes:
    """Encode 4-byte hello request payload to little-endian bytes."""
    return struct.pack("<I", r.host_nonce)


def decode_hello_req(b: bytes) -> HelloReq:
    """Decode 4-byte hello request payload from little-endian bytes."""
    if len(b) < 4:
        raise ValueError(f"HelloReq payload requires 4 bytes, got {len(b)}")
    (host_nonce,) = struct.unpack("<I", b[:4])
    return HelloReq(host_nonce=host_nonce)


@dataclass(slots=True)
class HelloAck:
    """24-Byte Proposed Hello Acknowledge Payload (HELLO_ACK)."""
    nonce_echo: int
    protocol_version_major: int
    protocol_version_minor: int
    supported_profiles_mask: int
    supported_encodings_mask: int
    hardware_sample_rate_hz: int
    firmware_version_major: int
    firmware_version_minor: int
    firmware_version_patch: int
    reserved: int
    max_frame_samples: int
    capability_flags: int
    device_uid_low: int


def encode_hello_ack(a: HelloAck) -> bytes:
    """Encode 24-byte hello acknowledge payload to little-endian bytes."""
    return struct.pack(
        "<IBBBBIBBBB HHI",
        a.nonce_echo,
        a.protocol_version_major,
        a.protocol_version_minor,
        a.supported_profiles_mask,
        a.supported_encodings_mask,
        a.hardware_sample_rate_hz,
        a.firmware_version_major,
        a.firmware_version_minor,
        a.firmware_version_patch,
        a.reserved,
        a.max_frame_samples,
        a.capability_flags,
        a.device_uid_low,
    )


def decode_hello_ack(b: bytes) -> HelloAck:
    """Decode 24-byte hello acknowledge payload from little-endian bytes."""
    if len(b) < 24:
        raise ValueError(f"HelloAck payload requires 24 bytes, got {len(b)}")
    fields = struct.unpack("<IBBBBIBBBB HHI", b[:24])
    return HelloAck(*fields)


@dataclass(slots=True)
class ErrorNotification:
    """8-Byte Proposed Error Notification Payload (ERROR)."""
    error_code: int
    error_context: int


def encode_error(e: ErrorNotification) -> bytes:
    """Encode 8-byte error notification payload to little-endian bytes."""
    return struct.pack("<II", e.error_code, e.error_context)


def decode_error(b: bytes) -> ErrorNotification:
    """Decode 8-byte error notification payload from little-endian bytes."""
    if len(b) < 8:
        raise ValueError(f"ErrorNotification payload requires 8 bytes, got {len(b)}")
    code, ctx = struct.unpack("<II", b[:8])
    return ErrorNotification(error_code=code, error_context=ctx)


@dataclass(slots=True)
class DecodedPacket:
    """Decoded protocol packet."""
    sequence_id: int
    timestamp_us: int
    sample_index_start: int
    sample_count: int
    sample_rate_hz: int
    meaningful_bits: int
    flags: int                          # Retains full 16 bits!
    encoding: int
    mcu_buffer_drops: int
    is_profile_b: bool
    crc_ok: bool
    raw_samples: np.ndarray             # int32 array (empty for control packets)
    normalized_samples: np.ndarray      # float32 array in [-1.0, +1.0] (empty for control)
    msg_type: int = MSG_TYPE_AUDIO_DATA # Opcode
    control_payload: Optional[Any] = None
    telemetry: Optional[StatusTelemetry] = None


# =========================================================================
# Packet Builders
# =========================================================================

def build_profile_a_packet(
    sequence: int,
    timestamp_us: int,
    samples: np.ndarray,
    flags: int = 0,
    corrupt_crc: bool = False,
) -> bytes:
    """Build a Profile A raw wire packet (16-byte header + payload + 2B CRC16)."""
    count = len(samples)
    payload = np.asarray(samples, dtype="<i4").tobytes()
    header = struct.pack("<2sBBIIHH", PROFILE_A_MAGIC, 1, 1, sequence, timestamp_us & 0xFFFFFFFF, count, flags)
    body = header + payload
    crc = crc16_ccitt(body)
    if corrupt_crc:
        crc ^= 0xFFFF
    return body + struct.pack("<H", crc)


def build_profile_b_packet(
    sequence_id: int,
    timestamp_us: int,
    sample_index_start: int,
    samples: np.ndarray,
    sample_rate_hz: int = 48000,
    meaningful_bits: int = 24,
    flags: int = 1,
    encoding: int = 1,
    mcu_drops: int = 0,
    corrupt_crc: bool = False,
) -> bytes:
    """Build a Profile B standard audio raw wire packet (40B header + payload + 4B CRC32).

    Retains full 16-bit flags.
    """
    count = len(samples)
    payload = np.asarray(samples, dtype="<i4").tobytes()
    header = struct.pack(
        "<4sBBHIIQQHBBBBH",
        PROFILE_B_MAGIC,
        1,  # version
        MSG_TYPE_AUDIO_DATA,
        flags & 0xFFFF,  # 16-bit flags
        sequence_id,
        sample_rate_hz,
        timestamp_us,
        sample_index_start,
        count,
        meaningful_bits,
        32,  # container_bits
        1,   # channels
        encoding,
        mcu_drops & 0xFFFF,
    )
    assert len(header) == PROFILE_B_HEADER_SIZE, f"Header size must be 40, got {len(header)}"
    body = header + payload
    crc = crc32_ieee(body)
    if corrupt_crc:
        crc ^= 0xFFFFFFFF
    return body + struct.pack("<I", crc)


def _build_control_packet(
    msg_type: int,
    payload: bytes,
    flags: int = FRAME_FLAG_TIMESTAMP_VALID,
    sequence_id: int = 0,
    timestamp_us: int = 0,
    corrupt_crc: bool = False,
) -> bytes:
    """Helper to build a 40B Profile B control packet with sample_count == 0."""
    header = struct.pack(
        "<4sBBHIIQQHBBBBH",
        PROFILE_B_MAGIC,
        1,  # version
        msg_type,
        flags & 0xFFFF,
        sequence_id,
        NOMINAL_SAMPLE_RATE_HZ,
        timestamp_us,
        0,  # sample_index_start is 0 for control frames
        0,  # CRITICAL: sample_count MUST be 0 for control frames
        NOMINAL_MEANINGFUL_BITS,
        32,
        1,
        1,
        0,
    )
    body = header + payload
    crc = crc32_ieee(body)
    if corrupt_crc:
        crc ^= 0xFFFFFFFF
    return body + struct.pack("<I", crc)


def build_hello_req_packet(host_nonce: int, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build a HELLO_REQ packet (48 bytes total)."""
    p = HelloReq(host_nonce=host_nonce)
    return _build_control_packet(MSG_TYPE_HELLO_REQ, encode_hello_req(p), flags=flags)


def build_hello_ack_packet(ack: HelloAck, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build a HELLO_ACK packet (68 bytes total)."""
    return _build_control_packet(MSG_TYPE_HELLO_ACK, encode_hello_ack(ack), flags=flags)


def build_start_req_packet(req: StartReq, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build a START_REQ packet (60 bytes total)."""
    return _build_control_packet(MSG_TYPE_STREAM_START_REQ, encode_start_req(req), flags=flags)


def build_start_ack_packet(ack: StartAck, flags: int = (FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SESSION_ACTIVE)) -> bytes:
    """Build a START_ACK packet (76 bytes total)."""
    return _build_control_packet(
        MSG_TYPE_STREAM_START_ACK,
        encode_start_ack(ack),
        flags=flags,
        timestamp_us=ack.session_reference_time_us,
    )


def build_stop_req_packet(session_id: int, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build a STOP_REQ packet (52 bytes total)."""
    p = StopReq(session_id=session_id)
    return _build_control_packet(MSG_TYPE_STREAM_STOP_REQ, encode_stop_req(p), flags=flags)


def build_stop_ack_packet(telem: StatusTelemetry, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build a STOP_ACK packet (116 bytes total)."""
    return _build_control_packet(
        MSG_TYPE_STREAM_STOP_ACK,
        encode_status_telemetry(telem),
        flags=flags,
        sequence_id=telem.audio_frames_queued,
    )


def build_status_packet(
    telem: StatusTelemetry,
    sequence_id: int = 0,
    timestamp_us: int = 0,
    flags: int = (FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SESSION_ACTIVE),
) -> bytes:
    """Build a STATUS telemetry packet (116 bytes total)."""
    return _build_control_packet(
        MSG_TYPE_HEARTBEAT_STATUS,
        encode_status_telemetry(telem),
        flags=flags,
        sequence_id=sequence_id,
        timestamp_us=timestamp_us,
    )


def build_error_packet(error_code: int, error_context: int = 0, flags: int = FRAME_FLAG_TIMESTAMP_VALID) -> bytes:
    """Build an ERROR packet (52 bytes total)."""
    p = ErrorNotification(error_code=error_code, error_context=error_context)
    return _build_control_packet(MSG_TYPE_ERROR_NOTIFICATION, encode_error(p), flags=flags)


# =========================================================================
# Streaming Protocol Decoder
# =========================================================================

class StreamingProtocolDecoder:
    """Streaming multi-fragment byte receiver and canonical protocol decoder.

    Guarantees:
    - Never emits partial/fragmented packets prematurely.
    - Recovers stream lock automatically after encountering arbitrary line noise.
    - Slices combined / concatenated packets arriving in a single socket/pipe read.
    - Validates CRC-16 (Profile A) and CRC-32 (Profile B).
    - Accurately decodes all canonical control messages with sample_count == 0.
    - Safely rejects unknown message types or malformed frames.
    - Preserves all 16 bits of status flags.
    - Maintains exact sample-level continuity and error telemetry on AUDIO frames only.
    - Strictly bounds internal memory accumulation to MAX_DECODER_BUFFER_BYTES.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.reset_stats()

    def reset_stats(self) -> None:
        """Reset accounting statistics."""
        self.total_samples_received: int = 0
        self.total_frames_received: int = 0
        self.total_frames_corrupted: int = 0
        self.total_sequence_gaps: int = 0
        self.total_duplicate_frames: int = 0
        self.total_reordered_frames: int = 0
        self.total_timestamp_regressions: int = 0
        self.garbage_bytes_discarded: int = 0
        self.malformed_headers: int = 0
        self.last_sequence_id: Optional[int] = None
        self.last_timestamp_us: Optional[int] = None
        self.last_sample_index: Optional[int] = None

    def reset(self) -> None:
        """Clear internal buffer and reset statistics for session reset/reconnection."""
        self._buffer.clear()
        self.reset_stats()

    @property
    def buffer_len(self) -> int:
        return len(self._buffer)

    def feed_bytes(self, chunk: bytes) -> List[DecodedPacket]:
        """Feed arbitrary chunk of raw bytes and return all assembled frames."""
        if not chunk:
            return []

        self._buffer.extend(chunk)

        # Enforce memory safety bound
        if len(self._buffer) > MAX_DECODER_BUFFER_BYTES:
            excess = len(self._buffer) - MAX_DECODER_BUFFER_BYTES
            self.garbage_bytes_discarded += excess
            del self._buffer[:excess]

        packets: List[DecodedPacket] = []

        while len(self._buffer) >= 4:
            # 1. Search for sync magic (Profile B 4B or Profile A 2B)
            buf_len = len(self._buffer)
            idx_b = self._buffer.find(PROFILE_B_MAGIC)
            idx_a = self._buffer.find(PROFILE_A_MAGIC)

            # Determine earliest candidate
            if idx_b != -1 and (idx_a == -1 or idx_b <= idx_a):
                sync_idx = idx_b
                is_profile_b = True
            elif idx_a != -1:
                sync_idx = idx_a
                is_profile_b = False
            else:
                # No sync magic in buffer: keep last 3 bytes and discard the rest
                if buf_len > 3:
                    discarded = buf_len - 3
                    self.garbage_bytes_discarded += discarded
                    del self._buffer[:discarded]
                break

            if sync_idx > 0:
                self.garbage_bytes_discarded += sync_idx
                del self._buffer[:sync_idx]

            # 2. Parse candidate frame
            if is_profile_b:
                if len(self._buffer) < PROFILE_B_HEADER_SIZE:
                    break

                magic, ver, mtype, flags, seq, rate, ts_us, idx_start, count, bits, cont, chan, enc, drops = struct.unpack(
                    "<4sBBHIIQQHBBBBH",
                    bytes(self._buffer[:PROFILE_B_HEADER_SIZE]),
                )

                if ver != 1:
                    self.malformed_headers += 1
                    del self._buffer[:4]
                    continue

                if mtype == MSG_TYPE_AUDIO_DATA:
                    if cont != 32 or chan != 1 or bits != 24 or rate != 48000 or enc not in (1,2):
                        self.malformed_headers += 1
                        del self._buffer[:4]
                        continue
                    if count == 0 or count > 1024:
                        self.malformed_headers += 1
                        del self._buffer[:4]
                        continue
                    payload_bytes = count * 4
                elif mtype in CONTROL_PAYLOAD_SIZES:
                    if count != 0:
                        # Control frames MUST have sample_count == 0
                        self.malformed_headers += 1
                        del self._buffer[:4]
                        continue
                    payload_bytes = CONTROL_PAYLOAD_SIZES[mtype]
                else:
                    # Unknown opcode: reject safely
                    self.malformed_headers += 1
                    del self._buffer[:4]
                    continue

                total_frame_len = PROFILE_B_HEADER_SIZE + payload_bytes + PROFILE_B_TRAILER_SIZE

                if len(self._buffer) < total_frame_len:
                    break

                frame_bytes = bytes(self._buffer[:total_frame_len])
                del self._buffer[:total_frame_len]

                crc_received = struct.unpack("<I", frame_bytes[-PROFILE_B_TRAILER_SIZE:])[0]
                crc_computed = crc32_ieee(frame_bytes[:-PROFILE_B_TRAILER_SIZE])

                if crc_received != crc_computed:
                    self.total_frames_corrupted += 1
                    pkt = DecodedPacket(
                        sequence_id=seq,
                        timestamp_us=ts_us,
                        sample_index_start=idx_start,
                        sample_count=count,
                        sample_rate_hz=rate,
                        meaningful_bits=bits,
                        flags=flags,
                        encoding=enc,
                        mcu_buffer_drops=drops,
                        is_profile_b=True,
                        crc_ok=False,
                        raw_samples=np.zeros(0, dtype=np.int32),
                        normalized_samples=np.zeros(0, dtype=np.float32),
                        msg_type=mtype,
                    )
                    packets.append(pkt)
                    continue

                payload_bytes_raw = frame_bytes[PROFILE_B_HEADER_SIZE:-PROFILE_B_TRAILER_SIZE]

                if mtype == MSG_TYPE_AUDIO_DATA:
                    raw_samples = np.frombuffer(payload_bytes_raw, dtype="<i4").copy()
                    if enc == 2:  # MSB aligned
                        lsb_samples = np.right_shift(raw_samples, 8)
                    else:
                        lsb_samples = raw_samples

                    scale = float(1 << (bits - 1))
                    norm_samples = np.clip(lsb_samples.astype(np.float32) / scale, -1.0, 1.0)

                    pkt = DecodedPacket(
                        sequence_id=seq,
                        timestamp_us=ts_us,
                        sample_index_start=idx_start,
                        sample_count=count,
                        sample_rate_hz=rate,
                        meaningful_bits=bits,
                        flags=flags,
                        encoding=enc,
                        mcu_buffer_drops=drops,
                        is_profile_b=True,
                        crc_ok=True,
                        raw_samples=raw_samples,
                        normalized_samples=norm_samples,
                        msg_type=mtype,
                    )
                    self._update_quality_stats(pkt)
                    packets.append(pkt)

                else:
                    # Control message parsing
                    control_obj = None
                    telem_obj = None

                    try:
                        if mtype in (MSG_TYPE_HEARTBEAT_STATUS, MSG_TYPE_STREAM_STOP_ACK):
                            telem_obj = decode_status_telemetry(payload_bytes_raw)
                            control_obj = telem_obj
                        elif mtype == MSG_TYPE_STREAM_START_REQ:
                            control_obj = decode_start_req(payload_bytes_raw)
                        elif mtype == MSG_TYPE_STREAM_START_ACK:
                            control_obj = decode_start_ack(payload_bytes_raw)
                        elif mtype == MSG_TYPE_STREAM_STOP_REQ:
                            control_obj = decode_stop_req(payload_bytes_raw)
                        elif mtype == MSG_TYPE_HELLO_REQ:
                            control_obj = decode_hello_req(payload_bytes_raw)
                        elif mtype == MSG_TYPE_HELLO_ACK:
                            control_obj = decode_hello_ack(payload_bytes_raw)
                        elif mtype == MSG_TYPE_ERROR_NOTIFICATION:
                            control_obj = decode_error(payload_bytes_raw)
                    except Exception:
                        self.malformed_headers += 1
                        continue

                    pkt = DecodedPacket(
                        sequence_id=seq,
                        timestamp_us=ts_us,
                        sample_index_start=0,
                        sample_count=0,
                        sample_rate_hz=rate,
                        meaningful_bits=bits,
                        flags=flags,
                        encoding=enc,
                        mcu_buffer_drops=drops,
                        is_profile_b=True,
                        crc_ok=True,
                        raw_samples=np.zeros(0, dtype=np.int32),
                        normalized_samples=np.zeros(0, dtype=np.float32),
                        msg_type=mtype,
                        control_payload=control_obj,
                        telemetry=telem_obj,
                    )
                    # Control frames MUST NOT update audio quality stats
                    packets.append(pkt)

            else:
                # Profile A (Historical 16-byte header)
                if len(self._buffer) < PROFILE_A_HEADER_SIZE:
                    break

                magic, ver, mtype, seq, ts_32, count, flags = struct.unpack(
                    "<2sBBIIHH",
                    bytes(self._buffer[:PROFILE_A_HEADER_SIZE]),
                )

                if ver != 1 or count == 0 or count > 2048:
                    self.malformed_headers += 1
                    del self._buffer[:2]
                    continue

                payload_bytes = count * 4
                total_frame_len = PROFILE_A_HEADER_SIZE + payload_bytes + PROFILE_A_TRAILER_SIZE

                if len(self._buffer) < total_frame_len:
                    break

                frame_bytes = bytes(self._buffer[:total_frame_len])
                del self._buffer[:total_frame_len]

                crc_received = struct.unpack("<H", frame_bytes[-PROFILE_A_TRAILER_SIZE:])[0]
                crc_computed = crc16_ccitt(frame_bytes[:-PROFILE_A_TRAILER_SIZE])

                if crc_received != crc_computed:
                    self.total_frames_corrupted += 1
                    pkt = DecodedPacket(
                        sequence_id=seq,
                        timestamp_us=ts_32,
                        sample_index_start=0,
                        sample_count=count,
                        sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
                        meaningful_bits=NOMINAL_MEANINGFUL_BITS,
                        flags=flags,
                        encoding=1,
                        mcu_buffer_drops=0,
                        is_profile_b=False,
                        crc_ok=False,
                        raw_samples=np.zeros(0, dtype=np.int32),
                        normalized_samples=np.zeros(0, dtype=np.float32),
                        msg_type=MSG_TYPE_AUDIO_DATA,
                    )
                    packets.append(pkt)
                    continue

                payload_bytes_raw = frame_bytes[PROFILE_A_HEADER_SIZE:-PROFILE_A_TRAILER_SIZE]
                raw_samples = np.frombuffer(payload_bytes_raw, dtype="<i4").copy()
                norm_samples = np.clip(raw_samples.astype(np.float32) / float(INT24_SCALE), -1.0, 1.0)

                pkt = DecodedPacket(
                    sequence_id=seq,
                    timestamp_us=ts_32,
                    sample_index_start=0,
                    sample_count=count,
                    sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
                    meaningful_bits=NOMINAL_MEANINGFUL_BITS,
                    flags=flags,
                    encoding=1,
                    mcu_buffer_drops=0,
                    is_profile_b=False,
                    crc_ok=True,
                    raw_samples=raw_samples,
                    normalized_samples=norm_samples,
                    msg_type=MSG_TYPE_AUDIO_DATA,
                )
                self._update_quality_stats(pkt)
                packets.append(pkt)

        return packets

    def _update_quality_stats(self, pkt: DecodedPacket) -> None:
        self.total_frames_received += 1
        self.total_samples_received += pkt.sample_count

        if self.last_sequence_id is None:
            self.last_sequence_id = pkt.sequence_id
            self.last_timestamp_us = pkt.timestamp_us
            self.last_sample_index = pkt.sample_index_start
            return

        # RFC 3550 signed sequence difference check
        delta = (pkt.sequence_id - self.last_sequence_id)
        if delta >= 0x80000000:
            delta -= 0x100000000
        elif delta < -0x80000000:
            delta += 0x100000000

        if delta == 1:
            pass  # Strictly sequential
        elif delta > 1:
            self.total_sequence_gaps += (delta - 1)
        elif delta == 0:
            self.total_duplicate_frames += 1
        else:
            self.total_reordered_frames += 1

        # Timestamp regression check
        if self.last_timestamp_us is not None and pkt.timestamp_us < self.last_timestamp_us:
            self.total_timestamp_regressions += 1

        self.last_sequence_id = pkt.sequence_id
        self.last_timestamp_us = pkt.timestamp_us
        self.last_sample_index = pkt.sample_index_start


def compute_deterministic_g1_sample(abs_sample_index: int) -> int:
    """Normative deterministic integer sequence formula for G1 verification.
    
    Formula: ((abs_sample_index * 16807 + 7) & 0x00FFFFFF), sign-extended to 24-bit.
    """
    val = ((abs_sample_index * 16807 + 7) & 0x00FFFFFF)
    if val & 0x00800000:
        val -= 0x01000000
    return int(val)


compute_deterministic_sample = compute_deterministic_g1_sample

