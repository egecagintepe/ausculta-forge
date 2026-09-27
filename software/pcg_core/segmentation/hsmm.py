"""AuscultaForge — Hidden Semi-Markov Model (HSMM) Extended Viterbi Decoding.

Implements the source-faithful Springer LR-HSMM explicit-duration sequence decoder:
1. Log-domain emission probability computation via Bayes' rule
2. Cyclic transition enforcement (S1 -> Systole -> S2 -> Diastole -> S1)
3. Extended Viterbi boundary handling (partial states permitted at recording start and end)
4. Cumulative prefix-sum emission scoring for O(1) duration evaluation
5. Exact backtracking producing a continuous 50 Hz state sequence in {1, 2, 3, 4}
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import scipy.stats

from .models import HeartSoundState, StateInterval, StateDurationStats
from .durations import get_duration_probabilities_50hz


def compute_hsmm_log_emissions(
    observation_matrix: np.ndarray,
    logistic_posteriors: np.ndarray,
    obs_mean: np.ndarray,
    obs_cov: np.ndarray,
    initial_probs: np.ndarray | list[float],
) -> np.ndarray:
    """Compute log emission probabilities ln P(o_t | S_t = j) using Bayes' rule.
    
    Formula:
    P(o_t | S_t = j) = P(S_t = j | o_t) * P(o_t) / P(S_t = j)
    ln P(o_t | S_t = j) = ln P(S_t = j | o_t) + ln P(o_t) - ln P(S_t = j)
    
    Parameters
    ----------
    observation_matrix : np.ndarray
        Shape (T, K) feature observations.
    logistic_posteriors : np.ndarray
        Shape (T, 4) logistic regression predicted posteriors.
    obs_mean : np.ndarray
        Shape (K,) overall observation mean vector.
    obs_cov : np.ndarray
        Shape (K, K) overall observation covariance matrix.
    initial_probs : np.ndarray | list[float]
        Prior state probabilities pi_j for j in {1, 2, 3, 4}.
        
    Returns
    -------
    np.ndarray
        Log-emission matrix of shape (4, T).
    """
    T = len(observation_matrix)
    if T == 0:
        return np.empty((4, 0), dtype=np.float64)

    K = observation_matrix.shape[1]
    pi = np.asarray(initial_probs, dtype=np.float64)
    log_pi = np.log(np.maximum(pi, 1e-12))

    # Safe multivariate normal density for P(o_t)
    # Add small regularization jitter to protect against near-singular covariance
    cov_reg = np.asarray(obs_cov, dtype=np.float64).copy()
    if cov_reg.ndim == 2 and cov_reg.shape[0] == K and cov_reg.shape[1] == K:
        cov_reg += 1e-6 * np.eye(K, dtype=np.float64)
        try:
            mvn = scipy.stats.multivariate_normal(mean=obs_mean, cov=cov_reg, allow_singular=True)
            log_p_obs = mvn.logpdf(observation_matrix)
        except Exception:
            log_p_obs = np.zeros(T, dtype=np.float64)
    else:
        log_p_obs = np.zeros(T, dtype=np.float64)

    # In case of 1D scalar return from logpdf on T=1
    log_p_obs = np.atleast_1d(log_p_obs)

    log_emissions = np.zeros((4, T), dtype=np.float64)
    log_posteriors = np.log(np.maximum(logistic_posteriors, 1e-30))

    for j in range(4):
        # ln B(j, t) = ln P(S_t=j | o_t) + ln P(o_t) - ln pi_j
        log_emissions[j, :] = log_posteriors[:, j] + log_p_obs - log_pi[j]

    # Ensure strictly finite output
    log_emissions = np.nan_to_num(log_emissions, nan=-100.0, posinf=0.0, neginf=-1000.0)
    return log_emissions


def viterbi_decode_pcg_extended(
    log_emissions: np.ndarray,
    duration_stats: Dict[HeartSoundState, StateDurationStats],
    initial_probs: Optional[list[float]] = None,
) -> Tuple[np.ndarray, list[StateInterval]]:
    """Decode the most likely cyclic state sequence using extended Viterbi algorithm.
    
    Cyclic Order:
    0 (S1) -> 1 (Systole) -> 2 (S2) -> 3 (Diastole) -> 0 (S1)
    
    Extended Boundary Semantics:
    - Recording can begin partway through a state (partial initial state).
    - Recording can end partway through a state (partial final state).
    
    Parameters
    ----------
    log_emissions : np.ndarray
        Shape (4, T) log emission probabilities.
    duration_stats : Dict[HeartSoundState, StateDurationStats]
        Explicit duration parameters for S1, SYSTOLE, S2, DIASTOLE.
    initial_probs : Optional[list[float]]
        Prior state probabilities (default [0.25, 0.25, 0.25, 0.25]).
        
    Returns
    -------
    Tuple[np.ndarray, list[StateInterval]]
        (state_sequence_50hz, state_intervals)
    """
    n_states, T = log_emissions.shape
    if T == 0:
        return np.array([], dtype=np.int32), []

    if initial_probs is None:
        pi = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    else:
        pi = np.asarray(initial_probs, dtype=np.float64)
    log_pi = np.log(np.maximum(pi, 1e-12))

    # Precompute duration distributions for each state 0..3
    state_enum_map = [
        HeartSoundState.S1,
        HeartSoundState.SYSTOLE,
        HeartSoundState.S2,
        HeartSoundState.DIASTOLE,
    ]

    dur_probs: list[np.ndarray] = []
    dur_log_probs: list[np.ndarray] = []
    dur_survival_logs: list[np.ndarray] = []
    d_mins: list[int] = []
    d_maxs: list[int] = []

    for j in range(4):
        st = state_enum_map[j]
        p_vec, log_p_vec, d_min, d_max = get_duration_probabilities_50hz(duration_stats[st])
        dur_probs.append(p_vec)
        dur_log_probs.append(log_p_vec)
        d_mins.append(d_min)
        d_maxs.append(d_max)

        # Compute survival function P(D >= d) = sum_{k=d}^d_max p(k) for partial states
        surv = np.zeros(len(p_vec), dtype=np.float64)
        for i in range(len(p_vec)):
            surv[i] = np.sum(p_vec[i:])
        surv_log = np.log(np.maximum(surv, 1e-30))
        dur_survival_logs.append(surv_log)

    # Precompute cumulative log emissions: cum_log_b[j, t] = sum_{tau=0}^t log_b[j, tau]
    # cum_log_b[:, -1] = 0 for convenience with t-d
    cum_log_b = np.zeros((4, T + 1), dtype=np.float64)
    for j in range(4):
        cum_log_b[j, 1:] = np.cumsum(log_emissions[j, :])

    # Dynamic programming matrices
    # delta[j, t]: best score of a state sequence ending with state j completed at time t
    NEG_INF = -1e20
    delta = np.full((4, T), NEG_INF, dtype=np.float64)

    # Backpointers: store (prev_state, duration)
    # prev_state == -1 indicates this state was the initial state (started at t=0)
    backpointer_dur = np.zeros((4, T), dtype=np.int32)
    backpointer_prev = np.full((4, T), -1, dtype=np.int32)

    # 1. INITIAL BOUNDARY CONDITIONS (Extended Viterbi: Partial State at t=0)
    # A state j can start at t=0 and complete at t=d-1 with duration d
    for j in range(4):
        d_min = d_mins[j]
        d_max = d_maxs[j]
        surv_logs = dur_survival_logs[j]

        # Candidate duration d observed from t=0 to t=d-1
        # It may be shorter than d_min or up to d_max because part of the state occurred before t=0
        for d in range(1, min(T, d_max) + 1):
            t_end = d - 1
            # Emission sum from 0 to d-1
            emis_sum = cum_log_b[j, d] - cum_log_b[j, 0]

            # In Springer extended Viterbi, initial partial state survival probability:
            # If d within duration bounds, use survival index d - d_min
            if d >= d_min:
                idx = min(len(surv_logs) - 1, d - d_min)
                log_p_dur = surv_logs[idx]
            else:
                # If d < d_min, the full duration D was at least d, which is guaranteed (probability 1.0)
                log_p_dur = 0.0

            score = log_pi[j] + log_p_dur + emis_sum

            if score > delta[j, t_end]:
                delta[j, t_end] = score
                backpointer_dur[j, t_end] = d
                backpointer_prev[j, t_end] = -1

    # 2. MAIN FORWARD RECURSION
    # Strict Cyclic Transition:
    # State j can ONLY be preceded by state j_prev = (j - 1) % 4
    for t in range(T):
        for j in range(4):
            j_prev = (j - 1) % 4
            d_min = d_mins[j]
            d_max = d_maxs[j]
            log_p_durs = dur_log_probs[j]

            # Try candidate full durations d in [d_min, d_max]
            for d_idx, d in enumerate(range(d_min, d_max + 1)):
                t_prev = t - d
                if t_prev < 0:
                    continue

                if delta[j_prev, t_prev] <= NEG_INF / 2:
                    continue

                # Emission sum from t-d+1 to t
                # Note: cum_log_b indices are shifted by +1 (time t is at index t+1)
                emis_sum = cum_log_b[j, t + 1] - cum_log_b[j, t_prev + 1]
                score = delta[j_prev, t_prev] + log_p_durs[d_idx] + emis_sum

                if score > delta[j, t]:
                    delta[j, t] = score
                    backpointer_dur[j, t] = d
                    backpointer_prev[j, t] = j_prev

    # 3. FINAL BOUNDARY CONDITIONS (Extended Viterbi: Partial State at t=T-1)
    # The recording can end partway through state j at time T-1
    best_final_score = NEG_INF
    best_final_state = 0
    best_final_is_partial = False
    best_partial_t_start = 0

    # First check completed states ending exactly at T-1
    for j in range(4):
        if delta[j, T - 1] > best_final_score:
            best_final_score = delta[j, T - 1]
            best_final_state = j
            best_final_is_partial = False

    # Check candidate partial states ending at T-1
    for j in range(4):
        j_prev = (j - 1) % 4
        d_min = d_mins[j]
        d_max = d_maxs[j]
        surv_logs = dur_survival_logs[j]

        # State j starts at t_start and gets truncated at T-1
        # Duration d = T - t_start
        for d in range(1, min(T, d_max) + 1):
            t_start = T - d
            t_prev = t_start - 1

            if t_prev >= 0:
                if delta[j_prev, t_prev] <= NEG_INF / 2:
                    continue
                prev_score = delta[j_prev, t_prev]
            else:
                # Started at t=0 and spans the whole recording
                prev_score = log_pi[j]

            emis_sum = cum_log_b[j, T] - cum_log_b[j, t_start]

            if d >= d_min:
                idx = min(len(surv_logs) - 1, d - d_min)
                log_p_dur = surv_logs[idx]
            else:
                log_p_dur = 0.0

            partial_score = prev_score + log_p_dur + emis_sum

            if partial_score > best_final_score:
                best_final_score = partial_score
                best_final_state = j
                best_final_is_partial = True
                best_partial_t_start = t_start

    # 4. BACKTRACKING
    state_seq = np.zeros(T, dtype=np.int32)
    t_curr = T - 1
    curr_state = best_final_state

    # If the optimal final path was an incomplete/partial state:
    if best_final_is_partial:
        state_seq[best_partial_t_start:T] = curr_state + 1
        t_curr = best_partial_t_start - 1
        curr_state = (curr_state - 1) % 4

    # Standard backtracking through dynamic programming matrix
    while t_curr >= 0:
        d = backpointer_dur[curr_state, t_curr]
        p_state = backpointer_prev[curr_state, t_curr]

        if d <= 0:
            # Fallback guard against zero duration
            d = max(1, d_mins[curr_state])

        t_start = max(0, t_curr - d + 1)
        state_seq[t_start:t_curr + 1] = curr_state + 1  # 1-indexed {1, 2, 3, 4}

        if p_state == -1 or t_start == 0:
            break

        t_curr = t_start - 1
        curr_state = p_state

    # Guarantee all frames in {1, 2, 3, 4}
    zero_mask = state_seq == 0
    if np.any(zero_mask):
        # Fill any unassigned initial frames with the adjacent state
        first_valid = 1
        valid_idx = np.where(~zero_mask)[0]
        if len(valid_idx) > 0:
            first_valid = state_seq[valid_idx[0]]
        state_seq[zero_mask] = first_valid

    # 5. CONVERT TO TEMPORAL INTERVALS
    intervals = extract_state_intervals_from_sequence(state_seq, feature_fs=50.0)
    return state_seq, intervals


def extract_state_intervals_from_sequence(
    state_sequence_50hz: np.ndarray,
    feature_fs: float = 50.0,
) -> list[StateInterval]:
    """Convert discrete 50 Hz state label sequence into temporal interval structures."""
    if len(state_sequence_50hz) == 0:
        return []

    intervals: list[StateInterval] = []
    n = len(state_sequence_50hz)
    dt = 1.0 / float(feature_fs)

    seg_start = 0
    curr_state = int(state_sequence_50hz[0])

    for i in range(1, n):
        if state_sequence_50hz[i] != curr_state:
            seg_end = i - 1
            st_enum = HeartSoundState(curr_state)
            intervals.append(
                StateInterval(
                    state=curr_state,
                    state_name=st_enum.name,
                    start_s=round(seg_start * dt, 4),
                    end_s=round((seg_end + 1) * dt, 4),
                    duration_s=round((seg_end - seg_start + 1) * dt, 4),
                    start_frame_50hz=seg_start,
                    end_frame_50hz=seg_end,
                )
            )
            curr_state = int(state_sequence_50hz[i])
            seg_start = i

    # Append final interval
    seg_end = n - 1
    st_enum = HeartSoundState(curr_state)
    intervals.append(
        StateInterval(
            state=curr_state,
            state_name=st_enum.name,
            start_s=round(seg_start * dt, 4),
            end_s=round((seg_end + 1) * dt, 4),
            duration_s=round((seg_end - seg_start + 1) * dt, 4),
            start_frame_50hz=seg_start,
            end_frame_50hz=seg_end,
        )
    )

    return intervals
