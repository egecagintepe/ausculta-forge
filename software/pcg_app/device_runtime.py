"""AuscultaForge — Device Runtime Foundation.

Provides the authoritative physical device lifecycle state machine, transport
and discovery abstractions, semantic packet framing, centralized acquisition profile
configuration, capability negotiation, runtime integrity telemetry, and structured event logging.

Phase-1 Architecture Rules:
- Physical transport is ESP32-S3 Native USB (final decision).
- USB class: CDC-ACM is the current Hardware Rev-A proposal under team review;
  USB descriptors (VID/PID) and endpoints are pending firmware declaration.
- Physical acquisition profile (Rev-A: 48 kHz mono 24-bit data in 32-bit container signed PCM)
  is decoupled from UI rendering rates and offline development sources.
- NO fake USB drivers, fake COM ports, or fake hardware simulation in production.
- Python runtime state is authoritative; the UI strictly reflects backend state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import queue
import struct
import threading
import time
from typing import Any, Callable, Optional, Protocol, runtime_checkable
import uuid

import numpy as np
from pcg_core.models import SampleBlock
from pcg_core.streaming import StreamQualityMonitor


# ==============================================================================
# 1. Device Lifecycle State Machine
# ==============================================================================

class DeviceState(str, Enum):
    """Authoritative physical device lifecycle states."""
    ABSENT = "absent"                  # No device hardware detected on host bus
    DETECTED = "detected"              # Candidate hardware detected; awaiting transport opening
    OPENING = "opening"                # Transport connection being established
    HANDSHAKING = "handshaking"        # Transport open; negotiating capabilities & protocol version
    READY = "ready"                    # Handshake validated; idle and ready to stream
    STREAMING = "streaming"            # Actively streaming acoustic sample frames
    INTERRUPTED = "interrupted"        # Physical transport lost mid-stream or mid-session
    ERROR = "error"                    # Hardware, protocol, or transport failure
    INCOMPATIBLE = "incompatible"      # Rejected during handshake (unsupported protocol/rates/format)


# Strict state transition matrix
ALLOWED_TRANSITIONS: dict[DeviceState, set[DeviceState]] = {
    DeviceState.ABSENT: {DeviceState.DETECTED},
    DeviceState.DETECTED: {DeviceState.OPENING, DeviceState.ABSENT},
    DeviceState.OPENING: {DeviceState.HANDSHAKING, DeviceState.ERROR, DeviceState.ABSENT},
    DeviceState.HANDSHAKING: {DeviceState.READY, DeviceState.INCOMPATIBLE, DeviceState.ERROR, DeviceState.ABSENT},
    DeviceState.READY: {DeviceState.STREAMING, DeviceState.ABSENT, DeviceState.ERROR},
    DeviceState.STREAMING: {DeviceState.READY, DeviceState.INTERRUPTED, DeviceState.ERROR, DeviceState.ABSENT},
    DeviceState.INTERRUPTED: {DeviceState.DETECTED, DeviceState.ABSENT, DeviceState.ERROR},
    DeviceState.ERROR: {DeviceState.DETECTED, DeviceState.ABSENT},
    DeviceState.INCOMPATIBLE: {DeviceState.ABSENT},
}


class InvalidStateTransitionError(RuntimeError):
    """Raised when an illegal device lifecycle state transition is attempted."""
    pass


class TransportError(RuntimeError):
    """Base exception for physical device transport errors."""
    pass


class TransportTimeoutError(TransportError):
    """Raised when transport read times out unexpectedly."""
    pass


class TransportDisconnectedError(TransportError):
    """Raised when physical transport link is lost or closed during operation."""
    pass


class TransportOverflowError(TransportError):
    """Raised when incoming buffer overflows bounded capacity."""
    pass


class TransportConcurrentOwnershipError(TransportError):
    """Raised when concurrent reader ownership is attempted."""
    pass


# ==============================================================================
# 2. Centralized Acquisition Profile & Configuration Model
# ==============================================================================

@dataclass(slots=True)
class AcquisitionProfile:
    """Centralized hardware acquisition configuration profile.

    Expresses physical acquisition parameters (e.g. Rev-A 48 kHz mono signed PCM
    with 24-bit meaningful sensor data carried in a 32-bit I2S/USB container)
    distinct from host display/rendering rates and distinct from sensor acoustic precision.

    CRITICAL DISTINCTIONS:
    - sample_container_bits (e.g. 32): The slot/transport width over I2S / USB framing.
    - meaningful_data_bits (e.g. 24): The sensor data word width within the container.
    - Sensor Precision: A 24-bit digital word does NOT imply 24-bit acoustic precision.
      Effective acoustic precision and SNR are determined by the microphone transducer
      physics (e.g. PUI DMM-4026-B-I2S-R acoustic dynamic range / noise floor).
    """
    profile_id: str = "rev_a_pui_dmm4026"
    preferred_sample_rate_hz: int = 48000
    channels: int = 1
    sample_container_bits: int = 32
    meaningful_data_bits: int = 24
    sample_encoding: str = "signed_pcm"
    preferred_block_size: int = 512
    negotiated_block_size: int = 512
    description: str = (
        "Hardware Rev-A baseline (PUI DMM-4026-B-I2S-R: 48 kHz mono 24-in-32 signed PCM)"
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Authoritative Hardware Rev-A proposal baseline profile
REV_A_BASELINE_PROFILE = AcquisitionProfile()

# Engineering/development test profile (for legacy 4 kHz test doubles and offline sources)
DEV_LEGACY_PROFILE = AcquisitionProfile(
    profile_id="dev_4khz_legacy",
    preferred_sample_rate_hz=4000,
    channels=1,
    sample_container_bits=16,
    meaningful_data_bits=16,
    sample_encoding="signed_pcm",
    preferred_block_size=128,
    negotiated_block_size=128,
    description="Development test profile: 4000 Hz mono 16-bit",
)


# ==============================================================================
# 3. Capabilities & Handshake Model
# ==============================================================================

SUPPORTED_PROTOCOL_VERSIONS = {"1.0"}
SUPPORTED_SAMPLE_ENCODINGS = {"signed_pcm", "float32", "int16", "int32"}


@dataclass(slots=True)
class DeviceCapabilities:
    """Semantic hardware capabilities reported during device handshake."""
    protocol_version: str
    firmware_version: str
    device_id: str
    sample_rate_hz: int = 48000
    sample_format: str = "signed_pcm"
    channels: int = 1
    max_block_size: int = 512
    sample_container_bits: int = 32
    meaningful_data_bits: int = 24

    def validate_compatibility(self, profile: AcquisitionProfile) -> None:
        """Validate reported capabilities against an active acquisition profile.

        Raises:
            ValueError: If protocol version, channel count, sample encoding, or sample rate
                        fail to satisfy the active acquisition profile.
        """
        if self.protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            raise ValueError(
                f"Unsupported protocol version: {self.protocol_version!r}. "
                f"Supported: {sorted(SUPPORTED_PROTOCOL_VERSIONS)}"
            )

        if self.channels != profile.channels:
            raise ValueError(
                f"Channel count mismatch: profile expects {profile.channels} channel(s), "
                f"got {self.channels}"
            )

        if self.sample_rate_hz != profile.preferred_sample_rate_hz:
            raise ValueError(
                f"Sample rate mismatch: profile expects {profile.preferred_sample_rate_hz} Hz, "
                f"got {self.sample_rate_hz} Hz"
            )

        if self.sample_format != profile.sample_encoding:
            raise ValueError(
                f"Sample format mismatch: profile requires canonical {profile.sample_encoding!r}, "
                f"got {self.sample_format!r}"
            )

        if self.sample_container_bits != profile.sample_container_bits:
            raise ValueError(
                f"Container bit width mismatch: profile requires {profile.sample_container_bits}-bit container, "
                f"got {self.sample_container_bits}-bit"
            )

        if self.meaningful_data_bits != profile.meaningful_data_bits:
            raise ValueError(
                f"Meaningful data bit width mismatch: profile requires {profile.meaningful_data_bits}-bit data, "
                f"got {self.meaningful_data_bits}-bit"
            )

        if self.max_block_size <= 0 or self.max_block_size > 16384:
            raise ValueError(f"Invalid max_block_size: {self.max_block_size}")

    def validate(self, profile: Optional[AcquisitionProfile] = None) -> None:
        """Validate capabilities against a profile (defaults to REV_A_BASELINE_PROFILE)."""
        active_profile = profile or REV_A_BASELINE_PROFILE
        self.validate_compatibility(active_profile)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 4. Semantic Packet Framing & Adapter to SampleBlock
# ==============================================================================

class DeviceSamplePacket:
    """Semantic decoded physical sample packet.

    Carries raw integer sensor samples in their container format without premature
    float conversion, preserving raw acquisition meaning until the DSP adapter boundary.
    """
    sequence: int
    timestamp_s: float
    raw_samples: np.ndarray
    flags: int
    crc_ok: bool
    meaningful_bits: int
    sample_rate_hz: int

    def __init__(
        self,
        sequence: int,
        timestamp_s: float,
        raw_samples: Any = None,
        flags: int = 0,
        crc_ok: bool = True,
        meaningful_bits: int = 24,
        sample_rate_hz: int = 48000,
        samples: Any = None,
    ) -> None:
        self.sequence = sequence
        self.timestamp_s = timestamp_s
        actual = raw_samples if raw_samples is not None else samples
        if actual is None:
            actual = np.zeros(0, dtype=np.int32)
        if not isinstance(actual, np.ndarray):
            actual = np.asarray(actual)
        self.raw_samples = actual
        self.flags = flags
        self.crc_ok = crc_ok
        self.meaningful_bits = meaningful_bits
        self.sample_rate_hz = sample_rate_hz

    @property
    def samples(self) -> np.ndarray:
        return self.raw_samples


def packet_to_sample_block(
    packet: DeviceSamplePacket,
    sample_rate_hz: Optional[int] = None,
    profile: Optional[AcquisitionProfile] = None,
) -> SampleBlock:
    """Adapter converting semantic DeviceSamplePacket into pcg_core SampleBlock.

    Normalizes signed integer container samples (e.g. 24-bit signed PCM carried in
    32-bit container) to [-1.0, +1.0] float32 for DSP pipeline consumption,
    preserving full acquisition sample rate (e.g. 48000 Hz) and timestamp metadata.
    """
    if not packet.crc_ok:
        raise ValueError(f"Cannot convert packet with CRC failure at sequence {packet.sequence}")

    rate = sample_rate_hz or (profile.preferred_sample_rate_hz if profile else packet.sample_rate_hz)
    raw = packet.raw_samples
    meaningful_bits = profile.meaningful_data_bits if profile else packet.meaningful_bits

    if np.issubdtype(raw.dtype, np.floating):
        normalized = raw.astype(np.float32)
    elif np.issubdtype(raw.dtype, np.integer):
        min_legal = -(1 << (meaningful_bits - 1))
        max_legal = (1 << (meaningful_bits - 1)) - 1

        if len(raw) > 0:
            raw_min = int(np.min(raw))
            raw_max = int(np.max(raw))
            if raw_min < min_legal or raw_max > max_legal:
                raise ValueError(
                    f"Raw sample integer out of legal {meaningful_bits}-bit signed range "
                    f"[{min_legal}, {max_legal}]: min found {raw_min}, max found {raw_max}"
                )

        scale = float(1 << (meaningful_bits - 1))
        normalized = (raw.astype(np.float32) / scale).astype(np.float32)
    else:
        normalized = np.asarray(raw, dtype=np.float32)

    return SampleBlock(
        sequence=packet.sequence,
        timestamp_s=packet.timestamp_s,
        sample_rate_hz=rate,
        samples=normalized,
    )


class DevicePacketDecoder(ABC):
    """Abstract codec interface for converting raw physical transport bytes to packets."""

    @abstractmethod
    def feed_bytes(self, chunk: bytes) -> list[DeviceSamplePacket]:
        """Process incoming raw wire bytes and return any completed packets."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal parsing buffer."""
        pass


def crc16_ccitt(data: bytes, init: int = 0xFFFF, poly: int = 0x1021) -> int:
    """CRC-16-CCITT computation over byte data.

    NOTE: Polynomial, initialization, reflection, and coverage remain PROPOSED / NOT APPROVED
    pending joint B->C sign-off (DW03-09).
    """
    crc = init
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def build_test_frame(
    sequence: int,
    timestamp_us: int,
    raw_samples: np.ndarray,
    flags: int = 0,
    corrupt_crc: bool = False,
    magic: bytes = b"\xaa\x55",
    version: int = 1,
    msg_type: int = 1,
) -> bytes:
    """Helper generating raw wire frame bytes for test transports.

    Layout (16-byte header + payload + 2-byte CRC):
    Magic (2B) | Ver (1B) | Type (1B) | Seq (4B) | Timestamp (4B) | Count (2B) | Flags (2B) | Payload (N*4B) | CRC (2B)
    """
    count = len(raw_samples)
    payload = np.asarray(raw_samples, dtype="<i4").tobytes()
    header = struct.pack("<2sBBIIHH", magic, version, msg_type, sequence, timestamp_us, count, flags)
    body = header + payload
    crc = crc16_ccitt(body)
    if corrupt_crc:
        crc ^= 0xFFFF
    return body + struct.pack("<H", crc)


class ReferenceFramedPacketDecoder(DevicePacketDecoder):
    """Illustrative reference decoder demonstrating robust multi-fragment frame assembly.

    NOTE: The byte-level wire format is PROPOSED / NOT APPROVED pending joint Module B/C agreement.
    This reference decoder demonstrates the transport supervisor's ability to:
    - Buffer fragmented chunk reads until a complete frame is assembled.
    - Recover framing synchronization after encountering garbage bytes or line noise.
    - Slice concatenated / combined frames arriving in a single read.
    - Reject corrupted frames via application CRC-16 check.
    """

    MAGIC: bytes = b"\xaa\x55"
    HEADER_SIZE: int = 16

    def __init__(self, meaningful_bits: int = 24, sample_rate_hz: int = 48000) -> None:
        self.meaningful_bits = meaningful_bits
        self.sample_rate_hz = sample_rate_hz
        self._buffer = bytearray()
        self._malformed_count = 0
        self._crc_failure_count = 0

    def reset(self) -> None:
        """Reset internal parser assembly buffer."""
        self._buffer.clear()

    @property
    def buffer_len(self) -> int:
        return len(self._buffer)

    @property
    def malformed_count(self) -> int:
        return self._malformed_count

    @property
    def crc_failure_count(self) -> int:
        return self._crc_failure_count

    def feed_bytes(self, chunk: bytes) -> list[DeviceSamplePacket]:
        """Process incoming raw wire bytes and assemble completed frames.

        CRITICAL GUARANTEE:
        A fragmented byte read is NEVER emitted prematurely as a complete frame.
        The buffer retains partial frames until all bytes (header + payload + CRC) arrive.
        """
        if not chunk:
            return []

        self._buffer.extend(chunk)
        packets: list[DeviceSamplePacket] = []

        while len(self._buffer) >= self.HEADER_SIZE:
            magic_idx = self._buffer.find(self.MAGIC)
            if magic_idx == -1:
                # No sync magic found; retain only the last byte (in case it is 0xAA)
                if len(self._buffer) > 1:
                    del self._buffer[:-1]
                break

            if magic_idx > 0:
                # Discard garbage preceding sync magic
                del self._buffer[:magic_idx]
                if len(self._buffer) < self.HEADER_SIZE:
                    break

            header_bytes = bytes(self._buffer[:self.HEADER_SIZE])
            magic, ver, mtype, seq, ts_us, count, flags = struct.unpack("<2sBBIIHH", header_bytes)

            if ver != 1 or mtype != 1 or count == 0 or count > 4096:
                # Invalid header: skip magic and search again
                self._malformed_count += 1
                del self._buffer[:2]
                continue

            payload_len = count * 4
            total_frame_len = self.HEADER_SIZE + payload_len + 2

            if len(self._buffer) < total_frame_len:
                # Fragmented read: wait for subsequent bytes!
                break

            frame_bytes = bytes(self._buffer[:total_frame_len])
            del self._buffer[:total_frame_len]

            crc_received = struct.unpack("<H", frame_bytes[-2:])[0]
            crc_computed = crc16_ccitt(frame_bytes[:-2])

            if crc_received != crc_computed:
                self._crc_failure_count += 1
                pkt = DeviceSamplePacket(
                    sequence=seq,
                    timestamp_s=float(ts_us) / 1_000_000.0,
                    raw_samples=np.zeros(0, dtype=np.int32),
                    flags=flags,
                    crc_ok=False,
                    meaningful_bits=self.meaningful_bits,
                    sample_rate_hz=self.sample_rate_hz,
                )
                packets.append(pkt)
                continue

            payload_bytes = frame_bytes[self.HEADER_SIZE:-2]
            raw_samples = np.frombuffer(payload_bytes, dtype="<i4")

            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=float(ts_us) / 1_000_000.0,
                raw_samples=raw_samples,
                flags=flags,
                crc_ok=True,
                meaningful_bits=self.meaningful_bits,
                sample_rate_hz=self.sample_rate_hz,
            )
            packets.append(pkt)

        return packets


# ==============================================================================
# 5. Physical Transport Abstraction
# ==============================================================================

@runtime_checkable
class DeviceTransport(Protocol):
    """Abstract interface for physical byte transport (USB-CDC, USB-Bulk, or test double)."""

    def open(self) -> bool:
        """Open physical transport connection."""
        ...

    def close(self) -> None:
        """Close physical transport connection."""
        ...

    def is_connected(self) -> bool:
        """Return True if physical transport link is currently established."""
        ...

    def read(self, max_bytes: int = 4096, timeout_s: float = 0.1) -> bytes:
        """Read available raw wire bytes from the device."""
        ...

    def write_control(self, data: bytes) -> int:
        """Send control or command message to device."""
        ...


# ==============================================================================
# 5.1 Transport Configuration & Factory Interfaces
# ==============================================================================

class TransportType(str, Enum):
    """Supported physical and test transport classes."""
    CDC_ACM = "cdc_acm"
    VENDOR_BULK = "vendor_bulk"
    TEST_DOUBLE = "test_double"


@dataclass(slots=True)
class TransportConfig(ABC):
    """Abstract configuration interface for physical device transports."""
    transport_type: TransportType

    @abstractmethod
    def validate(self) -> None:
        """Validate configuration parameters."""
        pass

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CdcAcmTransportConfig(TransportConfig):
    """Configuration interface for USB CDC-ACM (Virtual COM port) transport.

    NOTE: CDC-ACM is the Hardware Rev-A proposal under review (DW03-12).
    """
    transport_type: TransportType = field(default=TransportType.CDC_ACM, init=False)
    port: Optional[str] = None
    baudrate: int = 115200
    timeout_s: float = 0.1
    dtr: bool = True
    rts: bool = True
    read_buffer_size: int = 4096

    def validate(self) -> None:
        if self.baudrate <= 0:
            raise ValueError(f"Invalid baudrate: {self.baudrate}")
        if self.timeout_s < 0:
            raise ValueError(f"Timeout cannot be negative: {self.timeout_s}")


@dataclass(slots=True)
class VendorBulkTransportConfig(TransportConfig):
    """Configuration interface for USB Vendor Bulk (WinUSB / pyusb) transport.

    NOTE: Vendor Bulk is an alternative transport under review (DW03-12).
    """
    transport_type: TransportType = field(default=TransportType.VENDOR_BULK, init=False)
    vid: Optional[int] = None
    pid: Optional[int] = None
    read_endpoint: int = 0x81
    write_endpoint: int = 0x01
    timeout_ms: int = 100
    read_buffer_size: int = 4096

    def validate(self) -> None:
        if self.timeout_ms < 0:
            raise ValueError(f"Timeout cannot be negative: {self.timeout_ms}")
        if self.read_endpoint == self.write_endpoint:
            raise ValueError("Read and write endpoints cannot be identical")


@dataclass(slots=True)
class TestTransportConfig(TransportConfig):
    """Configuration for test-only in-memory or scripted transports."""
    __test__ = False
    transport_type: TransportType = field(default=TransportType.TEST_DOUBLE, init=False)
    read_buffer_size: int = 4096

    def validate(self) -> None:
        pass


class TransportFactory(ABC):
    """Pluggable factory interface for constructing physical device transports."""
    @abstractmethod
    def create_transport(self, config: TransportConfig) -> DeviceTransport:
        pass


class PendingHardwareTransportFactory(TransportFactory):
    """Production factory declaring that concrete USB class adapter is pending Module B sign-off."""
    def create_transport(self, config: TransportConfig) -> DeviceTransport:
        raise NotImplementedError(
            f"Concrete host transport adapter for {config.transport_type.value!r} is pending "
            f"joint B->C protocol approval (DW03-12). Use test-only transport doubles for development."
        )


# ==============================================================================
# 5.2 Transport Lifecycle Supervisor
# ==============================================================================

class TransportSupervisor:
    """Robust lifecycle supervisor for physical device transport read loops.

    Guarantees:
    - Single-reader ownership: raises TransportConcurrentOwnershipError if started concurrently.
    - Graceful cancellation and join timeouts: guarantees no orphan threads or leaked handles.
    - Bounded buffering: drops or throttles with explicit error / telemetry accounting rather than
      unbounded memory growth.
    - Resource cleanup: guarantees transport close() and decoder reset() on stop/disconnect/error.
    - Fragmented read assembly: passes raw chunks to DevicePacketDecoder, ensuring partial frames
      are buffered until complete.
    - Explicit error propagation: categorizes disconnects, timeouts, and framing errors with
      runtime event logging.
    """

    def __init__(
        self,
        transport: DeviceTransport,
        decoder: DevicePacketDecoder,
        read_chunk_size: int = 4096,
        read_timeout_s: float = 0.05,
        bounded_queue_size: int = 100,
        event_log: Optional[DeviceEventLog] = None,
        stats: Optional[DeviceIntegrityStats] = None,
    ) -> None:
        self.transport = transport
        self.decoder = decoder
        self.read_chunk_size = read_chunk_size
        self.read_timeout_s = read_timeout_s
        self.bounded_queue_size = bounded_queue_size
        self.event_log = event_log
        self.stats = stats

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._is_running = False
        self._on_packet_cb: Optional[Callable[[DeviceSamplePacket], None]] = None
        self._on_disconnect_cb: Optional[Callable[[str], None]] = None
        self._on_error_cb: Optional[Callable[[Exception], None]] = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running and self._thread is not None and self._thread.is_alive()

    def start(
        self,
        on_packet: Callable[[DeviceSamplePacket], None],
        on_disconnect: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Start the background transport reader thread with single-reader ownership enforcement."""
        with self._lock:
            if self._is_running or (self._thread is not None and self._thread.is_alive()):
                raise TransportConcurrentOwnershipError(
                    "Cannot start TransportSupervisor: reader loop is already active. "
                    "Concurrent reader ownership is prohibited."
                )

            if not self.transport.is_connected():
                raise TransportDisconnectedError(
                    "Cannot start TransportSupervisor: transport is not connected."
                )

            self._on_packet_cb = on_packet
            self._on_disconnect_cb = on_disconnect
            self._on_error_cb = on_error
            self._stop_event.clear()
            self._is_running = True

            self._thread = threading.Thread(
                target=self._run_loop,
                name="AuscultaForge-TransportSupervisor",
                daemon=True,
            )
            self._thread.start()

            if self.event_log:
                self.event_log.log(
                    "SUPERVISOR_STARTED",
                    "Transport supervisor background read loop started",
                    severity="info",
                )

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop the background reader thread cleanly and wait for it to join."""
        with self._lock:
            if not self._is_running and (self._thread is None or not self._thread.is_alive()):
                return
            self._stop_event.set()
            self._is_running = False

        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=timeout_s)
            if self._thread.is_alive() and self.event_log:
                self.event_log.log(
                    "SUPERVISOR_JOIN_TIMEOUT",
                    f"Transport supervisor thread did not exit within {timeout_s}s",
                    severity="warning",
                )

        with self._lock:
            self._cleanup_resources()
            self._thread = None
            if self.event_log:
                self.event_log.log(
                    "SUPERVISOR_STOPPED",
                    "Transport supervisor background read loop stopped cleanly",
                    severity="info",
                )

    def _cleanup_resources(self) -> None:
        try:
            self.decoder.reset()
        except Exception:
            pass
        try:
            self.transport.close()
        except Exception:
            pass

    def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                if not self.transport.is_connected():
                    self._handle_disconnect("Physical transport link disconnected")
                    break

                try:
                    chunk = self.transport.read(
                        max_bytes=self.read_chunk_size,
                        timeout_s=self.read_timeout_s,
                    )
                except (TimeoutError, TransportTimeoutError):
                    continue
                except TransportDisconnectedError as e:
                    self._handle_disconnect(str(e))
                    break
                except Exception as e:
                    if self._stop_event.is_set():
                        break
                    self._handle_error(e)
                    break

                if not chunk:
                    if not self.transport.is_connected():
                        self._handle_disconnect("EOF / Link terminated")
                        break
                    continue

                try:
                    packets = self.decoder.feed_bytes(chunk)
                except Exception as e:
                    if self.stats:
                        self.stats.record_malformed_frame()
                    if self.event_log:
                        self.event_log.log(
                            "DECODER_MALFORMED_FRAME",
                            f"Decoder error on wire chunk: {e}",
                            severity="warning",
                        )
                    continue

                for packet in packets:
                    if self._stop_event.is_set():
                        break
                    try:
                        if self._on_packet_cb:
                            self._on_packet_cb(packet)
                    except Exception as e:
                        if self.event_log:
                            self.event_log.log(
                                "PACKET_DISPATCH_ERROR",
                                f"Error dispatching packet: {e}",
                                severity="error",
                            )
        finally:
            with self._lock:
                self._is_running = False
                self._cleanup_resources()

    def _handle_disconnect(self, reason: str) -> None:
        if self.event_log:
            self.event_log.log("TRANSPORT_DISCONNECTED", reason, severity="warning")
        if self._on_disconnect_cb and not self._stop_event.is_set():
            try:
                self._on_disconnect_cb(reason)
            except Exception:
                pass

    def _handle_error(self, err: Exception) -> None:
        if self.event_log:
            self.event_log.log("TRANSPORT_ERROR", str(err), severity="error")
        if self._on_error_cb and not self._stop_event.is_set():
            try:
                self._on_error_cb(err)
            except Exception:
                pass


# ==============================================================================
# 5.3 Test-Only Injectable Transport Double
# ==============================================================================

class InjectableTestTransport:
    """Test-only injectable physical transport double for host readiness verification.

    Provides fine-grained test hooks for simulating:
    - Fragmented chunk reads (sub-frame byte slicing)
    - Concatenated / combined byte reads (multiple frames packed into single read)
    - Read timeouts (TimeoutError / empty chunks)
    - Buffer overflow conditions
    - Injected transport read errors
    - Sudden mid-stream physical cable disconnects
    """

    def __init__(self, should_fail_open: bool = False) -> None:
        self.should_fail_open = should_fail_open
        self._is_connected: bool = False
        self._chunks: list[bytes] = []
        self._control_writes: list[bytes] = []
        self._simulate_timeout: bool = False
        self._simulated_error: Optional[Exception] = None
        self._lock = threading.Lock()

    def open(self) -> bool:
        if self.should_fail_open:
            return False
        self._is_connected = True
        return True

    def close(self) -> None:
        self._is_connected = False

    def is_connected(self) -> bool:
        return self._is_connected

    def read(self, max_bytes: int = 4096, timeout_s: float = 0.05) -> bytes:
        with self._lock:
            if not self._is_connected:
                raise TransportDisconnectedError("Transport is disconnected")

            if self._simulated_error:
                err = self._simulated_error
                self._simulated_error = None
                raise err

            if self._simulate_timeout:
                raise TimeoutError(f"Simulated read timeout after {timeout_s}s")

            if not self._chunks:
                time.sleep(min(timeout_s, 0.01))
                return b""

            chunk = self._chunks.pop(0)
            if len(chunk) > max_bytes:
                rem = chunk[max_bytes:]
                self._chunks.insert(0, rem)
                chunk = chunk[:max_bytes]
            return chunk

    def write_control(self, data: bytes) -> int:
        with self._lock:
            self._control_writes.append(data)
            return len(data)

    # Injectable test helpers
    def push_bytes(self, data: bytes, chunk_size: Optional[int] = None) -> None:
        """Push raw byte sequence into transport, optionally sliced into fragments."""
        with self._lock:
            if chunk_size is not None and chunk_size > 0:
                for i in range(0, len(data), chunk_size):
                    self._chunks.append(data[i : i + chunk_size])
            else:
                self._chunks.append(data)

    def push_chunk(self, chunk: bytes) -> None:
        with self._lock:
            self._chunks.append(chunk)

    def push_combined_frames(self, frames: list[bytes]) -> None:
        """Push multiple complete frames concatenated into a single chunk."""
        combined = b"".join(frames)
        self.push_chunk(combined)

    def simulate_timeout(self, enabled: bool = True) -> None:
        with self._lock:
            self._simulate_timeout = enabled

    def simulate_error(self, exc: Exception) -> None:
        with self._lock:
            self._simulated_error = exc

    def simulate_disconnect(self) -> None:
        with self._lock:
            self._is_connected = False

    @property
    def pending_chunks_count(self) -> int:
        with self._lock:
            return len(self._chunks)

    @property
    def control_writes(self) -> list[bytes]:
        with self._lock:
            return list(self._control_writes)


# ==============================================================================
# 6. Device Discovery Abstraction
# ==============================================================================

@dataclass(slots=True)
class DeviceCandidate:
    """Discovered candidate physical hardware probe."""
    device_id: str
    descriptor: str
    detected_at_utc: str
    transport_hint: str = "native_usb"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeviceDiscoveryProvider(ABC):
    """Abstract discovery provider scanning system hardware buses."""

    @abstractmethod
    def poll_candidates(self) -> list[DeviceCandidate]:
        """Scan system and return list of compatible detected hardware probes."""
        pass

    @abstractmethod
    def get_status_description(self) -> str:
        """Human-readable status of the hardware discovery provider."""
        pass


class PendingDescriptorDiscoveryProvider(DeviceDiscoveryProvider):
    """Truthful production provider reflecting that USB descriptors are not yet finalized.

    ESP32-S3 Native USB is finalized as physical transport technology.
    CDC-ACM is the current Hardware Rev-A proposal under team review.
    Host transport driver implementation remains pending firmware descriptor/endpoint availability.
    """

    def poll_candidates(self) -> list[DeviceCandidate]:
        # Truthful behavior: No hardware driver claimed until ESP32-S3 descriptors are finalized
        return []

    def get_status_description(self) -> str:
        return (
            "Hardware discovery pending Phase-1 ESP32-S3 Native USB descriptors "
            "(Hardware Rev-A proposal: CDC-ACM under review)"
        )


# ==============================================================================
# 7. Runtime Integrity Telemetry Counters
# ==============================================================================

@dataclass(slots=True)
class DeviceIntegrityStats:
    """Runtime integrity counters for streaming hardware telemetry.

    Strictly exposes counters maintained by runtime code with zero decorative fields:
    - packets_received
    - samples_received
    - sequence_gaps
    - repeated_packets
    - out_of_order_packets
    - crc_failures
    - malformed_frames
    - timestamp_regressions
    - disconnect_count
    - reconnect_count
    """
    packets_received: int = 0
    samples_received: int = 0
    sequence_gaps: int = 0
    repeated_packets: int = 0
    out_of_order_packets: int = 0
    crc_failures: int = 0
    malformed_frames: int = 0
    timestamp_regressions: int = 0
    disconnect_count: int = 0
    reconnect_count: int = 0
    last_valid_sequence: Optional[int] = None
    last_valid_timestamp_s: Optional[float] = None

    def record_packet(self, packet: DeviceSamplePacket) -> None:
        """Update integrity counters upon receiving a semantic packet."""
        if not packet.crc_ok:
            self.crc_failures += 1
            return

        self.packets_received += 1
        self.samples_received += len(packet.raw_samples)

        if self.last_valid_sequence is not None:
            expected = self.last_valid_sequence + 1
            if packet.sequence == self.last_valid_sequence:
                self.repeated_packets += 1
            elif packet.sequence < self.last_valid_sequence:
                self.out_of_order_packets += 1
            elif packet.sequence > expected:
                self.sequence_gaps += (packet.sequence - expected)

        if self.last_valid_timestamp_s is not None and packet.timestamp_s < self.last_valid_timestamp_s:
            self.timestamp_regressions += 1

        self.last_valid_sequence = packet.sequence
        self.last_valid_timestamp_s = packet.timestamp_s

    def record_malformed_frame(self) -> None:
        """Increment count of malformed frames received from decoder/wire."""
        self.malformed_frames += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "packets_received": self.packets_received,
            "samples_received": self.samples_received,
            "sequence_gaps": self.sequence_gaps,
            "repeated_packets": self.repeated_packets,
            "out_of_order_packets": self.out_of_order_packets,
            "crc_failures": self.crc_failures,
            "malformed_frames": self.malformed_frames,
            "timestamp_regressions": self.timestamp_regressions,
            "disconnect_count": self.disconnect_count,
            "reconnect_count": self.reconnect_count,
        }


# ==============================================================================
# 8. Structured Device Event Log
# ==============================================================================

@dataclass(slots=True)
class DeviceEvent:
    """Structured audit trail event for the Diagnostics terminal."""
    id: str
    timestamp_utc: str
    severity: str  # "info" | "warning" | "error"
    code: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeviceEventLog:
    """Bounded circular in-memory log for real device events."""

    def __init__(self, max_entries: int = 200) -> None:
        self.max_entries = max_entries
        self._entries: list[DeviceEvent] = []

    def log(
        self,
        code: str,
        message: str,
        severity: str = "info",
        metadata: Optional[dict[str, Any]] = None,
    ) -> DeviceEvent:
        now_str = datetime.now(timezone.utc).isoformat()
        evt = DeviceEvent(
            id=f"dev-evt-{uuid.uuid4().hex[:8]}",
            timestamp_utc=now_str,
            severity=severity,
            code=code,
            message=message,
            metadata=metadata or {},
        )
        self._entries.append(evt)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)
        return evt

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries[-limit:]]

    def clear(self) -> None:
        self._entries.clear()


# ==============================================================================
# 9. Device Runtime Manager
# ==============================================================================

class DeviceRuntime:
    """Authoritative physical device manager coordinating lifecycle, transport, and telemetry."""

    def __init__(
        self,
        discovery_provider: Optional[DeviceDiscoveryProvider] = None,
        acquisition_profile: Optional[AcquisitionProfile] = None,
        event_log_size: int = 200,
    ) -> None:
        self.discovery_provider: DeviceDiscoveryProvider = (
            discovery_provider or PendingDescriptorDiscoveryProvider()
        )
        self.profile: AcquisitionProfile = acquisition_profile or REV_A_BASELINE_PROFILE
        self.event_log = DeviceEventLog(max_entries=event_log_size)
        self.stats = DeviceIntegrityStats()

        # State fields
        self._state: DeviceState = DeviceState.ABSENT
        self._active_candidate: Optional[DeviceCandidate] = None
        self._active_transport: Optional[DeviceTransport] = None
        self._decoder: Optional[DevicePacketDecoder] = None
        self._supervisor: Optional[TransportSupervisor] = None
        self._capabilities: Optional[DeviceCapabilities] = None
        self._last_error: Optional[str] = None
        self._connected_at_utc: Optional[str] = None
        self._disconnected_at_utc: Optional[str] = None

    @property
    def state(self) -> DeviceState:
        return self._state

    @property
    def capabilities(self) -> Optional[DeviceCapabilities]:
        return self._capabilities

    @property
    def active_candidate(self) -> Optional[DeviceCandidate]:
        return self._active_candidate

    @property
    def active_transport(self) -> Optional[DeviceTransport]:
        return self._active_transport

    @property
    def decoder(self) -> Optional[DevicePacketDecoder]:
        return self._decoder

    @property
    def supervisor(self) -> Optional[TransportSupervisor]:
        return self._supervisor

    def transition_to(self, new_state: DeviceState, error_msg: Optional[str] = None) -> None:
        """Transition device to a new lifecycle state following ALLOWED_TRANSITIONS."""
        if new_state == self._state:
            return

        valid_targets = ALLOWED_TRANSITIONS.get(self._state, set())
        if new_state not in valid_targets:
            msg = f"Illegal device state transition: {self._state.value} -> {new_state.value}"
            self.event_log.log("INVALID_STATE_TRANSITION", msg, severity="error")
            raise InvalidStateTransitionError(msg)

        old_state = self._state
        self._state = new_state

        if error_msg:
            self._last_error = error_msg
            self.event_log.log(
                "DEVICE_ERROR",
                f"Device transitioned to {new_state.value}: {error_msg}",
                severity="error",
                metadata={"from_state": old_state.value, "to_state": new_state.value},
            )
        else:
            self.event_log.log(
                f"STATE_{new_state.value.upper()}",
                f"Device state changed from {old_state.value} to {new_state.value}",
                severity="info",
                metadata={"from_state": old_state.value, "to_state": new_state.value},
            )

        if new_state == DeviceState.READY and old_state == DeviceState.HANDSHAKING:
            self._connected_at_utc = datetime.now(timezone.utc).isoformat()
            if self.stats.disconnect_count > 0:
                self.stats.reconnect_count += 1

        elif new_state in (DeviceState.INTERRUPTED, DeviceState.ABSENT):
            if old_state in (DeviceState.STREAMING, DeviceState.READY):
                self._disconnected_at_utc = datetime.now(timezone.utc).isoformat()
                self.stats.disconnect_count += 1

    def attach_candidate(self, candidate: DeviceCandidate) -> None:
        """Handle candidate device arrival from discovery layer."""
        self._active_candidate = candidate
        self.transition_to(DeviceState.DETECTED)
        self.event_log.log(
            "DEVICE_DETECTED",
            f"Candidate hardware probe detected: {candidate.device_id} ({candidate.descriptor})",
            severity="info",
            metadata={"device_id": candidate.device_id, "descriptor": candidate.descriptor},
        )

    def attach_transport(self, transport: DeviceTransport) -> None:
        """Attach physical transport and begin handshake."""
        self.transition_to(DeviceState.OPENING)
        try:
            opened = transport.open()
            if not opened:
                raise RuntimeError("Transport open() returned False")
            self._active_transport = transport
            self.transition_to(DeviceState.HANDSHAKING)
        except Exception as e:
            err = f"Failed to open transport: {e}"
            self.transition_to(DeviceState.ERROR, error_msg=err)
            raise

    def attach_decoder(self, decoder: DevicePacketDecoder) -> None:
        """Attach packet framing decoder to the device runtime."""
        self._decoder = decoder
        self.event_log.log(
            "DECODER_ATTACHED",
            f"Packet framing decoder attached: {decoder.__class__.__name__}",
            severity="info",
        )

    def complete_handshake(self, capabilities: DeviceCapabilities) -> None:
        """Validate reported capabilities against active profile and transition to READY."""
        if self._state != DeviceState.HANDSHAKING:
            raise InvalidStateTransitionError(
                f"Cannot complete handshake while in state {self._state.value}"
            )

        try:
            capabilities.validate_compatibility(self.profile)
            self._capabilities = capabilities

            # Compute defensible negotiated block size: cannot exceed device's advertised max_block_size
            negotiated = min(self.profile.preferred_block_size, capabilities.max_block_size)
            self.profile.negotiated_block_size = negotiated

            self.transition_to(DeviceState.READY)
            self.event_log.log(
                "HANDSHAKE_COMPLETE",
                f"Handshake validated for {capabilities.device_id} at {capabilities.sample_rate_hz} Hz ({capabilities.sample_format}), negotiated block size: {negotiated}",
                severity="info",
                metadata={**capabilities.to_dict(), "negotiated_block_size": negotiated},
            )
        except ValueError as e:
            err = f"Device rejected during handshake: {e}"
            self._capabilities = capabilities
            self.transition_to(DeviceState.INCOMPATIBLE, error_msg=err)
            self.event_log.log(
                "HANDSHAKE_REJECTED",
                err,
                severity="error",
                metadata=capabilities.to_dict(),
            )
            raise

    def start_supervisor(
        self,
        on_packet: Callable[[DeviceSamplePacket], None],
        on_disconnect: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> TransportSupervisor:
        """Initialize and start the supervised background transport read loop.

        Enforces single-reader ownership and safe state transition to STREAMING.
        """
        if not self._active_transport:
            raise RuntimeError("Cannot start supervisor: no transport attached")
        if not self._decoder:
            raise RuntimeError("Cannot start supervisor: no packet decoder attached")

        if self._supervisor is None:
            self._supervisor = TransportSupervisor(
                transport=self._active_transport,
                decoder=self._decoder,
                event_log=self.event_log,
                stats=self.stats,
            )

        self._supervisor.start(
            on_packet=on_packet,
            on_disconnect=on_disconnect,
            on_error=on_error,
        )

        if self._state == DeviceState.READY:
            self.start_streaming()

        return self._supervisor

    def stop_supervisor(self) -> None:
        """Stop supervisor cleanly, close transport handle, and join worker thread."""
        if self._supervisor:
            self._supervisor.stop()
            self._supervisor = None
        if self._state == DeviceState.STREAMING:
            self.stop_streaming()

    def start_streaming(self) -> None:
        """Transition device to STREAMING state."""
        self.transition_to(DeviceState.STREAMING)
        self.event_log.log("STREAM_STARTED", "Acoustic stream started from hardware", severity="info")

    def stop_streaming(self) -> None:
        """Transition device back to READY state cleanly."""
        if self._state == DeviceState.STREAMING:
            self.transition_to(DeviceState.READY)
            self.event_log.log("STREAM_STOPPED", "Acoustic stream stopped cleanly", severity="info")

    def handle_disconnect(self, error_msg: Optional[str] = None) -> None:
        """Handle hardware disconnect event cleanly without leaked handles or orphan threads."""
        # 1. Transition state according to current lifecycle state
        if self._state == DeviceState.STREAMING:
            self.transition_to(DeviceState.INTERRUPTED, error_msg=error_msg or "Physical link lost while streaming")
        elif self._state in (DeviceState.DETECTED, DeviceState.OPENING, DeviceState.HANDSHAKING, DeviceState.READY):
            self.transition_to(DeviceState.ABSENT, error_msg=error_msg or "Device detached from host")
        elif self._state in (DeviceState.ERROR, DeviceState.INCOMPATIBLE):
            self.transition_to(DeviceState.ABSENT)

        # 2. Stop supervisor and clean up background threads
        if self._supervisor:
            try:
                self._supervisor.stop()
            except Exception:
                pass
            self._supervisor = None

        # 3. Release physical transport handle
        if self._active_transport:
            try:
                self._active_transport.close()
            except Exception:
                pass
            self._active_transport = None

    def get_state_dict(self) -> dict[str, Any]:
        """Produce structured state representation for UI/WebSocket transport."""
        return {
            "state": self._state.value,
            "device_state": self._state.value,
            "connected": self._state in (DeviceState.READY, DeviceState.STREAMING),
            "is_connected": self._state in (DeviceState.READY, DeviceState.STREAMING),
            "device_id": self._capabilities.device_id if self._capabilities else (
                self._active_candidate.device_id if self._active_candidate else None
            ),
            "firmware_version": self._capabilities.firmware_version if self._capabilities else None,
            "sample_rate_hz": self._capabilities.sample_rate_hz if self._capabilities else None,
            "sample_format": self._capabilities.sample_format if self._capabilities else None,
            "channels": self._capabilities.channels if self._capabilities else None,
            "sample_container_bits": (
                self._capabilities.sample_container_bits
                if self._capabilities
                else self.profile.sample_container_bits
            ),
            "meaningful_data_bits": (
                self._capabilities.meaningful_data_bits
                if self._capabilities
                else self.profile.meaningful_data_bits
            ),
            "transport_type": self._active_candidate.transport_hint if self._active_candidate else None,
            "connected_at_utc": self._connected_at_utc,
            "disconnected_at_utc": self._disconnected_at_utc,
            "last_error": self._last_error,
            "discovery_status": self.discovery_provider.get_status_description(),
            "negotiated_block_size": self.profile.negotiated_block_size,
            "acquisition_profile": self.profile.to_dict(),
            "supervisor_active": self._supervisor.is_running if self._supervisor else False,
            "decoder_type": self._decoder.__class__.__name__ if self._decoder else None,
        }
