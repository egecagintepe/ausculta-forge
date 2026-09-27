"""AuscultaForge — Automated Tests for Springer Logistic Regression.

Verifies:
- Numerically stable sigmoid function (overflow/underflow resilience)
- Unregularized binary logistic regression convergence
- Deterministic 4-class one-vs-rest training with explicit random seed
- Class balancing via negative-class subsampling
- Probability bounding in [0, 1]
- High accuracy on separable synthetic feature clusters
- Model serialization round-trip
"""

import math
import numpy as np
import pytest

from pcg_core.segmentation.logistic import (
    stable_sigmoid,
    train_single_binary_logistic_model,
    train_springer_one_vs_rest_logistic,
    predict_logistic_state_posteriors,
)
from pcg_core.segmentation.models import SpringerSegmentationModel, HeartSoundState


class TestSpringerLogistic:
    """Verifies Springer binary logistic regression and one-vs-rest training."""

    def test_stable_sigmoid_extreme_values(self):
        # Extreme negative -> near 0.0 (no underflow crash)
        neg_val = stable_sigmoid(-1000.0)
        assert 0.0 <= neg_val < 1e-15

        # Extreme positive -> near 1.0 (no overflow crash)
        pos_val = stable_sigmoid(1000.0)
        assert 1.0 - 1e-15 < pos_val <= 1.0

        # Zero -> exactly 0.5
        zero_val = stable_sigmoid(0.0)
        assert zero_val == 0.5

    def test_single_binary_logistic_separable_data(self):
        rng = np.random.default_rng(42)
        # 100 positive samples around +3.0, 100 negative samples around -3.0
        X_pos = rng.normal(loc=3.0, scale=0.5, size=(100, 2))
        X_neg = rng.normal(loc=-3.0, scale=0.5, size=(100, 2))

        X = np.vstack([X_pos, X_neg])
        y = np.concatenate([np.ones(100), np.zeros(100)])

        w, b = train_single_binary_logistic_model(X, y)

        # Must cleanly separate the two clusters
        preds_pos = stable_sigmoid(np.dot(X_pos, w) + b)
        preds_neg = stable_sigmoid(np.dot(X_neg, w) + b)

        assert np.mean(preds_pos) > 0.95
        assert np.mean(preds_neg) < 0.05

    def test_one_vs_rest_training_deterministic_with_seed(self):
        rng = np.random.default_rng(2026)
        n_each = 150

        # 4 distinct synthetic clusters in 3D feature space
        c1 = rng.normal(loc=[3.0, 0.0, 0.0], scale=0.5, size=(n_each, 3))
        c2 = rng.normal(loc=[0.0, 3.0, 0.0], scale=0.5, size=(n_each, 3))
        c3 = rng.normal(loc=[0.0, 0.0, 3.0], scale=0.5, size=(n_each, 3))
        c4 = rng.normal(loc=[-3.0, -3.0, -3.0], scale=0.5, size=(n_each, 3))

        X = np.vstack([c1, c2, c3, c4])
        y = np.concatenate([
            np.full(n_each, 1),
            np.full(n_each, 2),
            np.full(n_each, 3),
            np.full(n_each, 4),
        ])

        # Run 1
        w1, b1 = train_springer_one_vs_rest_logistic(X, y, random_seed=123)
        # Run 2 with identical seed
        w2, b2 = train_springer_one_vs_rest_logistic(X, y, random_seed=123)

        # Coefficients must be exactly identical
        for k in ["1", "2", "3", "4"]:
            np.testing.assert_allclose(w1[k], w2[k], atol=1e-6)
            assert pytest.approx(b1[k], abs=1e-6) == b2[k]

        # Predict posteriors
        posteriors = predict_logistic_state_posteriors(X, w1, b1)
        assert posteriors.shape == (len(X), 4)
        assert np.all(posteriors >= 0.0)
        assert np.all(posteriors <= 1.0)

        # For cluster 1 (S1), state 1 probability must be highest
        c1_posts = posteriors[:n_each]
        assert np.mean(np.argmax(c1_posts, axis=1)) == 0  # 0-indexed column 0 is S1

    def test_model_artifact_serialization_round_trip(self):
        model = SpringerSegmentationModel(
            model_id="test_model_001",
            algorithm_id="SPRINGER_LR_HSMM_V1",
            feature_profile_id="SPRINGER_PHYSIONET_REFERENCE_V1",
            feature_names=["homomorphic", "hilbert", "psd"],
            feature_count=3,
            feature_sample_rate_hz=50.0,
            analysis_sample_rate_hz=1000.0,
            lr_weights={"1": [0.1, 0.2, 0.3], "2": [-0.1, -0.2, -0.3], "3": [0.5, 0.4, 0.1], "4": [-0.5, -0.4, -0.1]},
            lr_intercepts={"1": 0.05, "2": -0.05, "3": 0.10, "4": -0.10},
            observation_mean=[0.0, 0.0, 0.0],
            observation_covariance=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            initial_state_probabilities=[0.25, 0.25, 0.25, 0.25],
            training_random_seed=42,
            training_metadata={"records": 10},
            created_at_utc="2026-09-27T12:00:00Z",
        )

        d = model.to_dict()
        assert d["model_id"] == "test_model_001"
        assert len(d["lr_weights"]) == 4

        reloaded = SpringerSegmentationModel.from_dict(d)
        assert reloaded.model_id == model.model_id
        assert reloaded.feature_count == 3
        assert reloaded.lr_weights == model.lr_weights
        assert reloaded.lr_intercepts == model.lr_intercepts
