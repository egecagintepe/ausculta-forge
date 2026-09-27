"""AuscultaForge — Compact Unregularized Binary Logistic Regression & One-vs-Rest Training.

Implements the 4 one-vs-rest logistic regression models used in Springer et al. (2016):
- S1 vs Rest
- Systole vs Rest
- S2 vs Rest
- Diastole vs Rest

Methodological Specifications:
- Unregularized maximum likelihood optimization via SciPy (L-BFGS-B)
- Numerically stable sigmoid function protecting against exp overflow
- Deterministic class balancing via random subsampling with explicit random_seed
- Numerically stable binary cross-entropy loss with exact analytical gradients
"""

from __future__ import annotations

from typing import Dict, Tuple, Any
import numpy as np
import scipy.optimize

from .models import HeartSoundState


def stable_sigmoid(z: np.ndarray | float) -> np.ndarray:
    """Compute numerically stable sigmoid function preventing exponential overflow."""
    z_arr = np.asarray(z, dtype=np.float64)
    # For z >= 0: 1 / (1 + exp(-z))
    # For z < 0: exp(z) / (1 + exp(z))
    pos_mask = z_arr >= 0
    res = np.zeros_like(z_arr, dtype=np.float64)

    # Positive branch
    res[pos_mask] = 1.0 / (1.0 + np.exp(-z_arr[pos_mask]))

    # Negative branch
    exp_neg = np.exp(z_arr[~pos_mask])
    res[~pos_mask] = exp_neg / (1.0 + exp_neg)

    return res


def _binary_logistic_loss_and_grad(
    params: np.ndarray,
    X: np.ndarray,
    y: np.ndarray,
) -> Tuple[float, np.ndarray]:
    """Compute unregularized binary cross-entropy loss and analytical gradient.
    
    params : [w_1, w_2, ..., w_K, b]
    """
    w = params[:-1]
    b = params[-1]
    n_samples = len(y)

    z = np.dot(X, w) + b
    p = stable_sigmoid(z)
    p_safe = np.clip(p, 1e-15, 1.0 - 1e-15)

    # Binary cross entropy: -1/N * sum(y * log(p) + (1-y) * log(1-p))
    loss = -float(np.mean(y * np.log(p_safe) + (1.0 - y) * np.log(1.0 - p_safe)))

    # Gradient
    diff = p - y
    grad_w = np.dot(X.T, diff) / float(n_samples)
    grad_b = float(np.mean(diff))

    grad = np.concatenate([grad_w, [grad_b]])
    return loss, grad


def train_single_binary_logistic_model(
    X: np.ndarray,
    y_binary: np.ndarray,
    initial_weights: np.ndarray | None = None,
) -> Tuple[np.ndarray, float]:
    """Train single unregularized binary logistic regression model using SciPy L-BFGS-B."""
    n_features = X.shape[1]
    if initial_weights is None:
        init_params = np.zeros(n_features + 1, dtype=np.float64)
    else:
        init_params = np.asarray(initial_weights, dtype=np.float64)

    res = scipy.optimize.minimize(
        fun=_binary_logistic_loss_and_grad,
        x0=init_params,
        args=(X, y_binary),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 200, "ftol": 1e-9, "gtol": 1e-7},
    )

    fitted = res.x
    w = np.asarray(fitted[:-1], dtype=np.float64)
    b = float(fitted[-1])
    return w, b


def train_springer_one_vs_rest_logistic(
    X: np.ndarray,
    y: np.ndarray,
    random_seed: int = 42,
) -> Tuple[Dict[str, list[float]], Dict[str, float]]:
    """Train four balanced one-vs-rest binary logistic regression models.
    
    Parameters
    ----------
    X : np.ndarray
        Feature matrix of shape (N, K).
    y : np.ndarray
        Integer state labels in {1, 2, 3, 4} of length N.
    random_seed : int
        Seed for deterministic negative-class balancing subsampling.
        
    Returns
    -------
    Tuple[Dict[str, list[float]], Dict[str, float]]
        (weights_per_state, intercepts_per_state)
    """
    if len(X) != len(y):
        raise ValueError(f"Feature count ({len(X)}) must match label count ({len(y)}).")
    if len(X) == 0:
        raise ValueError("Cannot train logistic regression on empty dataset.")

    unique_states = np.unique(y)
    for s in [1, 2, 3, 4]:
        if s not in unique_states:
            raise ValueError(f"Dataset is missing required cardiac state {s} ({HeartSoundState(s).name}).")

    weights: Dict[str, list[float]] = {}
    intercepts: Dict[str, float] = {}

    rng = np.random.default_rng(random_seed)

    for state_int in [1, 2, 3, 4]:
        state_key = str(state_int)
        pos_idx = np.where(y == state_int)[0]
        n_pos = len(pos_idx)

        # Source-faithful Springer class balancing:
        # Separate negative pools for each of the other three states
        other_states = [s for s in [1, 2, 3, 4] if s != state_int]
        other_pools = [np.where(y == s)[0] for s in other_states]
        min_other_len = min(len(pool) for pool in other_pools)

        per_other = min(n_pos // 3, min_other_len)
        if per_other < 1:
            per_other = 1

        # Sample per_other observations from EACH other state
        sampled_neg_parts = []
        for pool in other_pools:
            replace = len(pool) < per_other
            sampled_neg_parts.append(rng.choice(pool, size=per_other, replace=replace))
        sampled_neg_idx = np.concatenate(sampled_neg_parts)

        # Sample exactly 3 * per_other from the target state
        n_pos_sample = 3 * per_other
        replace_pos = n_pos < n_pos_sample
        sampled_pos_idx = rng.choice(pos_idx, size=n_pos_sample, replace=replace_pos)

        balanced_idx = np.concatenate([sampled_pos_idx, sampled_neg_idx])
        rng.shuffle(balanced_idx)

        X_b = X[balanced_idx]
        y_b = (y[balanced_idx] == state_int).astype(np.float64)

        w, b = train_single_binary_logistic_model(X_b, y_b)
        weights[state_key] = [float(v) for v in w]
        intercepts[state_key] = float(b)

    return weights, intercepts


def predict_logistic_state_posteriors(
    X: np.ndarray,
    weights: Dict[str, list[float]],
    intercepts: Dict[str, float],
) -> np.ndarray:
    """Compute posterior probabilities P(state = j | o_t) for each observation.
    
    Parameters
    ----------
    X : np.ndarray
        Observation matrix of shape (T, K).
    weights : Dict[str, list[float]]
        Weights dictionary with string keys '1', '2', '3', '4'.
    intercepts : Dict[str, float]
        Intercept dictionary with string keys '1', '2', '3', '4'.
        
    Returns
    -------
    np.ndarray
        Posterior probability matrix of shape (T, 4), bounded in [0, 1].
    """
    if len(X) == 0:
        return np.empty((0, 4), dtype=np.float64)

    T = len(X)
    posteriors = np.zeros((T, 4), dtype=np.float64)

    for col, state_int in enumerate([1, 2, 3, 4]):
        state_key = str(state_int)
        w = np.asarray(weights[state_key], dtype=np.float64)
        b = float(intercepts[state_key])

        z = np.dot(X, w) + b
        p = stable_sigmoid(z)
        posteriors[:, col] = p

    # Guarantee strict [1e-15, 1.0] numerical safety
    return np.clip(posteriors, 1e-15, 1.0)
