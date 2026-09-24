"""AuscultaForge — CLI for Offline PCG WAV Analysis.

Usage:
    python -m pcg_core.analyze data/raw/a0001.wav
    python -m pcg_core.analyze data/raw/a0001.wav --output experiments/output/a0001.json
"""

import argparse
from pathlib import Path
import sys

from .analysis import analyze_wav


def print_summary(result) -> None:
    sep = "=" * 64
    print(sep)
    print("AuscultaForge — PCG Analysis Report")
    print(sep)
    print(f"Source          : {result.source_name}")
    print(f"Sample Rate     : {result.sample_rate_hz} Hz")
    print(f"Duration        : {result.duration_s:.3f} s ({result.total_samples:,} samples)")
    print()
    print("Filtering (Provisional Bandpass):")
    print(f"  Type          : {result.filter_config.filter_type}")
    print(f"  Band          : {result.filter_config.low_hz:.1f} – {result.filter_config.high_hz:.1f} Hz (Order: {result.filter_config.order})")
    print()
    print("Metrics (Raw -> Filtered):")
    print(f"  RMS           : {result.raw_metrics.rms:.5f} -> {result.filtered_metrics.rms:.5f}")
    print(f"  Peak Absolute : {result.raw_metrics.peak_abs:.5f} -> {result.filtered_metrics.peak_abs:.5f}")
    print(f"  Crest Factor  : {result.raw_metrics.crest_factor:.3f} -> {result.filtered_metrics.crest_factor:.3f}")
    print()
    print("Spectrogram Summary:")
    spec = result.spectrogram
    print(f"  Grid Shape    : {spec.shape[0]} frequency bins × {spec.shape[1]} time bins")
    print(f"  Frequency Span: {spec.f_min_hz:.1f} Hz to {spec.f_max_hz:.1f} Hz (resolution: {spec.f_resolution_hz:.2f} Hz)")
    print(f"  Time Span     : {spec.time_min_s:.2f} s to {spec.time_max_s:.2f} s (step: {spec.time_step_s:.3f} s)")
    print(f"  Peak Frequency: {spec.peak_frequency_hz:.2f} Hz")
    print("  Energy Ratios :")
    for band, ratio in spec.band_energy_ratios.items():
        print(f"    - {band:26s}: {ratio * 100:.1f}%")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AuscultaForge offline PCG analysis CLI."
    )
    parser.add_argument(
        "wav_path",
        type=str,
        help="Path to the mono PCG WAV file to analyze.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Optional path to write the JSON analysis report (e.g. experiments/output/report.json).",
    )
    parser.add_argument(
        "--low-hz",
        type=float,
        default=20.0,
        help="Provisional bandpass low cutoff frequency in Hz (default: 20.0).",
    )
    parser.add_argument(
        "--high-hz",
        type=float,
        default=600.0,
        help="Provisional bandpass high cutoff frequency in Hz (default: 600.0).",
    )
    parser.add_argument(
        "--order",
        type=int,
        default=4,
        help="Butterworth filter order (default: 4).",
    )
    parser.add_argument(
        "--include-matrix",
        action="store_true",
        help="Include full 2D spectrogram matrix array in the output JSON.",
    )

    args = parser.parse_args()

    wav_file = Path(args.wav_path)
    if not wav_file.exists():
        print(f"Error: WAV file not found at '{wav_file}'", file=sys.stderr)
        sys.exit(1)

    try:
        result = analyze_wav(
            path=wav_file,
            filter_low_hz=args.low_hz,
            filter_high_hz=args.high_hz,
            filter_order=args.order,
            include_spectrogram_matrix=args.include_matrix,
        )
    except Exception as e:
        print(f"Analysis error: {e}", file=sys.stderr)
        sys.exit(1)

    print_summary(result)

    # Determine output location if specified or write to experiments/output/ by default if requested
    out_path = None
    if args.output:
        out_path = Path(args.output)
    else:
        # Default convenience output in experiments/output
        exp_dir = Path("experiments/output")
        if exp_dir.exists():
            out_path = exp_dir / f"{wav_file.stem}_analysis.json"

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.to_json(indent=2), encoding="utf-8")
        print(f"JSON analysis written to: {out_path}")


if __name__ == "__main__":
    main()
