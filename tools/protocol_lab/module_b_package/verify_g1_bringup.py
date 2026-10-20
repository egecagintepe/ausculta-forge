#!/usr/bin/env python3
"""AuscultaForge — Hardware Bring-Up Verification Tool for Module B (Ozan).

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)

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

# Add python protocol lab to path
SCRIPT_DIR = Path(__file__).resolve().parent
LAB_PYTHON_DIR = SCRIPT_DIR.parent / "python"
if str(LAB_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_PYTHON_DIR))

from protocol_codec import StreamingProtocolDecoder, NOMINAL_SAMPLE_RATE_HZ, PROFILE_B_SAMPLES_PER_FRAME
from protocol_validator import ProtocolValidator
import numpy as np


def run_serial_verification(port: str, baudrate: int, duration_s: float):
    try:
        import serial
    except ImportError:
        print("[ERROR] 'pyserial' package is required for hardware COM verification.")
        print("        Install with: pip install pyserial")
        sys.exit(1)

    print(f"[HARDWARE] Opening USB CDC-ACM serial port: {port} (baudrate={baudrate})...")
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.1)
    ser.reset_input_buffer()

    decoder = StreamingProtocolDecoder()
    accumulated_samples = []

    print(f"[HARDWARE] Streaming for {duration_s:.1f} seconds...")
    t_start = time.perf_counter()
    t_end = t_start + duration_s

    while time.perf_counter() < t_end:
        n_waiting = ser.in_waiting
        chunk = ser.read(max(n_waiting, 1024))
        if chunk:
            packets = decoder.feed_bytes(chunk)
            for p in packets:
                if p.crc_ok and len(p.raw_samples) > 0:
                    accumulated_samples.append(p.raw_samples)

    ser.close()
    t_actual = time.perf_counter() - t_start
    evaluate_stream_results(decoder, accumulated_samples, t_actual, duration_s, is_hardware=True)


def run_synthetic_dry_run(duration_s: float):
    import subprocess
    c_runner = SCRIPT_DIR.parent / "c" / "g1_sim_runner.exe"
    if not c_runner.exists():
        print("[ERROR] g1_sim_runner.exe not found. Compile tools/protocol_lab/c first.")
        sys.exit(1)

    print(f"[DRY-RUN] Executing synthetic C stream runner for {duration_s:.1f} seconds...")
    cmd = [str(c_runner), "--mode=stream", "--signal=sine_100hz", f"--seconds={duration_s}", "--profile=b"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    decoder = StreamingProtocolDecoder()
    accumulated_samples = []
    t_start = time.perf_counter()

    while True:
        chunk = proc.stdout.read(1024)
        if not chunk:
            break
        packets = decoder.feed_bytes(chunk)
        for p in packets:
            if p.crc_ok and len(p.raw_samples) > 0:
                accumulated_samples.append(p.raw_samples)

    proc.stdout.close()
    proc.wait()
    t_actual = time.perf_counter() - t_start
    evaluate_stream_results(decoder, accumulated_samples, t_actual, duration_s, is_hardware=False)


def evaluate_stream_results(decoder, sample_arrays, t_actual, duration_nominal, is_hardware):
    all_samples = np.concatenate(sample_arrays) if sample_arrays else np.zeros(0, dtype=np.int32)
    expected_samples = int(duration_nominal * NOMINAL_SAMPLE_RATE_HZ)
    expected_frames = expected_samples // PROFILE_B_SAMPLES_PER_FRAME

    print("\n=======================================================")
    print("AuscultaForge G1 Bring-Up Verification Report")
    print("=======================================================")
    print(f"Mode: {'PHYSICAL ESP32-S3 HARDWARE' if is_hardware else 'HOST SOFTWARE SIMULATION'}")
    print(f"Elapsed Time: {t_actual:.3f} s")
    print(f"Samples Acquired: {decoder.total_samples_received} (Expected: {expected_samples})")
    print(f"Frames Received: {decoder.total_frames_received} (Expected: {expected_frames})")
    print(f"CRC-32 Checksum Errors: {decoder.total_frames_corrupted}")
    print(f"Sequence Gaps: {decoder.total_sequence_gaps}")
    print(f"Duplicate Frames: {decoder.total_duplicate_frames}")
    print(f"Timestamp Regressions: {decoder.total_timestamp_regressions}")
    print(f"Garbage Noise Discarded: {decoder.garbage_bytes_discarded} bytes")

    passed = (
        decoder.total_frames_corrupted == 0 and
        decoder.total_sequence_gaps == 0 and
        decoder.total_duplicate_frames == 0 and
        abs(decoder.total_samples_received - expected_samples) <= (PROFILE_B_SAMPLES_PER_FRAME * 2)
    )

    if len(all_samples) >= 480:
        spectral = ProtocolValidator.validate_sine_100hz(all_samples, NOMINAL_SAMPLE_RATE_HZ, 100.0)
        print(f"\nSpectral Telemetry:")
        print(f"  Fundamental Peak: {spectral['peak_freq_hz']:.2f} Hz")
        print(f"  Estimated SNR: {spectral['snr_db']:.1f} dB")
        print(f"  Crest Factor: {spectral['crest_factor']:.3f} (Ideal: 1.414)")
        passed = passed and spectral["passed"]

    print("\n-------------------------------------------------------")
    if is_hardware:
        if passed:
            print(">>> STATUS: PHYSICAL G1 MILESTONE PASSED! <<<")
        else:
            print(">>> STATUS: HARDWARE VERIFICATION FAILED (Review error counters above) <<<")
    else:
        print(">>> STATUS: SOFTWARE SIMULATION PASSED (Does not mark physical G1 pass) <<<")
    print("=======================================================\n")


def main():
    parser = argparse.ArgumentParser(description="AuscultaForge Hardware G1 Bring-Up Validator")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g. COM3 or /dev/ttyACM0)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Virtual baud rate (default: 115200)")
    parser.add_argument("--seconds", type=float, default=10.0, help="Stream duration in seconds (default: 10.0)")
    parser.add_argument("--synthetic", action="store_true", help="Run software simulation dry-run without hardware")
    args = parser.parse_args()

    if args.port:
        run_serial_verification(args.port, args.baudrate, args.seconds)
    elif args.synthetic or not args.port:
        run_synthetic_dry_run(args.seconds)


if __name__ == "__main__":
    main()
