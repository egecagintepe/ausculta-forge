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
    floor_frames = max(1, int(round(fs_feat / 50.0)))

    # Frame-domain exact reference calculations
    mean_s1_f = float(round(s1_mean_s * fs_feat))
    std_s1_f = float(round(s1_std_s * fs_feat))

    mean_s2_f = float(round(s2_mean_s * fs_feat))
    std_s2_f = float(round(s2_std_s * fs_feat))

    mean_sys_f = float(round(systolic_interval_s * fs_feat)) - mean_s1_f
    std_sys_f = 0.025 * fs_feat

    mean_dia_f = (float(cycle_duration_s) - float(systolic_interval_s) - s2_mean_s) * fs_feat
    std_dia_f = 0.07 * mean_dia_f + 0.006 * fs_feat

    # Physiological / technical validity guards
    if mean_sys_f < 1.0:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Estimated systolic frames ({mean_sys_f:.1f}) < 1.0 "
            f"(systolic_interval_s={systolic_interval_s:.3f} s, S1 mean={s1_mean_s:.3f} s)."
        )
    if mean_dia_f < 1.0:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Estimated diastolic frames ({mean_dia_f:.1f}) < 1.0 "
            f"(cycle_duration_s={cycle_duration_s:.3f} s, systolic_interval_s={systolic_interval_s:.3f} s)."
        )
    if cycle_duration_s <= systolic_interval_s:
        raise ValueError(
            f"SEGMENTATION_PARAMETERS_INVALID: Cycle duration ({cycle_duration_s:.3f} s) "
            f"must be strictly greater than systolic interval ({systolic_interval_s:.3f} s)."
        )

    # 3-sigma bounds with Fs_feat / 50 floor
    min_s1_f = max(floor_frames, int(round(mean_s1_f - 3.0 * std_s1_f)))
    max_s1_f = int(round(mean_s1_f + 3.0 * std_s1_f))

    min_s2_f = max(floor_frames, int(round(mean_s2_f - 3.0 * std_s2_f)))
    max_s2_f = int(round(mean_s2_f + 3.0 * std_s2_f))

    min_sys_f = max(floor_frames, int(round(mean_sys_f - 3.0 * (std_sys_f + std_s1_f))))
    max_sys_f = int(round(mean_sys_f + 3.0 * (std_sys_f + std_s1_f)))

    min_dia_f = max(floor_frames, int(round(mean_dia_f - 3.0 * std_dia_f)))
    max_dia_f = int(round(mean_dia_f + 3.0 * std_dia_f))

    frame_params = {
        HeartSoundState.S1: (mean_s1_f, std_s1_f, min_s1_f, max_s1_f),
        HeartSoundState.SYSTOLE: (mean_sys_f, std_sys_f, min_sys_f, max_sys_f),
        HeartSoundState.S2: (mean_s2_f, std_s2_f, min_s2_f, max_s2_f),
        HeartSoundState.DIASTOLE: (mean_dia_f, std_dia_f, min_dia_f, max_dia_f),
    }

    stats: Dict[HeartSoundState, StateDurationStats] = {}
    for state, (mu_f, s_f, mn_f, mx_f) in frame_params.items():
        stats[state] = StateDurationStats(
            mean_s=round(mu_f / fs_feat, 4),
            std_s=round(s_f / fs_feat, 4),
            min_s=round(mn_f / fs_feat, 4),
            max_s=round(mx_f / fs_feat, 4),
            mean_frames_50hz=int(round(mu_f)),
            std_frames_50hz=round(s_f, 4),
            min_frames_50hz=int(mn_f),
            max_frames_50hz=int(mx_f),
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
