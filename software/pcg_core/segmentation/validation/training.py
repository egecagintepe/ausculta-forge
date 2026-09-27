"""AuscultaForge — Real PCG Springer Segmentation Model Training.

Extracts features from training PCG records, aligns them with verified reference
annotations, filters out state 0 frames, and trains a real Springer LR-HSMM model artifact.

Guarantees:
- Reuses train_springer_model_from_features (zero math duplication).
- Never uses demo models.
- Explicit real model IDs: auscultaforge_circor_springer_ref_v1_fold{k}.
- State 0 frames are strictly excluded from training pools.
- Optional filesystem caching for extracted feature matrices.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import scipy.io.wavfile

from ..springer import (
    train_springer_model_from_features,
    SpringerSegmentationModel,
)
from ..springer_config import (
    SpringerProfileConfig,
    SPRINGER_PHYSIONET_REFERENCE_V1,
)
from ..springer_features import extract_springer_features
from ..springer_preprocessing import run_springer_preprocessing
from .models import AnnotatedPCGRecord
from .annotations import convert_intervals_to_50hz_labels


def get_record_cache_key(
    record: AnnotatedPCGRecord,
    profile_id: str,
    feature_rate_hz: float = 50.0,
) -> str:
    """Generate deterministic fingerprint key for caching extracted features and reference labels."""
    hasher = hashlib.sha256()
    hasher.update(record.dataset_id.encode("utf-8"))
    hasher.update(record.dataset_version.encode("utf-8"))
    hasher.update(record.record_id.encode("utf-8"))
    hasher.update(str(record.duration_s).encode("utf-8"))
    hasher.update(profile_id.encode("utf-8"))
    hasher.update(str(feature_rate_hz).encode("utf-8"))

    if record.wav_path and os.path.exists(record.wav_path):
        stat = os.stat(record.wav_path)
        hasher.update(str(stat.st_size).encode("utf-8"))
        hasher.update(str(stat.st_mtime).encode("utf-8"))

    return hasher.hexdigest()[:24]


def extract_record_features_and_labels(
    record: AnnotatedPCGRecord,
    config: SpringerProfileConfig = SPRINGER_PHYSIONET_REFERENCE_V1,
    cache_dir: Optional[Path | str] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract 50 Hz features, reference state labels, and evaluation mask for a single record.
    
    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        feature_matrix: 2D array of shape (N, n_features)
        reference_labels: 1D array of shape (N,) with states in {0, 1, 2, 3, 4}
        eval_mask: 1D bool array of shape (N,)
    """
    cache_path: Optional[Path] = None
    if cache_dir:
        cd = Path(cache_dir)
        cd.mkdir(parents=True, exist_ok=True)
        key = get_record_cache_key(record, config.profile_id, config.feature_sample_rate_hz)
        cache_path = cd / f"{record.record_id}_{key}.npz"
        if cache_path.is_file():
            try:
                data = np.load(cache_path)
                return data["X"], data["y"], data["mask"]
            except Exception:
                pass  # Recompute on any cache corruption

    # Load audio
    if not record.wav_path or not os.path.exists(record.wav_path):
        raise FileNotFoundError(f"Cannot extract features: WAV file missing for record {record.record_id}")

    fs_orig, audio = scipy.io.wavfile.read(record.wav_path)
    if audio.ndim > 1:
        audio = audio[:, 0]
    audio_float = audio.astype(np.float64)
    # Normalize if integer PCM
    if np.issubdtype(audio.dtype, np.integer):
        max_val = float(np.iinfo(audio.dtype).max)
        audio_float /= max_val

    # 1. Preprocessing (resample to 1000 Hz, cascaded LP400->HP25, spike removal)
    x_1000, _ = run_springer_preprocessing(audio_float, sample_rate_hz=float(fs_orig), config=config)

    # 2. Extract multi-envelope features downsampled to 50 Hz
    feat_res = extract_springer_features(x_1000, config=config, original_fs=float(fs_orig))
    X_50hz = np.asarray(feat_res.feature_matrix, dtype=np.float64)
    n_feat_frames = len(X_50hz)

    # 3. Convert reference intervals to 50 Hz labels matching frame count
    y_50hz, mask_50hz = convert_intervals_to_50hz_labels(
        record.annotation_intervals,
        total_frames_50hz=n_feat_frames,
        feature_sample_rate_hz=config.feature_sample_rate_hz,
    )

    # Align / harmonize length if small difference
    min_len = min(len(X_50hz), len(y_50hz))
    X_50hz = X_50hz[:min_len]
    y_50hz = y_50hz[:min_len]
    mask_50hz = mask_50hz[:min_len]

    # Save to cache if enabled
    if cache_path:
        try:
            np.savez_compressed(cache_path, X=X_50hz, y=y_50hz, mask=mask_50hz)
        except Exception:
            pass

    return X_50hz, y_50hz, mask_50hz


def train_fold_springer_model(
    training_records: Sequence[AnnotatedPCGRecord],
    fold_idx: int,
    config: SpringerProfileConfig = SPRINGER_PHYSIONET_REFERENCE_V1,
    random_seed: int = 2026,
    cache_dir: Optional[Path | str] = None,
) -> SpringerSegmentationModel:
    """Train a real Springer segmentation model artifact from training partition records.
    
    Rules:
    - Never uses synthetic demo model.
    - Excludes state 0 frames from training observations.
    - Balances classes via Springer per-other state sampling.
    """
    if not training_records:
        raise ValueError("Cannot train Springer model with zero training records.")

    all_X_list: list[np.ndarray] = []
    all_y_list: list[np.ndarray] = []

    total_annotated_frames = 0
    unique_training_subjects = {r.subject_id for r in training_records}

    for rec in training_records:
        try:
            X, y, mask = extract_record_features_and_labels(rec, config=config, cache_dir=cache_dir)
        except Exception as e:
            # Skip corrupted audio in training
            continue

        # Filter: strictly keep frames where reference state is in {1, 2, 3, 4}
        valid_indices = np.where(mask & (y >= 1) & (y <= 4))[0]
        if len(valid_indices) > 0:
            all_X_list.append(X[valid_indices])
            all_y_list.append(y[valid_indices])
            total_annotated_frames += len(valid_indices)

    if not all_X_list:
        raise ValueError(
            f"Fold {fold_idx}: No valid annotated training frames found across {len(training_records)} records."
        )

    X_train = np.vstack(all_X_list)
    y_train = np.concatenate(all_y_list)

    # Check representation of all 4 states
    present_states = set(np.unique(y_train))
    missing = {1, 2, 3, 4} - present_states
    if missing:
        raise ValueError(
            f"Fold {fold_idx}: Training set is missing observations for states {missing}."
        )

    model_id = f"auscultaforge_circor_springer_ref_v1_fold{fold_idx}"
    training_meta = {
        "dataset_name": "CirCor DigiScope Phonocardiogram Dataset",
        "dataset_version": "1.0.3",
        "profile_id": config.profile_id,
        "fold_idx": fold_idx,
        "training_subject_count": len(unique_training_subjects),
        "training_record_count": len(training_records),
        "training_annotated_frame_count": int(total_annotated_frames),
        "random_seed": random_seed,
        "is_production_validated": False,
        "is_synthetic_demo": False,
        "algorithm": "Springer LR-HSMM Segmentation (Stage-C Real Validation)",
    }

    model = train_springer_model_from_features(
        training_features=X_train,
        training_labels=y_train,
        model_id=model_id,
        feature_profile_id=config.profile_id,
        feature_names=config.feature_names,
        random_seed=random_seed,
        training_metadata=training_meta,
    )

    return model
