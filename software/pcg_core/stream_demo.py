"""AuscultaForge — Real-time PCG Replay & Streaming Demonstration CLI.

Simulates a live MCU digital audio stream from a real PCG WAV recording.

Usage:
    python -m pcg_core.stream_demo data/raw/a0001.wav
    python -m pcg_core.stream_demo data/raw/a0001.wav --fast
    python -m pcg_core.stream_demo data/raw/a0001.wav --speed 2.0 --buffer-duration 5.0
"""

import argparse
from pathlib import Path
import sys
import time

from .sources import RealtimeWavSource
from .streaming import LiveStreamingPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AuscultaForge live PCG streaming replay demonstration."
    )
    parser.add_argument(
        "wav_path",
        type=str,
        help="Path to PCG WAV file to stream (e.g. data/raw/a0001.wav).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run without real-time wall-clock pacing (maximum execution speed).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed factor for real-time mode (e.g. 2.0 for 2x speed).",
    )
    parser.add_argument(
        "--buffer-duration",
        type=float,
        default=5.0,
        help="Rolling buffer retention duration in seconds (default: 5.0).",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=256,
        help="Streaming block size in samples (default: 256).",
    )
    parser.add_argument(
        "--log-interval",
        type=float,
        default=1.0,
        help="Interval in stream seconds between console progress outputs (default: 1.0).",
    )

    args = parser.parse_args()

    wav_file = Path(args.wav_path)
    if not wav_file.exists():
        print(f"Error: WAV file not found: {wav_file}", file=sys.stderr)
        sys.exit(1)

    realtime_mode = not args.fast
    source = RealtimeWavSource(
        path=wav_file,
        block_size=args.block_size,
        realtime=realtime_mode,
        speed_factor=args.speed,
    )

    pipeline = LiveStreamingPipeline(
        buffer_duration_s=args.buffer_duration,
        filter_low_hz=20.0,
        filter_high_hz=600.0,
        filter_order=4,
    )

    sep = "=" * 76
    print(sep)
    print("AuscultaForge — Live PCG Stream Simulator")
    print(sep)
    print(f"Source Audio    : {wav_file.name}")
    print(f"Replay Mode     : {'Fast (unpaced)' if args.fast else f'Real-time ({args.speed:.1f}x speed)'}")
    print(f"Rolling Buffer  : {args.buffer_duration:.1f} s capacity")
    print(f"Block Size      : {args.block_size} samples")
    print("-" * 76)

    last_log_t = -float("inf")
    last_frame = None
    start_wall = time.perf_counter()

    for block in source.blocks():
        frame = pipeline.process_block(block)
        last_frame = frame
        current_t = frame.metrics.timestamp_s

        if current_t - last_log_t >= args.log_interval:
            last_log_t = current_t
            drops = pipeline.quality_monitor.report.dropped_blocks
            print(
                f"t={current_t:6.2f}s | "
                f"blocks={pipeline.quality_monitor.report.total_blocks:4d} | "
                f"rms={frame.metrics.rms:7.5f} | "
                f"peak={frame.metrics.peak_abs:7.5f} | "
                f"buffer={frame.metrics.buffer_duration_s:4.1f}s | "
                f"drops={drops:d}"
            )

    elapsed_wall = time.perf_counter() - start_wall

    print("-" * 76)
    rep = pipeline.quality_monitor.report
    print("Stream Replay Completed Successfully:")
    if last_frame:
        print(f"  Total Stream Time  : {last_frame.metrics.timestamp_s:.2f} s")
    print(f"  Wall-clock Runtime : {elapsed_wall:.2f} s")
    print(f"  Total Blocks       : {rep.total_blocks:,}")
    print(f"  Total Samples      : {rep.total_samples:,}")
    print(f"  Sample Rate        : {rep.current_fs} Hz")
    print(f"  Dropped Blocks     : {rep.dropped_blocks}")
    print(f"  Sequence Errors    : {rep.sequence_discontinuities}")
    print(f"  Timestamp Errors   : {rep.timestamp_regressions}")
    print(f"  Stream Health      : {'HEALTHY' if rep.is_healthy else 'WARNINGS DETECTED'}")
    print(sep)


if __name__ == "__main__":
    main()
