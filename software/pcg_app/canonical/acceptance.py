"""Independent bounded G1 observation and the one acceptance policy for CLI/Desktop."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import time

import numpy as np

from .codec import MSG_TYPE_AUDIO_DATA, MSG_TYPE_STREAM_START_ACK
from .transport import UsbCdcAcmAdapter, TransportState


class G1Observation:
    def __init__(self):
        self.digest = hashlib.sha256()
        self.frames = self.samples = self.mismatches = self.format_errors = 0
        self.timestamp_errors = 0
        self.sequence_errors = 0
        self.first_mismatch = None
        self.reference_us = None
        self.first_arrival = self.last_arrival = None
        self.started = time.monotonic()

    def observe(self, packet):
        if not packet.crc_ok:
            return
        if packet.msg_type == MSG_TYPE_STREAM_START_ACK:
            self.reference_us = packet.control_payload.session_reference_time_us
        if packet.msg_type != MSG_TYPE_AUDIO_DATA:
            return
        now = time.monotonic()
        if self.first_arrival is None:
            self.first_arrival = now
        self.last_arrival = now
        self.frames += 1
        self.sequence_errors += int(packet.sequence_id != self.frames-1)
        self.samples += packet.sample_count
        self.format_errors += int(not (
            packet.is_profile_b and packet.sample_count == 256 and
            packet.sample_rate_hz == 48000 and packet.meaningful_bits == 24 and
            packet.encoding == 1 and packet.mcu_buffer_drops == 0 and
            packet.flags & 0x20 and packet.flags & 1 and packet.flags & 0x80 and not packet.flags & ~0xb1
        ))
        if self.reference_us is None or packet.timestamp_us != (
            self.reference_us + packet.sample_index_start*1000000//48000
        ):
            self.timestamp_errors += 1
        indices = np.arange(packet.sample_count, dtype=np.uint64) + np.uint64(packet.sample_index_start)
        expected = ((indices*np.uint64(16807)+np.uint64(7)) & np.uint64(0xffffff)).astype(np.int64)
        expected = np.where(expected & 0x800000, expected-0x1000000, expected)
        wrong = np.flatnonzero(packet.raw_samples != expected)
        self.mismatches += len(wrong)
        if len(wrong) and self.first_mismatch is None:
            i = int(wrong[0])
            self.first_mismatch = {"index": int(indices[i]), "expected": int(expected[i]),
                                   "actual": int(packet.raw_samples[i])}
        self.digest.update(np.asarray(packet.raw_samples, dtype="<i4").tobytes())


def assess_g1(engine):
    """Evaluate facts independently; unknown provenance can never earn a physical pass."""
    s, o = engine.session, engine.g1_observation
    d, t, cfg, caps = s.decoder, s.final_telemetry, s.active_start_config, s.device_capabilities
    physical = type(engine.transport) is UsbCdcAcmAdapter and not engine.is_simulated
    physical = physical and engine.physical_transport_opened and engine.transport.get_state() == TransportState.CONNECTED
    checks = {
        "handshake": caps is not None and caps.protocol_version_major == 1 and
            bool(caps.supported_profiles_mask & 2) and bool(caps.supported_encodings_mask & 1) and
            caps.hardware_sample_rate_hz == 48000 and caps.max_frame_samples == 256,
        "configuration": cfg is not None and (cfg.target_samples,cfg.source_mode,cfg.sample_rate_hz,
            cfg.encoding,cfg.channels,cfg.profile_id) == (480000,1,48000,1,1,2),
        "firmware_version": caps is not None and (caps.firmware_version_major,
            caps.firmware_version_minor,caps.firmware_version_patch) in ((1,0,0),(1,1,0)),
        "session": bool(s.active_session_id) and t is not None and t.session_id == s.active_session_id,
        "stop_ack": s.state.value == "COMPLETE" and t is not None,
        "exact_samples": s.host_samples_accepted == o.samples == 480000,
        "exact_frames": s.host_audio_frames_accepted == o.frames == 1875,
        "sample_integrity": s.sample_validator is not None and o.mismatches == s.host_sample_value_errors == 0,
        "crc": d.total_frames_corrupted == 0,
        "sequence": o.sequence_errors == d.total_sequence_gaps == d.total_duplicate_frames == d.total_reordered_frames == 0,
        "indices": s.host_index_discontinuities == 0,
        "timestamps": o.timestamp_errors == d.total_timestamp_regressions == 0,
        "frame_format": o.format_errors == 0,
        "parser": d.malformed_headers == d.garbage_bytes_discarded == 0 and d.buffer_len == 0,
        "session_errors": not s.error_log,
        "host_ingestion": engine.host_ingestion_errors == 0,
        "physical_generation_window": engine.is_simulated or (o.last_arrival is not None and
            9.0 <= o.last_arrival-o.started <= 15.0),
        "telemetry": t is not None and t.generated_samples == t.fully_queued_samples == 480000 and
            t.audio_frames_queued == 1875 and t.audio_bytes_queued == 2002500 and
            t.dropped_samples == t.dma_overflow_events == t.ring_overflow_events ==
            t.usb_timeout_events == t.usb_disconnect_events == t.error_code == 0 and t.stop_reason in (0,1),
    }
    passed = all(checks.values())
    conclusion = ("PHYSICAL_G1_PASSED" if physical else "SOFTWARE_SIMULATION_PASS") if passed else "G1_FAILED"
    if passed and not physical and not engine.is_simulated:
        conclusion = "G1_INCOMPLETE"
        checks["physical_transport"] = False
        passed = False
    elapsed = (o.last_arrival-o.first_arrival) if o.first_arrival is not None else None
    return {
        "session_id": hex(s.active_session_id) if s.active_session_id else None,
        "mode": "DETERMINISTIC_G1", "target_samples": 480000,
        "host_samples_accepted": s.host_samples_accepted, "host_frames_accepted": s.host_audio_frames_accepted,
        "host_sample_value_errors": o.mismatches, "host_index_discontinuities": s.host_index_discontinuities,
        "firmware_samples_generated": t.generated_samples if t else None,
        "firmware_samples_dropped": t.dropped_samples if t else None,
        "verification_result": "PASS" if passed else "FAIL", "conclusion": conclusion,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "is_simulated": engine.is_simulated,
        "physical_transport": engine.physical_transport_opened and caps is not None,
        "transport_connected_at_report": physical,
        "gates": {k: "PASS" if v else "FAIL" for k,v in checks.items()},
        "failure_reasons": [k for k,v in checks.items() if not v],
        "sha256_hash": o.digest.hexdigest(), "first_mismatch": o.first_mismatch,
        "telemetry": asdict(t) if t else None,
        "capabilities": asdict(caps) if caps else None,
        "host_integrity": {"crc_errors":d.total_frames_corrupted,"sequence_gaps":d.total_sequence_gaps,
            "duplicates":d.total_duplicate_frames,"reordered_frames":d.total_reordered_frames,
            "malformed_headers":d.malformed_headers,"incomplete_bytes":d.buffer_len,
            "discarded_garbage_bytes":d.garbage_bytes_discarded,"timestamp_errors":o.timestamp_errors,
            "host_ingestion_errors":engine.host_ingestion_errors},
        "transport":engine.transport.get_telemetry() if engine.transport else {"state":"UNAVAILABLE"},
        "session_errors":list(s.error_log),
        "timing": {"host_first_to_last_arrival_s": elapsed,
            "host_samples_per_second": (o.samples-256)/elapsed if elapsed and elapsed > 0 else None,
            "elapsed_since_start_command_s": time.monotonic()-o.started,
            "device_generated_rate_hz": "NOMINAL_48000_NOT_INDEPENDENTLY_MEASURED",
            "physical_sampling_clock_accuracy": "UNAVAILABLE",
            "usb_queue_occupancy": "UNAVAILABLE_IN_CANONICAL_V0_1"},
    }
