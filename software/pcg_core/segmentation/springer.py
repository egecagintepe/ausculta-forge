"""AuscultaForge — Top-Level Springer LR-HSMM Segmentation Orchestrator.

Provides the primary public entry points:
- segment_pcg_springer(): Top-level PCG segmentation inference
- train_springer_model_from_features(): Model training from annotated feature matrices
- build_demo_springer_model(): Deterministic synthetic demo model builder

Strict Boundaries:
- If no model is supplied, returns truthful MODEL_REQUIRED; does NOT fabricate states.
- Results represent acoustic segmentation intervals, NOT medical diagnosis.
"""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import uuid
from typing import Optional, Dict, Any, List
import numpy as np

from .models import (
    HeartSoundState,
    SegmentationStatus,
    StateInterval,
    SpringerFeatureResult,
    SpringerSegmentationModel,
    SpringerSegmentationResult,
)
from .springer_config import (
    SpringerProfileConfig,
    SPRINGER_PHYSIONET_REFERENCE_V1,
    SUPPORTED_SPRINGER_PROFILES,
)
from .springer_preprocessing import run_springer_preprocessing
from .springer_features import extract_springer_features
from .heart_rate import run_cardiac_timing_estimation
from .durations import compute_springer_duration_distributions
from .logistic import (
    train_springer_one_vs_rest_logistic,
    predict_logistic_state_posteriors,
)
from .hsmm import compute_hsmm_log_emissions, viterbi_decode_pcg_extended


def segment_pcg_springer(
    signal: np.ndarray,
    sample_rate_hz: float,
    model: Optional[SpringerSegmentationModel] = None,
    config: Optional[SpringerProfileConfig] = None,
) -> SpringerSegmentationResult:
    """Execute complete Springer LR-HSMM heart-sound segmentation inference on PCG audio.
    
    Parameters
    ----------
    signal : np.ndarray
        Raw 1D PCG audio array (e.g. from 4000 Hz, 48000 Hz, or 1000 Hz source).
    sample_rate_hz : float
        Sampling frequency in Hertz.
    model : Optional[SpringerSegmentationModel]
        Trained Springer segmentation model artifact.
    config : Optional[SpringerProfileConfig]
        Pipeline profile configuration (default: SPRINGER_PHYSIONET_REFERENCE_V1).
        
    Returns
    -------
    SpringerSegmentationResult
        Quantitative segmentation result including state sequence, intervals, and HR estimates.
    """
    cfg = config or SPRINGER_PHYSIONET_REFERENCE_V1
    profile_id = cfg.profile_id

    # 1. TRUTHFUL NO-MODEL GUARD: DO NOT FABRICATE STATES
    if model is None:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.MODEL_REQUIRED,
            profile_id=profile_id,
            model_id="",
            technical_warnings=["No trained Springer segmentation model is currently selected. State sequence was not computed."],
            provenance={"notice": "Model required for Springer LR-HSMM segmentation inference."},
        )

    # Validate signal
    if not isinstance(signal, np.ndarray):
        signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim != 1:
        signal = signal.flatten()

    total_samples = len(signal)
    duration_s = float(total_samples) / float(sample_rate_hz) if sample_rate_hz > 0 else 0.0

    # 2. SHORT RECORDING GUARD
    if duration_s < 2.0:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.SIGNAL_TOO_SHORT,
            profile_id=profile_id,
            model_id=model.model_id,
            duration_s=round(duration_s, 4),
            technical_warnings=[f"Signal duration ({duration_s:.2f} s) is below the 2.0 s minimum required for cardiac timing estimation."],
        )

    # 3. PREPROCESSING TO 1000 HZ ANALYSIS RATE
    x_1000, prep_meta = run_springer_preprocessing(signal, sample_rate_hz=sample_rate_hz, config=cfg)

    # 4. CARDIAC TIMING ESTIMATION (HR & Systolic Interval)
    timing = run_cardiac_timing_estimation(x_1000, sample_rate_hz=cfg.analysis_sample_rate_hz)
    if not timing["is_valid"]:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.HEART_RATE_ESTIMATION_FAILED,
            profile_id=profile_id,
            model_id=model.model_id,
            duration_s=round(duration_s, 4),
            technical_warnings=[f"Cardiac timing estimation failed: {timing['error']}"],
            provenance={"preprocessing": prep_meta},
        )

    hr_bpm = timing["heart_rate_bpm"]
    cycle_s = timing["cycle_duration_s"]
    sys_s = timing["systolic_interval_s"]

    # 5. DURATION DISTRIBUTIONS
    try:
        dur_stats = compute_springer_duration_distributions(
            cycle_duration_s=cycle_s,
            systolic_interval_s=sys_s,
            feature_sample_rate_hz=cfg.feature_sample_rate_hz,
        )
    except Exception as e:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.SEGMENTATION_PARAMETERS_INVALID,
            profile_id=profile_id,
            model_id=model.model_id,
            duration_s=round(duration_s, 4),
            heart_rate_estimate_bpm=hr_bpm,
            cycle_duration_estimate_s=cycle_s,
            systolic_interval_estimate_s=sys_s,
            technical_warnings=[f"Duration distribution calculation failed: {e}"],
            provenance={"preprocessing": prep_meta},
        )

    # 6. FEATURE EXTRACTION (Downsampled to 50 Hz, z-score normalized)
    feat_res = extract_springer_features(x_1000, config=cfg, original_fs=sample_rate_hz)
    X_obs = np.asarray(feat_res.feature_matrix, dtype=np.float64)

    if len(X_obs) == 0:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.DECODING_FAILED,
            profile_id=profile_id,
            model_id=model.model_id,
            technical_warnings=["Feature extraction produced 0 observation frames."],
        )

    # Check feature count compatibility with model
    if X_obs.shape[1] != model.feature_count:
        return SpringerSegmentationResult(
            schema_version="1.0.0",
            status=SegmentationStatus.DECODING_FAILED,
            profile_id=profile_id,
            model_id=model.model_id,
            technical_warnings=[
                f"Feature dimension mismatch: extracted {X_obs.shape[1]} features, "
                f"but model '{model.model_id}' expects {model.feature_count} features."
            ],
        )

    # 7. LOGISTIC REGRESSION POSTERIORS
    posteriors = predict_logistic_state_posteriors(
        X_obs,
        weights=model.lr_weights,
        intercepts=model.lr_intercepts,
    )

    # 8. BAYES EMISSION CALCULATION
    log_emissions = compute_hsmm_log_emissions(
        observation_matrix=X_obs,
        logistic_posteriors=posteriors,
        obs_mean=np.asarray(model.observation_mean, dtype=np.float64),
        obs_cov=np.asarray(model.observation_covariance, dtype=np.float64),
        initial_probs=model.initial_state_probabilities,
    )

    # 9. EXTENDED VITERBI DECODING
    state_seq_50hz, intervals = viterbi_decode_pcg_extended(
        log_emissions=log_emissions,
        duration_stats=dur_stats,
        initial_probs=model.initial_state_probabilities,
    )

    # 10. INTERVAL PARTITIONING
    s1_list = [iv.to_dict() for iv in intervals if iv.state == HeartSoundState.S1]
    s2_list = [iv.to_dict() for iv in intervals if iv.state == HeartSoundState.S2]
    sys_list = [iv.to_dict() for iv in intervals if iv.state == HeartSoundState.SYSTOLE]
    dia_list = [iv.to_dict() for iv in intervals if iv.state == HeartSoundState.DIASTOLE]

    # Cycle count is the number of complete S1 -> Systole -> S2 -> Diastole cycles
    cycle_count = min(len(s1_list), len(s2_list))

    dur_summary = {
        state.name: dur_stats[state].to_dict() for state in dur_stats
    }

    provenance = {
        "analysis_type": "springer_lr_hsmm_segmentation",
        "profile_id": profile_id,
        "model_id": model.model_id,
        "original_sample_rate_hz": float(sample_rate_hz),
        "analysis_sample_rate_hz": float(cfg.analysis_sample_rate_hz),
        "feature_sample_rate_hz": float(cfg.feature_sample_rate_hz),
        "feature_names": cfg.feature_names,
        "feature_frames_count": len(state_seq_50hz),
        "preprocessing": prep_meta,
        "durations_summary": dur_summary,
        "notice": "Research acoustic temporal segmentation only. Not a medical diagnosis.",
    }

    feat_dict: dict[str, Any] = {
        "time_s": feat_res.time_s,
        "homomorphic": feat_res.homomorphic,
        "hilbert": feat_res.hilbert,
        "psd": feat_res.psd,
    }
    if feat_res.wavelet is not None:
        feat_dict["wavelet"] = feat_res.wavelet

    return SpringerSegmentationResult(
        schema_version="1.0.0",
        status=SegmentationStatus.SUCCESS,
        profile_id=profile_id,
        model_id=model.model_id,
        heart_rate_estimate_bpm=hr_bpm,
        cycle_duration_estimate_s=cycle_s,
        systolic_interval_estimate_s=sys_s,
        feature_sample_rate_hz=cfg.feature_sample_rate_hz,
        total_frames_50hz=len(state_seq_50hz),
        duration_s=round(duration_s, 4),
        state_sequence_50hz=[int(s) for s in state_seq_50hz],
        state_intervals=[iv.to_dict() for iv in intervals],
        s1_intervals=s1_list,
        s2_intervals=s2_list,
        systole_intervals=sys_list,
        diastole_intervals=dia_list,
        cycle_count=cycle_count,
        technical_warnings=[],
        feature_traces=feat_dict,
        durations_summary=dur_summary,
        provenance=provenance,
    )


def train_springer_model_from_features(
    training_features: np.ndarray,
    training_labels: np.ndarray,
    model_id: str,
    feature_profile_id: str = "SPRINGER_PHYSIONET_REFERENCE_V1",
    feature_names: Optional[list[str]] = None,
    random_seed: int = 42,
    training_metadata: Optional[dict[str, Any]] = None,
) -> SpringerSegmentationModel:
    """Train four one-vs-rest logistic regression models and build model artifact.
    
    Parameters
    ----------
    training_features : np.ndarray
        Array of shape (N, K) containing normalized feature observations.
    training_labels : np.ndarray
        Array of length N with state integers in {1, 2, 3, 4}.
    model_id : str
        Unique identifier for the trained model artifact.
    feature_profile_id : str
        Profile ID (default: SPRINGER_PHYSIONET_REFERENCE_V1).
    feature_names : Optional[list[str]]
        Names of the K feature columns.
    random_seed : int
        Seed for deterministic class-balancing negative subsampling.
    training_metadata : Optional[dict[str, Any]]
        Provenance metadata describing training records, source datasets, etc.
        
    Returns
    -------
    SpringerSegmentationModel
        Complete versioned model artifact ready for serialization or inference.
    """
    X = np.asarray(training_features, dtype=np.float64)
    y = np.asarray(training_labels, dtype=np.int32)
    K = X.shape[1]

    names = feature_names or [f"feature_{i}" for i in range(K)]

    # 1. Train 4 one-vs-rest logistic regression models
    weights, intercepts = train_springer_one_vs_rest_logistic(X, y, random_seed=random_seed)

    # 2. Compute observation statistics for Bayes density P(o)
    obs_mean = [float(v) for v in np.mean(X, axis=0)]
    obs_cov = [[float(v) for v in row] for row in np.cov(X, rowvar=False)]

    now_utc = datetime.now(timezone.utc).isoformat()

    return SpringerSegmentationModel(
        schema_version="1.0.0",
        model_id=model_id,
        algorithm_id="SPRINGER_LR_HSMM_V1",
        feature_profile_id=feature_profile_id,
        state_order=[1, 2, 3, 4],
        feature_names=names,
        feature_count=K,
        feature_sample_rate_hz=50.0,
        analysis_sample_rate_hz=1000.0,
        lr_weights=weights,
        lr_intercepts=intercepts,
        observation_mean=obs_mean,
        observation_covariance=obs_cov,
        initial_state_probabilities=[0.25, 0.25, 0.25, 0.25],
        training_random_seed=random_seed,
        training_metadata=training_metadata or {},
        dependency_versions={
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        git_commit_sha="",
        created_at_utc=now_utc,
    )


def build_demo_springer_model(
    random_seed: int = 42,
    include_wavelet: bool = False,
) -> SpringerSegmentationModel:
    """Build a deterministic synthetic demo model for reproducible testing and verification.
    
    Generates synthetic feature distributions reflecting characteristic Springer envelope signatures:
    - S1: elevated homomorphic, elevated Hilbert, high 40-60 Hz PSD energy
    - Systole: low homomorphic, low Hilbert, low PSD energy
    - S2: elevated homomorphic, elevated Hilbert, moderate 40-60 Hz PSD energy
    - Diastole: low homomorphic, low Hilbert, low PSD energy
    """
    rng = np.random.default_rng(random_seed)
    n_samples_per_state = 500

    # 3 features: [homomorphic, hilbert, psd] (+ optional wavelet)
    features_list = []
    labels_list = []

    # S1 (State 1): High energy across envelopes and PSD
    s1_feat = rng.normal(loc=[1.5, 1.4, 1.8], scale=0.3, size=(n_samples_per_state, 3))
    # Systole (State 2): Low quiescent energy
    sys_feat = rng.normal(loc=[-0.8, -0.7, -0.6], scale=0.3, size=(n_samples_per_state, 3))
    # S2 (State 3): Moderate-high energy, slightly lower PSD than S1
    s2_feat = rng.normal(loc=[1.2, 1.1, 0.8], scale=0.3, size=(n_samples_per_state, 3))
    # Diastole (State 4): Low quiescent energy
    dia_feat = rng.normal(loc=[-0.9, -0.8, -0.7], scale=0.3, size=(n_samples_per_state, 3))

    if include_wavelet:
        s1_wav = rng.normal(loc=1.6, scale=0.3, size=(n_samples_per_state, 1))
        sys_wav = rng.normal(loc=-0.8, scale=0.3, size=(n_samples_per_state, 1))
        s2_wav = rng.normal(loc=1.3, scale=0.3, size=(n_samples_per_state, 1))
        dia_wav = rng.normal(loc=-0.9, scale=0.3, size=(n_samples_per_state, 1))
        s1_feat = np.column_stack([s1_feat, s1_wav])
        sys_feat = np.column_stack([sys_feat, sys_wav])
        s2_feat = np.column_stack([s2_feat, s2_wav])
        dia_feat = np.column_stack([dia_feat, dia_wav])

    X_syn = np.vstack([s1_feat, sys_feat, s2_feat, dia_feat])
    y_syn = np.concatenate([
        np.full(n_samples_per_state, 1, dtype=np.int32),
        np.full(n_samples_per_state, 2, dtype=np.int32),
        np.full(n_samples_per_state, 3, dtype=np.int32),
        np.full(n_samples_per_state, 4, dtype=np.int32),
    ])

    feature_names = ["homomorphic", "hilbert", "psd"]
    if include_wavelet:
        feature_names.append("wavelet")

    model_id = "springer_demo_3feature_v1" if not include_wavelet else "springer_demo_4feature_v1"
    meta = {
        "purpose": "DEMO / REPRODUCIBILITY MODEL",
        "is_production_validated": False,
        "synthetic": True,
        "sample_count": len(y_syn),
        "notes": "Generated programmatically for software verification without external proprietary weights.",
    }

    return train_springer_model_from_features(
        training_features=X_syn,
        training_labels=y_syn,
        model_id=model_id,
        feature_profile_id="SPRINGER_PHYSIONET_REFERENCE_V1" if not include_wavelet else "SPRINGER_PAPER_4FEATURE_V1",
        feature_names=feature_names,
        random_seed=random_seed,
        training_metadata=meta,
    )
