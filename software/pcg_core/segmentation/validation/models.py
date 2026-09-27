"""AuscultaForge — Scientific Real PCG Segmentation Validation Models.

Defines typed, immutable dataclasses and schemas for:
- Reference PCG interval annotations and records
- Event and tolerance evaluation metrics
- State-level frame metrics and confusion matrices
- Subject-grouped fold summaries
- Full benchmark configuration and report structures
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
import math
from typing import Any, Optional, Sequence
import numpy as np


class BenchmarkStatus(str, Enum):
    """Explicit truthfulness status of a benchmark run."""
    COMPLETE_DATASET = "COMPLETE_DATASET"
    PARTIAL_DATASET = "PARTIAL_DATASET"
    DATASET_NOT_AVAILABLE = "DATASET_NOT_AVAILABLE"
    FAILED = "FAILED"


@dataclass(slots=True, frozen=True)
class ReferenceStateInterval:
    """Contiguous annotated interval for a single heart sound state.
    
    States:
    0 = UNANNOTATED / IGNORE (MUST NOT be treated as Diastole)
    1 = S1
    2 = SYSTOLE
    3 = S2
    4 = DIASTOLE
    """
    state: int
    start_s: float
    end_s: float
    duration_s: float = 0.0

    def __post_init__(self) -> None:
        if self.state not in (0, 1, 2, 3, 4):
            raise ValueError(f"Invalid reference state: {self.state}. Must be in {{0, 1, 2, 3, 4}}.")
        if not math.isfinite(self.start_s) or not math.isfinite(self.end_s):
            raise ValueError(f"Interval bounds must be finite: start={self.start_s}, end={self.end_s}")
        if self.start_s > self.end_s:
            raise ValueError(f"Invalid interval: start ({self.start_s}) > end ({self.end_s})")
        object.__setattr__(self, "duration_s", max(0.0, self.end_s - self.start_s))

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "start_s": round(self.start_s, 6),
            "end_s": round(self.end_s, 6),
            "duration_s": round(self.duration_s, 6),
        }


@dataclass(slots=True)
class AnnotatedPCGRecord:
    """A real PCG recording with verified reference segmentation annotations.
    
    Paths (wav_path, annotation_path) are strictly INTERNAL and must never
    be leaked into public benchmark reports.
    """
    dataset_id: str
    dataset_version: str
    record_id: str
    subject_id: str
    sample_rate_hz: float
    duration_s: float
    annotation_intervals: list[ReferenceStateInterval]
    auscultation_location: Optional[str] = None  # e.g., 'AV', 'MV', 'PV', 'TV', 'Phc'
    wav_path: Optional[str] = None               # INTERNAL ONLY
    annotation_path: Optional[str] = None        # INTERNAL ONLY
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def annotated_duration_s(self) -> float:
        """Total duration of valid cardiac states (1, 2, 3, 4)."""
        return sum(iv.duration_s for iv in self.annotation_intervals if iv.state in (1, 2, 3, 4))

    @property
    def ignored_duration_s(self) -> float:
        """Total duration of state 0 / unannotated segments."""
        return sum(iv.duration_s for iv in self.annotation_intervals if iv.state == 0)

    def to_dict(self, include_paths: bool = False) -> dict[str, Any]:
        d = {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "record_id": self.record_id,
            "subject_id": self.subject_id,
            "sample_rate_hz": self.sample_rate_hz,
            "duration_s": round(self.duration_s, 4),
            "auscultation_location": self.auscultation_location,
            "intervals_count": len(self.annotation_intervals),
            "annotated_duration_s": round(self.annotated_duration_s, 4),
            "ignored_duration_s": round(self.ignored_duration_s, 4),
            "metadata": self.metadata,
        }
        if include_paths:
            d["wav_path"] = self.wav_path
            d["annotation_path"] = self.annotation_path
        return d


@dataclass(slots=True)
class EventToleranceMetrics:
    """One-to-one event detection metrics at an exact tolerance window."""
    tolerance_ms: float
    tp: int
    fp: int
    fn: int
    sensitivity: float
    precision: float
    f1: float

    @property
    def recall(self) -> float:
        """Recall is equivalent to sensitivity in detection metrics."""
        return self.sensitivity

    def to_dict(self) -> dict[str, Any]:
        return {
            "tolerance_ms": self.tolerance_ms,
            "tp": int(self.tp),
            "fp": int(self.fp),
            "fn": int(self.fn),
            "sensitivity": round(float(self.sensitivity), 4),
            "recall": round(float(self.sensitivity), 4),
            "precision": round(float(self.precision), 4),
            "f1": round(float(self.f1), 4),
        }


@dataclass(slots=True)
class EventEvaluationResult:
    """Event-level evaluation for S1, S2, and combined events at a specific tolerance."""
    tolerance_ms: float
    s1: EventToleranceMetrics
    s2: EventToleranceMetrics
    combined: EventToleranceMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "tolerance_ms": self.tolerance_ms,
            "s1": self.s1.to_dict(),
            "s2": self.s2.to_dict(),
            "combined": self.combined.to_dict(),
        }


@dataclass(slots=True)
class TimingErrorMetrics:
    """Signed and absolute time differences for matched reference/prediction pairs."""
    mean_signed_ms: float
    median_signed_ms: float
    mean_abs_ms: float
    median_abs_ms: float
    p25_abs_ms: float
    p75_abs_ms: float
    p95_abs_ms: float
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean_signed_ms": round(float(self.mean_signed_ms), 2),
            "median_signed_ms": round(float(self.median_signed_ms), 2),
            "mean_abs_ms": round(float(self.mean_abs_ms), 2),
            "median_abs_ms": round(float(self.median_abs_ms), 2),
            "p25_abs_ms": round(float(self.p25_abs_ms), 2),
            "p75_abs_ms": round(float(self.p75_abs_ms), 2),
            "p95_abs_ms": round(float(self.p95_abs_ms), 2),
            "count": int(self.count),
        }


@dataclass(slots=True)
class StateMetrics:
    """4-state (S1, Systole, S2, Diastole) 50 Hz frame agreement metrics.
    
    State 0 is explicitly excluded from frame counts and confusion matrix.
    """
    confusion_matrix: list[list[int]]  # 4x4 matrix for states [1, 2, 3, 4]
    per_state_precision: dict[str, float]
    per_state_recall: dict[str, float]
    per_state_f1: dict[str, float]
    macro_f1: float
    annotated_frame_agreement: float
    total_annotated_frames: int
    total_ignored_frames: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "confusion_matrix": self.confusion_matrix,
            "per_state_precision": {k: round(v, 4) for k, v in self.per_state_precision.items()},
            "per_state_recall": {k: round(v, 4) for k, v in self.per_state_recall.items()},
            "per_state_f1": {k: round(v, 4) for k, v in self.per_state_f1.items()},
            "macro_f1": round(float(self.macro_f1), 4),
            "annotated_frame_agreement": round(float(self.annotated_frame_agreement), 4),
            "total_annotated_frames": int(self.total_annotated_frames),
            "total_ignored_frames": int(self.total_ignored_frames),
        }


@dataclass(slots=True)
class LocationMetrics:
    """Descriptive performance metrics stratified by auscultation location."""
    location: str
    record_count: int
    subject_count: int
    coverage: float
    s1_f1_100ms: float
    s2_f1_100ms: float
    combined_f1_100ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "record_count": int(self.record_count),
            "subject_count": int(self.subject_count),
            "coverage": round(float(self.coverage), 4),
            "s1_f1_100ms": round(float(self.s1_f1_100ms), 4),
            "s2_f1_100ms": round(float(self.s2_f1_100ms), 4),
            "combined_f1_100ms": round(float(self.combined_f1_100ms), 4),
        }


@dataclass(slots=True)
class FoldSummary:
    """Summary of training and evaluation statistics for a single cross-validation fold."""
    fold_idx: int
    train_subject_count: int
    eval_subject_count: int
    train_record_count: int
    eval_record_count: int
    coverage: float
    s1_f1_100ms: float
    s2_f1_100ms: float
    combined_f1_100ms: float
    macro_state_f1: float
    model_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_idx": self.fold_idx,
            "train_subject_count": self.train_subject_count,
            "eval_subject_count": self.eval_subject_count,
            "train_record_count": self.train_record_count,
            "eval_record_count": self.eval_record_count,
            "coverage": round(self.coverage, 4),
            "s1_f1_100ms": round(self.s1_f1_100ms, 4),
            "s2_f1_100ms": round(self.s2_f1_100ms, 4),
            "combined_f1_100ms": round(self.combined_f1_100ms, 4),
            "macro_state_f1": round(self.macro_state_f1, 4),
            "model_id": self.model_id,
        }


@dataclass(slots=True)
class SegmentationBenchmarkConfig:
    """Configuration governing the real PCG segmentation benchmark execution."""
    schema_version: str = "1.0.0"
    dataset_id: str = "CIRCOR_DIGISCOPE"
    dataset_version: str = "1.0.3"
    profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1"
    fold_count: int = 5
    random_seed: int = 2026
    event_tolerances_ms: tuple[float, ...] = (20.0, 40.0, 60.0, 80.0, 100.0)
    primary_event_anchor: str = "ONSET"  # "ONSET" or "SPRINGER_CONTEXT"
    include_state_metrics: bool = True
    feature_cache_enabled: bool = True
    max_records: Optional[int] = None     # Debug / pilot control only
    max_subjects: Optional[int] = None    # Debug / pilot control only

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "profile_id": self.profile_id,
            "fold_count": self.fold_count,
            "random_seed": self.random_seed,
            "event_tolerances_ms": list(self.event_tolerances_ms),
            "primary_event_anchor": self.primary_event_anchor,
            "include_state_metrics": self.include_state_metrics,
            "feature_cache_enabled": self.feature_cache_enabled,
            "max_records": self.max_records,
            "max_subjects": self.max_subjects,
        }


@dataclass(slots=True)
class SegmentationBenchmarkReport:
    """Complete, JSON-safe benchmark evaluation report."""
    schema_version: str = "1.0.0"
    benchmark_id: str = ""
    status: BenchmarkStatus = BenchmarkStatus.COMPLETE_DATASET
    config: SegmentationBenchmarkConfig = field(default_factory=SegmentationBenchmarkConfig)
    dataset_summary: dict[str, Any] = field(default_factory=dict)
    fold_summaries: list[FoldSummary] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    end_to_end_event_metrics: dict[str, EventEvaluationResult] = field(default_factory=dict)
    conditional_event_metrics: dict[str, EventEvaluationResult] = field(default_factory=dict)
    timing_errors: dict[str, TimingErrorMetrics] = field(default_factory=dict)
    state_metrics: Optional[StateMetrics] = None
    location_breakdown: list[LocationMetrics] = field(default_factory=list)
    failure_status_counts: dict[str, int] = field(default_factory=dict)
    macro_subject_metrics: dict[str, Any] = field(default_factory=dict)
    training_summary: dict[str, Any] = field(default_factory=dict)
    runtime_summary: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "benchmark_id": self.benchmark_id,
            "status": self.status.value if isinstance(self.status, BenchmarkStatus) else str(self.status),
            "config": self.config.to_dict(),
            "dataset_summary": self.dataset_summary,
            "fold_summaries": [f.to_dict() for f in self.fold_summaries],
            "coverage": self.coverage,
            "end_to_end_event_metrics": {k: v.to_dict() for k, v in self.end_to_end_event_metrics.items()},
            "conditional_event_metrics": {k: v.to_dict() for k, v in self.conditional_event_metrics.items()},
            "timing_errors": {k: v.to_dict() for k, v in self.timing_errors.items()},
            "state_metrics": self.state_metrics.to_dict() if self.state_metrics else None,
            "location_breakdown": [loc.to_dict() for loc in self.location_breakdown],
            "failure_status_counts": self.failure_status_counts,
            "macro_subject_metrics": self.macro_subject_metrics,
            "training_summary": self.training_summary,
            "runtime_summary": self.runtime_summary,
            "provenance": self.provenance,
            "warnings": self.warnings,
            "limitations": self.limitations,
        }
