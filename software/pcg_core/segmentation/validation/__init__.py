"""AuscultaForge — Scientific PCG Segmentation Validation & Benchmarking.

Provides:
- CirCor DigiScope (v1.0.3) dataset loading and validation
- CinC 2016 secondary cross-database adapter
- 50 Hz label converter with state 0 ignore semantics
- Deterministic subject-grouped fold splitting (zero leakage)
- One-to-one event matching and timing error metrics
- Two-view metric calculation (End-to-End vs Conditional-on-Success)
- Multi-tolerance event evaluation (20–100 ms) and 4-state confusion matrix
- Benchmark orchestration, CLI, and artifact persistence
"""

from .models import (
    BenchmarkStatus,
    ReferenceStateInterval,
    AnnotatedPCGRecord,
    EventToleranceMetrics,
    EventEvaluationResult,
    TimingErrorMetrics,
    StateMetrics,
    LocationMetrics,
    FoldSummary,
    SegmentationBenchmarkConfig,
    SegmentationBenchmarkReport,
)
from .circor import (
    CIRCOR_DATASET_ID,
    CIRCOR_DATASET_VERSION,
    CIRCOR_DOI,
    CIRCOR_URL,
    parse_circor_filename,
    parse_circor_tsv,
    scan_circor_dataset,
    load_circor_checksums,
    verify_sha256_checksum,
)
from .cinc2016 import (
    CINC2016_DATASET_ID,
    CINC2016_DATASET_VERSION,
    CINC2016_DOI,
    scan_cinc2016_dataset,
    parse_cinc2016_state_annotation_file,
)
from .annotations import (
    convert_intervals_to_50hz_labels,
    extract_events_from_reference_intervals,
    extract_events_from_predictions,
)
from .splitting import (
    create_subject_grouped_folds,
)
from .matching import (
    match_events_one_to_one,
    compute_event_metrics_at_tolerance,
    compute_timing_error_metrics,
)
from .metrics import (
    evaluate_single_record,
    aggregate_event_metrics_view,
    aggregate_timing_errors,
    aggregate_state_metrics,
    compute_macro_subject_metrics,
    compute_location_breakdown,
    RecordEvaluationOutcome,
)
from .training import (
    extract_record_features_and_labels,
    train_fold_springer_model,
)
from .benchmark import (
    run_segmentation_benchmark,
)
from .report import (
    compile_benchmark_report,
    save_benchmark_artifacts,
)

__all__ = [
    "BenchmarkStatus",
    "ReferenceStateInterval",
    "AnnotatedPCGRecord",
    "EventToleranceMetrics",
    "EventEvaluationResult",
    "TimingErrorMetrics",
    "StateMetrics",
    "LocationMetrics",
    "FoldSummary",
    "SegmentationBenchmarkConfig",
    "SegmentationBenchmarkReport",
    "CIRCOR_DATASET_ID",
    "CIRCOR_DATASET_VERSION",
    "CIRCOR_DOI",
    "CIRCOR_URL",
    "parse_circor_filename",
    "parse_circor_tsv",
    "scan_circor_dataset",
    "load_circor_checksums",
    "verify_sha256_checksum",
    "CINC2016_DATASET_ID",
    "CINC2016_DATASET_VERSION",
    "CINC2016_DOI",
    "scan_cinc2016_dataset",
    "parse_cinc2016_state_annotation_file",
    "convert_intervals_to_50hz_labels",
    "extract_events_from_reference_intervals",
    "extract_events_from_predictions",
    "create_subject_grouped_folds",
    "match_events_one_to_one",
    "compute_event_metrics_at_tolerance",
    "compute_timing_error_metrics",
    "evaluate_single_record",
    "aggregate_event_metrics_view",
    "aggregate_timing_errors",
    "aggregate_state_metrics",
    "compute_macro_subject_metrics",
    "compute_location_breakdown",
    "RecordEvaluationOutcome",
    "extract_record_features_and_labels",
    "train_fold_springer_model",
    "run_segmentation_benchmark",
    "compile_benchmark_report",
    "save_benchmark_artifacts",
]
