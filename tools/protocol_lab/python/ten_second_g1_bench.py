"""AuscultaForge 10-Second G1 Simulation Benchmark & Evidence Generator.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)

MISSION:
Execute an end-to-end 10-second 48 kHz acquisition simulation bridging the
compiled C11 simulation runner (g1_sim_runner.exe) and the Python reference decoder.
Demonstrates:
1. Exact sample accounting (480,000 samples across 1,875 frames @ 256 samples/frame).
2. Closed-form mathematical known-answer verification (100 Hz pure sine).
3. Monotonic sample ramp counter continuity.
4. Robust detection of simulated errors (drops, CRC corruption, duplicate frames, noise, regressions).
5. Comprehensive, truthful JSON evidence generation.

CRITICAL HARDWARE DISCLAIMER:
-----------------------------
This execution is a SOFTWARE SIMULATION running purely on host CPU.
Passing this software simulation does NOT satisfy or mark physical ESP32-S3 G1 PASS.
Physical G1 requires physical ESP32-S3 hardware streaming real DMA samples over physical USB.
Physical metrics (SFDR, THD, hardware CRC cycles, physical USB bus occupancy) are marked NOT MEASURED.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from protocol_codec import (
    StreamingProtocolDecoder,
    PROFILE_B_SAMPLES_PER_FRAME,
    NOMINAL_SAMPLE_RATE_HZ,
)
from protocol_validator import ProtocolValidator

C_DIR = Path(__file__).resolve().parent.parent / "c"
RUNNER_EXE = C_DIR / "bin" / "g1_sim_runner.exe"
if not RUNNER_EXE.exists():
    RUNNER_EXE = C_DIR / "g1_sim_runner.exe"
OUTPUT_REPORT = Path(__file__).resolve().parent.parent / "g1_simulation_evidence.json"


def ensure_runner_compiled() -> Path:
    """Ensure g1_sim_runner.exe is compiled with GCC."""
    if not RUNNER_EXE.exists():
        bin_dir = C_DIR / "bin"
        bin_dir.mkdir(exist_ok=True)
        target = bin_dir / "g1_sim_runner.exe"
        print(f"[BUILD] Compiling {target.name} using gcc...")
        cmd = [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-Iinclude",
            "-o",
            str(target),
            "src/g1_sim_runner.c",
            "src/waveform_gen.c",
            "src/ring_buffer.c",
            "src/packet_framing.c",
            "-lm",
        ]
        res = subprocess.run(cmd, cwd=str(C_DIR), capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to compile C runner:\n{res.stderr}")
        print(f"[BUILD] Successfully compiled {target.name}")
        return target
    return RUNNER_EXE


def run_g1_stream_test(
    signal_type: str = "sine_100hz",
    duration_s: float = 10.0,
    is_fuzz: bool = False,
    chunk_size: int = 1024,
) -> Dict[str, Any]:
    """Execute C binary stream through Python decoder via pipe."""
    exe = ensure_runner_compiled()
    mode = "fuzz" if is_fuzz else "stream"

    cmd = [
        str(exe),
        f"--mode={mode}",
        f"--signal={signal_type}",
        f"--seconds={duration_s}",
        "--profile=b",
    ]

    print(f"\n[BENCH] Running: {' '.join(cmd)}")
    t0 = time.perf_counter()

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    decoder = StreamingProtocolDecoder()

    accumulated_samples: list[np.ndarray] = []

    # Stream in chunks
    while True:
        chunk = proc.stdout.read(chunk_size)
        if not chunk:
            break
        frames = decoder.feed_bytes(chunk)
        for f in frames:
            if f.crc_ok and len(f.raw_samples) > 0:
                accumulated_samples.append(f.raw_samples)

    proc.stdout.close()
    proc.wait()
    t_elapsed = time.perf_counter() - t0

    all_samples = np.concatenate(accumulated_samples) if accumulated_samples else np.zeros(0, dtype=np.int32)
    throughput_samples_per_sec = float(len(all_samples)) / max(t_elapsed, 1e-6)
    throughput_kb_per_sec = (float(len(all_samples) * 4) / 1024.0) / max(t_elapsed, 1e-6)

    print(f"  Execution Time: {t_elapsed:.3f} s (Real-time factor: {duration_s / max(t_elapsed, 1e-6):.1f}x)")
    print(f"  Samples Received: {decoder.total_samples_received} (Expected: {int(duration_s * NOMINAL_SAMPLE_RATE_HZ)})")
    print(f"  Frames Received: {decoder.total_frames_received} (Expected: {int(duration_s * NOMINAL_SAMPLE_RATE_HZ) // PROFILE_B_SAMPLES_PER_FRAME})")
    print(f"  CRC Failures: {decoder.total_frames_corrupted}")
    print(f"  Sequence Gaps: {decoder.total_sequence_gaps}")
    print(f"  Duplicate Frames: {decoder.total_duplicate_frames}")
    print(f"  Reordered Frames: {decoder.total_reordered_frames}")
    print(f"  Timestamp Regressions: {decoder.total_timestamp_regressions}")
    print(f"  Garbage Discarded: {decoder.garbage_bytes_discarded} bytes")

    # Signal validation
    spectral_metrics: Dict[str, Any] = {}
    ramp_metrics: Dict[str, Any] = {}

    if not is_fuzz and signal_type == "sine_100hz" and len(all_samples) > 0:
        spectral_metrics = ProtocolValidator.validate_sine_100hz(all_samples, NOMINAL_SAMPLE_RATE_HZ, 100.0)
        print(f"  Spectral Validation: Peak={spectral_metrics['peak_freq_hz']:.2f} Hz, SNR={spectral_metrics['snr_db']:.2f} dB, Crest={spectral_metrics['crest_factor']:.4f} (Passed: {spectral_metrics['passed']})")

    if not is_fuzz and signal_type == "ramp" and len(all_samples) > 0:
        ramp_metrics = ProtocolValidator.validate_ramp_counter(all_samples, 24)
        print(f"  Ramp Counter Validation: Gaps={ramp_metrics['gaps']} (Passed: {ramp_metrics['passed']})")

    g1_validation = ProtocolValidator.validate_g1_run(
        sample_count=decoder.total_samples_received,
        frame_count=decoder.total_frames_received,
        corrupted_frames=decoder.total_frames_corrupted,
        sequence_gaps=decoder.total_sequence_gaps,
        duplicate_frames=decoder.total_duplicate_frames,
        timestamp_regressions=decoder.total_timestamp_regressions,
        garbage_bytes=decoder.garbage_bytes_discarded,
        expected_duration_s=duration_s,
        expected_rate_hz=NOMINAL_SAMPLE_RATE_HZ,
        expected_frame_size=PROFILE_B_SAMPLES_PER_FRAME,
    )

    return {
        "signal_type": signal_type,
        "is_fuzz": is_fuzz,
        "duration_nominal_s": duration_s,
        "wall_clock_duration_s": t_elapsed,
        "throughput_samples_per_sec": throughput_samples_per_sec,
        "throughput_kb_per_sec": throughput_kb_per_sec,
        "decoder_stats": {
            "total_samples": decoder.total_samples_received,
            "total_frames": decoder.total_frames_received,
            "crc_errors": decoder.total_frames_corrupted,
            "sequence_gaps": decoder.total_sequence_gaps,
            "duplicate_frames": decoder.total_duplicate_frames,
            "reordered_frames": decoder.total_reordered_frames,
            "timestamp_regressions": decoder.total_timestamp_regressions,
            "garbage_bytes_discarded": decoder.garbage_bytes_discarded,
        },
        "g1_accounting_validation": g1_validation,
        "spectral_validation": spectral_metrics,
        "ramp_validation": ramp_metrics,
    }


def main():
    print("=========================================================================")
    print("AuscultaForge — Operation Protocol Forge: 10-Second G1 Simulation Suite")
    print("=========================================================================")

    # 1. Type Audit Check
    exe = ensure_runner_compiled()
    audit_res = subprocess.run([str(exe), "--audit"], capture_output=True, text=True, check=True)
    c_audit = json.loads(audit_res.stdout)
    print("✓ C11 Compiler Type & Endianness Audit PASSED")

    # 2. Run 10-second 100 Hz Sine Benchmark (Nominal Clean Run)
    print("\n--- Test 1: Nominal 10-Second 48 kHz Sine Wave Benchmark ---")
    sine_results = run_g1_stream_test(signal_type="sine_100hz", duration_s=10.0, is_fuzz=False)
    assert sine_results["g1_accounting_validation"]["passed"] is True, "Clean G1 sine accounting failed!"
    assert sine_results["spectral_validation"]["passed"] is True, "Spectral 100 Hz validation failed!"

    # 3. Run 10-second Ramp Counter Benchmark
    print("\n--- Test 2: Monotonic 10-Second Ramp Counter Benchmark ---")
    ramp_results = run_g1_stream_test(signal_type="ramp", duration_s=10.0, is_fuzz=False)
    assert ramp_results["g1_accounting_validation"]["passed"] is True, "Clean G1 ramp accounting failed!"
    assert ramp_results["ramp_validation"]["passed"] is True, "Ramp counter continuity failed!"

    # 4. Run Simulated Error Injection & Fuzzing Benchmark
    print("\n--- Test 3: Controlled Error Injection & Resynchronization Benchmark ---")
    fuzz_results = run_g1_stream_test(signal_type="sine_100hz", duration_s=10.0, is_fuzz=True)
    stats = fuzz_results["decoder_stats"]

    # Verify that the decoder faithfully trapped every injected defect:
    # - 2 sequence gaps: 1 from dropped frame #100, 1 from corrupted CRC frame #250
    # - 1 CRC failure: frame #250
    # - 1 duplicate frame: frame #500
    # - 17 garbage noise bytes: before frame #750
    # - 1 timestamp regression: frame #1000
    assert stats["sequence_gaps"] == 2, f"Expected 2 sequence gaps (1 drop + 1 corrupted), got {stats['sequence_gaps']}"
    assert stats["crc_errors"] == 1, f"Expected 1 corrupted CRC frame, got {stats['crc_errors']}"
    assert stats["duplicate_frames"] == 1, f"Expected 1 duplicate frame, got {stats['duplicate_frames']}"
    assert stats["garbage_bytes_discarded"] == 17, f"Expected 17 garbage noise bytes discarded, got {stats['garbage_bytes_discarded']}"
    assert stats["timestamp_regressions"] == 1, f"Expected 1 timestamp regression, got {stats['timestamp_regressions']}"
    print("✓ All 5 controlled error injections (drop, CRC, duplicate, noise, regression) correctly trapped and accounted.")

    # 5. Build Master Evidence JSON
    evidence_report = {
        "report_title": "AuscultaForge Protocol Forge G1 Simulation Acceptance Evidence",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disclaimer": (
            "CRITICAL ARCHITECTURAL NOTICE: This report represents a 100% SOFTWARE SIMULATION "
            "executing on host CPU (C11 + Python). A software simulation passing NEVER constitutes "
            "or marks physical ESP32-S3 G1 milestone pass. Physical G1 requires physical ESP32-S3 "
            "hardware streaming real DMA samples over physical USB."
        ),
        "physical_measurements_notice": (
            "All physical hardware metrics (SFDR, THD, hardware CRC execution cycles, oscilloscope jitter, "
            "physical USB bus occupancy) are marked NOT MEASURED. Software simulation throughput numbers reflect "
            "pipe I/O on host CPU and do NOT represent physical USB transfer."
        ),
        "host_platform": sys.platform,
        "python_version": sys.version,
        "c_compiler_audit": c_audit,
        "parameters": {
            "sample_rate_hz": NOMINAL_SAMPLE_RATE_HZ,
            "duration_seconds": 10.0,
            "samples_per_frame": PROFILE_B_SAMPLES_PER_FRAME,
            "total_samples_expected": 480000,
            "total_frames_expected": 1875,
            "payload_bytes_per_frame": 1024,
            "header_bytes_per_frame": 40,
            "trailer_bytes_per_frame": 4,
            "frame_total_bytes": 1068,
            "payload_data_rate_bps": 192000 * 8,
            "total_wire_data_rate_bps": int(187.5 * 1068 * 8),
        },
        "benchmarks": {
            "nominal_sine_100hz": sine_results,
            "monotonic_ramp_counter": ramp_results,
            "simulated_error_injection": fuzz_results,
        },
        "physical_hardware_metrics": {
            "sfdr_db": "NOT MEASURED",
            "thd_db": "NOT MEASURED",
            "esp32_hardware_crc_cycles": "NOT MEASURED",
            "oscilloscope_jitter_ns": "NOT MEASURED",
            "physical_usb_bus_utilization": "NOT MEASURED",
            "physical_g1_status": "PENDING_PHYSICAL_HARDWARE",
        },
        "status": "SOFTWARE_SIMULATION_PASSED",
        "physical_g1_milestone_status": "PENDING_PHYSICAL_HARDWARE_ARRIVAL",
    }

    OUTPUT_REPORT.write_text(json.dumps(evidence_report, indent=2), encoding="utf-8")
    print(f"\n✓ Generated machine-readable evidence artifact: {OUTPUT_REPORT}")
    print("=========================================================================")
    print("ALL G1 BENCHMARKS PASSED 100% (SOFTWARE SIMULATION VERIFIED)")
    print("=========================================================================")


if __name__ == "__main__":
    main()
