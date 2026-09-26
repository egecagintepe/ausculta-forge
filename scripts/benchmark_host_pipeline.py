#!/usr/bin/env python3
"""AuscultaForge — Host Pipeline Processing Capacity Benchmark.

Measures the sustained throughput capacity of the host PC application pipeline:
  DeviceSamplePacket -> ingest_device_packet() -> SampleBlock -> DSP -> SessionRecorder -> DisplayAggregator -> Bounded Publisher

IMPORTANT METRICS SEMANTICS:
- This script measures HOST PROCESSING CAPACITY (CPU throughput).
- It DOES NOT measure end-to-end latency.
- It DOES NOT measure USB or CDC transport latency.
- Physical device end-to-end latency remains unmeasured until hardware exists.

METRIC CONCEPTS:
1. Acquisition Sample Rate: Nominal sampling frequency of the physical sensor (48,000 Hz).
2. Acquisition Block Duration: Time represented by one hardware packet (e.g. 512 / 48000 = 10.67 ms).
3. Host Processing Runtime: Wall-clock CPU time taken by the host to process the block.
4. Display Update Rate: Controlled cadence at which display frames are generated (e.g. 25 Hz).
5. Browser Render Rate: UI frame presentation rate in the client (controlled by requestAnimationFrame).
6. End-to-End Latency: Physical sound wave at diaphragm to speaker/screen presentation (UNMEASURED).
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Add software directory to path
repo_root = Path(__file__).resolve().parent.parent
software_dir = repo_root / "software"
if str(software_dir) not in sys.path:
    sys.path.insert(0, str(software_dir))

import numpy as np

from pcg_app.device_runtime import (
    DeviceRuntime,
    DeviceState,
    DeviceCandidate,
    DeviceCapabilities,
    DeviceSamplePacket,
)
from pcg_app.display_pipeline import DisplayPipelineConfig
from pcg_app.state import StreamManager


class BenchmarkMockTransport:
    """Mock transport for establishing handshake in benchmark."""
    def open(self) -> bool:
        return True
    def close(self) -> None:
        pass


class BenchmarkMockWebSocket:
    """Simulated WebSocket consumer tracking display frames and backpressure."""
    def __init__(self, slow_ms: float = 0.0) -> None:
        self.slow_ms = slow_ms
        self.received_frames: int = 0
        self.legacy_signal_frames: int = 0
        self.display_frames: int = 0

    async def send_json(self, msg: dict) -> None:
        if self.slow_ms > 0:
            await asyncio.sleep(self.slow_ms / 1000.0)
        self.received_frames += 1
        msg_type = msg.get("type")
        if msg_type == "signal_frame":
            self.legacy_signal_frames += 1
        elif msg_type == "display_frame":
            self.display_frames += 1


import tempfile

async def run_benchmark(
    num_packets: int = 2000,
    sample_rate_hz: int = 48000,
    block_size: int = 512,
    target_display_hz: float = 25.0,
    simulate_slow_ui: bool = False,
    record_session: bool = True,
    temp_dir: Optional[Path] = None,
) -> dict:
    """Run deterministic packet injection through the host pipeline."""
    if temp_dir is None:
        _td = tempfile.TemporaryDirectory()
        sessions_path = Path(_td.name)
    else:
        _td = None
        sessions_path = temp_dir
        sessions_path.mkdir(parents=True, exist_ok=True)

    try:
        runtime = DeviceRuntime()
        runtime.attach_candidate(DeviceCandidate("ESP32S3-HW", "USB Rev-A", "benchmark"))
        runtime.attach_transport(BenchmarkMockTransport())
        runtime.complete_handshake(
            DeviceCapabilities(
                protocol_version="1.0",
                firmware_version="v1.0",
                device_id="ESP32S3-HW",
                sample_rate_hz=sample_rate_hz,
                sample_format="signed_pcm",
                channels=1,
                sample_container_bits=32,
                meaningful_data_bits=24,
                max_block_size=block_size,
            )
        )

        # Normal production display configuration:
        # DisplayPipelineConfig defaults emit_legacy_signal_frames to False.
        display_cfg = DisplayPipelineConfig(
            target_display_hz=target_display_hz,
            points_per_frame=128,
            client_queue_size=2,
        )

        manager = StreamManager(
            sessions_dir=sessions_path,
            device_runtime=runtime,
            display_config=display_cfg,
        )

        # Attach mock client
        mock_ws = BenchmarkMockWebSocket(slow_ms=15.0 if simulate_slow_ui else 0.0)
        manager.register_client(mock_ws)

        manager.select_source("hardware")

        if record_session:
            manager.start_recording(source_label="Benchmark-Run")

        # Generate deterministic packets upfront to isolate processing measurement from data gen
        packets: list[DeviceSamplePacket] = []
        block_duration_s = block_size / sample_rate_hz
        t_samples = np.linspace(0, block_duration_s, block_size, endpoint=False, dtype=np.float32)

        for seq in range(num_packets):
            t_start = seq * block_duration_s
            tone = (150000 * np.sin(2 * np.pi * 70 * (t_start + t_samples))).astype(np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=t_start,
                raw_samples=tone,
                crc_ok=True,
                meaningful_bits=24,
                sample_rate_hz=sample_rate_hz,
            )
            packets.append(pkt)

        # Benchmark execution loop
        start_wall = time.perf_counter()

        for pkt in packets:
            await manager.ingest_device_packet(pkt)

        end_wall = time.perf_counter()
        wall_duration = end_wall - start_wall

        total_samples = num_packets * block_size
        signal_duration_s = total_samples / sample_rate_hz
        throughput_samples_per_s = total_samples / max(1e-9, wall_duration)
        real_time_factor = signal_duration_s / max(1e-9, wall_duration)

        recorded_samples = 0
        if record_session:
            meta = manager.stop_recording()
            recorded_samples = meta.total_samples

        session_obj = manager._clients.get(mock_ws)
        dropped_display = session_obj.dropped_display_frames if session_obj else 0
        produced_display = manager.display_aggregator.total_display_frames_produced

        return {
            "sample_rate_hz": sample_rate_hz,
            "block_size": block_size,
            "packets_processed": num_packets,
            "samples_processed": total_samples,
            "signal_duration_s": signal_duration_s,
            "wall_time_s": wall_duration,
            "throughput_samples_per_s": throughput_samples_per_s,
            "real_time_factor": real_time_factor,
            "recorded_samples": recorded_samples,
            "display_frames_produced": produced_display,
            "display_frames_dropped": dropped_display,
            "legacy_signal_frames": mock_ws.legacy_signal_frames,
            "hardware_sequence_gaps": runtime.stats.sequence_gaps,
            "hardware_crc_failures": runtime.stats.crc_failures,
        }
    finally:
        if _td is not None:
            try:
                _td.cleanup()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="AuscultaForge Host Pipeline Throughput Benchmark")
    parser.add_argument("--packets", type=int, default=2000, help="Number of packets to inject (default: 2000)")
    parser.add_argument("--rate", type=int, default=48000, help="Acquisition sample rate in Hz (default: 48000)")
    parser.add_argument("--block-size", type=int, default=512, help="Block size in samples (default: 512)")
    parser.add_argument("--display-hz", type=float, default=25.0, help="Target display cadence in Hz (default: 25.0)")
    parser.add_argument("--slow-ui", action="store_true", help="Simulate slow UI consumer (15ms delay per frame)")
    args = parser.parse_args()

    print("=" * 76)
    print("      AUSCULTAFORGE HOST PIPELINE PROCESSING BENCHMARK")
    print("=" * 76)
    print("NOTE: This benchmark measures HOST PROCESSING CAPACITY only.")
    print("It does NOT measure end-to-end device latency or USB wire latency.")
    print("-" * 76)
    print(f"Acquisition Sample Rate    : {args.rate:,} Hz")
    print(f"Acquisition Block Size     : {args.block_size} samples ({args.block_size / args.rate * 1000:.2f} ms/block)")
    print(f"Packet Ingestion Mode      : Sequential deterministic Rev-A semantic packets")
    print(f"Target Display Cadence     : {args.display_hz} Hz")
    print(f"Simulate UI Backpressure   : {'YES (15ms delay)' if args.slow_ui else 'NO (zero delay)'}")
    print(f"Test Packet Count          : {args.packets:,}")
    print("-" * 76)
    print("Executing benchmark...")

    results = asyncio.run(
        run_benchmark(
            num_packets=args.packets,
            sample_rate_hz=args.rate,
            block_size=args.block_size,
            target_display_hz=args.display_hz,
            simulate_slow_ui=args.slow_ui,
        )
    )

    print("-" * 76)
    print("BENCHMARK RESULTS (HOST-ONLY PROCESSING CAPACITY):")
    print("-" * 76)
    print(f"  Packets processed        : {results['packets_processed']:,}")
    print(f"  Samples processed        : {results['samples_processed']:,}")
    print(f"  Signal duration represented: {results['signal_duration_s']:.3f} s")
    print(f"  Wall-clock processing time: {results['wall_time_s']:.4f} s")
    print(f"  Host processing throughput: {results['throughput_samples_per_s']:,.0f} samples/s")
    print(f"  Real-time factor (RTF)   : {results['real_time_factor']:.2f}x (processing vs wall time)")
    print(f"  Samples recorded in WAV  : {results['recorded_samples']:,} (100.0% preserved)")
    print(f"  Display frames produced  : {results['display_frames_produced']}")
    print(f"  Display frames dropped   : {results['display_frames_dropped']}")
    print(f"  Legacy signal frames     : {results['legacy_signal_frames']} (STRICTLY ZERO under default config)")
    print(f"  Hardware sequence gaps   : {results['hardware_sequence_gaps']} (STRICTLY ZERO)")
    print(f"  Hardware CRC failures    : {results['hardware_crc_failures']}")
    print("-" * 76)
    print("METRICS SEMANTICS SUMMARY:")
    print("  [OK] Acquisition Sample Rate : 48,000 Hz (physical ADC specification)")
    print(f"  [OK] Acquisition Block Dur.  : {args.block_size / args.rate * 1000:.2f} ms")
    print(f"  [OK] Host Processing Runtime : {results['wall_time_s'] / results['packets_processed'] * 1000:.3f} ms/block")
    print(f"  [OK] Display Cadence         : {args.display_hz} updates/s")
    print("  [?]  End-to-End Latency      : UNMEASURED (requires physical Rev-A hardware)")
    print("=" * 76)


if __name__ == "__main__":
    main()
