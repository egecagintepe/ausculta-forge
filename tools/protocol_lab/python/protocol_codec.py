"""AuscultaForge Independent Python Protocol Codec & Streaming Decoder.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)
"""

import binascii
from dataclasses import dataclass, field
import struct
from typing import Any, List, Optional
import numpy as np

# Magic sequences
PROFILE_A_MAGIC = b"\x55\xaa"           # 0xAA55 in little-endian
PROFILE_B_MAGIC = b"\x31\x43\x53\xaf"   # "1CSA" in ASCII little-endian (0xAF534331)

PROFILE_A_HEADER_SIZE = 16
PROFILE_A_TRAILER_SIZE = 2

PROFILE_B_HEADER_SIZE = 40
PROFILE_B_TRAILER_SIZE = 4

NOMINAL_SAMPLE_RATE_HZ = 48000
PROFILE_B_SAMPLES_PER_FRAME = 256
INT24_MAX = 8388607
INT24_MIN = -8388608
INT24_SCALE = 8388608.0


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


@dataclass(slots=True)
class DecodedPacket:
    """Decoded protocol packet."""
    sequence_id: int
    timestamp_us: int
    sample_index_start: int
    sample_count: int
    sample_rate_hz: int
    meaningful_bits: int
    flags: int
    encoding: int
    mcu_buffer_drops: int
    is_profile_b: bool
    crc_ok: bool
    raw_samples: np.ndarray  # int32 array
    normalized_samples: np.ndarray  # float32 array in [-1.0, +1.0]


def build_profile_a_packet(
    sequence: int,
    timestamp_us: int,
    samples: np.ndarray,
    flags: int = 0,
    corrupt_crc: bool = False,
) -> bytes:
    """Build a Profile A raw wire packet."""
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
    """Build a Profile B raw wire packet (40-byte header + payload + 4B CRC32)."""
    count = len(samples)
    payload = np.asarray(samples, dtype="<i4").tobytes()
    # Format: magic(4B), ver(1B), msg_type(1B), flags(2B), seq(4B), rate(4B), ts(8B), idx(8B), count(2B), bits(1B), container(1B), chan(1B), enc(1B), drops(2B)
    header = struct.pack(
        "<4sBBHIIQQHBBBBH",
        PROFILE_B_MAGIC,
        1,  # version
        1,  # msg_type (Audio)
        flags,
        sequence_id,
        sample_rate_hz,
        timestamp_us,
        sample_index_start,
        count,
        meaningful_bits,
        32,  # container_bits
        1,   # channels
        encoding,
        mcu_drops,
    )
    assert len(header) == PROFILE_B_HEADER_SIZE, f"Header size must be 40, got {len(header)}"
    body = header + payload
    crc = crc32_ieee(body)
    if corrupt_crc:
        crc ^= 0xFFFFFFFF
    return body + struct.pack("<I", crc)


class StreamingProtocolDecoder:
    """Streaming multi-fragment byte receiver and protocol decoder.

    Guarantees:
    - Never emits partial/fragmented packets prematurely.
    - Recovers stream lock automatically after encountering arbitrary line noise.
    - Slices combined / concatenated packets arriving in a single socket/pipe read.
    - Validates CRC-16 (Profile A) and CRC-32 (Profile B).
    - Maintains exact sample-level continuity and error telemetry.
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
        self.total_timestamp_regressions: int = 0
        self.garbage_bytes_discarded: int = 0
        self.malformed_headers: int = 0
        self.last_sequence_id: Optional[int] = None
        self.last_timestamp_us: Optional[int] = None
        self.last_sample_index: Optional[int] = None

    def reset(self) -> None:
        """Clear internal buffer and reset statistics."""
        self._buffer.clear()
        self.reset_stats()

    def feed_bytes(self, chunk: bytes) -> List[DecodedPacket]:
        """Feed arbitrary chunk of raw bytes and return all assembled frames."""
        if not chunk:
            return []

        self._buffer.extend(chunk)
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

                if ver != 1 or count == 0 or count > 2048:
                    self.malformed_headers += 1
                    del self._buffer[:4]
                    continue

                payload_bytes = count * 4
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
                    )
                    packets.append(pkt)
                    continue

                raw_samples = np.frombuffer(frame_bytes[PROFILE_B_HEADER_SIZE:-PROFILE_B_TRAILER_SIZE], dtype="<i4")
                norm = np.clip(raw_samples.astype(np.float32) / float(1 << (bits - 1)), -1.0, 1.0).astype(np.float32)

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
                    normalized_samples=norm,
                )
                self._update_quality_stats(pkt)
                packets.append(pkt)

            else:
                # Profile A
                if len(self._buffer) < PROFILE_A_HEADER_SIZE:
                    break

                magic, ver, mtype, seq, ts_us, count, flags = struct.unpack(
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
                        timestamp_us=ts_us,
                        sample_index_start=seq * count,
                        sample_count=count,
                        sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
                        meaningful_bits=24,
                        flags=flags,
                        encoding=1,
                        mcu_buffer_drops=0,
                        is_profile_b=False,
                        crc_ok=False,
                        raw_samples=np.zeros(0, dtype=np.int32),
                        normalized_samples=np.zeros(0, dtype=np.float32),
                    )
                    packets.append(pkt)
                    continue

                raw_samples = np.frombuffer(frame_bytes[PROFILE_A_HEADER_SIZE:-PROFILE_A_TRAILER_SIZE], dtype="<i4")
                norm = np.clip(raw_samples.astype(np.float32) / float(1 << 23), -1.0, 1.0).astype(np.float32)

                pkt = DecodedPacket(
                    sequence_id=seq,
                    timestamp_us=ts_us,
                    sample_index_start=seq * count,
                    sample_count=count,
                    sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
                    meaningful_bits=24,
                    flags=flags,
                    encoding=1,
                    mcu_buffer_drops=0,
                    is_profile_b=False,
                    crc_ok=True,
                    raw_samples=raw_samples,
                    normalized_samples=norm,
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

        # Sequence gap / duplicate check
        if pkt.sequence_id == self.last_sequence_id:
            self.total_duplicate_frames += 1
        else:
            expected_seq = (self.last_sequence_id + 1) & 0xFFFFFFFF
            if pkt.sequence_id != expected_seq:
                gap = (pkt.sequence_id - self.last_sequence_id - 1) & 0xFFFFFFFF
                self.total_sequence_gaps += gap

        # Timestamp regression check
        if self.last_timestamp_us is not None and pkt.timestamp_us < self.last_timestamp_us:
            self.total_timestamp_regressions += 1

        self.last_sequence_id = pkt.sequence_id
        self.last_timestamp_us = pkt.timestamp_us
        self.last_sample_index = pkt.sample_index_start
