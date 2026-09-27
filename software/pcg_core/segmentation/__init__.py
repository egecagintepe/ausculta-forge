"""AuscultaForge — Scientific Heart-Sound Segmentation Module.

Implements source-faithful Springer Logistic Regression + Hidden Semi-Markov Model (LR-HSMM)
cardiac cycle segmentation:
S1 -> Systole -> S2 -> Diastole -> S1
"""

from .models import (
    HeartSoundState,
    SegmentationStatus,
    StateInterval,
    StateDurationStats,
    SpringerFeatureResult,
    SpringerSegmentationModel,
    SpringerSegmentationResult,
    SegmentationEvaluationMetrics,
)
from .springer_config import (
    SpringerProfileConfig,
    SPRINGER_PHYSIONET_REFERENCE_V1,
    SPRINGER_PAPER_4FEATURE_V1,
    SUPPORTED_SPRINGER_PROFILES,
    SPRINGER_PROFILES,
    get_springer_profile,
)
from .springer_preprocessing import (
    prepare_springer_analysis_signal,
    apply_springer_bandpass_filter,
    remove_schmidt_spikes,
    run_springer_preprocessing,
)
from .springer_features import (
    compute_springer_homomorphic_envelope,
    compute_springer_hilbert_feature,
    compute_springer_psd_feature,
    compute_springer_wavelet_feature,
    normalize_features_per_recording,
    extract_springer_features,
)
from .heart_rate import (
    estimate_heart_rate_schmidt,
    estimate_systolic_interval,
    run_cardiac_timing_estimation,
)
from .durations import (
    compute_springer_duration_distributions,
    get_duration_probabilities_50hz,
)
from .logistic import (
    stable_sigmoid,
    train_single_binary_logistic_model,
    train_springer_one_vs_rest_logistic,
    predict_logistic_state_posteriors,
)
from .hsmm import (
    compute_hsmm_log_emissions,
    viterbi_decode_pcg_extended,
    extract_state_intervals_from_sequence,
)
from .evaluation import (
    evaluate_segmentation_onsets,
)
from .springer import (
    segment_pcg_springer,
    train_springer_model_from_features,
    build_demo_springer_model,
)

__all__ = [
    "HeartSoundState",
    "SegmentationStatus",
    "StateInterval",
    "StateDurationStats",
    "SpringerFeatureResult",
    "SpringerSegmentationModel",
    "SpringerSegmentationResult",
    "SegmentationEvaluationMetrics",
    "SpringerProfileConfig",
    "SPRINGER_PHYSIONET_REFERENCE_V1",
    "SPRINGER_PAPER_4FEATURE_V1",
    "SUPPORTED_SPRINGER_PROFILES",
    "SPRINGER_PROFILES",
    "get_springer_profile",
    "prepare_springer_analysis_signal",
    "apply_springer_bandpass_filter",
    "remove_schmidt_spikes",
    "run_springer_preprocessing",
    "compute_springer_homomorphic_envelope",
    "compute_springer_hilbert_feature",
    "compute_springer_psd_feature",
    "compute_springer_wavelet_feature",
    "normalize_features_per_recording",
    "extract_springer_features",
    "estimate_heart_rate_schmidt",
    "estimate_systolic_interval",
    "run_cardiac_timing_estimation",
    "compute_springer_duration_distributions",
    "get_duration_probabilities_50hz",
    "stable_sigmoid",
    "train_single_binary_logistic_model",
    "train_springer_one_vs_rest_logistic",
    "predict_logistic_state_posteriors",
    "compute_hsmm_log_emissions",
    "viterbi_decode_pcg_extended",
    "extract_state_intervals_from_sequence",
    "evaluate_segmentation_onsets",
    "segment_pcg_springer",
    "train_springer_model_from_features",
    "build_demo_springer_model",
]
