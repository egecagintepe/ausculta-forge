"""AuscultaForge Host-Side Canonical Session State Machine.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

Session Lifecycle:
DISCONNECTED -> HELLO_PENDING -> READY -> START_PENDING -> STREAMING -> STOPPING -> COMPLETE.
"""

from enum import Enum
import random
import time
from typing import Any, Callable, Dict, List, Optional
import numpy as np

try:
    from .protocol_codec import (
        StreamingProtocolDecoder,
        DecodedPacket,
        StatusTelemetry,
        StartReq,
        StartAck,
        StopReq,
        HelloReq,
        HelloAck,
        ErrorNotification,
        build_hello_req_packet,
        build_start_req_packet,
        build_stop_req_packet,
        MSG_TYPE_AUDIO_DATA,
        MSG_TYPE_HEARTBEAT_STATUS,
        MSG_TYPE_STREAM_START_REQ,
        MSG_TYPE_STREAM_START_ACK,
        MSG_TYPE_STREAM_STOP_REQ,
        MSG_TYPE_STREAM_STOP_ACK,
        MSG_TYPE_ERROR_NOTIFICATION,
        MSG_TYPE_HELLO_REQ,
        MSG_TYPE_HELLO_ACK,
        NOMINAL_SAMPLE_RATE_HZ,
        PROFILE_B_SAMPLES_PER_FRAME,
    )
except ImportError:
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
        build_hello_req_packet,
        build_start_req_packet,
        build_stop_req_packet,
        MSG_TYPE_AUDIO_DATA,
        MSG_TYPE_HEARTBEAT_STATUS,
        MSG_TYPE_STREAM_START_REQ,
        MSG_TYPE_STREAM_START_ACK,
        MSG_TYPE_STREAM_STOP_REQ,
        MSG_TYPE_STREAM_STOP_ACK,
        MSG_TYPE_ERROR_NOTIFICATION,
        MSG_TYPE_HELLO_REQ,
        MSG_TYPE_HELLO_ACK,
        NOMINAL_SAMPLE_RATE_HZ,
        PROFILE_B_SAMPLES_PER_FRAME,
    )


class SessionState(str, Enum):
    """Canonical host session lifecycle states."""
    DISCONNECTED  = "DISCONNECTED"
    HELLO_PENDING = "HELLO_PENDING"
    READY         = "READY"
    START_PENDING = "START_PENDING"
    STREAMING     = "STREAMING"
    STOPPING      = "STOPPING"
    COMPLETE      = "COMPLETE"
    ERROR         = "ERROR"


class HostProtocolSession:
    """Deterministic, testable host-side session manager for B/C protocol."""

    def __init__(self, sample_validator: Optional[Callable[[int, int], bool]] = None) -> None:
        self.state: SessionState = SessionState.DISCONNECTED
        self.active_session_id: Optional[int] = None
        self.host_nonce: Optional[int] = None
        self.device_capabilities: Optional[HelloAck] = None
        self.active_start_config: Optional[StartReq] = None
        self.latest_telemetry: Optional[StatusTelemetry] = None
        self.final_telemetry: Optional[StatusTelemetry] = None

        self.decoder = StreamingProtocolDecoder()
        self.sample_validator = sample_validator

        # Independent Host Sample Accounting
        self.host_samples_accepted: int = 0
        self.host_audio_frames_accepted: int = 0
        self.host_sample_value_errors: int = 0
        self.host_index_discontinuities: int = 0
        self.expected_next_sample_index: int = 0
        self.last_audio_sequence: Optional[int] = None

        # Diagnostic records
        self.error_log: List[str] = []
        self.received_audio_frames: List[DecodedPacket] = []

    def reset_session(self) -> None:
        """Invalidate session ID and reset accounting for new session."""
        self.active_session_id = None
        self.host_nonce = None
        self.active_start_config = None
        self.latest_telemetry = None
        self.final_telemetry = None

        self.host_samples_accepted = 0
        self.host_audio_frames_accepted = 0
        self.host_sample_value_errors = 0
        self.host_index_discontinuities = 0
        self.expected_next_sample_index = 0
        self.last_audio_sequence = None
        self.received_audio_frames.clear()

        self.decoder.reset()

    def initiate_handshake(self, host_nonce: Optional[int] = None) -> bytes:
        """Transition from DISCONNECTED to HELLO_PENDING and emit HELLO_REQ."""
        self.reset_session()
        if host_nonce is None:
            self.host_nonce = random.randint(1, 0xFFFFFFFF)
        else:
            self.host_nonce = host_nonce & 0xFFFFFFFF

        self.state = SessionState.HELLO_PENDING
        return build_hello_req_packet(self.host_nonce)

    def request_start(
        self,
        target_samples: int = 480000,
        source_mode: int = 1,
        sample_rate_hz: int = NOMINAL_SAMPLE_RATE_HZ,
        encoding: int = 1,
        channels: int = 1,
    ) -> bytes:
        """Transition from READY to START_PENDING and emit START_REQ."""
        if self.state != SessionState.READY:
            raise RuntimeError(f"Cannot request start in state {self.state}; must be READY.")

        self.active_start_config = StartReq(
            sample_rate_hz=sample_rate_hz,
            target_samples=target_samples,
            source_mode=source_mode,
            encoding=encoding,
            channels=channels,
            profile_id=2,  # Profile B
        )
        self.state = SessionState.START_PENDING
        return build_start_req_packet(self.active_start_config)

    def request_stop(self) -> bytes:
        """Transition to STOPPING and emit STOP_REQ."""
        if self.state not in (SessionState.STREAMING, SessionState.START_PENDING):
            raise RuntimeError(f"Cannot request stop in state {self.state}; must be STREAMING or START_PENDING.")

        if self.active_session_id is None:
            raise RuntimeError("Cannot stop without an active session ID.")

        self.state = SessionState.STOPPING
        return build_stop_req_packet(self.active_session_id)

    def handle_incoming_bytes(self, chunk: bytes) -> List[DecodedPacket]:
        """Feed bytes to decoder and dispatch decoded packets through the FSM."""
        packets = self.decoder.feed_bytes(chunk)
        for pkt in packets:
            self._dispatch_packet(pkt)
        return packets

    def _dispatch_packet(self, pkt: DecodedPacket) -> None:
        if not pkt.crc_ok:
            self.error_log.append(f"CRC error detected on seq {pkt.sequence_id}, opcode {pkt.msg_type}")
            return

        opcode = pkt.msg_type

        if opcode == MSG_TYPE_HELLO_ACK:
            self._handle_hello_ack(pkt)
        elif opcode == MSG_TYPE_STREAM_START_ACK:
            self._handle_start_ack(pkt)
        elif opcode == MSG_TYPE_AUDIO_DATA:
            self._handle_audio_frame(pkt)
        elif opcode == MSG_TYPE_HEARTBEAT_STATUS:
            self._handle_status(pkt)
        elif opcode == MSG_TYPE_STREAM_STOP_ACK:
            self._handle_stop_ack(pkt)
        elif opcode == MSG_TYPE_ERROR_NOTIFICATION:
            self._handle_error(pkt)

    def _handle_hello_ack(self, pkt: DecodedPacket) -> None:
        if self.state != SessionState.HELLO_PENDING:
            self.error_log.append(f"Unexpected HELLO_ACK received in state {self.state}")
            return

        ack: HelloAck = pkt.control_payload
        if ack.nonce_echo != self.host_nonce:
            self.state = SessionState.ERROR
            self.error_log.append(f"HELLO_ACK nonce mismatch: expected {self.host_nonce:#x}, got {ack.nonce_echo:#x}")
            return

        self.device_capabilities = ack
        self.state = SessionState.READY

    def _handle_start_ack(self, pkt: DecodedPacket) -> None:
        if self.state != SessionState.START_PENDING:
            self.error_log.append(f"Unexpected START_ACK received in state {self.state}")
            return

        ack: StartAck = pkt.control_payload
        if ack.session_id == 0:
            self.state = SessionState.ERROR
            self.error_log.append("Device returned invalid zero session_id in START_ACK")
            return

        self.active_session_id = ack.session_id

        # Deterministic sample counter reset
        self.host_samples_accepted = 0
        self.host_audio_frames_accepted = 0
        self.host_sample_value_errors = 0
        self.host_index_discontinuities = 0
        self.expected_next_sample_index = 0
        self.last_audio_sequence = None
        self.received_audio_frames.clear()

        self.state = SessionState.STREAMING

    def _handle_audio_frame(self, pkt: DecodedPacket) -> None:
        if self.state not in (SessionState.STREAMING, SessionState.STOPPING):
            self.error_log.append(f"AUDIO frame received in invalid state {self.state}")
            return

        # Check sample index continuity
        if pkt.sample_index_start != self.expected_next_sample_index:
            self.host_index_discontinuities += 1
            self.error_log.append(
                f"Sample index discontinuity: expected {self.expected_next_sample_index}, got {pkt.sample_index_start}"
            )

        # Validate samples if custom validator provided
        if self.sample_validator is not None:
            for i, val in enumerate(pkt.raw_samples):
                abs_idx = pkt.sample_index_start + i
                if not self.sample_validator(abs_idx, val):
                    self.host_sample_value_errors += 1

        self.host_samples_accepted += pkt.sample_count
        self.host_audio_frames_accepted += 1
        self.expected_next_sample_index = pkt.sample_index_start + pkt.sample_count
        self.last_audio_sequence = pkt.sequence_id
        self.received_audio_frames.append(pkt)

        # Check target samples auto-stop condition
        if self.active_start_config and self.active_start_config.target_samples > 0:
            if self.host_samples_accepted >= self.active_start_config.target_samples:
                if self.state == SessionState.STREAMING:
                    # Host target reached
                    pass

    def _handle_status(self, pkt: DecodedPacket) -> None:
        self.latest_telemetry = pkt.telemetry

    def _handle_stop_ack(self, pkt: DecodedPacket) -> None:
        if self.state != SessionState.STOPPING:
            self.error_log.append(f"Unexpected STOP_ACK received in state {self.state}")

        self.final_telemetry = pkt.telemetry
        self.latest_telemetry = pkt.telemetry
        self.state = SessionState.COMPLETE

    def _handle_error(self, pkt: DecodedPacket) -> None:
        err: ErrorNotification = pkt.control_payload
        self.error_log.append(f"Device reported ERROR: code={err.error_code}, context={err.error_context}")
        self.state = SessionState.ERROR

    def handle_disconnect(self) -> None:
        """Physical or transport disconnect event."""
        self.active_session_id = None
        self.state = SessionState.DISCONNECTED
        self.decoder.reset()

    def handle_timeout(self, context: str) -> None:
        """Handle timeout on expected device response."""
        self.error_log.append(f"Timeout occurred during operation: {context}")
        self.state = SessionState.ERROR
