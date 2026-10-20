"""AuscultaForge — Core Digital Signal Processing (DSP) Engine.

Provides causal stateful IIR filters for live streaming and verified offline filters
with rigorous metadata tracking (causal IIR vs. zero-phase non-causal).

Metrological Principles:
1. No filter may retroactively modify recorded raw data.
2. Filtering introduces phase distortion and group delay unless explicitly using zero-phase.
3. Causal streaming filters (sosfilt) MUST declare phase_policy="causal_iir".
4. Offline zero-phase forward-backward filters (sosfiltfilt) MUST declare phase_policy="zero_phase_noncausal".
5. 20–500 Hz is the mandatory project characterization band; 20–600 Hz is the provisional general development preset.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi, sosfiltfilt

from .models import SampleBlock


class StreamingBandpass:
    """Stateful, causal block-by-block Butterworth band-pass filter using Second-Order Sections (SOS).

    Maintains internal filter state (zi) across consecutive SampleBlocks to ensure
    seamless continuity across block boundaries without phase or amplitude step discontinuities.

    Default passband: 20–600 Hz (provisional development preset) or 20–500 Hz (mandatory characterization).
    """

    def __init__(
        self,
        sample_rate_hz: int | float,
        low_hz: float = 20.0,
        high_hz: float = 600.0,
        order: int = 4,
    ) -> None:
        fs = float(sample_rate_hz)
        if fs <= 0:
            raise ValueError(f"Sample rate must be strictly positive, got {sample_rate_hz}")
        nyq = fs / 2.0
        if not (0 < low_hz < high_hz < nyq):
            raise ValueError(
                f"Invalid bandpass cutoffs: require 0 < low_hz ({low_hz}) < high_hz ({high_hz}) < Nyquist ({nyq}) Hz"
            )

        self.fs = int(sample_rate_hz)
        self.low_hz = float(low_hz)
        self.high_hz = float(high_hz)
        self.order = int(order)
        self.phase_policy: str = "causal_iir"
        self.filter_type: str = "butterworth_bandpass"

        self.sos = butter(
            self.order,
            [self.low_hz, self.high_hz],
            btype="bandpass",
            fs=fs,
            output="sos",
        )
        self.zi = sosfilt_zi(self.sos) * 0.0

    def reset(self) -> None:
        """Reset internal filter delay registers to zero."""
        self.zi = sosfilt_zi(self.sos) * 0.0

    def get_metadata(self) -> dict[str, Any]:
        """Return explicit mathematical metadata for the filter configuration."""
        return {
            "filter_type": self.filter_type,
            "phase_policy": self.phase_policy,
            "order": self.order,
            "low_hz": self.low_hz,
            "high_hz": self.high_hz,
            "sample_rate_hz": self.fs,
            "structure": "cascaded_second_order_sections_sos",
            "is_causal": True,
        }

    def process(self, block: SampleBlock) -> SampleBlock:
        """Process a single SampleBlock causally, updating internal state."""
        if block.sample_rate_hz != self.fs:
            raise ValueError(
                f"Block sample rate ({block.sample_rate_hz} Hz) does not match filter sample rate ({self.fs} Hz)"
            )

        samples = np.asarray(block.samples, dtype=np.float64)
        if len(samples) == 0:
            return SampleBlock(
                sequence=block.sequence,
                timestamp_s=block.timestamp_s,
                sample_rate_hz=block.sample_rate_hz,
                samples=np.array([], dtype=np.float32),
                source=f"{block.source}|bandpass",
            )

        y, self.zi = sosfilt(self.sos, samples, zi=self.zi)
        return SampleBlock(
            sequence=block.sequence,
            timestamp_s=block.timestamp_s,
            sample_rate_hz=block.sample_rate_hz,
            samples=np.asarray(y, dtype=np.float32),
            source=f"{block.source}|bandpass",
        )


def offline_bandpass(
    samples: np.ndarray,
    sample_rate_hz: int | float,
    low_hz: float = 20.0,
    high_hz: float = 500.0,
    order: int = 4,
    zero_phase: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply offline Butterworth bandpass filtering to a full audio sequence.

    Parameters
    ----------
    samples : np.ndarray
        1D floating-point audio sequence.
    sample_rate_hz : int | float
        Sampling frequency in Hertz (must be > 0).
    low_hz : float
        Lower cutoff frequency in Hertz (default: 20.0 Hz).
    high_hz : float
        Upper cutoff frequency in Hertz (default: 500.0 Hz mandatory characterization).
    order : int
        Filter order (default: 4).
    zero_phase : bool
        If True, applies forward-backward non-causal zero-phase filtering (sosfiltfilt).
        If False, applies strictly causal forward IIR filtering (sosfilt).

    Returns
    -------
    tuple[np.ndarray, dict[str, Any]]
        (filtered_samples as float32, filter_metadata_dict)
    """
    fs = float(sample_rate_hz)
    if fs <= 0:
        raise ValueError(f"Sample rate must be strictly positive, got {sample_rate_hz}")
    nyq = fs / 2.0
    if not (0 < low_hz < high_hz < nyq):
        raise ValueError(
            f"Invalid bandpass cutoffs: require 0 < low_hz ({low_hz}) < high_hz ({high_hz}) < Nyquist ({nyq}) Hz"
        )

    if not isinstance(samples, np.ndarray):
        samples = np.asarray(samples, dtype=np.float64)

    if samples.ndim != 1:
        samples = samples.flatten()

    if len(samples) == 0:
        meta = {
            "filter_type": "butterworth_bandpass",
            "phase_policy": "zero_phase_noncausal" if zero_phase else "causal_iir",
            "order": order,
            "low_hz": float(low_hz),
            "high_hz": float(high_hz),
            "sample_rate_hz": float(fs),
            "zero_phase": zero_phase,
            "sample_count": 0,
        }
        return np.array([], dtype=np.float32), meta

    if np.any(np.isnan(samples)) or np.any(np.isinf(samples)):
        raise ValueError("Cannot filter signal containing NaN or infinite values.")

    sos = butter(order, [low_hz, high_hz], btype="bandpass", fs=fs, output="sos")

    if zero_phase:
        # Forward-backward non-causal filtering eliminates phase distortion
        min_len = 3 * (2 * order + 1)
        padlen = min(min_len, len(samples) - 1) if len(samples) > 1 else None
        filtered = sosfiltfilt(sos, samples, padlen=padlen)
        phase_policy = "zero_phase_noncausal"
    else:
        # Strictly causal forward IIR filtering introduces physical group delay
        zi = sosfilt_zi(sos) * samples[0] if len(samples) > 0 else sosfilt_zi(sos) * 0.0
        filtered, _ = sosfilt(sos, samples, zi=zi)
        phase_policy = "causal_iir"

    metadata = {
        "filter_type": "butterworth_bandpass",
        "phase_policy": phase_policy,
        "order": order,
        "low_hz": float(low_hz),
        "high_hz": float(high_hz),
        "sample_rate_hz": float(fs),
        "zero_phase": bool(zero_phase),
        "structure": "cascaded_second_order_sections_sos",
        "sample_count": len(filtered),
    }

    return np.asarray(filtered, dtype=np.float32), metadata
