"""Deterministic, auditable NONCLINICAL filter recommendation foundation.

Never changes raw input. Heuristics are deliberately conservative and signal-specific.
AI can later *rank* safe candidates, never synthesize arbitrary unstable filter coefficients.
"""
from dataclasses import asdict, dataclass
import numpy as np
from scipy.signal import welch, iirnotch, sosfiltfilt, butter


@dataclass(frozen=True)
class FilterRecommendation:
    family: str
    reason: str
    parameters: dict
    evidence: dict
    provenance: str = 'deterministic_heuristic_v1'
    warnings: tuple = ()


def recommend_filters(samples, fs: int) -> list[FilterRecommendation]:
    x = np.asarray(samples, dtype=np.float64).reshape(-1)
    if len(x) < fs or fs < 1200 or not np.all(np.isfinite(x)):
        raise ValueError('Expected >=1s of finite waveform sampled at >=1200 Hz')
    out = []
    dc = float(abs(np.mean(x)))
    rms = float(np.sqrt(np.mean(x*x)) + 1e-12)
    if dc / rms > .12:
        out.append(FilterRecommendation('dc_detrend', 'DC level is substantial relative to signal RMS',
             {'method': 'constant'}, {'dc_to_rms_ratio': round(dc / rms, 4)},
             warnings=('Preserve the original raw samples; detrending changes the waveform.',)))
    f, p = welch(x-np.mean(x), fs=fs, nperseg=min(len(x), fs*2))
    for mains in (50, 60):
        center = int(np.argmin(abs(f-mains)))
        side = (f >= mains - 7) & (f <= mains + 7) & (abs(f-mains) >= 2)
        if side.sum() < 3: continue
        contrast = 10 * np.log10((p[center]+1e-20) / (np.median(p[side])+1e-20))
        if contrast > 13:
            out.append(FilterRecommendation('notch_preview', f'Narrow spectral peak near {mains} Hz',
                {'center_hz': mains, 'q': 30}, {'contrast_db': round(float(contrast), 2)},
                warnings=('A real cardiac component may overlap this frequency.',
                          'Do not infer electrical mains as confirmed cause from PSD alone.',
                          'Evaluate S1/S2 timing and spectral distortion before accepting.')))
    return out


def render_filter_preview(samples, fs: int, recommendation: FilterRecommendation):
    """Returns a new array; existing recording is NEVER modified."""
    x = np.asarray(samples, dtype=np.float64)
    if recommendation.family == 'dc_detrend':
        return x - np.mean(x)
    if recommendation.family == 'notch_preview':
        center = float(recommendation.parameters['center_hz'])
        q = float(recommendation.parameters['q'])
        if not (0 < center < fs/2 and 10 <= q <= 60):
            raise ValueError('Unsafe notch parameters')
        from scipy.signal import iirnotch, filtfilt
        b, a = iirnotch(center, q, fs)
        return filtfilt(b, a, x)
    raise ValueError('Unsupported filter recommendation')
