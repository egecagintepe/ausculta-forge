"""AuscultaForge — Reference-vs-Capture Signal Validation CLI.

Compares a known reference PCG signal with a captured or replayed recording
(or a synthetically distorted capture for bench validation), producing objective
engineering quality metrics and provenance records.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import uuid

import numpy as np
import scipy

from .experiment import compute_file_sha256, get_git_commit_sha
from .validation import (
    load_wav_as_float32,
    simulate_distorted_capture,
    validate_signals,
    ValidationResult,
)


def print_validation_report(res: ValidationResult) -> None:
    """Print a clean, objective terminal summary of the comparison metrics."""
    print("=" * 76)
    print("AuscultaForge — PCG Reference vs. Capture Validation Report")
    print("=" * 76)
    print(f"Reference  : {res.reference_name} ({res.reference_fs} Hz)")
    print(f"Captured   : {res.captured_name} ({res.captured_fs} Hz)")
    print(f"Resampled  : {'Yes (matched to ' + str(res.effective_fs) + ' Hz)' if res.resampled else 'No'}")
    print(f"Overlap    : {res.overlap_samples} samples ({res.overlap_duration_s:.3f} s)")
    print("-" * 76)
    print("TIME & ALIGNMENT:")
    print(f"  Estimated Delay          : {res.delay_ms:+.3f} ms ({res.delay_samples:+d} samples)")
    print(f"  Normalized Cross-Corr    : {res.normalized_cross_correlation:.5f}")
    print("-" * 76)
    print("AMPLITUDE & GAIN:")
    print(f"  Gain Ratio (RMS)         : {res.gain_ratio_rms:.4f}")
    print(f"  Gain Ratio (Peak)        : {res.gain_ratio_peak:.4f}")
    print(f"  Least-Squares Gain       : {res.least_squares_gain:.4f}")
    print(f"  RMSE (Raw Amplitude)     : {res.rmse:.6f}")
    print(f"  Normalized RMSE (NRMSE)  : {res.normalized_rmse:.5f}")
    print(f"  Signal-to-Error (SER)    : {res.signal_to_error_ratio_db:.2f} dB")
    print("-" * 76)
    print("SPECTRAL CHARACTERISTICS:")
    print(f"  Dominant Frequency (Ref) : {res.reference_dominant_hz:.1f} Hz")
    print(f"  Dominant Frequency (Cap) : {res.captured_dominant_hz:.1f} Hz")
    print(f"  Dominant Freq Difference : {res.dominant_frequency_diff_hz:.1f} Hz")
    print(f"  Band Energy Differences  : {res.band_energy_ratio_diffs}")
    print(f"  Mean Coherence (20-600Hz): {res.mean_coherence_pcg_band:.4f}")
    print("=" * 76)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Reference vs. Capture PCG Validation Runner."
    )
    parser.add_argument(
        "--reference", "-r",
        required=True,
        type=str,
        help="Path to clean reference PCG WAV file.",
    )
    parser.add_argument(
        "--capture", "-c",
        type=str,
        default=None,
        help="Path to captured/recorded PCG WAV file (required unless --simulate is specified).",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate a distorted capture from the reference signal for bench validation.",
    )
    parser.add_argument(
        "--delay-ms",
        type=float,
        default=45.0,
        help="Delay in milliseconds to inject during simulation (default: 45.0 ms).",
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=0.8,
        help="Gain multiplier to inject during simulation (default: 0.8).",
    )
    parser.add_argument(
        "--noise-std",
        type=float,
        default=0.01,
        help="Gaussian noise standard deviation to inject during simulation (default: 0.01).",
    )
    parser.add_argument(
        "--lowpass-hz",
        type=float,
        default=None,
        help="Optional lowpass filter cutoff frequency in Hz for simulation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic simulation (default: 42).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Directory to save JSON validation report (e.g. experiments/output).",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save a machine-readable JSON report to experiments/output/.",
    )

    args = parser.parse_args()

    ref_path = Path(args.reference)
    if not ref_path.exists():
        print(f"Error: Reference file not found: {ref_path}", file=sys.stderr)
        sys.exit(1)

    ref_samples, ref_fs = load_wav_as_float32(ref_path)
    ref_sha256 = compute_file_sha256(ref_path)

    if args.simulate:
        cap_name = f"simulated_delay{args.delay_ms}ms_gain{args.gain}"
        cap_samples = simulate_distorted_capture(
            reference_samples=ref_samples,
            fs=ref_fs,
            delay_ms=args.delay_ms,
            gain=args.gain,
            noise_std=args.noise_std,
            lowpass_cutoff_hz=args.lowpass_hz,
            seed=args.seed,
        )
        cap_fs = ref_fs
        cap_sha256 = "synthetic_simulation"
    elif args.capture:
        cap_path = Path(args.capture)
        if not cap_path.exists():
            print(f"Error: Captured file not found: {cap_path}", file=sys.stderr)
            sys.exit(1)
        cap_name = cap_path.name
        cap_samples, cap_fs = load_wav_as_float32(cap_path)
        cap_sha256 = compute_file_sha256(cap_path)
    else:
        print("Error: Either --capture <path> or --simulate must be specified.", file=sys.stderr)
        sys.exit(1)

    # Execute validation
    result = validate_signals(
        reference=ref_samples,
        captured=cap_samples,
        reference_fs=ref_fs,
        captured_fs=cap_fs,
        reference_name=ref_path.name,
        captured_name=cap_name,
    )

    print_validation_report(result)

    # Save JSON report if requested or output_dir specified
    if args.save_report or args.output_dir:
        out_dir = Path(args.output_dir) if args.output_dir else Path("experiments/output")
        out_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"val_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        report_file = out_dir / f"{run_id}_{ref_path.stem}_vs_{cap_name}.json"

        report_data = {
            "validation_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "provenance": {
                "git_commit_sha": get_git_commit_sha(),
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "os_platform": platform.platform(),
            },
            "reference_file": {
                "path": str(ref_path).replace("\\", "/"),
                "sha256": ref_sha256,
                "sample_rate_hz": ref_fs,
            },
            "captured_file": {
                "path": args.capture if args.capture else "simulated",
                "sha256": cap_sha256,
                "sample_rate_hz": cap_fs,
                "is_synthetic": bool(args.simulate),
            },
            "parameters": {
                "simulate": args.simulate,
                "injected_delay_ms": args.delay_ms if args.simulate else None,
                "injected_gain": args.gain if args.simulate else None,
                "injected_noise_std": args.noise_std if args.simulate else None,
                "injected_lowpass_hz": args.lowpass_hz if args.simulate else None,
            },
            "metrics": result.to_dict(),
        }

        report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()
