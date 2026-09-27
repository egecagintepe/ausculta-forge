"""AuscultaForge — Scientific PCG Segmentation Benchmark Orchestrator.

Orchestrates:
1. Dataset discovery, integrity checking, and eligibility filtering.
2. Subject-safe 5-fold cross-validation (zero subject leakage).
3. Real Springer LR-HSMM model training on training folds.
4. Independent PCG-only segmentation on held-out evaluation folds.
5. End-to-end and conditional evaluation across tolerances (20–100 ms).
6. Failure coverage tracking and descriptive location analysis.
7. Artifact persistence under experiments/benchmarks/.
"""

from __future__ import annotations

import datetime
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import scipy.io.wavfile

from ..springer import segment_pcg_springer
from ..springer_config import (
    SpringerProfileConfig,
    SPRINGER_PHYSIONET_REFERENCE_V1,
    get_springer_profile,
)
from .models import (
    AnnotatedPCGRecord,
    BenchmarkStatus,
    FoldSummary,
    SegmentationBenchmarkConfig,
    SegmentationBenchmarkReport,
)
from .circor import (
    scan_circor_dataset,
    CIRCOR_DATASET_ID,
    CIRCOR_DATASET_VERSION,
    CIRCOR_DOI,
)
from .splitting import create_subject_grouped_folds
from .training import train_fold_springer_model
from .metrics import (
    evaluate_single_record,
    aggregate_event_metrics_view,
    aggregate_timing_errors,
    aggregate_state_metrics,
    compute_macro_subject_metrics,
    compute_location_breakdown,
    RecordEvaluationOutcome,
)
from .report import compile_benchmark_report, save_benchmark_artifacts


def get_git_commit_hash() -> str:
    """Obtain current git commit SHA if git is available."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def build_system_provenance(profile_id: str) -> dict[str, Any]:
    """Capture complete execution provenance metadata."""
    pywt_version = "NOT_INSTALLED"
    try:
        import pywt
        pywt_version = pywt.__version__
    except ImportError:
        pass

    return {
        "auscultaforge_commit": get_git_commit_hash(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "scipy_version": importlib.metadata.version("scipy"),
        "pywavelets_version": pywt_version,
        "profile_id": profile_id,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_schema_version": "1.0.0",
        "benchmark_schema_version": "1.0.0",
    }


def run_segmentation_benchmark(
    dataset_root: Path | str,
    config: Optional[SegmentationBenchmarkConfig] = None,
    output_root: Optional[Path | str] = None,
    cache_dir: Optional[Path | str] = None,
    scan_only: bool = False,
) -> SegmentationBenchmarkReport:
    """Run the complete Stage-C real PCG segmentation benchmark.
    
    Parameters
    ----------
    dataset_root : Path | str
        Path to CirCor dataset root directory.
    config : Optional[SegmentationBenchmarkConfig]
        Benchmark configuration (default: 5-fold, seed 2026, SPRINGER_PHYSIONET_REFERENCE_V1).
    output_root : Optional[Path | str]
        Directory under which benchmark artifacts are saved (default: experiments/benchmarks/<benchmark_id>).
    cache_dir : Optional[Path | str]
        Directory for feature caching (default: experiments/cache/segmentation).
    scan_only : bool
        If True, scan dataset and return dataset summary without training.
    """
    t_start_total = time.time()
    cfg = config or SegmentationBenchmarkConfig()

    # Rule 17: Never allow demo model or profile to generate benchmark performance
    if "demo" in cfg.profile_id.lower():
        raise ValueError(
            f"Demo model/profile {cfg.profile_id!r} is strictly forbidden for benchmark evaluation (Requirement 17)."
        )

    benchmark_id = f"circor_springer_benchmark_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # 1. Dataset Discovery and Eligibility Filtering
    root_p = Path(dataset_root)
    if not root_p.exists():
        provenance = build_system_provenance(cfg.profile_id)
        return compile_benchmark_report(
            benchmark_id=benchmark_id,
            status=BenchmarkStatus.DATASET_NOT_AVAILABLE.value,
            config=cfg,
            dataset_summary={"error": f"Dataset directory not found: {dataset_root}"},
            fold_summaries=[],
            outcomes=[],
            end_to_end_event_metrics={},
            conditional_event_metrics={},
            timing_errors={},
            state_metrics=None,
            location_breakdown=[],
            macro_subject_metrics={},
            training_summary={},
            runtime_summary={"total_seconds": round(time.time() - t_start_total, 2)},
            provenance=provenance,
            warnings=["CirCor v1.0.3 dataset was not found at specified root path."],
            limitations=["No real dataset available for evaluation."],
        )

    records = scan_circor_dataset(
        root_path=root_p,
        max_subjects=cfg.max_subjects,
        max_records=cfg.max_records,
    )

    if not records:
        provenance = build_system_provenance(cfg.profile_id)
        return compile_benchmark_report(
            benchmark_id=benchmark_id,
            status=BenchmarkStatus.DATASET_NOT_AVAILABLE.value,
            config=cfg,
            dataset_summary={"error": "No valid annotated PCG records found in dataset directory."},
            fold_summaries=[],
            outcomes=[],
            end_to_end_event_metrics={},
            conditional_event_metrics={},
            timing_errors={},
            state_metrics=None,
            location_breakdown=[],
            macro_subject_metrics={},
            training_summary={},
            runtime_summary={"total_seconds": round(time.time() - t_start_total, 2)},
            provenance=provenance,
            warnings=["Directory exists but zero eligible CirCor records were parsed."],
            limitations=["Dataset empty or invalid file formats."],
        )

    # Compute dataset totals
    total_audio_duration_s = sum(r.duration_s for r in records)
    total_annotated_duration_s = sum(r.annotated_duration_s for r in records)
    total_ignored_duration_s = sum(r.ignored_duration_s for r in records)
    unique_subjects = {r.subject_id for r in records}

    dataset_summary = {
        "dataset_id": cfg.dataset_id,
        "dataset_version": cfg.dataset_version,
        "dataset_doi": CIRCOR_DOI,
        "source": "PhysioNet",
        "eligible_record_count": len(records),
        "eligible_subject_count": len(unique_subjects),
        "total_audio_duration_s": round(total_audio_duration_s, 2),
        "total_annotated_duration_s": round(total_annotated_duration_s, 2),
        "total_ignored_duration_s": round(total_ignored_duration_s, 2),
    }

    # Determine status (PARTIAL if pilot controls used)
    is_partial = (cfg.max_records is not None) or (cfg.max_subjects is not None)
    status_str = BenchmarkStatus.PARTIAL_DATASET.value if is_partial else BenchmarkStatus.COMPLETE_DATASET.value

    # Scan-only dry run return
    if scan_only:
        provenance = build_system_provenance(cfg.profile_id)
        return compile_benchmark_report(
            benchmark_id=benchmark_id,
            status=status_str,
            config=cfg,
            dataset_summary=dataset_summary,
            fold_summaries=[],
            outcomes=[],
            end_to_end_event_metrics={},
            conditional_event_metrics={},
            timing_errors={},
            state_metrics=None,
            location_breakdown=[],
            macro_subject_metrics={},
            training_summary={},
            runtime_summary={"scan_seconds": round(time.time() - t_start_total, 2)},
            provenance=provenance,
            warnings=["Scan-only mode: Model training and inference were skipped."],
            limitations=["Dry run scan only."],
        )

    # 2. Subject-Grouped Fold Split (Guaranteed zero leakage)
    folds = create_subject_grouped_folds(
        records=records,
        fold_count=cfg.fold_count,
        random_seed=cfg.random_seed,
    )

    profile = get_springer_profile(cfg.profile_id)
    cache_p = Path(cache_dir) if cache_dir else Path("experiments/cache/segmentation")
    if cfg.feature_cache_enabled:
        cache_p.mkdir(parents=True, exist_ok=True)

    if output_root:
        out_base = Path(output_root)
        out_dir = out_base / benchmark_id if out_base.name != benchmark_id else out_base
        fold_models_dir = out_dir / "models"
    else:
        out_dir = Path("experiments/benchmarks") / benchmark_id
        fold_models_dir = Path("experiments/models/benchmark") / benchmark_id
    fold_models_dir.mkdir(parents=True, exist_ok=True)

    all_outcomes: list[RecordEvaluationOutcome] = []
    fold_summaries: list[FoldSummary] = []

    training_time_total = 0.0
    inference_time_total = 0.0

    # 3. Execute Cross-Validation Folds
    for fold_idx, (train_recs, eval_recs) in enumerate(folds):
        train_sids = {r.subject_id for r in train_recs}
        eval_sids = {r.subject_id for r in eval_recs}

        # Train real model from training partition annotations
        t0_tr = time.time()
        fold_model = train_fold_springer_model(
            training_records=train_recs,
            fold_idx=fold_idx,
            config=profile,
            random_seed=cfg.random_seed,
            cache_dir=cache_p if cfg.feature_cache_enabled else None,
        )
        t_tr = time.time() - t0_tr
        training_time_total += t_tr

        # Save model artifact under ignored research path
        model_file = fold_models_dir / f"fold_{fold_idx}.json"
        with open(model_file, "w", encoding="utf-8") as f:
            json.dump(fold_model.to_dict(), f, indent=2)

        # Run inference on held-out evaluation records (PCG ONLY)
        t0_inf = time.time()
        fold_outcomes: list[RecordEvaluationOutcome] = []

        for rec in eval_recs:
            # Read audio
            fs_orig, audio = scipy.io.wavfile.read(rec.wav_path)
            if audio.ndim > 1:
                audio = audio[:, 0]
            audio_f = audio.astype(np.float64)
            if np.issubdtype(audio.dtype, np.integer):
                audio_f /= float(np.iinfo(audio.dtype).max)

            # Normal PCG inference: held-out annotations are NEVER supplied
            seg_res = segment_pcg_springer(
                signal=audio_f,
                sample_rate_hz=float(fs_orig),
                model=fold_model,
                config=profile,
            )

            # Annotation-aware evaluation (held-out annotations used ONLY after inference)
            outcome = evaluate_single_record(
                record=rec,
                prediction_result=seg_res,
                event_tolerances_ms=cfg.event_tolerances_ms,
                event_anchor=cfg.primary_event_anchor,
                include_state_metrics=cfg.include_state_metrics,
            )
            fold_outcomes.append(outcome)
            all_outcomes.append(outcome)

        t_inf = time.time() - t0_inf
        inference_time_total += t_inf

        # Fold Summary Statistics
        fold_succ = sum(1 for o in fold_outcomes if o.is_success)
        fold_cov = float(fold_succ) / float(len(eval_recs)) if eval_recs else 0.0
        fold_e2e_view = aggregate_event_metrics_view(fold_outcomes, [100.0])
        fold_100ms = fold_e2e_view.get("100ms")
        fold_state_m = aggregate_state_metrics(fold_outcomes)

        fold_summaries.append(
            FoldSummary(
                fold_idx=fold_idx,
                train_subject_count=len(train_sids),
                eval_subject_count=len(eval_sids),
                train_record_count=len(train_recs),
                eval_record_count=len(eval_recs),
                coverage=fold_cov,
                s1_f1_100ms=fold_100ms.s1.f1 if fold_100ms else 0.0,
                s2_f1_100ms=fold_100ms.s2.f1 if fold_100ms else 0.0,
                combined_f1_100ms=fold_100ms.combined.f1 if fold_100ms else 0.0,
                macro_state_f1=fold_state_m.macro_f1 if fold_state_m else 0.0,
                model_id=fold_model.model_id,
            )
        )

    # 4. Global Metric Aggregation
    # View A: End-to-End Metrics (Primary engineering benchmark, includes FNs from failed records)
    end_to_end_metrics = aggregate_event_metrics_view(all_outcomes, cfg.event_tolerances_ms)

    # View B: Conditional-on-Success Metrics
    succ_outcomes = [o for o in all_outcomes if o.is_success]
    conditional_metrics = aggregate_event_metrics_view(succ_outcomes, cfg.event_tolerances_ms)

    timing_errors = aggregate_timing_errors(succ_outcomes)
    state_metrics = aggregate_state_metrics(succ_outcomes)
    location_breakdown = compute_location_breakdown(all_outcomes, tolerance_ms=100.0)
    macro_subject_metrics = compute_macro_subject_metrics(all_outcomes, tolerance_ms=100.0)

    t_total = time.time() - t_start_total
    rtf = inference_time_total / total_audio_duration_s if total_audio_duration_s > 0 else 0.0

    runtime_summary = {
        "total_benchmark_seconds": round(t_total, 2),
        "total_training_seconds": round(training_time_total, 2),
        "total_inference_seconds": round(inference_time_total, 2),
        "mean_inference_seconds_per_record": round(inference_time_total / len(records), 4) if records else 0.0,
        "real_time_factor": round(rtf, 4),
    }

    training_summary = {
        "folds_executed": len(folds),
        "profile_id": cfg.profile_id,
        "model_architecture": "Logistic Regression + Hidden Semi-Markov Model (Springer LR-HSMM)",
        "synthetic_demo_used": False,
        "feature_cache_enabled": cfg.feature_cache_enabled,
    }

    provenance = build_system_provenance(cfg.profile_id)

    warnings: list[str] = []
    if is_partial:
        warnings.append(
            f"PARTIAL_DATASET: Bounded subset evaluated (max_subjects={cfg.max_subjects}, max_records={cfg.max_records}). "
            f"Not representative of the full CirCor v1.0.3 dataset."
        )

    limitations = [
        "AuscultaForge engineering validation on CirCor DigiScope (pediatric PCG data).",
        "This evaluation validates temporal heart sound segmentation only; it is NOT clinical or diagnostic validation.",
        "Performance measured on CirCor is not directly comparable to the Springer paper published on a separate dataset.",
        "State 0 (unannotated/ambiguous segments) is strictly excluded from all training and evaluation metrics.",
    ]

    report = compile_benchmark_report(
        benchmark_id=benchmark_id,
        status=status_str,
        config=cfg,
        dataset_summary=dataset_summary,
        fold_summaries=fold_summaries,
        outcomes=all_outcomes,
        end_to_end_event_metrics=end_to_end_metrics,
        conditional_event_metrics=conditional_metrics,
        timing_errors=timing_errors,
        state_metrics=state_metrics,
        location_breakdown=location_breakdown,
        macro_subject_metrics=macro_subject_metrics,
        training_summary=training_summary,
        runtime_summary=runtime_summary,
        provenance=provenance,
        warnings=warnings,
        limitations=limitations,
    )

    # 5. Persist Artifacts
    save_benchmark_artifacts(report=report, outcomes=all_outcomes, output_dir=out_dir)

    return report
