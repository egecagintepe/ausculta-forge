"""AuscultaForge — Deterministic Stimulus Preparation for Acoustic Phantom Characterization.

Provides deterministic stimulus generation for research-grade acoustic phantom driving:
1. 100 Hz Pure Sine (Acoustic calibration tone)
2. Cardiac Passband Multitone (Schroeder-phase optimized for low crest factor)
3. Logarithmic Sine Sweep (20–500 Hz mandatory band or broadband)
4. Periodic Impulse / Step Train (Time-of-flight and impulse response)
5. Reference PCG WAV asset preparation with rational polyphase resampling

Metrological Rules:
- All stimuli are strictly floating-point in normalized Full-Scale units ([-1.0, +1.0] FS).
- No uncalibrated physical acoustic units (Pa, dB SPL) are claimed.
- Every stimulus includes SHA-256 integrity hash and exact parameter provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import io
import math
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import scipy.signal
from scipy.io import wavfile


@dataclass(slots=True)
class StimulusRecord:
    """Deterministic stimulus container with mathematical and provenance metadata."""
    stimulus_id: str
    stimulus_type: str
    sample_rate_hz: int
    total_samples: int
    duration_s: float
    amplitude_fs: float
    rms_fs: float
    peak_fs: float
    crest_factor: float
    sha256: str
    parameters: dict[str, Any]
    samples: np.ndarray

    def to_dict(self, include_samples: bool = False) -> dict[str, Any]:
        d = {
            "stimulus_id": self.stimulus_id,
            "stimulus_type": self.stimulus_type,
            "sample_rate_hz": self.sample_rate_hz,
            "total_samples": self.total_samples,
            "duration_s": round(self.duration_s, 4),
            "amplitude_fs": round(self.amplitude_fs, 5),
            "rms_fs": round(self.rms_fs, 5),
            "peak_fs": round(self.peak_fs, 5),
            "crest_factor": round(self.crest_factor, 3),
            "sha256": self.sha256,
            "parameters": self.parameters,
        }
        if include_samples:
            d["samples"] = [round(float(v), 5) for v in self.samples]
        return d

    def to_wav_bytes(self, bit_depth: int = 16) -> bytes:
        """Serialize stimulus samples to standard mono WAV bytes."""
        buf = io.BytesIO()
        clipped = np.clip(self.samples, -1.0, 1.0)
        if bit_depth == 16:
            int16_samples = (clipped * 32767.0).astype(np.int16)
            wavfile.write(buf, self.sample_rate_hz, int16_samples)
        elif bit_depth == 32:
            float32_samples = clipped.astype(np.float32)
            wavfile.write(buf, self.sample_rate_hz, float32_samples)
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}. Only 16 or 32 allowed.")
        return buf.getvalue()


def _compute_sha256(samples: np.ndarray) -> str:
    """Compute deterministic SHA-256 hash of float32 sample buffer."""
    buf = np.ascontiguousarray(samples, dtype=np.float32).tobytes()
    return hashlib.sha256(buf).hexdigest()


def generate_100hz_sine(
    duration_s: float = 5.0,
    sample_rate_hz: int = 48000,
    amplitude_fs: float = 0.8,
    phase_rad: float = 0.0,
) -> StimulusRecord:
    """Generate a single-frequency 100 Hz calibration sinusoid.
    
    Parameters
    ----------
    duration_s : float
        Duration in seconds (must be > 0).
    sample_rate_hz : int
        Sampling frequency in Hertz (default: 48000).
    amplitude_fs : float
        Peak amplitude in Full Scale units (0 < amplitude_fs <= 1.0).
    phase_rad : float
        Initial phase offset in radians.
    """
    if duration_s <= 0:
        raise ValueError(f"duration_s must be positive, got {duration_s}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    if not (0.0 < amplitude_fs <= 1.0):
        raise ValueError(f"amplitude_fs must be in (0.0, 1.0], got {amplitude_fs}")

    n_samples = int(round(duration_s * sample_rate_hz))
    t = np.arange(n_samples, dtype=np.float64) / float(sample_rate_hz)
    samples = (amplitude_fs * np.sin(2.0 * np.pi * 100.0 * t + phase_rad)).astype(np.float32)

    peak_val = float(np.max(np.abs(samples)))
    rms_val = float(np.sqrt(np.mean(samples ** 2)))
    cf = float(peak_val / (rms_val + 1e-12))
    sha = _compute_sha256(samples)

    return StimulusRecord(
        stimulus_id=f"stim_sine100hz_{sample_rate_hz}_{sha[:8]}",
        stimulus_type="sine_100hz",
        sample_rate_hz=sample_rate_hz,
        total_samples=n_samples,
        duration_s=float(n_samples / sample_rate_hz),
        amplitude_fs=amplitude_fs,
        rms_fs=rms_val,
        peak_fs=peak_val,
        crest_factor=cf,
        sha256=sha,
        parameters={
            "frequency_hz": 100.0,
            "phase_rad": phase_rad,
            "target_band_hz": [20.0, 500.0],
        },
        samples=samples,
    )


def generate_multitone(
    frequencies_hz: Sequence[float] = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0),
    duration_s: float = 5.0,
    sample_rate_hz: int = 48000,
    peak_amplitude_fs: float = 0.8,
    use_schroeder_phase: bool = True,
) -> StimulusRecord:
    """Generate an orthogonal harmonic multitone with Schroeder phase optimization.
    
    Schroeder phase formula: theta_k = pi * k * (k - 1) / K
    minimizes peak-to-average power ratio (crest factor), maximizing SNR across
    the acoustic exciter passband without inducing non-linear amplifier clipping.
    """
    if duration_s <= 0 or sample_rate_hz <= 0:
        raise ValueError("duration_s and sample_rate_hz must be positive.")
    if not (0.0 < peak_amplitude_fs <= 1.0):
        raise ValueError("peak_amplitude_fs must be in (0.0, 1.0].")
    if not frequencies_hz or len(frequencies_hz) == 0:
        raise ValueError("frequencies_hz sequence cannot be empty.")

    nyquist = sample_rate_hz / 2.0
    for f in frequencies_hz:
        if f <= 0 or f >= nyquist:
            raise ValueError(f"Frequency {f} Hz is outside valid range (0, Nyquist={nyquist} Hz).")

    n_samples = int(round(duration_s * sample_rate_hz))
    t = np.arange(n_samples, dtype=np.float64) / float(sample_rate_hz)
    k_total = len(frequencies_hz)

    raw_signal = np.zeros(n_samples, dtype=np.float64)
    for k, freq in enumerate(frequencies_hz):
        if use_schroeder_phase and k_total > 1:
            phase = math.pi * k * (k - 1) / float(k_total)
        else:
            phase = 0.0
        raw_signal += np.sin(2.0 * np.pi * freq * t + phase)

    # Normalize to desired peak amplitude
    max_raw = float(np.max(np.abs(raw_signal)))
    if max_raw > 1e-12:
        samples = (raw_signal * (peak_amplitude_fs / max_raw)).astype(np.float32)
    else:
        samples = np.zeros(n_samples, dtype=np.float32)

    peak_val = float(np.max(np.abs(samples)))
    rms_val = float(np.sqrt(np.mean(samples ** 2)))
    cf = float(peak_val / (rms_val + 1e-12))
    sha = _compute_sha256(samples)

    return StimulusRecord(
        stimulus_id=f"stim_multitone_{sample_rate_hz}_{sha[:8]}",
        stimulus_type="multitone",
        sample_rate_hz=sample_rate_hz,
        total_samples=n_samples,
        duration_s=float(n_samples / sample_rate_hz),
        amplitude_fs=peak_amplitude_fs,
        rms_fs=rms_val,
        peak_fs=peak_val,
        crest_factor=cf,
        sha256=sha,
        parameters={
            "frequencies_hz": [float(f) for f in frequencies_hz],
            "use_schroeder_phase": use_schroeder_phase,
            "target_band_hz": [min(frequencies_hz), max(frequencies_hz)],
        },
        samples=samples,
    )


def generate_log_sweep(
    f_start_hz: float = 20.0,
    f_stop_hz: float = 500.0,
    duration_s: float = 5.0,
    sample_rate_hz: int = 48000,
    amplitude_fs: float = 0.8,
    taper_duration_s: float = 0.05,
) -> StimulusRecord:
    """Generate a continuous logarithmic sine sweep (chirp) with Hann end tapers.
    
    Logarithmic sweeping provides equal energy per fractional octave, optimal for
    system identification of acoustic transducers and structural resonators.
    """
    if duration_s <= 0 or sample_rate_hz <= 0:
        raise ValueError("duration_s and sample_rate_hz must be positive.")
    if f_start_hz <= 0 or f_stop_hz <= f_start_hz:
        raise ValueError(f"Invalid sweep frequencies: {f_start_hz} -> {f_stop_hz} Hz.")
    nyquist = sample_rate_hz / 2.0
    if f_stop_hz >= nyquist:
        raise ValueError(f"f_stop_hz ({f_stop_hz} Hz) must be strictly below Nyquist ({nyquist} Hz).")
    if not (0.0 < amplitude_fs <= 1.0):
        raise ValueError("amplitude_fs must be in (0.0, 1.0].")

    n_samples = int(round(duration_s * sample_rate_hz))
    t = np.arange(n_samples, dtype=np.float64) / float(sample_rate_hz)

    # Scipy logarithmic chirp
    sweep = scipy.signal.chirp(t, f0=f_start_hz, t1=duration_s, f1=f_stop_hz, method="logarithmic")
    sweep = sweep * amplitude_fs

    # Apply Hann cosine taper to avoid edge spectral splatter
    taper_samples = int(round(taper_duration_s * sample_rate_hz))
    if taper_samples > 0 and 2 * taper_samples < n_samples:
        ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, taper_samples)))
        sweep[:taper_samples] *= ramp
        sweep[-taper_samples:] *= ramp[::-1]

    samples = sweep.astype(np.float32)
    peak_val = float(np.max(np.abs(samples)))
    rms_val = float(np.sqrt(np.mean(samples ** 2)))
    cf = float(peak_val / (rms_val + 1e-12))
    sha = _compute_sha256(samples)

    return StimulusRecord(
        stimulus_id=f"stim_logsweep_{sample_rate_hz}_{sha[:8]}",
        stimulus_type="log_sweep",
        sample_rate_hz=sample_rate_hz,
        total_samples=n_samples,
        duration_s=float(n_samples / sample_rate_hz),
        amplitude_fs=amplitude_fs,
        rms_fs=rms_val,
        peak_fs=peak_val,
        crest_factor=cf,
        sha256=sha,
        parameters={
            "f_start_hz": f_start_hz,
            "f_stop_hz": f_stop_hz,
            "taper_duration_s": taper_duration_s,
            "target_band_hz": [f_start_hz, f_stop_hz],
        },
        samples=samples,
    )


def generate_impulse_train(
    interval_s: float = 1.0,
    duration_s: float = 5.0,
    sample_rate_hz: int = 48000,
    amplitude_fs: float = 0.8,
    pulse_width_samples: int = 1,
) -> StimulusRecord:
    """Generate a periodic discrete unit impulse train for acoustic time-of-flight estimation."""
    if interval_s <= 0 or duration_s <= 0 or sample_rate_hz <= 0:
        raise ValueError("interval_s, duration_s, and sample_rate_hz must be positive.")
    if not (0.0 < amplitude_fs <= 1.0):
        raise ValueError("amplitude_fs must be in (0.0, 1.0].")

    n_samples = int(round(duration_s * sample_rate_hz))
    samples = np.zeros(n_samples, dtype=np.float32)

    interval_samples = int(round(interval_s * sample_rate_hz))
    if interval_samples <= 0:
        interval_samples = sample_rate_hz

    # Inject first pulse after 0.2s pre-roll for baseline settling
    start_offset = int(round(0.2 * sample_rate_hz))
    for idx in range(start_offset, n_samples, interval_samples):
        end_idx = min(n_samples, idx + pulse_width_samples)
        samples[idx:end_idx] = amplitude_fs

    peak_val = float(np.max(np.abs(samples)))
    rms_val = float(np.sqrt(np.mean(samples ** 2)))
    cf = float(peak_val / (rms_val + 1e-12))
    sha = _compute_sha256(samples)

    return StimulusRecord(
        stimulus_id=f"stim_impulsetrain_{sample_rate_hz}_{sha[:8]}",
        stimulus_type="impulse_train",
        sample_rate_hz=sample_rate_hz,
        total_samples=n_samples,
        duration_s=float(n_samples / sample_rate_hz),
        amplitude_fs=amplitude_fs,
        rms_fs=rms_val,
        peak_fs=peak_val,
        crest_factor=cf,
        sha256=sha,
        parameters={
            "interval_s": interval_s,
            "pulse_width_samples": pulse_width_samples,
            "initial_offset_s": 0.2,
            "target_band_hz": [20.0, 500.0],
        },
        samples=samples,
    )


def prepare_reference_wav_stimulus(
    wav_bytes: bytes,
    target_sample_rate_hz: Optional[int] = None,
    normalize_peak_fs: Optional[float] = 0.8,
    filename: str = "reference.wav",
) -> StimulusRecord:
    """Prepare a clinical or synthetic reference WAV file as a stimulus record."""
    if not wav_bytes or len(wav_bytes) < 44:
        raise ValueError("Invalid WAV bytes: file too short.")

    buf = io.BytesIO(wav_bytes)
    fs, data = wavfile.read(buf)

    if fs <= 0:
        raise ValueError(f"Invalid WAV sample rate: {fs} Hz.")

    # Convert to mono float32
    if data.ndim > 1:
        data = data.mean(axis=1)

    if np.issubdtype(data.dtype, np.integer):
        max_int = float(np.iinfo(data.dtype).max)
        samples = (data.astype(np.float32) / max_int)
    else:
        samples = data.astype(np.float32)

    if len(samples) < 16:
        raise ValueError("WAV file contains fewer than 16 samples.")

    # Rational polyphase resampling if target_sample_rate_hz differs
    orig_fs = int(fs)
    effective_fs = orig_fs
    resampled = False
    if target_sample_rate_hz is not None and target_sample_rate_hz != orig_fs:
        if target_sample_rate_hz <= 0:
            raise ValueError("target_sample_rate_hz must be positive.")
        gcd = math.gcd(orig_fs, target_sample_rate_hz)
        up = target_sample_rate_hz // gcd
        down = orig_fs // gcd
        samples = scipy.signal.resample_poly(samples, up, down).astype(np.float32)
        effective_fs = target_sample_rate_hz
        resampled = True

    # Peak normalization if requested
    if normalize_peak_fs is not None and normalize_peak_fs > 0.0:
        cur_pk = float(np.max(np.abs(samples)))
        if cur_pk > 1e-12:
            samples = samples * (float(normalize_peak_fs) / cur_pk)

    peak_val = float(np.max(np.abs(samples)))
    rms_val = float(np.sqrt(np.mean(samples ** 2)))
    cf = float(peak_val / (rms_val + 1e-12))
    sha = _compute_sha256(samples)

    return StimulusRecord(
        stimulus_id=f"stim_refwav_{effective_fs}_{sha[:8]}",
        stimulus_type="reference_pcg_wav",
        sample_rate_hz=effective_fs,
        total_samples=len(samples),
        duration_s=float(len(samples) / effective_fs),
        amplitude_fs=peak_val,
        rms_fs=rms_val,
        peak_fs=peak_val,
        crest_factor=cf,
        sha256=sha,
        parameters={
            "source_filename": filename,
            "original_sample_rate_hz": orig_fs,
            "resampled": resampled,
            "target_band_hz": [20.0, 500.0],
        },
        samples=samples,
    )
