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
        self.corrupt_sample_indices: Set[int] = set()
        self.corrupt_nonce: bool = False
        self.missing_hello_ack: bool = False
        self.reject_config: bool = False
        self.wrong_start_encoding: bool = False
        self.zero_session_id: bool = False
        self.stale_session_id: bool = False
        self.missing_stop_ack: bool = False
        self.wrong_stop_session_id: bool = False
        self.falsify_telemetry: Optional[Dict[str, int]] = None
        self.stall_streaming: bool = False
        self.cap_samples: Optional[int] = None
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
                if self.missing_hello_ack:
                    continue
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

                assigned_session_id = 0 if self.zero_session_id else self.current_session_id
                assigned_encoding = 99 if self.wrong_start_encoding else req_start.encoding

                ack_start = StartAck(
                    session_id=assigned_session_id,
                    session_reference_time_us=self.t0_us,
                    accepted_sample_rate_hz=req_start.sample_rate_hz,
                    accepted_target_samples=req_start.target_samples,
                    accepted_source_mode=req_start.source_mode,
                    encoding=assigned_encoding,
                    channels=req_start.channels,
                    profile_id=req_start.profile_id,
                )
                self.device_state = "STREAMING"
                reply.extend(build_start_ack_packet(ack_start))

            elif pkt.msg_type == MSG_TYPE_STREAM_STOP_REQ:
                if self.missing_stop_ack:
                    continue
                stop_req: StopReq = pkt.control_payload
                if self.stale_session_id or stop_req.session_id != self.current_session_id:
                    err = build_error_packet(error_code=0x00000003, error_context=int(stop_req.session_id & 0xFFFFFFFF))
                    reply.extend(err)
                    continue

                self.device_state = "STOPPED"
                telem = self.get_current_telemetry(stop_reason=1)
                if self.wrong_stop_session_id:
                    telem = StatusTelemetry(
                        session_id=0xDEADBEEF00000000,
                        generated_samples=telem.generated_samples,
                        fully_queued_samples=telem.fully_queued_samples,
                        dropped_samples=telem.dropped_samples,
                        audio_frames_queued=telem.audio_frames_queued,
                        dma_overflow_events=telem.dma_overflow_events,
                        ring_overflow_events=telem.ring_overflow_events,
                        usb_partial_write_events=telem.usb_partial_write_events,
                        usb_timeout_events=telem.usb_timeout_events,
                        usb_disconnect_events=telem.usb_disconnect_events,
                        audio_bytes_queued=telem.audio_bytes_queued,
                        stop_reason=telem.stop_reason,
                        error_code=telem.error_code,
                    )
                reply.extend(build_stop_ack_packet(telem))

        return bytes(reply)

    def produce_next_audio_frame(self) -> bytes:
        """Produce the next Profile B AUDIO packet according to deterministic sequence."""
        if self.device_state != "STREAMING":
            return b""

        if self.stall_streaming:
            return b""

        # Cap generation at target_samples or injected cap_samples if configured
        target_limit = self.active_config.target_samples if (self.active_config and self.active_config.target_samples > 0) else None
        if self.cap_samples is not None:
            target_limit = min(target_limit, self.cap_samples) if target_limit is not None else self.cap_samples

        if target_limit is not None and self.samples_generated >= target_limit:
            return b""

        n_samples = PROFILE_B_SAMPLES_PER_FRAME
        if target_limit is not None and (self.samples_generated + n_samples) > target_limit:
            n_samples = target_limit - self.samples_generated
        if n_samples <= 0:
            return b""

        frame_idx = self.frames_generated
        first_sample_idx = self.samples_generated

        # Generate n_samples with possible sample corruption
        samples = np.empty(n_samples, dtype=np.int32)
        for s in range(n_samples):
            abs_s = first_sample_idx + s
            val = compute_deterministic_sample(abs_s)
            if abs_s in self.corrupt_sample_indices:
                val ^= 0x000000FF  # Corrupt sample value
            samples[s] = val

        # Monotonic timestamp: t0 + floor(first_sample_idx * 1e6 / 48000)
        ts_us = self.t0_us + (first_sample_idx * 1000000 // NOMINAL_SAMPLE_RATE_HZ)

        self.frames_generated += 1
        self.samples_generated += n_samples

        # Check drop simulation
        if frame_idx in self.drop_frames:
            self.samples_dropped += n_samples
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

        self.samples_queued += n_samples
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
        gen = self.samples_generated
        queued = self.samples_queued
        dropped = self.samples_dropped
        frames_q = self.audio_frames_queued
        err = error_code

        if self.falsify_telemetry:
            gen = self.falsify_telemetry.get("generated_samples", gen)
            queued = self.falsify_telemetry.get("fully_queued_samples", queued)
            dropped = self.falsify_telemetry.get("dropped_samples", dropped)
            frames_q = self.falsify_telemetry.get("audio_frames_queued", frames_q)
            err = self.falsify_telemetry.get("error_code", err)

        return StatusTelemetry(
            session_id=self.current_session_id,
            generated_samples=gen,
            fully_queued_samples=queued,
            dropped_samples=dropped,
            audio_frames_queued=frames_q,
            dma_overflow_events=self.dma_overflow_events,
            ring_overflow_events=self.ring_overflow_events,
            usb_partial_write_events=self.usb_partial_write_events,
            usb_timeout_events=self.usb_timeout_events,
            usb_disconnect_events=self.usb_disconnect_events,
            audio_bytes_queued=frames_q * 1068,
            stop_reason=stop_reason,
            error_code=err,
        )
