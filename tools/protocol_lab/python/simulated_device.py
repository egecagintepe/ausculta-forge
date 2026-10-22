"""AuscultaForge Hardware-Free ESP32-S3 Device Simulator.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

MISSION:
Simulates the proposed ESP32-S3 firmware wire contract for Module B/C protocol
verification without requiring physical hardware.
Supports:
- HELLO_REQ / HELLO_ACK handshake with host nonce echo.
- START_REQ / START_ACK with unique 64-bit session ID.
- 480,000 deterministic sample values across 1,875 AUDIO frames @ 256 samples/frame.
- Periodic STATUS telemetry frames.
- STOP_REQ / STOP_ACK with agreed 72-byte telemetry schema.
- Comprehensive fault injection: CRC corruption, frame drop, duplication,
  stale session ID, config rejection, simulated backpressure, and transport disconnection.
"""

from typing import Dict, List, Optional, Set
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
        build_hello_ack_packet,
        build_start_ack_packet,
        build_stop_ack_packet,
        build_status_packet,
        build_error_packet,
        build_profile_b_packet,
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
        FRAME_FLAG_TIMESTAMP_VALID,
        FRAME_FLAG_SIMULATED_SOURCE,
        FRAME_FLAG_SESSION_ACTIVE,
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
        build_hello_ack_packet,
        build_start_ack_packet,
        build_stop_ack_packet,
        build_status_packet,
        build_error_packet,
        build_profile_b_packet,
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
        FRAME_FLAG_TIMESTAMP_VALID,
        FRAME_FLAG_SIMULATED_SOURCE,
        FRAME_FLAG_SESSION_ACTIVE,
    )


def compute_deterministic_sample(abs_sample_index: int) -> int:
    """Independent deterministic integer sequence: 24-bit signed integer."""
    val = ((abs_sample_index * 16807 + 7) & 0x00FFFFFF)
    if val & 0x00800000:
        val -= 0x01000000
    return int(val)


class SimulatedEsp32Device:
    """Host-runnable simulated ESP32-S3 device implementing canonical B/C protocol."""

    def __init__(self, initial_session_id: int = 0x41555343554C5441) -> None:
        self.device_state: str = "DISCONNECTED"
        self.current_session_id: int = initial_session_id
        self.t0_us: int = 1000000
        self.active_config: Optional[StartReq] = None

        self.frames_generated: int = 0
        self.samples_generated: int = 0
        self.samples_queued: int = 0
        self.samples_dropped: int = 0
        self.audio_frames_queued: int = 0
        self.dma_overflow_events: int = 0
        self.ring_overflow_events: int = 0
        self.usb_partial_write_events: int = 0
        self.usb_timeout_events: int = 0
        self.usb_disconnect_events: int = 0

        self.decoder = StreamingProtocolDecoder()

        # Fault Injection Flags
        self.corrupt_crc_frames: Set[int] = set()
        self.drop_frames: Set[int] = set()
        self.duplicate_frames: Set[int] = set()
        self.corrupt_nonce: bool = False
        self.reject_config: bool = False
        self.stale_session_id: bool = False
        self.status_interval_frames: int = 0

    def connect(self) -> None:
        """Simulate hardware power-on / USB cable plug-in."""
        self.device_state = "IDLE"
        self.decoder.reset()

    def disconnect(self) -> None:
        """Simulate physical USB cable disconnect."""
        self.device_state = "DISCONNECTED"
        self.usb_disconnect_events += 1
        self.decoder.reset()

    def process_incoming_bytes(self, chunk: bytes) -> bytes:
        """Receive bytes from host and return immediate reply bytes (if any)."""
        if self.device_state == "DISCONNECTED":
            return b""

        packets = self.decoder.feed_bytes(chunk)
        reply = bytearray()

        for pkt in packets:
            if not pkt.crc_ok:
                continue

            if pkt.msg_type == MSG_TYPE_HELLO_REQ:
                req: HelloReq = pkt.control_payload
                nonce = (req.host_nonce ^ 0xFF) if self.corrupt_nonce else req.host_nonce
                ack = HelloAck(
                    nonce_echo=nonce,
                    protocol_version_major=1,
                    protocol_version_minor=0,
                    supported_profiles_mask=0x02,
                    supported_encodings_mask=0x01,
                    hardware_sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
                    firmware_version_major=1,
                    firmware_version_minor=0,
                    firmware_version_patch=0,
                    reserved=0,
                    max_frame_samples=PROFILE_B_SAMPLES_PER_FRAME,
                    capability_flags=0x0007,
                    device_uid_low=0x53433332,
                )
                self.device_state = "READY"
                reply.extend(build_hello_ack_packet(ack))

            elif pkt.msg_type == MSG_TYPE_STREAM_START_REQ:
                if self.reject_config:
                    err = build_error_packet(error_code=0x00000004, error_context=pkt.msg_type)
                    reply.extend(err)
                    continue

                req_start: StartReq = pkt.control_payload
                self.active_config = req_start
                self.current_session_id += 1
                self.frames_generated = 0
                self.samples_generated = 0
                self.samples_queued = 0
                self.samples_dropped = 0
                self.audio_frames_queued = 0

                ack_start = StartAck(
                    session_id=self.current_session_id,
                    session_reference_time_us=self.t0_us,
                    accepted_sample_rate_hz=req_start.sample_rate_hz,
                    accepted_target_samples=req_start.target_samples,
                    accepted_source_mode=req_start.source_mode,
                    encoding=req_start.encoding,
                    channels=req_start.channels,
                    profile_id=req_start.profile_id,
                )
                self.device_state = "STREAMING"
                reply.extend(build_start_ack_packet(ack_start))

            elif pkt.msg_type == MSG_TYPE_STREAM_STOP_REQ:
                stop_req: StopReq = pkt.control_payload
                if self.stale_session_id or stop_req.session_id != self.current_session_id:
                    err = build_error_packet(error_code=0x00000003, error_context=int(stop_req.session_id & 0xFFFFFFFF))
                    reply.extend(err)
                    continue

                self.device_state = "STOPPED"
                telem = self.get_current_telemetry(stop_reason=1)
                reply.extend(build_stop_ack_packet(telem))

        return bytes(reply)

    def produce_next_audio_frame(self) -> bytes:
        """Produce the next Profile B AUDIO packet according to deterministic sequence."""
        if self.device_state != "STREAMING":
            return b""

        # Cap generation at target_samples if configured
        if self.active_config and self.active_config.target_samples > 0:
            if self.samples_generated >= self.active_config.target_samples:
                return b""

        frame_idx = self.frames_generated
        first_sample_idx = frame_idx * PROFILE_B_SAMPLES_PER_FRAME

        # Generate 256 samples
        samples = np.empty(PROFILE_B_SAMPLES_PER_FRAME, dtype=np.int32)
        for s in range(PROFILE_B_SAMPLES_PER_FRAME):
            samples[s] = compute_deterministic_sample(first_sample_idx + s)

        # Monotonic timestamp: t0 + floor(first_sample_idx * 1e6 / 48000)
        ts_us = self.t0_us + (first_sample_idx * 1000000 // NOMINAL_SAMPLE_RATE_HZ)

        self.frames_generated += 1
        self.samples_generated += PROFILE_B_SAMPLES_PER_FRAME

        # Check drop simulation
        if frame_idx in self.drop_frames:
            self.samples_dropped += PROFILE_B_SAMPLES_PER_FRAME
            return b""

        corrupt_crc = (frame_idx in self.corrupt_crc_frames)
        mcu_drops_sat = min(self.samples_dropped, 65535)

        wire_bytes = build_profile_b_packet(
            sequence_id=frame_idx,
            timestamp_us=ts_us,
            sample_index_start=first_sample_idx,
            samples=samples,
            sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
            meaningful_bits=24,
            flags=(FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SIMULATED_SOURCE | FRAME_FLAG_SESSION_ACTIVE),
            encoding=1,
            mcu_drops=mcu_drops_sat,
            corrupt_crc=corrupt_crc,
        )

        self.samples_queued += PROFILE_B_SAMPLES_PER_FRAME
        self.audio_frames_queued += 1

        out = bytearray(wire_bytes)
        if frame_idx in self.duplicate_frames:
            out.extend(wire_bytes)

        # Periodic STATUS emission if configured
        if self.status_interval_frames > 0 and (frame_idx % self.status_interval_frames == 0):
            telem = self.get_current_telemetry(stop_reason=0)
            status_pkt = build_status_packet(telem, sequence_id=frame_idx, timestamp_us=ts_us)
            out.extend(status_pkt)

        return bytes(out)

    def get_current_telemetry(self, stop_reason: int = 0, error_code: int = 0) -> StatusTelemetry:
        """Construct the agreed 72-byte telemetry record."""
        return StatusTelemetry(
            session_id=self.current_session_id,
            generated_samples=self.samples_generated,
            fully_queued_samples=self.samples_queued,
            dropped_samples=self.samples_dropped,
            audio_frames_queued=self.audio_frames_queued,
            dma_overflow_events=self.dma_overflow_events,
            ring_overflow_events=self.ring_overflow_events,
            usb_partial_write_events=self.usb_partial_write_events,
            usb_timeout_events=self.usb_timeout_events,
            usb_disconnect_events=self.usb_disconnect_events,
            audio_bytes_queued=self.audio_frames_queued * 1068,
            stop_reason=stop_reason,
            error_code=error_code,
        )
