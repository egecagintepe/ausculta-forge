"""AuscultaForge — Real PCG Segmentation Validation & Benchmark CLI.

Usage:
    python -m pcg_core.segmentation.validation.cli --dataset circor --root <dataset_path> [options]

Options:
    --dataset circor|cinc2016    Target dataset (default: circor)
    --root PATH                  Path to dataset directory (required)
    --profile PROFILE_ID         Springer extraction profile (default: SPRINGER_PHYSIONET_REFERENCE_V1)
    --folds INT                  Number of subject-grouped folds (default: 5)
    --seed INT                   Random seed (default: 2026)
    --scan-only                  Dry run: scan and report dataset statistics without training
    --max-subjects INT           Debug/pilot limit on number of unique subjects
    --max-records INT            Debug/pilot limit on number of records
    --output-dir PATH            Output directory for benchmark report artifacts
    --no-cache                   Disable feature caching
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import SegmentationBenchmarkConfig
from .benchmark import run_segmentation_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Real PCG Segmentation Validation & Benchmarking CLI"
    )
    parser.add_argument(
        "--dataset",
        choices=["circor", "cinc2016"],
        default="circor",
        help="Dataset adapter to use (default: circor)",
    )
    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="Path to dataset directory containing WAV and TSV files",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="SPRINGER_PHYSIONET_REFERENCE_V1",
        help="Feature profile ID (default: SPRINGER_PHYSIONET_REFERENCE_V1)",
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of subject-grouped cross-validation folds (default: 5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Deterministic random seed (default: 2026)",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Dry-run scan: report dataset statistics without training models",
    )
    parser.add_argument(
        "--max-subjects",
        type=int,
        default=None,
        help="Pilot/debug constraint: maximum number of subjects to evaluate",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Pilot/debug constraint: maximum number of records to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save benchmark JSON and CSV artifacts",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable feature extraction caching",
    )

    args = parser.parse_args()

    config = SegmentationBenchmarkConfig(
        dataset_id="CIRCOR_DIGISCOPE" if args.dataset == "circor" else "CINC_2016",
        dataset_version="1.0.3" if args.dataset == "circor" else "1.0.0",
        profile_id=args.profile,
        fold_count=args.folds,
        random_seed=args.seed,
        feature_cache_enabled=not args.no_cache,
        max_records=args.max_records,
        max_subjects=args.max_subjects,
    )

    print(f"=== AuscultaForge Stage-C Benchmark ===")
    print(f"Dataset: {config.dataset_id} v{config.dataset_version}")
    print(f"Root: {args.root}")
    print(f"Profile: {config.profile_id}")
    print(f"Mode: {'SCAN-ONLY (Dry Run)' if args.scan_only else f'{config.fold_count}-Fold Subject-Grouped CV'}")
    if config.max_subjects or config.max_records:
        print(f"PILOT CONSTRAINTS: max_subjects={config.max_subjects}, max_records={config.max_records} -> PARTIAL_DATASET")

    report = run_segmentation_benchmark(
        dataset_root=args.root,
        config=config,
        output_root=args.output_dir,
        scan_only=args.scan_only,
    )

    print(f"\nBenchmark Status: {report.status}")
    print(f"Eligible Records: {report.dataset_summary.get('eligible_record_count', 0)}")
    print(f"Eligible Subjects: {report.dataset_summary.get('eligible_subject_count', 0)}")
    print(f"Total Audio Duration: {report.dataset_summary.get('total_audio_duration_s', 0.0):.1f} s")
    print(f"Total Annotated Duration: {report.dataset_summary.get('total_annotated_duration_s', 0.0):.1f} s")

    if not args.scan_only and report.status != "DATASET_NOT_AVAILABLE":
        cov = report.coverage
        print(f"\nSegmentation Coverage: {cov.get('coverage_rate', 0.0) * 100:.1f}% ({cov.get('successful_segmentations', 0)}/{cov.get('total_eligible_records', 0)})")

        e2e_100 = report.end_to_end_event_metrics.get("100ms")
        if e2e_100:
            print(f"\n--- END-TO-END EVENT METRICS (Primary Benchmark @ 100ms) ---")
            print(f"S1 Event F1: {e2e_100.s1.f1:.4f} (Sens: {e2e_100.s1.sensitivity:.4f}, Prec: {e2e_100.s1.precision:.4f})")
            print(f"S2 Event F1: {e2e_100.s2.f1:.4f} (Sens: {e2e_100.s2.sensitivity:.4f}, Prec: {e2e_100.s2.precision:.4f})")
            print(f"Combined F1: {e2e_100.combined.f1:.4f}")

        cond_100 = report.conditional_event_metrics.get("100ms")
        if cond_100:
            print(f"\n--- CONDITIONAL-ON-SUCCESS EVENT METRICS (@ 100ms) ---")
            print(f"S1 Event F1: {cond_100.s1.f1:.4f}")
            print(f"S2 Event F1: {cond_100.s2.f1:.4f}")
            print(f"Combined F1: {cond_100.combined.f1:.4f}")

        if report.state_metrics:
            print(f"\n--- STATE-LEVEL FRAME METRICS (50 Hz) ---")
            print(f"Annotated-Frame Agreement: {report.state_metrics.annotated_frame_agreement * 100:.2f}%")
            print(f"Macro State F1: {report.state_metrics.macro_f1:.4f}")

    print(f"\nBenchmark completed.")


if __name__ == "__main__":
    main()
