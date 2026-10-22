#!/usr/bin/env python3
"""AuscultaForge — Hardware Bring-Up Verification Tool for Module B (Ozan).

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

STATUS SEPARATION:
- PHYSICAL_G1_PASS: Emitted ONLY when communication with physical ESP32-S3 hardware
  over USB CDC-ACM passes 100% of acceptance gates with zero tolerance.
- PHYSICAL_G1_FAIL: Hardware verification failed; process exits with code 1.
- SOFTWARE_SIMULATION_PASS: Simulated software dry-run; does NOT mark physical G1 pass.
- NOT_EXECUTED: Neither port nor simulation executed.

USAGE:
  # When ESP32-S3 board is plugged into USB COM port:
  python verify_g1_bringup.py --port COM3 --seconds 10

  # Simulation dry-run without hardware:
  python verify_g1_bringup.py --synthetic --seconds 10
"""

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional, Tuple

# Add python protocol lab to path
SCRIPT_DIR = Path(__file__).resolve().parent
LAB_PYTHON_DIR = SCRIPT_DIR.parent / "python"
if str(LAB_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_PYTHON_DIR))

from protocol_codec import (
    NOMINAL_SAMPLE_RATE_HZ,
    PROFILE_B_SAMPLES_PER_FRAME,
    StatusTelemetry,
)
from protocol_session import HostProtocolSession, SessionState


def compute_normative_deterministic_sample(n: int) -> int:
    """Normative independent sample sequence: 24-bit integer, sign-extended to int32.
    Formula: U_n = (n * 16807 + 7) mod 2^24; S_n = U_n - 2^24 if U_n >= 2^23 else U_n.
    """
    val = (n * 16807 + 7) & 0x00FFFFFF
    if val & 0x00800000:
        val -= 0x01000000
    return int(val)


# Verify reference known-answer vectors at load time
assert compute_normative_deterministic_sample(0) == 7
assert compute_normative_deterministic_sample(1) == 16814
assert compute_normative_deterministic_sample(500) == -8373709
assert compute_normative_deterministic_sample(1000) == 29791
assert compute_normative_deterministic_sample(479999) == -2497696


class SerialPortTransport:
    """Wrapper over pyserial Serial port providing uniform read/write interface."""

    def __init__(self, ser_instance: Any) -> None:
        self.ser = ser_instance

    def write(self, data: bytes) -> int:
        return self.ser.write(data)

    def read(self, max_bytes: int = 1024) -> bytes:
        n_waiting = getattr(self.ser, "in_waiting", 0)
        to_read = max(n_waiting, 1) if n_waiting > 0 else 1
        to_read = min(to_read, max_bytes)
        return self.ser.read(to_read)

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass


def execute_physical_g1_protocol(
    transport: Any,
    duration_s: float = 10.0,
    is_physical: bool = True,
    handshake_timeout_s: float = 2.0,
    streaming_inactivity_timeout_s: float = 2.0,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Execute the canonical finite-state physical acceptance flow with strict zero-tolerance gates.
    
    Returns:
        (passed, status_verdict, metrics_dict)
    """
    expected_samples = int(duration_s * NOMINAL_SAMPLE_RATE_HZ)
    expected_frames = expected_samples // PROFILE_B_SAMPLES_PER_FRAME

    # Host session with independent sample validator
    def independent_sample_validator(abs_idx: int, sample_val: int) -> bool:
        expected = compute_normative_deterministic_sample(abs_idx)
        return sample_val == expected

    session = HostProtocolSession(sample_validator=independent_sample_validator)
    t_start = time.perf_counter()

    metrics: Dict[str, Any] = {
        "is_physical": is_physical,
        "duration_nominal_s": duration_s,
        "expected_samples": expected_samples,
        "expected_frames": expected_frames,
        "hello_ack_received": False,
        "start_ack_received": False,
        "active_session_id": None,
        "host_samples_accepted": 0,
        "host_frames_accepted": 0,
        "sample_value_errors": 0,
        "sequence_gaps": 0,
        "duplicate_frames": 0,
        "crc_corrupted_frames": 0,
        "timestamp_regressions": 0,
        "stop_ack_received": False,
        "telemetry": None,
        "failure_reasons": [],
    }

    # -------------------------------------------------------------------------
    # STEP 1 & 2: HELLO Handshake
    # -------------------------------------------------------------------------
    hello_req = session.initiate_handshake(host_nonce=0x41555343)
    transport.write(hello_req)

    t_hello_deadline = time.perf_counter() + handshake_timeout_s
    while time.perf_counter() < t_hello_deadline:
        chunk = transport.read(1024)
        if chunk:
            session.handle_incoming_bytes(chunk)
            if session.state == SessionState.READY:
                break
            if session.state == SessionState.ERROR:
                metrics["failure_reasons"].append(f"State transitioned to ERROR during HELLO: {session.error_log}")
                return False, ("PHYSICAL_G1_FAIL" if is_physical else "SIMULATED_TRANSPORT_FAIL"), metrics
        time.sleep(0.005)

    if session.state != SessionState.READY or session.device_capabilities is None:
        metrics["failure_reasons"].append(f"Timed out waiting for valid HELLO_ACK (state: {session.state})")
        return False, ("PHYSICAL_G1_FAIL" if is_physical else "SIMULATED_TRANSPORT_FAIL"), metrics

    metrics["hello_ack_received"] = True

    # -------------------------------------------------------------------------
    # STEP 3 & 4: START Request & Acknowledgment Verification
    # -------------------------------------------------------------------------
    start_req = session.request_start(
        target_samples=expected_samples,
        source_mode=1,  # Deterministic Integer Ramp
        sample_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
        encoding=1,     # Signed PCM LSB-aligned
        channels=1,
    )
    transport.write(start_req)

    t_start_deadline = time.perf_counter() + handshake_timeout_s
    while time.perf_counter() < t_start_deadline:
        chunk = transport.read(1024)
        if chunk:
            session.handle_incoming_bytes(chunk)
            if session.state == SessionState.STREAMING:
                break
            if session.state == SessionState.ERROR:
                metrics["failure_reasons"].append(f"State transitioned to ERROR during START: {session.error_log}")
                return False, ("PHYSICAL_G1_FAIL" if is_physical else "SIMULATED_TRANSPORT_FAIL"), metrics
        time.sleep(0.005)

    if session.state != SessionState.STREAMING or session.active_session_id is None or session.active_session_id == 0:
        metrics["failure_reasons"].append(f"Timed out waiting for valid START_ACK with non-zero session ID (state: {session.state})")
        return False, ("PHYSICAL_G1_FAIL" if is_physical else "SIMULATED_TRANSPORT_FAIL"), metrics

    active_session_id = session.active_session_id
    metrics["start_ack_received"] = True
    metrics["active_session_id"] = hex(active_session_id)

    # -------------------------------------------------------------------------
    # STEP 5: Stream Acquisition until Target Samples Reached
    # -------------------------------------------------------------------------
    overall_timeout_s = duration_s + 5.0
    t_stream_deadline = time.perf_counter() + overall_timeout_s
    last_audio_recv_time = time.perf_counter()
    prev_frames_count = 0

    while time.perf_counter() < t_stream_deadline:
        chunk = transport.read(2048)
        if chunk:
            session.handle_incoming_bytes(chunk)
            if session.state == SessionState.ERROR:
                metrics["failure_reasons"].append(f"Session error during streaming: {session.error_log}")
                break

            if session.host_audio_frames_accepted > prev_frames_count:
                last_audio_recv_time = time.perf_counter()
                prev_frames_count = session.host_audio_frames_accepted

            if session.host_samples_accepted >= expected_samples:
                # Target sample count reached
                break
        else:
            time.sleep(0.002)

        # Inactivity timeout check
        if time.perf_counter() - last_audio_recv_time > streaming_inactivity_timeout_s:
            metrics["failure_reasons"].append(
                f"Streaming inactivity timeout: no audio frames received for > {streaming_inactivity_timeout_s}s"
            )
            break

    # -------------------------------------------------------------------------
    # STEP 6 & 7: STOP Request and Buffer Drain
    # -------------------------------------------------------------------------
    if session.state in (SessionState.STREAMING, SessionState.START_PENDING):
        try:
            stop_req = session.request_stop()
            transport.write(stop_req)
        except Exception as e:
            metrics["failure_reasons"].append(f"Failed to issue STOP_REQ: {e}")

        # Await STOP_ACK and drain pending packets
        t_stop_deadline = time.perf_counter() + handshake_timeout_s
        while time.perf_counter() < t_stop_deadline:
            chunk = transport.read(1024)
            if chunk:
                session.handle_incoming_bytes(chunk)
                if session.state == SessionState.COMPLETE:
                    break
                if session.state == SessionState.ERROR:
                    metrics["failure_reasons"].append(f"Session error during STOP drain: {session.error_log}")
                    break
            else:
                time.sleep(0.005)

    t_elapsed = time.perf_counter() - t_start

    # Record metrics
    metrics["host_samples_accepted"] = session.host_samples_accepted
    metrics["host_frames_accepted"] = session.host_audio_frames_accepted
    metrics["sample_value_errors"] = session.host_sample_value_errors
    metrics["sequence_gaps"] = session.decoder.total_sequence_gaps
    metrics["duplicate_frames"] = session.decoder.total_duplicate_frames
    metrics["crc_corrupted_frames"] = session.decoder.total_frames_corrupted
    metrics["timestamp_regressions"] = session.decoder.total_timestamp_regressions
    metrics["index_discontinuities"] = session.host_index_discontinuities
    metrics["elapsed_seconds"] = round(t_elapsed, 4)

    if session.state == SessionState.COMPLETE and session.final_telemetry is not None:
        metrics["stop_ack_received"] = True
        metrics["telemetry"] = {
            "session_id": hex(session.final_telemetry.session_id),
            "generated_samples": session.final_telemetry.generated_samples,
            "fully_queued_samples": session.final_telemetry.fully_queued_samples,
            "dropped_samples": session.final_telemetry.dropped_samples,
            "audio_frames_queued": session.final_telemetry.audio_frames_queued,
            "dma_overflow_events": session.final_telemetry.dma_overflow_events,
            "ring_overflow_events": session.final_telemetry.ring_overflow_events,
            "usb_partial_write_events": session.final_telemetry.usb_partial_write_events,
            "usb_timeout_events": session.final_telemetry.usb_timeout_events,
            "usb_disconnect_events": session.final_telemetry.usb_disconnect_events,
            "audio_bytes_queued": session.final_telemetry.audio_bytes_queued,
            "stop_reason": session.final_telemetry.stop_reason,
            "error_code": session.final_telemetry.error_code,
        }
    else:
        metrics["failure_reasons"].append(f"STOP_ACK not confirmed (final state: {session.state})")

    # -------------------------------------------------------------------------
    # STRICT ZERO-TOLERANCE ACCEPTANCE GATES
    # -------------------------------------------------------------------------
    g1_samples_ok = (session.host_samples_accepted == expected_samples)
    g2_frames_ok = (session.host_audio_frames_accepted == expected_frames)
    g3_values_ok = (session.host_sample_value_errors == 0)
    g4_crc_ok = (session.decoder.total_frames_corrupted == 0)
    g5_continuity_ok = (
        session.decoder.total_sequence_gaps == 0 and
        session.decoder.total_duplicate_frames == 0 and
        session.host_index_discontinuities == 0 and
        session.decoder.total_timestamp_regressions == 0
    )
    g6_session_ok = (session.state == SessionState.COMPLETE and session.active_session_id is not None)

    g7_telemetry_ok = False
    if session.final_telemetry is not None:
        t = session.final_telemetry
        g7_telemetry_ok = (
            t.session_id == session.active_session_id and
            t.generated_samples == expected_samples and
            t.fully_queued_samples == expected_samples and
            t.dropped_samples == 0 and
            t.audio_frames_queued == expected_frames and
            t.dma_overflow_events == 0 and
            t.ring_overflow_events == 0 and
            t.usb_partial_write_events == 0 and
            t.usb_timeout_events == 0 and
            t.usb_disconnect_events == 0 and
            t.error_code == 0
        )
        if not g7_telemetry_ok:
            metrics["failure_reasons"].append(f"MCU Telemetry mismatch: {metrics['telemetry']}")

    if not g1_samples_ok:
        metrics["failure_reasons"].append(
            f"Sample count discrepancy: expected {expected_samples}, got {session.host_samples_accepted}"
        )
    if not g2_frames_ok:
        metrics["failure_reasons"].append(
            f"Frame count discrepancy: expected {expected_frames}, got {session.host_audio_frames_accepted}"
        )
    if not g3_values_ok:
        metrics["failure_reasons"].append(
            f"Sample value errors detected: {session.host_sample_value_errors} mismatches"
        )
    if not g4_crc_ok:
        metrics["failure_reasons"].append(
            f"CRC errors detected: {session.decoder.total_frames_corrupted}"
        )
    if not g5_continuity_ok:
        metrics["failure_reasons"].append(
            f"Sequence/index continuity violated: gaps={session.decoder.total_sequence_gaps}, "
            f"dups={session.decoder.total_duplicate_frames}, index_disconts={session.host_index_discontinuities}"
        )

    all_passed = (
        g1_samples_ok and
        g2_frames_ok and
        g3_values_ok and
        g4_crc_ok and
        g5_continuity_ok and
        g6_session_ok and
        g7_telemetry_ok
    )

    if all_passed:
        verdict = "PHYSICAL_G1_PASS" if is_physical else "SOFTWARE_SIMULATION_PASS"
    else:
        verdict = "PHYSICAL_G1_FAIL" if is_physical else "SIMULATED_TRANSPORT_FAIL"

    return all_passed, verdict, metrics


def run_serial_verification(port: str, baudrate: int, duration_s: float) -> bool:
    """Run verification against physical USB CDC-ACM serial port."""
    try:
        import serial
    except ImportError:
        print("[ERROR] 'pyserial' package is required for hardware COM verification.")
        print("        Install with: pip install pyserial")
        sys.exit(1)

    print(f"[HARDWARE] Opening USB CDC-ACM serial port: {port} (baudrate={baudrate})...")
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.1, write_timeout=0.5)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception as e:
        print(f"\n[FATAL] Could not open serial port '{port}': {e}")
        print("\n=======================================================")
        print(">>> STATUS: PHYSICAL_G1_FAIL <<<")
        print("Reason: Serial port connection error")
        print("=======================================================\n")
        sys.exit(1)

    transport = SerialPortTransport(ser)
    passed, verdict, metrics = execute_physical_g1_protocol(transport, duration_s=duration_s, is_physical=True)
    transport.close()

    print_verification_report(verdict, metrics)
    if not passed:
        sys.exit(1)
    return passed


def run_synthetic_dry_run(duration_s: float) -> bool:
    """Run software simulation benchmark using SimulatedEsp32Device loopback."""
    from simulated_device import SimulatedEsp32Device
    from usb_adapter import DuplexLoopbackAdapter

    print(f"[DRY-RUN] Executing host software loopback simulation for {duration_s:.1f} seconds...")
    device = SimulatedEsp32Device(initial_session_id=0xCAFEFEED00000001)
    transport = DuplexLoopbackAdapter(device=device, max_chunk_size=1024)
    transport.open()

    passed, verdict, metrics = execute_physical_g1_protocol(transport, duration_s=duration_s, is_physical=False)
    transport.close()

    print_verification_report(verdict, metrics)
    return passed


def print_verification_report(verdict: str, metrics: Dict[str, Any]) -> None:
    """Print standard AuscultaForge G1 verification report."""
    print("\n=======================================================")
    print("AuscultaForge G1 Bring-Up Verification Report")
    print("=======================================================")
    print(f"Verdict: {verdict}")
    print(f"Physical Hardware Target: {metrics.get('is_physical')}")
    print(f"Elapsed Time: {metrics.get('elapsed_seconds', 0.0):.3f} s (Nominal: {metrics.get('duration_nominal_s')} s)")
    print(f"Samples Acquired: {metrics.get('host_samples_accepted')} (Expected: {metrics.get('expected_samples')})")
    print(f"Frames Received: {metrics.get('host_frames_accepted')} (Expected: {metrics.get('expected_frames')})")
    print(f"Sample Value Mismatches: {metrics.get('sample_value_errors')}")
    print(f"CRC-32 Checksum Errors: {metrics.get('crc_corrupted_frames')}")
    print(f"Sequence Gaps: {metrics.get('sequence_gaps')}")
    print(f"Duplicate Frames: {metrics.get('duplicate_frames')}")
    print(f"Timestamp Regressions: {metrics.get('timestamp_regressions')}")
    print(f"Active Session ID: {metrics.get('active_session_id')}")

    telem = metrics.get("telemetry")
    if telem is not None:
        print("\n--- Hardware Telemetry Reconciliation (STOP_ACK 72B) ---")
        print(f"  MCU Session ID:            {telem['session_id']}")
        print(f"  MCU Generated Samples:     {telem['generated_samples']}")
        print(f"  MCU Fully Queued Samples:  {telem['fully_queued_samples']}")
        print(f"  MCU Dropped Samples:       {telem['dropped_samples']}")
        print(f"  MCU Audio Frames Queued:   {telem['audio_frames_queued']}")
        print(f"  MCU DMA Overflows:         {telem['dma_overflow_events']}")
        print(f"  MCU Ring Buffer Overflows: {telem['ring_overflow_events']}")
        print(f"  MCU USB Partial Writes:    {telem['usb_partial_write_events']}")
        print(f"  MCU Error Code:            {telem['error_code']}")

    reasons = metrics.get("failure_reasons", [])
    if reasons:
        print("\n--- Gate Failure Reasons ---")
        for r in reasons:
            print(f"  [FAIL] {r}")

    print("\n-------------------------------------------------------")
    if verdict == "PHYSICAL_G1_PASS":
        print(">>> STATUS: PHYSICAL_G1_PASS <<<")
    elif verdict == "PHYSICAL_G1_FAIL":
        print(">>> STATUS: PHYSICAL_G1_FAIL <<<")
    elif verdict == "SOFTWARE_SIMULATION_PASS":
        print(">>> STATUS: SOFTWARE_SIMULATION_PASS (Does not mark physical G1 pass) <<<")
    else:
        print(f">>> STATUS: {verdict} <<<")
    print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AuscultaForge Hardware G1 Bring-Up Validator")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g. COM3 or /dev/ttyACM0)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Virtual baud rate (default: 115200)")
    parser.add_argument("--seconds", type=float, default=10.0, help="Stream duration in seconds (default: 10.0)")
    parser.add_argument("--synthetic", action="store_true", help="Run software simulation dry-run without hardware")
    args = parser.parse_args()

    if args.port:
        run_serial_verification(args.port, args.baudrate, args.seconds)
    elif args.synthetic:
        run_synthetic_dry_run(args.seconds)
    else:
        print("=======================================================")
        print(">>> STATUS: NOT_EXECUTED <<<")
        print("Specify --port <PORT> for physical ESP32-S3 hardware verification,")
        print("or --synthetic for host software simulation dry-run.")
        print("=======================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
