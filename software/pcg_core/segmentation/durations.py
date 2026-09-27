"""AuscultaForge — Springer/Schmidt State Duration Modeling.

Computes explicit state duration distributions at 50 Hz feature rate for:
1: S1
2: SYSTOLE
3: S2
4: DIASTOLE

Mathematical Basis:
- Springer et al. (2016), Section III-B
- Schmidt et al. (2010), Duration-dependent HSMM

Guarantees:
- Enforces physiological validity guards
- Protects against negative or zero state durations
- Provides normalized duration probabilities and log-probabilities
"""

from __future__ import annotations

import math
from typing import Dict, Tuple, Any
import numpy as np

from .models import StateDurationStats, HeartSoundState


# PhysioNet / Springer Reference Fixed Duration Parameters (in seconds)
SPRINGER_S1_MEAN_S: float = 0.122
SPRINGER_S1_STD_S: float = 0.022

SPRINGER_S2_MEAN_S: float = 0.094
SPRINGER_S2_STD_S: float = 0.022


def compute_springer_duration_distributions(
    cycle_duration_s: float,
    systolic_interval_s: float,
    feature_sample_rate_hz: float = 50.0,
    s1_mean_s: float = SPRINGER_S1_MEAN_S,
    s1_std_s: float = SPRINGER_S1_STD_S,
    s2_mean_s: float = SPRINGER_S2_MEAN_S,
    s2_std_s: float = SPRINGER_S2_STD_S,
) -> Dict[HeartSoundState, StateDurationStats]:
    """Compute Gaussian duration distribution parameters for all 4 cardiac states.
    
    Parameters
    ----------
    cycle_duration_s : float
        Estimated cardiac cycle duration in seconds (T_cycle = 60 / BPM).
    systolic_interval_s : float
        Estimated systolic interval in seconds (S1 onset to S2 onset).
    feature_sample_rate_hz : float
        Feature observation sampling rate (default: 50.0 Hz -> 20 ms per frame).
    s1_mean_s, s1_std_s : float
        S1 duration mean and standard deviation in seconds.
    s2_mean_s, s2_std_s : float
        S2 duration mean and standard deviation in seconds.
        
    Returns
    -------
    Dict[HeartSoundState, StateDurationStats]
        Duration distribution parameters per state.
        
    Raises
    ------
    ValueError
        If parameters yield physically or mathematically invalid state durations.
    """
    fs_feat = float(feature_sample_rate_hz)

    # 1. State 1: S1
    mu_s1 = float(s1_mean_s)
    std_s1 = float(s1_std_s)

    # 2. State 3: S2
    mu_s2 = float(s2_mean_s)
    std_s2 = float(s2_std_s)

    # 3. State 2: Systole (interval between S1 and S2)
    mu_sys = float(systolic_interval_s) - mu_s1
    std_sys = 0.025  # Reference standard deviation ~25 ms

    # 4. State 4: Diastole (interval between S2 and next S1)
    mu_dia = float(cycle_duration_s) - float(systolic_interval_s) - mu_s2
    std_dia = max(0.020, 0.035 * (mu_dia / 0.40))  # Scales mildly with diastolic length

    # Physiological validity checks
    min_frame_s = 1.0 / fs_feat  # 0.02 s = 20 ms
    if mu_sys < min_frame_s:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Estimated systolic duration ({mu_sys:.3f} s) "
            f"is below minimum feature frame duration ({min_frame_s:.3f} s)."
        )
    if mu_dia < min_frame_s:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Estimated diastolic duration ({mu_dia:.3f} s) "
            f"is below minimum feature frame duration ({min_frame_s:.3f} s)."
        )
    if cycle_duration_s <= systolic_interval_s:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Cycle duration ({cycle_duration_s:.3f} s) "
            f"must be strictly greater than systolic interval ({systolic_interval_s:.3f} s)."
        )

    means = {
        HeartSoundState.S1: mu_s1,
        HeartSoundState.SYSTOLE: mu_sys,
        HeartSoundState.S2: mu_s2,
        HeartSoundState.DIASTOLE: mu_dia,
    }
    stds = {
        HeartSoundState.S1: std_s1,
        HeartSoundState.SYSTOLE: std_sys,
        HeartSoundState.S2: std_s2,
        HeartSoundState.DIASTOLE: std_dia,
    }

    stats: Dict[HeartSoundState, StateDurationStats] = {}

    for state, mu in means.items():
        std = stds[state]

        # Convert to frames at 50 Hz
        mean_frames = max(1, int(round(mu * fs_feat)))
        std_frames = max(0.5, std * fs_feat)

        # 3-sigma bounds truncated to at least 1 frame
        min_frames = max(1, int(round(mean_frames - 3.0 * std_frames)))
        max_frames = max(min_frames + 1, int(round(mean_frames + 3.0 * std_frames)))

        min_s = float(min_frames) / fs_feat
        max_s = float(max_frames) / fs_feat

        stats[state] = StateDurationStats(
            mean_s=round(mu, 4),
            std_s=round(std, 4),
            min_s=round(min_s, 4),
            max_s=round(max_s, 4),
            mean_frames_50hz=mean_frames,
            std_frames_50hz=round(std_frames, 3),
            min_frames_50hz=min_frames,
            max_frames_50hz=max_frames,
        )

    return stats


def get_duration_probabilities_50hz(
    stats: StateDurationStats,
) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """Compute discrete probability vector and log-probabilities for state durations d in [d_min, d_max].
    
    Returns
    -------
    Tuple[np.ndarray, np.ndarray, int, int]
        (probabilities, log_probabilities, min_frames, max_frames)
    """
    d_min = stats.min_frames_50hz
    d_max = stats.max_frames_50hz
    durations = np.arange(d_min, d_max + 1, dtype=np.float64)

    mu = float(stats.mean_frames_50hz)
    std = float(stats.std_frames_50hz)

    # Gaussian PDF evaluation
    var = std ** 2
    probs = np.exp(-0.5 * ((durations - mu) ** 2) / var)
    total_p = np.sum(probs)
    if total_p > 0:
        probs = probs / total_p
    else:
        probs = np.ones_like(durations) / len(durations)

    # Safe log-probabilities
    log_probs = np.log(np.maximum(probs, 1e-30))

    return probs, log_probs, d_min, d_max
