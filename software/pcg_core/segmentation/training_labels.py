"""AuscultaForge — Springer ECG-to-PCG Training Annotation Bridge.

Provides training-only and evaluation-only mapping from ECG reference annotations
(R-peaks and end-T-waves) to 50 Hz 4-state ground-truth cardiac labels:
1: S1
2: SYSTOLE
3: S2
4: DIASTOLE

Provenance / Methodological Basis:
- Springer et al. (2016), Section II-B: Annotation of Training Data
- PhysioNet HSS Reference Pipeline
- Strictly for TRAINING / EVALUATION. Normal inference remains PCG-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Sequence
import numpy as np
import scipy.signal

from .models import HeartSoundState


@dataclass(slots=True)
class SpringerTrainingAnnotations:
    """ECG reference annotations for training Springer LR-HSMM segmentation models.
    
    Attributes
    ----------
    recording_id : str
        Unique identifier for the recording.
    annotation_sample_rate_hz : float
        Sampling frequency in Hz of the annotation sample indices (e.g., 1000.0 Hz).
    r_peak_positions : Sequence[int]
        Sample indices of ECG R-peaks.
    end_t_wave_positions : Sequence[int]
        Sample indices of ECG end-T-waves.
    subject_id : Optional[str]
        Optional subject or patient identifier.
    metadata : dict[str, Any]
        Additional annotation provenance metadata.
    """
    recording_id: str
    annotation_sample_rate_hz: float
    r_peak_positions: Sequence[int] | np.ndarray
    end_t_wave_positions: Sequence[int] | np.ndarray
    subject_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["r_peak_positions"] = [int(p) for p in self.r_peak_positions]
        d["end_t_wave_positions"] = [int(p) for p in self.end_t_wave_positions]
        return d


def label_pcg_states_from_annotations(
    pcg_signal: np.ndarray,
    pcg_sample_rate_hz: float,
    annotations: SpringerTrainingAnnotations,
    feature_sample_rate_hz: float = 50.0,
    expected_s1_duration_s: float = 0.122,
    expected_s2_duration_s: float = 0.094,
    s2_search_window_s: float = 0.100,
) -> np.ndarray:
    """Convert ECG R-peak and end-T-wave annotations into 50 Hz 4-state labels.
    
    Rules (Springer et al. 2016 / Reference Pipeline):
    - S1: Begins at the ECG R-peak and spans expected S1 duration.
    - S2: Searches PCG Hilbert envelope around end-T-wave within +/- s2_search_window_s,
          locates maximum peak, and centers expected S2 duration on this peak.
    - SYSTOLE: Assigned to interval between end of S1 and start of S2.
    - DIASTOLE: Assigned to interval between end of S2 and start of next S1.
    - Boundaries: Pre-first-S1 is marked as DIASTOLE; post-last-event is marked as
      DIASTOLE (if after S2) or SYSTOLE (if after S1).
      
    Parameters
    ----------
    pcg_signal : np.ndarray
        Raw or preprocessed PCG signal.
    pcg_sample_rate_hz : float
        Sampling frequency of pcg_signal in Hz.
    annotations : SpringerTrainingAnnotations
        ECG R-peak and end-T-wave positions.
    feature_sample_rate_hz : float
        Target feature rate (default: 50.0 Hz).
    expected_s1_duration_s : float
        Prior mean S1 duration in seconds (default: 0.122 s).
    expected_s2_duration_s : float
        Prior mean S2 duration in seconds (default: 0.094 s).
    s2_search_window_s : float
        Window (+/- s) around end-T-wave to search on PCG Hilbert envelope.
        
    Returns
    -------
    np.ndarray
        1D array of int32 labels in {1, 2, 3, 4} matching feature_sample_rate_hz length.
    """
    if len(pcg_signal) == 0:
        return np.array([], dtype=np.int32)

    duration_s = float(len(pcg_signal)) / float(pcg_sample_rate_hz)
    total_frames = int(round(duration_s * feature_sample_rate_hz))
    if total_frames <= 0:
        return np.array([], dtype=np.int32)

    # Initialize all frames with DIASTOLE (state 4) by default
    labels = np.full(total_frames, int(HeartSoundState.DIASTOLE), dtype=np.int32)

    fs_ann = float(annotations.annotation_sample_rate_hz)
    r_peaks_s = np.sort(np.asarray(annotations.r_peak_positions, dtype=np.float64) / fs_ann)
    t_ends_s = np.sort(np.asarray(annotations.end_t_wave_positions, dtype=np.float64) / fs_ann)

    if len(r_peaks_s) == 0:
        return labels

    # Compute PCG Hilbert envelope for S2 peak localization
    pcg_clean = np.nan_to_num(pcg_signal, nan=0.0, posinf=0.0, neginf=0.0)
    analytic = scipy.signal.hilbert(pcg_clean)
    hilb_env = np.abs(analytic)

    s1_frames_len = max(1, int(round(expected_s1_duration_s * feature_sample_rate_hz)))
    s2_frames_len = max(1, int(round(expected_s2_duration_s * feature_sample_rate_hz)))

    # Process each cardiac cycle
    for i, t_r in enumerate(r_peaks_s):
        # 1. S1 begins at ECG R-peak
        s1_start_f = int(round(t_r * feature_sample_rate_hz))
        s1_end_f = s1_start_f + s1_frames_len

        # Clamp S1 frames within bounds
        s1_start_clamped = max(0, min(total_frames, s1_start_f))
        s1_end_clamped = max(0, min(total_frames, s1_end_f))
        if s1_start_clamped < s1_end_clamped:
            labels[s1_start_clamped:s1_end_clamped] = int(HeartSoundState.S1)

        # Determine next R-peak time for cycle gating
        next_t_r = r_peaks_s[i + 1] if i + 1 < len(r_peaks_s) else duration_s

        # 2. Find matching end-T-wave between this R-peak and next R-peak
        candidate_t = t_ends_s[(t_ends_s > t_r) & (t_ends_s < next_t_r)]
        if len(candidate_t) > 0:
            t_t = candidate_t[0]

            # Search PCG Hilbert envelope around end-T-wave
            t_search_start = max(0.0, t_t - s2_search_window_s)
            t_search_end = min(duration_s, t_t + s2_search_window_s)

            idx_start = int(round(t_search_start * pcg_sample_rate_hz))
            idx_end = int(round(t_search_end * pcg_sample_rate_hz))

            if idx_start < idx_end and idx_end <= len(hilb_env):
                search_region = hilb_env[idx_start:idx_end]
                best_rel = int(np.argmax(search_region))
                t_s2_peak = (idx_start + best_rel) / pcg_sample_rate_hz
            else:
                t_s2_peak = t_t

            # Center S2 duration on detected peak
            s2_center_f = int(round(t_s2_peak * feature_sample_rate_hz))
            s2_start_f = s2_center_f - (s2_frames_len // 2)
            s2_end_f = s2_start_f + s2_frames_len

            # Ensure S2 starts strictly after S1
            if s2_start_f < s1_end_f:
                s2_start_f = s1_end_f
                s2_end_f = s2_start_f + s2_frames_len

            # 3. SYSTOLE between S1 and S2
            sys_start_clamped = max(0, min(total_frames, s1_end_f))
            sys_end_clamped = max(0, min(total_frames, s2_start_f))
            if sys_start_clamped < sys_end_clamped:
                labels[sys_start_clamped:sys_end_clamped] = int(HeartSoundState.SYSTOLE)

            # Mark S2
            s2_start_clamped = max(0, min(total_frames, s2_start_f))
            s2_end_clamped = max(0, min(total_frames, s2_end_f))
            if s2_start_clamped < s2_end_clamped:
                labels[s2_start_clamped:s2_end_clamped] = int(HeartSoundState.S2)

            # 4. DIASTOLE between S2 and next S1
            next_s1_start_f = int(round(next_t_r * feature_sample_rate_hz)) if i + 1 < len(r_peaks_s) else total_frames
            dia_start_clamped = max(0, min(total_frames, s2_end_f))
            dia_end_clamped = max(0, min(total_frames, next_s1_start_f))
            if dia_start_clamped < dia_end_clamped:
                labels[dia_start_clamped:dia_end_clamped] = int(HeartSoundState.DIASTOLE)

        else:
            # No end-T-wave found in this cycle; mark interval to next R-peak as SYSTOLE/DIASTOLE
            next_s1_start_f = int(round(next_t_r * feature_sample_rate_hz)) if i + 1 < len(r_peaks_s) else total_frames
            sys_start_clamped = max(0, min(total_frames, s1_end_f))
            sys_end_clamped = max(0, min(total_frames, next_s1_start_f))
            if sys_start_clamped < sys_end_clamped:
                labels[sys_start_clamped:sys_end_clamped] = int(HeartSoundState.SYSTOLE)

    return labels
