"""AuscultaForge — Springer LR-HSMM Heart-Sound Segmentation Models.

Defines deterministic, JSON-safe data structures for:
- HeartSoundState enum (S1, SYSTOLE, S2, DIASTOLE)
- SegmentationStatus enum
- SpringerFeatureResult (features at 50 Hz, provenance, normalization metadata)
- SpringerSegmentationModel (versioned model artifact with LR weights and MVN stats)
- SpringerSegmentationResult (state sequence, temporal intervals, HR/systolic estimates)
- Evaluation Metrics (tolerance-based TP, FP, FN, Precision, Recall, F1)

Strict Medical Boundary:
Segmentation states are temporal acoustic intervals, NOT diagnostic classifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
import math
from typing import Any, Optional
import numpy as np


class HeartSoundState(IntEnum):
    """Cyclic heart sound states in strict physiological sequence."""
    S1 = 1
    SYSTOLE = 2
    S2 = 3
    DIASTOLE = 4

    @property
    def label(self) -> str:
        return self.name

    @classmethod
    def from_int(cls, val: int) -> HeartSoundState:
        return cls(val)

    @classmethod
    def next_state(cls, state: HeartSoundState) -> HeartSoundState:
        """Strict cyclic transition: S1 -> SYSTOLE -> S2 -> DIASTOLE -> S1."""
        order = [cls.S1, cls.SYSTOLE, cls.S2, cls.DIASTOLE]
        idx = order.index(state)
        return order[(idx + 1) % 4]


class SegmentationStatus(str, Enum):
    """Explicit technical status for Springer segmentation outcomes."""
    SUCCESS = "SUCCESS"
    MODEL_REQUIRED = "MODEL_REQUIRED"
    MODEL_PROFILE_MISMATCH = "MODEL_PROFILE_MISMATCH"
    SIGNAL_TOO_SHORT = "SIGNAL_TOO_SHORT"
    HEART_RATE_ESTIMATION_FAILED = "HEART_RATE_ESTIMATION_FAILED"
    SEGMENTATION_PARAMETERS_INVALID = "SEGMENTATION_PARAMETERS_INVALID"
    DECODING_FAILED = "DECODING_FAILED"


def sanitize_float(val: float | int | None, default: float = 0.0) -> float:
    """Ensure floating-point value is finite and JSON-serializable."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def sanitize_list(arr: np.ndarray | list[float] | None, default_val: float = 0.0) -> list[float]:
    """Convert array or list to a JSON-safe list of finite floats."""
    if arr is None:
        return []
    if isinstance(arr, np.ndarray):
        flat = arr.flatten()
        clean = np.where(np.isnan(flat) | np.isinf(flat), default_val, flat)
        return [float(x) for x in clean]
    return [sanitize_float(x, default_val) for x in arr]


@dataclass(slots=True)
class StateInterval:
    """Temporal interval bounding a contiguous cardiac state."""
    state: int
    state_name: str
    start_s: float
    end_s: float
    duration_s: float
    start_frame_50hz: int
    end_frame_50hz: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StateDurationStats:
    """Mean and variance duration distribution parameters for a single cardiac state."""
    mean_s: float
    std_s: float
    min_s: float
    max_s: float
    mean_frames_50hz: int
    std_frames_50hz: float
    min_frames_50hz: int
    max_frames_50hz: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpringerFeatureResult:
    """Multidimensional feature stream extracted from PCG for HSMM observation."""
    schema_version: str = "1.0.0"
    profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1"
    original_sample_rate_hz: float = 4000.0
    analysis_sample_rate_hz: float = 1000.0
    feature_sample_rate_hz: float = 50.0
    time_s: list[float] = field(default_factory=list)
    homomorphic: list[float] = field(default_factory=list)
    hilbert: list[float] = field(default_factory=list)
    psd: list[float] = field(default_factory=list)
    wavelet: Optional[list[float]] = None
    feature_matrix: list[list[float]] = field(default_factory=list)
    normalization_metadata: dict[str, Any] = field(default_factory=dict)
    preprocessing_metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["time_s"] = sanitize_list(self.time_s)
        d["homomorphic"] = sanitize_list(self.homomorphic)
        d["hilbert"] = sanitize_list(self.hilbert)
        d["psd"] = sanitize_list(self.psd)
        if self.wavelet is not None:
            d["wavelet"] = sanitize_list(self.wavelet)
        return d


@dataclass(slots=True)
class SpringerSegmentationModel:
    """Versioned model artifact holding trained LR-HSMM parameters."""
    schema_version: str = "1.0.0"
    model_id: str = ""
    algorithm_id: str = "SPRINGER_LR_HSMM_V1"
    feature_profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1"
    state_order: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
    feature_names: list[str] = field(default_factory=lambda: ["homomorphic", "hilbert", "psd"])
    feature_count: int = 3
    feature_sample_rate_hz: float = 50.0
    analysis_sample_rate_hz: float = 1000.0
    lr_weights: dict[str, list[float]] = field(default_factory=dict)
    lr_intercepts: dict[str, float] = field(default_factory=dict)
    observation_mean: list[float] = field(default_factory=list)
    observation_covariance: list[list[float]] = field(default_factory=list)
    initial_state_probabilities: list[float] = field(default_factory=lambda: [0.25, 0.25, 0.25, 0.25])
    training_random_seed: int = 42
    training_metadata: dict[str, Any] = field(default_factory=dict)
    dependency_versions: dict[str, str] = field(default_factory=dict)
    git_commit_sha: str = ""
    created_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpringerSegmentationModel:
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            model_id=data.get("model_id", ""),
            algorithm_id=data.get("algorithm_id", "SPRINGER_LR_HSMM_V1"),
            feature_profile_id=data.get("feature_profile_id", "SPRINGER_PHYSIONET_REFERENCE_V1"),
            state_order=data.get("state_order", [1, 2, 3, 4]),
            feature_names=data.get("feature_names", ["homomorphic", "hilbert", "psd"]),
            feature_count=data.get("feature_count", 3),
            feature_sample_rate_hz=float(data.get("feature_sample_rate_hz", 50.0)),
            analysis_sample_rate_hz=float(data.get("analysis_sample_rate_hz", 1000.0)),
            lr_weights=data.get("lr_weights", {}),
            lr_intercepts=data.get("lr_intercepts", {}),
            observation_mean=data.get("observation_mean", []),
            observation_covariance=data.get("observation_covariance", []),
            initial_state_probabilities=data.get("initial_state_probabilities", [0.25, 0.25, 0.25, 0.25]),
            training_random_seed=data.get("training_random_seed", 42),
            training_metadata=data.get("training_metadata", {}),
            dependency_versions=data.get("dependency_versions", {}),
            git_commit_sha=data.get("git_commit_sha", ""),
            created_at_utc=data.get("created_at_utc", ""),
        )


@dataclass(slots=True)
class SpringerSegmentationResult:
    """Quantitative result of Springer LR-HSMM segmentation inference."""
    schema_version: str = "1.0.0"
    status: str = "SUCCESS"
    profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1"
    model_id: str = ""
    heart_rate_estimate_bpm: Optional[float] = None
    cycle_duration_estimate_s: Optional[float] = None
    systolic_interval_estimate_s: Optional[float] = None
    feature_sample_rate_hz: float = 50.0
    total_frames_50hz: int = 0
    duration_s: float = 0.0
    state_sequence_50hz: list[int] = field(default_factory=list)
    state_intervals: list[dict[str, Any]] = field(default_factory=list)
    s1_intervals: list[dict[str, Any]] = field(default_factory=list)
    s2_intervals: list[dict[str, Any]] = field(default_factory=list)
    systole_intervals: list[dict[str, Any]] = field(default_factory=list)
    diastole_intervals: list[dict[str, Any]] = field(default_factory=list)
    cycle_count: int = 0
    technical_warnings: list[str] = field(default_factory=list)
    feature_traces: Optional[dict[str, Any]] = None
    durations_summary: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SegmentationEvaluationMetrics:
    """Performance evaluation against reference temporal event annotations."""
    tolerance_ms: float
    true_positives: int
    false_positives: int
    false_negatives: int
    sensitivity: float
    positive_predictivity: float
    f1_score: float
    total_reference_events: int
    total_predicted_events: int
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
