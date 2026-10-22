"""AuscultaForge Host-Side Canonical Session State Machine.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

Session Lifecycle:
DISCONNECTED -> HELLO_PENDING -> READY -> START_PENDING -> STREAMING -> STOPPING -> COMPLETE.
"""

from collections import deque
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

    def __init__(
        self,
        sample_validator: Optional[Callable[[int, int], bool]] = None,
        max_stored_audio_frames: int = 128,
        diagnostic_journal: Optional[Any] = None,
    ) -> None:
        self.state: SessionState = SessionState.DISCONNECTED
        self.active_session_id: Optional[int] = None
        self.host_nonce: Optional[int] = None
        self.device_capabilities: Optional[HelloAck] = None
        self.active_start_config: Optional[StartReq] = None
        self.latest_telemetry: Optional[StatusTelemetry] = None
        self.final_telemetry: Optional[StatusTelemetry] = None
        self.diagnostic_journal = diagnostic_journal

        self.decoder = StreamingProtocolDecoder()
        self.sample_validator = sample_validator

        # Independent Host Sample Accounting
        self.host_samples_accepted: int = 0
        self.host_audio_frames_accepted: int = 0
        self.host_sample_value_errors: int = 0
        self.host_index_discontinuities: int = 0
        self.expected_next_sample_index: int = 0
        self.last_audio_sequence: Optional[int] = None

        # Diagnostic records & bounded memory ring for audio frames
        self.error_log: List[str] = []
        self.max_stored_audio_frames = max_stored_audio_frames
        self.received_audio_frames: deque = deque(maxlen=max_stored_audio_frames)

    def _emit_diagnostic(
        self,
        fault_code: str,
        message: str,
        severity: str = "ERROR",
        subsystem: str = "PROTOCOL",
        counter_snapshot: Optional[dict[str, Any]] = None,
    ) -> None:
        """Forward fault event to diagnostic journal if configured."""
        if self.diagnostic_journal is not None:
            try:
                from pcg_app.diagnostics.event_model import Severity, Subsystem, EvidenceOrigin
                sev = Severity(severity) if hasattr(Severity, severity) else Severity.ERROR
                sub = Subsystem(subsystem) if hasattr(Subsystem, subsystem) else Subsystem.PROTOCOL
                self.diagnostic_journal.record(
                    fault_code=fault_code,
                    message=message,
                    subsystem=sub,
                    severity=sev,
                    session_id=f"0x{self.active_session_id:08x}" if self.active_session_id else None,
                    counter_snapshot=counter_snapshot,
                    evidence_origin=EvidenceOrigin.REPORTED_BY_FIRMWARE if "Firmware" in message or "Device reported" in message else EvidenceOrigin.OBSERVED_HOST,
                )
            except Exception:
                pass

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
            self.state = SessionState.ERROR
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
            self.state = SessionState.ERROR
            raise RuntimeError(f"Cannot request stop in state {self.state}; must be STREAMING or START_PENDING.")

        if self.active_session_id is None:
            self.state = SessionState.ERROR
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
            self._emit_diagnostic(
                fault_code="AF-PRT-002",
                message=f"CRC error detected on seq {pkt.sequence_id}, opcode {pkt.msg_type}",
                severity="ERROR",
                subsystem="PROTOCOL",
            )
            self.state = SessionState.ERROR
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
            self.error_log.append(f"Unexpected or stale HELLO_ACK received in state {self.state}")
            self._emit_diagnostic("AF-PRT-007", f"Unexpected or stale HELLO_ACK in state {self.state}")
            self.state = SessionState.ERROR
            return

        ack: HelloAck = pkt.control_payload
        if ack.protocol_version_major != 1:
            self.error_log.append(f"HELLO_ACK protocol version mismatch: expected 1, got {ack.protocol_version_major}")
            self._emit_diagnostic(
                "AF-PRT-003",
                f"Protocol version mismatch: expected 1, device returned major {ack.protocol_version_major}",
            )
            self.state = SessionState.ERROR
            return
        if ack.nonce_echo != self.host_nonce:
            self.state = SessionState.ERROR
            self.error_log.append(f"HELLO_ACK nonce mismatch: expected {self.host_nonce:#x}, got {ack.nonce_echo:#x}")
            self._emit_diagnostic(
                "AF-PRT-004",
                f"HELLO nonce mismatch: expected {self.host_nonce:#x}, got {ack.nonce_echo:#x}",
            )
            return

        self.device_capabilities = ack
        self.state = SessionState.READY

    def _handle_start_ack(self, pkt: DecodedPacket) -> None:
        if self.state != SessionState.START_PENDING:
            self.error_log.append(f"Unexpected or stale START_ACK received in state {self.state}")
            self._emit_diagnostic("AF-PRT-007", f"Unexpected or stale START_ACK in state {self.state}")
            self.state = SessionState.ERROR
            return

        ack: StartAck = pkt.control_payload
        if ack.session_id == 0:
            self.state = SessionState.ERROR
            self.error_log.append("Device returned invalid zero session_id in START_ACK")
            self._emit_diagnostic("AF-PRT-006", "Device returned invalid zero session_id in START_ACK")
            return

        # Strict Configuration Verification
        if self.active_start_config is not None:
            mismatches = []
            if ack.accepted_sample_rate_hz != self.active_start_config.sample_rate_hz:
                mismatches.append(f"sample_rate expected {self.active_start_config.sample_rate_hz} got {ack.accepted_sample_rate_hz}")
            if ack.accepted_target_samples != self.active_start_config.target_samples:
                mismatches.append(f"target_samples expected {self.active_start_config.target_samples} got {ack.accepted_target_samples}")
            if ack.accepted_source_mode != self.active_start_config.source_mode:
                mismatches.append(f"source_mode expected {self.active_start_config.source_mode} got {ack.accepted_source_mode}")
            if ack.encoding != self.active_start_config.encoding:
                mismatches.append(f"encoding expected {self.active_start_config.encoding} got {ack.encoding}")
            if ack.channels != self.active_start_config.channels:
                mismatches.append(f"channels expected {self.active_start_config.channels} got {ack.channels}")
            if ack.profile_id != self.active_start_config.profile_id:
                mismatches.append(f"profile_id expected {self.active_start_config.profile_id} got {ack.profile_id}")

            if mismatches:
                msg = f"START_ACK configuration rejected: {', '.join(mismatches)}"
                self.state = SessionState.ERROR
                self.error_log.append(msg)
                self._emit_diagnostic("AF-PRT-005", msg)
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
            self._emit_diagnostic("AF-PRT-007", f"AUDIO frame received in invalid state {self.state}")
            self.state = SessionState.ERROR
            return

        if pkt.sample_count == 0:
            self.error_log.append("AUDIO frame with sample_count == 0 received")
            self._emit_diagnostic("AF-PRT-007", "AUDIO frame with zero sample_count received")
            self.state = SessionState.ERROR
            return

        # Check sequence continuity
        if self.last_audio_sequence is not None:
            expected_seq = (self.last_audio_sequence + 1) & 0xFFFF
            if pkt.sequence_id == self.last_audio_sequence:
                self._emit_diagnostic(
                    "AF-STR-002",
                    f"Duplicate audio frame sequence received: {pkt.sequence_id}",
                    severity="WARNING",
                    subsystem="STREAMING",
                )
            elif pkt.sequence_id != expected_seq:
                self._emit_diagnostic(
                    "AF-STR-001",
                    f"Frame sequence gap detected: expected {expected_seq}, got {pkt.sequence_id}",
                    severity="WARNING",
                    subsystem="STREAMING",
                )

        # Check sample index continuity
        if pkt.sample_index_start != self.expected_next_sample_index:
            self.host_index_discontinuities += 1
            msg = f"Sample index discontinuity: expected {self.expected_next_sample_index}, got {pkt.sample_index_start}"
            self.error_log.append(msg)
            self._emit_diagnostic("AF-STR-003", msg, severity="WARNING", subsystem="STREAMING")

        # Validate samples if custom validator provided
        if self.sample_validator is not None:
            for i, val in enumerate(pkt.raw_samples):
                abs_idx = pkt.sample_index_start + i
                if not self.sample_validator(abs_idx, val):
                    self.host_sample_value_errors += 1
                    if self.host_sample_value_errors == 1:
                        self._emit_diagnostic(
                            "AF-STR-009",
                            f"Sample verification failed at index {abs_idx} (observed {val})",
                            severity="ERROR",
                            subsystem="STREAMING",
                        )

        self.host_samples_accepted += pkt.sample_count
        self.host_audio_frames_accepted += 1
        self.expected_next_sample_index = pkt.sample_index_start + pkt.sample_count
        self.last_audio_sequence = pkt.sequence_id
        self.received_audio_frames.append(pkt)

        # Note: Target reached does NOT transition to COMPLETE. STOP_ACK is required.

    def _handle_status(self, pkt: DecodedPacket) -> None:
        self.latest_telemetry = pkt.telemetry
        if pkt.telemetry is not None:
            if pkt.telemetry.dropped_samples > 0:
                self._emit_diagnostic(
                    "AF-STR-005",
                    f"Firmware reported {pkt.telemetry.dropped_samples} dropped samples",
                    severity="WARNING",
                    subsystem="STREAMING",
                    counter_snapshot={"dropped_samples": pkt.telemetry.dropped_samples},
                )
            if pkt.telemetry.dma_overflow_events > 0:
                self._emit_diagnostic(
                    "AF-STR-006",
                    f"Firmware reported {pkt.telemetry.dma_overflow_events} DMA overflow events",
                    severity="ERROR",
                    subsystem="STREAMING",
                    counter_snapshot={"dma_overflow_events": pkt.telemetry.dma_overflow_events},
                )
            if pkt.telemetry.ring_overflow_events > 0:
                self._emit_diagnostic(
                    "AF-STR-007",
                    f"Firmware reported {pkt.telemetry.ring_overflow_events} ring buffer overflow events",
                    severity="ERROR",
                    subsystem="STREAMING",
                    counter_snapshot={"ring_overflow_events": pkt.telemetry.ring_overflow_events},
                )
            if pkt.telemetry.usb_partial_write_events > 0:
                self._emit_diagnostic(
                    "AF-STR-008",
                    f"Firmware reported {pkt.telemetry.usb_partial_write_events} USB partial write / backpressure events",
                    severity="WARNING",
                    subsystem="STREAMING",
                    counter_snapshot={"usb_partial_write_events": pkt.telemetry.usb_partial_write_events},
                )

    def _handle_stop_ack(self, pkt: DecodedPacket) -> None:
        if self.state != SessionState.STOPPING:
            self.error_log.append(f"Unexpected STOP_ACK received in state {self.state}")
            self._emit_diagnostic("AF-PRT-007", f"Unexpected STOP_ACK in state {self.state}")
            self.state = SessionState.ERROR
            return

        if pkt.telemetry is None:
            self.error_log.append("STOP_ACK packet missing telemetry payload")
            self._emit_diagnostic("AF-PRT-007", "STOP_ACK packet missing telemetry payload")
            self.state = SessionState.ERROR
            return

        if pkt.telemetry.session_id != self.active_session_id:
            msg = f"STOP_ACK session_id mismatch: expected {self.active_session_id:#x}, got {pkt.telemetry.session_id:#x}"
            self.error_log.append(msg)
            self._emit_diagnostic("AF-PRT-006", msg)
            self.state = SessionState.ERROR
            return

        self.final_telemetry = pkt.telemetry
        self.latest_telemetry = pkt.telemetry
        self.state = SessionState.COMPLETE

    def _handle_error(self, pkt: DecodedPacket) -> None:
        err: ErrorNotification = pkt.control_payload
        msg = f"Device reported ERROR: code={err.error_code}, context={err.error_context}"
        self.error_log.append(msg)
        self._emit_diagnostic(
            "AF-PRT-009",
            msg,
            severity="ERROR",
            subsystem="PROTOCOL",
            counter_snapshot={"firmware_error_code": err.error_code, "context": err.error_context},
        )
        self.state = SessionState.ERROR

    def handle_disconnect(self) -> None:
        """Physical or transport disconnect event."""
        msg = f"Transport disconnected (previous state: {self.state})"
        self.error_log.append(msg)
        self._emit_diagnostic("AF-USB-004", msg, severity="ERROR", subsystem="USB")
        self.active_session_id = None
        self.state = SessionState.DISCONNECTED
        self.decoder.reset()

    def handle_timeout(self, context: str) -> None:
        """Handle timeout on expected device response."""
        msg = f"Timeout occurred during operation: {context}"
        self.error_log.append(msg)
        self._emit_diagnostic("AF-USB-005", msg, severity="ERROR", subsystem="USB")
        self.state = SessionState.ERROR
