"""AuscultaForge — Single-Owner Bidirectional Canonical Session Engine.

Coordinates the real physical USB CDC-ACM (or simulated) transport in a dedicated,
single-owner worker thread. Eliminates competing readers, prevents race conditions,
enforces strict nonzero session IDs, handles command-response timeouts, and streams
canonical Profile B audio frames directly into the host runtime.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional

from .codec import (
    DecodedPacket,
    HelloAck,
    StartAck,
    StatusTelemetry,
    NOMINAL_SAMPLE_RATE_HZ,
    MSG_TYPE_AUDIO_DATA,
    MSG_TYPE_HEARTBEAT_STATUS,
    MSG_TYPE_STREAM_START_ACK,
    MSG_TYPE_STREAM_STOP_ACK,
    MSG_TYPE_HELLO_ACK,
    MSG_TYPE_ERROR_NOTIFICATION,
    compute_deterministic_g1_sample,
)
from .session import HostProtocolSession, SessionState
from .transport import (
    BaseTransportAdapter,
    TransportState,
    UsbCdcAcmAdapter,
    DuplexLoopbackAdapter,
)
from .simulator import SimulatedEsp32Device
from .acceptance import G1Observation, assess_g1


class EngineCommandType:
    HELLO = "HELLO"
    START = "START"
    STOP = "STOP"
    DISCONNECT = "DISCONNECT"


@dataclass
class EngineCommand:
    cmd_type: str
    future: concurrent.futures.Future
    deadline: float
    payload: Optional[Dict[str, Any]] = None


def _validate_g1_sample(idx: int, val: int) -> bool:
    return int(val) == compute_deterministic_g1_sample(idx)


class CanonicalSessionEngine:
    """Thread-safe, single-owner controller for AuscultaForge USB CDC-ACM communications."""

    def __init__(
        self,
        diagnostic_journal: Optional[Any] = None,
        on_audio_packet: Optional[Callable[[DecodedPacket], None]] = None,
        on_state_change: Optional[Callable[[SessionState], None]] = None,
        on_telemetry: Optional[Callable[[StatusTelemetry], None]] = None,
        on_disconnect: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.diagnostic_journal = diagnostic_journal
        self.on_audio_packet = on_audio_packet
        self.on_state_change = on_state_change
        self.on_telemetry = on_telemetry
        self.on_disconnect = on_disconnect
        self.on_error = on_error

        self.transport: Optional[BaseTransportAdapter] = None
        self.session: HostProtocolSession = HostProtocolSession(
            sample_validator=_validate_g1_sample,
            diagnostic_journal=diagnostic_journal,
        )

        self._thread: Optional[threading.Thread] = None
        self._cmd_queue: queue.Queue[EngineCommand] = queue.Queue()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Telemetry & Evidence Tracking
        self.port_name: Optional[str] = None
        self.is_simulated: bool = False
        self.last_g1_evidence: Optional[Dict[str, Any]] = None
        self.g1_observation = G1Observation()
        self.host_ingestion_errors = 0
        self.physical_transport_opened = False

    @property
    def state(self) -> SessionState:
        return self.session.state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_summary(self) -> Dict[str, Any]:
        """Return structured session status snapshot for REST API and UI."""
        caps = None
        if self.session.device_capabilities:
            c = self.session.device_capabilities
            caps = {
                "protocol_version": f"{c.protocol_version_major}.{c.protocol_version_minor}",
                "firmware_version": f"{c.firmware_version_major}.{c.firmware_version_minor}.{c.firmware_version_patch}",
                "hardware_sample_rate_hz": c.hardware_sample_rate_hz,
                "supported_profiles_mask": c.supported_profiles_mask,
                "max_frame_samples": c.max_frame_samples,
                "device_uid_low": f"0x{c.device_uid_low:08x}",
            }

        active_cfg = None
        if self.session.active_start_config:
            cfg = self.session.active_start_config
            active_cfg = {
                "sample_rate_hz": cfg.sample_rate_hz,
                "target_samples": cfg.target_samples,
                "source_mode": cfg.source_mode,
                "encoding": cfg.encoding,
                "channels": cfg.channels,
                "profile_id": cfg.profile_id,
            }

        last_telem = None
        if self.session.latest_telemetry:
            t = self.session.latest_telemetry
            last_telem = {
                "session_id": f"0x{t.session_id:08x}",
                "generated_samples": t.generated_samples,
                "queued_samples": t.fully_queued_samples,
                "dropped_samples": t.dropped_samples,
                "audio_frames_queued": t.audio_frames_queued,
                "dma_overflows": t.dma_overflow_events,
                "ring_overflows": t.ring_overflow_events,
                "usb_timeouts": t.usb_timeout_events,
                "stop_reason": t.stop_reason,
                "error_code": t.error_code,
            }

        final_telem = None
        if self.session.final_telemetry:
            ft = self.session.final_telemetry
            final_telem = {
                "session_id": f"0x{ft.session_id:08x}",
                "generated_samples": ft.generated_samples,
                "dropped_samples": ft.dropped_samples,
                "stop_reason": ft.stop_reason,
            }

        return {
            "session_state": self.session.state.value,
            "port": self.port_name,
            "is_simulated": self.is_simulated,
            "active_session_id": f"0x{self.session.active_session_id:08x}" if self.session.active_session_id else None,
            "device_capabilities": caps,
            "active_config": active_cfg,
            "counters": {
                "crc_errors": self.session.decoder.total_frames_corrupted,
                "sequence_gaps": self.session.decoder.total_sequence_gaps,
                "host_samples_accepted": self.session.host_samples_accepted,
                "host_frames_accepted": self.session.host_audio_frames_accepted,
                "host_sample_value_errors": self.session.host_sample_value_errors,
                "host_index_discontinuities": self.session.host_index_discontinuities,
                "expected_next_sample_index": self.session.expected_next_sample_index,
                "last_audio_sequence": self.session.last_audio_sequence,
            },
            "latest_telemetry": last_telem,
            "final_telemetry": final_telem,
            "has_g1_evidence": self.last_g1_evidence is not None,
        }

    # =========================================================================
    # Public Asynchronous Operations (Return concurrent.futures.Future)
    # =========================================================================

    def connect(
        self,
        port: str,
        baudrate: int = 115200,
        timeout_s: float = 3.0,
    ) -> concurrent.futures.Future[HelloAck]:
        """Open physical or simulated port and complete canonical HELLO handshake."""
        with self._lock:
            if self.is_running:
                raise RuntimeError("Session engine is already running. Disconnect first.")

            self.port_name = port
            self.physical_transport_opened = False
            self.session = HostProtocolSession(sample_validator=_validate_g1_sample,
                                               diagnostic_journal=self.diagnostic_journal)
            self._cmd_queue = queue.Queue(maxsize=32)
            self.last_g1_evidence = None
            self.is_simulated = (port.upper() in ("SIMULATED", "SIMULATED_ESP32_S3", "LOOPBACK"))

            if self.is_simulated:
                sim_dev = SimulatedEsp32Device()
                self.transport = DuplexLoopbackAdapter(sim_dev)
            else:
                self.transport = UsbCdcAcmAdapter()

            try:
                self.transport.open(port=port, baudrate=baudrate, timeout_s=0.5)
                self.physical_transport_opened = type(self.transport) is UsbCdcAcmAdapter
            except Exception as e:
                self.transport = None
                raise ConnectionError(f"Failed to open port '{port}': {e}") from e

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="AuscultaForge-USB-Worker",
                daemon=True,
            )
            self._thread.start()

            fut: concurrent.futures.Future[HelloAck] = concurrent.futures.Future()
            cmd = EngineCommand(
                cmd_type=EngineCommandType.HELLO,
                future=fut,
                deadline=time.monotonic() + timeout_s,
            )
            self._cmd_queue.put(cmd)
            return fut

    def start_acquisition(
        self,
        target_samples: int = 480000,
        source_mode: int = 1,
        sample_rate_hz: int = NOMINAL_SAMPLE_RATE_HZ,
        encoding: int = 1,
        channels: int = 1,
        timeout_s: float = 3.0,
    ) -> concurrent.futures.Future[StartAck]:
        """Request start of acquisition session (Mode 1: G1 deterministic, Mode 0: Acoustic)."""
        fut: concurrent.futures.Future[StartAck] = concurrent.futures.Future()
        if not self.is_running or self.session.state not in (SessionState.READY, SessionState.COMPLETE):
            fut.set_exception(RuntimeError(f"Cannot start acquisition in state {self.session.state.value}; must be READY."))
            return fut

        cmd = EngineCommand(
            cmd_type=EngineCommandType.START,
            future=fut,
            deadline=time.monotonic() + timeout_s,
            payload={
                "target_samples": target_samples,
                "source_mode": source_mode,
                "sample_rate_hz": sample_rate_hz,
                "encoding": encoding,
                "channels": channels,
            },
        )
        self._cmd_queue.put(cmd)
        return fut

    def stop_acquisition(
        self,
        timeout_s: float = 4.0,
    ) -> concurrent.futures.Future[StatusTelemetry]:
        """Request stop of active streaming session and await STOP_ACK."""
        fut: concurrent.futures.Future[StatusTelemetry] = concurrent.futures.Future()
        if not self.is_running or self.session.state not in (SessionState.STREAMING, SessionState.START_PENDING):
            fut.set_exception(RuntimeError(f"Cannot stop acquisition in state {self.session.state.value}."))
            return fut

        cmd = EngineCommand(
            cmd_type=EngineCommandType.STOP,
            future=fut,
            deadline=time.monotonic() + timeout_s,
        )
        self._cmd_queue.put(cmd)
        return fut

    def disconnect(self, timeout_s: float = 3.0) -> concurrent.futures.Future[None]:
        """Gracefully terminate session and close transport handle."""
        fut: concurrent.futures.Future[None] = concurrent.futures.Future()
        if not self.is_running:
            fut.set_result(None)
            return fut

        cmd = EngineCommand(
            cmd_type=EngineCommandType.DISCONNECT,
            future=fut,
            deadline=time.monotonic() + timeout_s,
        )
        self._cmd_queue.put(cmd)
        return fut

    # =========================================================================
    # Single-Owner Worker Thread Execution Loop
    # =========================================================================

    def _worker_loop(self) -> None:
        """Dedicated thread executing all transport reads, writes, and protocol dispatch."""
        pending_cmd: Optional[EngineCommand] = None
        disconnect_future = None

        while not self._stop_event.is_set():
            # 1. Process outbound command if not waiting for a synchronous ACK
            if pending_cmd is None and not self._cmd_queue.empty():
                try:
                    cmd = self._cmd_queue.get_nowait()
                    self._execute_outbound_command(cmd)
                    if cmd.cmd_type == EngineCommandType.DISCONNECT:
                        disconnect_future = cmd.future
                        break
                    if cmd.future.done():
                        continue
                    pending_cmd = cmd
                except queue.Empty:
                    pass

            # 2. Check pending command deadline
            if pending_cmd is not None and time.monotonic() > pending_cmd.deadline:
                err_msg = f"Transport operation {pending_cmd.cmd_type} timed out without device response."
                pending_cmd.future.set_exception(TimeoutError(err_msg))
                self.session.state = SessionState.ERROR
                self._notify_state_change()
                if self.on_error:
                    self.on_error(err_msg)
                pending_cmd = None

            # 3. Read incoming bytes from transport
            chunk = b""
            if self.transport is not None:
                try:
                    chunk = self.transport.read(max_bytes=4096)
                except Exception as e:
                    disc_msg = f"Transport read failure: {e}"
                    self._handle_transport_interruption(disc_msg, pending_cmd)
                    break

            # 4. Dispatch bytes through canonical session FSM
            if chunk:
                packets = self.session.decoder.feed_bytes(chunk)
                for pkt in packets:
                    self.session._dispatch_packet(pkt)
                    if self.session.active_start_config and self.session.active_start_config.source_mode == 1:
                        self.g1_observation.observe(pkt)
                    if not pkt.crc_ok:
                        continue

                    # Match pending commands with received acknowledgments
                    if pending_cmd is not None:
                        if (
                            pending_cmd.cmd_type == EngineCommandType.HELLO
                            and pkt.msg_type == MSG_TYPE_HELLO_ACK
                            and self.session.state == SessionState.READY
                        ):
                            pending_cmd.future.set_result(self.session.device_capabilities)
                            pending_cmd = None
                            self._notify_state_change()

                        elif (
                            pending_cmd.cmd_type == EngineCommandType.START
                            and pkt.msg_type == MSG_TYPE_STREAM_START_ACK
                            and self.session.state == SessionState.STREAMING
                        ):
                            pending_cmd.future.set_result(pkt.control_payload)
                            pending_cmd = None
                            self._notify_state_change()

                        elif (
                            pending_cmd.cmd_type == EngineCommandType.STOP
                            and pkt.msg_type == MSG_TYPE_STREAM_STOP_ACK
                            and self.session.state == SessionState.COMPLETE
                        ):
                            self._record_g1_evidence_if_applicable()
                            pending_cmd.future.set_result(self.session.final_telemetry)
                            pending_cmd = None
                            self._notify_state_change()

                        elif pkt.msg_type == MSG_TYPE_ERROR_NOTIFICATION:
                            err_notif = pkt.control_payload
                            action = {
                                1: "Invalid device state; disconnect, HELLO and retry.",
                                2: "Unsupported source: live mode needs a reviewed I2S firmware profile.",
                                3: "Session mismatch; reconnect and start a fresh session.",
                                4: "Unsupported configuration; use 48 kHz mono, encoding 1, Profile B.",
                                5: "Device transport fault; inspect cable, queue health and reconnect.",
                                6: "I2S acquisition fault; inspect clocks, wiring and the reviewed board profile.",
                            }.get(err_notif.error_code, "Save diagnostics and inspect firmware logs.")
                            pending_cmd.future.set_exception(
                                RuntimeError(f"{action} (firmware code 0x{err_notif.error_code:04x})")
                            )
                            pending_cmd = None
                            self._notify_state_change()

                    # Handle audio stream packets
                    if pkt.msg_type == MSG_TYPE_AUDIO_DATA and self.on_audio_packet and self.session.state in (SessionState.STREAMING,SessionState.STOPPING):
                        try:
                            if self.on_audio_packet(pkt) is False:
                                raise RuntimeError("StreamManager rejected acquisition samples")
                        except Exception as e:
                            self.host_ingestion_errors += 1
                            self.session._emit_diagnostic("AF-STR-007", f"Host ingestion failed: {e}")

                    # Handle periodic heartbeat telemetry
                    elif pkt.msg_type == MSG_TYPE_HEARTBEAT_STATUS and self.on_telemetry:
                        self.on_telemetry(pkt.control_payload)

                if self.session.state == SessionState.ERROR and self.session.active_start_config and self.session.active_start_config.source_mode == 1:
                    self.last_g1_evidence = assess_g1(self)

            else:
                if self.transport is not None and self.transport.get_state() != TransportState.CONNECTED:
                    self._handle_transport_interruption("USB transport disconnected or failed", pending_cmd)
                    break
                # No bytes read; yield thread briefly to prevent busy-spinning
                time.sleep(0.005)

        # Teardown
        self._teardown_transport()
        if disconnect_future is not None and not disconnect_future.done():
            disconnect_future.set_result(None)

    def _execute_outbound_command(self, cmd: EngineCommand) -> None:
        """Serialize and transmit outbound control packets."""
        if self.transport is None:
            cmd.future.set_exception(RuntimeError("Transport is not open."))
            return

        try:
            if cmd.cmd_type == EngineCommandType.HELLO:
                wire_bytes = self.session.initiate_handshake()
                written = self.transport.write(wire_bytes)
                if written != len(wire_bytes):
                    raise ConnectionError(f"Incomplete command write: {written}/{len(wire_bytes)}")
                self._notify_state_change()

            elif cmd.cmd_type == EngineCommandType.START:
                p = cmd.payload or {}
                if self.session.state == SessionState.COMPLETE:
                    self.session.state = SessionState.READY
                self.session.reset_session()
                self.session.error_log.clear()
                self.session.sample_validator = _validate_g1_sample if p.get("source_mode",1) == 1 else None
                self.g1_observation = G1Observation()
                self.host_ingestion_errors = 0
                self.last_g1_evidence = None
                wire_bytes = self.session.request_start(
                    target_samples=p.get("target_samples", 480000),
                    source_mode=p.get("source_mode", 1),
                    sample_rate_hz=p.get("sample_rate_hz", NOMINAL_SAMPLE_RATE_HZ),
                    encoding=p.get("encoding", 1),
                    channels=p.get("channels", 1),
                )
                written = self.transport.write(wire_bytes)
                if written != len(wire_bytes):
                    raise ConnectionError(f"Incomplete command write: {written}/{len(wire_bytes)}")
                self._notify_state_change()

            elif cmd.cmd_type == EngineCommandType.STOP:
                wire_bytes = self.session.request_stop()
                written = self.transport.write(wire_bytes)
                if written != len(wire_bytes):
                    raise ConnectionError(f"Incomplete command write: {written}/{len(wire_bytes)}")
                self._notify_state_change()

            elif cmd.cmd_type == EngineCommandType.DISCONNECT:
                self._stop_event.set()

        except Exception as e:
            cmd.future.set_exception(e)
            self.session.state = SessionState.ERROR
            self._notify_state_change()

    def _record_g1_evidence_if_applicable(self) -> None:
        """Use the same strict acceptance policy as physical CLI and Desktop export."""
        if self.session.active_start_config and self.session.active_start_config.source_mode == 1:
            self.last_g1_evidence = assess_g1(self)

    def _handle_transport_interruption(self, reason: str, pending_cmd: Optional[EngineCommand]) -> None:
        """Handle physical USB unplug or transport failure."""
        self.session.state = SessionState.ERROR
        if self.session.active_start_config and self.session.active_start_config.source_mode == 1:
            self.last_g1_evidence = assess_g1(self)
        self._notify_state_change()
        if pending_cmd is not None:
            pending_cmd.future.set_exception(ConnectionError(reason))
        if self.on_disconnect:
            self.on_disconnect(reason)

    def _teardown_transport(self) -> None:
        """Release serial port handles cleanly and reset state."""
        with self._lock:
            if self.transport is not None:
                try:
                    self.transport.close()
                except Exception:
                    pass
                self.transport = None
            self.session.state = SessionState.DISCONNECTED
            self._notify_state_change()
            self._thread = None

    def _notify_state_change(self) -> None:
        if self.on_state_change:
            try:
                self.on_state_change(self.session.state)
            except Exception:
                pass
