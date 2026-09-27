"""AuscultaForge — Benchmark Report Compilation and Persistence.

Compiles and exports:
- benchmark.json (clean, structured, no absolute filesystem paths)
- summary.csv (key engineering metrics)
- folds.csv (per-fold metrics)
- failures.csv (unsuccessful segmentation details)
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Sequence
import numpy as np

from .models import (
    SegmentationBenchmarkReport,
    FoldSummary,
)
from .metrics import RecordEvaluationOutcome


def compile_benchmark_report(
    benchmark_id: str,
    status: str,
    config: Any,
    dataset_summary: dict[str, Any],
    fold_summaries: list[FoldSummary],
    outcomes: Sequence[RecordEvaluationOutcome],
    end_to_end_event_metrics: dict[str, Any],
    conditional_event_metrics: dict[str, Any],
    timing_errors: dict[str, Any],
    state_metrics: Any,
    location_breakdown: list[Any],
    macro_subject_metrics: dict[str, Any],
    training_summary: dict[str, Any],
    runtime_summary: dict[str, Any],
    provenance: dict[str, Any],
    warnings: list[str],
    limitations: list[str],
) -> SegmentationBenchmarkReport:
    """Assemble all calculated metrics into a SegmentationBenchmarkReport."""
    total_records = len(outcomes)
    success_count = sum(1 for o in outcomes if o.is_success)
    failed_count = total_records - success_count
    coverage_rate = float(success_count) / float(total_records) if total_records > 0 else 0.0

    failure_status_counts: dict[str, int] = {}
    for o in outcomes:
        if not o.is_success:
            st = o.segmentation_status
            failure_status_counts[st] = failure_status_counts.get(st, 0) + 1

    coverage_dict = {
        "total_eligible_records": total_records,
        "successful_segmentations": success_count,
        "failed_segmentations": failed_count,
        "coverage_rate": round(coverage_rate, 4),
        "failure_status_counts": failure_status_counts,
    }

    return SegmentationBenchmarkReport(
        schema_version="1.0.0",
        benchmark_id=benchmark_id,
        status=status,
        config=config,
        dataset_summary=dataset_summary,
        fold_summaries=fold_summaries,
        coverage=coverage_dict,
        end_to_end_event_metrics=end_to_end_event_metrics,
        conditional_event_metrics=conditional_event_metrics,
        timing_errors=timing_errors,
        state_metrics=state_metrics,
        location_breakdown=location_breakdown,
        failure_status_counts=failure_status_counts,
        macro_subject_metrics=macro_subject_metrics,
        training_summary=training_summary,
        runtime_summary=runtime_summary,
        provenance=provenance,
        warnings=warnings,
        limitations=limitations,
    )


def save_benchmark_artifacts(
    report: SegmentationBenchmarkReport,
    outcomes: Sequence[RecordEvaluationOutcome],
    output_dir: Path | str,
) -> dict[str, str]:
    """Persist benchmark.json, summary.csv, folds.csv, and failures.csv.
    
    Guarantees:
    - Never exports absolute filesystem paths.
    - Never writes raw audio or patient identifiers.
    """
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    created_files: dict[str, str] = {}

    # 1. benchmark.json
    json_path = out_p / "benchmark.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    created_files["json"] = str(json_path)

    # 2. summary.csv
    summary_path = out_p / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["benchmark_id", report.benchmark_id])
        writer.writerow(["status", report.status])
        writer.writerow(["dataset_id", report.config.dataset_id])
        writer.writerow(["dataset_version", report.config.dataset_version])
        writer.writerow(["profile_id", report.config.profile_id])
        writer.writerow(["coverage_rate", report.coverage.get("coverage_rate", 0.0)])
        writer.writerow(["total_records", report.coverage.get("total_eligible_records", 0)])

        # End-to-end 100ms F1
        e2e_100 = report.end_to_end_event_metrics.get("100ms")
        if e2e_100:
            writer.writerow(["end_to_end_s1_f1_100ms", e2e_100.s1.f1])
            writer.writerow(["end_to_end_s2_f1_100ms", e2e_100.s2.f1])
            writer.writerow(["end_to_end_combined_f1_100ms", e2e_100.combined.f1])

        # Conditional 100ms F1
        cond_100 = report.conditional_event_metrics.get("100ms")
        if cond_100:
            writer.writerow(["conditional_s1_f1_100ms", cond_100.s1.f1])
            writer.writerow(["conditional_s2_f1_100ms", cond_100.s2.f1])
            writer.writerow(["conditional_combined_f1_100ms", cond_100.combined.f1])

        if report.state_metrics:
            writer.writerow(["macro_state_f1", report.state_metrics.macro_f1])
            writer.writerow(["annotated_frame_agreement", report.state_metrics.annotated_frame_agreement])

    created_files["summary_csv"] = str(summary_path)

    # 3. folds.csv
    folds_path = out_p / "folds.csv"
    with open(folds_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fold_idx",
            "train_subjects",
            "eval_subjects",
            "train_records",
            "eval_records",
            "coverage",
            "s1_f1_100ms",
            "s2_f1_100ms",
            "combined_f1_100ms",
            "macro_state_f1",
            "model_id",
        ])
        for fs in report.fold_summaries:
            writer.writerow([
                fs.fold_idx,
                fs.train_subject_count,
                fs.eval_subject_count,
                fs.train_record_count,
                fs.eval_record_count,
                fs.coverage,
                fs.s1_f1_100ms,
                fs.s2_f1_100ms,
                fs.combined_f1_100ms,
                fs.macro_state_f1,
                fs.model_id,
            ])
    created_files["folds_csv"] = str(folds_path)

    # 4. failures.csv
    failures_path = out_p / "failures.csv"
    with open(failures_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "subject_id", "location", "duration_s", "status"])
        for o in outcomes:
            if not o.is_success:
                writer.writerow([
                    o.record_id,
                    o.subject_id,
                    o.auscultation_location or "N/A",
                    round(o.duration_s, 2),
                    o.segmentation_status,
                ])
    created_files["failures_csv"] = str(failures_path)

    return created_files
