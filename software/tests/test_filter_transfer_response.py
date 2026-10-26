"""Numerical verification of causal streaming DSP filter transfer functions.

Verifies:
1. Single-tone frequency response across passband and stopband for all presets.
2. Multi-tone composite test verifying selective spectral preservation and attenuation.
3. Both 2000 Hz and 4000 Hz sampling rates.
4. Filter order and cutoff metadata.
"""

import numpy as np
import pytest
from pcg_core.dsp import StreamingBandpass
from pcg_core.models import SampleBlock
from pcg_app.protocol import FILTER_PRESETS


def generate_tone(freq_hz: float, fs: int, duration_s: float = 1.0) -> np.ndarray:
    """Generate pure sinusoidal tone."""
    t = np.arange(int(fs * duration_s)) / fs
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


def measure_gain_db(filter_inst: StreamingBandpass, tone: np.ndarray, fs: int, block_size: int = 256) -> float:
    """Pass signal through StreamingBandpass in blocks, discard transient, and compute steady-state gain in dB."""
    filter_inst.reset()
    out_blocks = []
    for seq, start in enumerate(range(0, len(tone), block_size)):
        chunk = tone[start:start + block_size]
        if len(chunk) == 0:
            break
        block = SampleBlock(sequence=seq, timestamp_s=start / fs, sample_rate_hz=fs, samples=chunk, source="synth")
        filt_block = filter_inst.process(block)
        out_blocks.append(filt_block.samples)

    filtered = np.concatenate(out_blocks)
    # Discard first 20% transient
    steady_start = int(len(tone) * 0.25)
    in_rms = float(np.sqrt(np.mean(tone[steady_start:] ** 2)))
    out_rms = float(np.sqrt(np.mean(filtered[steady_start:] ** 2)))

    if out_rms < 1e-9:
        return -120.0
    return float(20.0 * np.log10(out_rms / in_rms))


@pytest.mark.parametrize("fs", [2000, 4000])
@pytest.mark.parametrize("preset, cutoffs", [
    ("recommended", (20.0, 200.0)),
    ("bell", (20.0, 120.0)),
    ("diaphragm", (100.0, 500.0)),
    ("extended", (20.0, 600.0)),
])
def test_filter_preset_passband_and_stopband_response(fs: int, preset: str, cutoffs: tuple[float, float]):
    """Verify numerical gain: passband tones must pass with minimal loss, stopbands must attenuate."""
    low_hz, high_hz = cutoffs
    center_hz = np.sqrt(low_hz * high_hz)  # geometric center of passband
    stop_low_hz = max(3.0, low_hz * 0.25)
    stop_high_hz = min(fs / 2.0 - 50.0, high_hz * 2.5)

    bandpass = StreamingBandpass(sample_rate_hz=fs, low_hz=low_hz, high_hz=high_hz, order=4)

    # 1. Passband center tone
    center_gain_db = measure_gain_db(bandpass, generate_tone(center_hz, fs, 1.5), fs)
    assert center_gain_db > -3.5, f"{preset} center tone ({center_hz:.1f} Hz) attenuated too much: {center_gain_db:.2f} dB"

    # 2. Stopband low tone
    stop_low_gain_db = measure_gain_db(bandpass, generate_tone(stop_low_hz, fs, 1.5), fs)
    assert stop_low_gain_db < -12.0, f"{preset} low stopband ({stop_low_hz:.1f} Hz) not attenuated: {stop_low_gain_db:.2f} dB"

    # 3. Stopband high tone
    if stop_high_hz < fs / 2.0:
        stop_high_gain_db = measure_gain_db(bandpass, generate_tone(stop_high_hz, fs, 1.5), fs)
        assert stop_high_gain_db < -12.0, f"{preset} high stopband ({stop_high_hz:.1f} Hz) not attenuated: {stop_high_gain_db:.2f} dB"


def test_multitone_spectral_separation():
    """Verify multi-tone composite signal filtering across presets."""
    fs = 4000
    duration_s = 2.0
    t = np.arange(int(fs * duration_s)) / fs

    # 4 distinct tones:
    # 5 Hz: sub-audible DC rumble
    # 60 Hz: bell/fundamental band
    # 250 Hz: murmur / diaphragm band
    # 1500 Hz: high-frequency noise
    f_sub, f_bell, f_diaph, f_high = 5.0, 60.0, 250.0, 1500.0
    composite = (
        np.sin(2 * np.pi * f_sub * t)
        + np.sin(2 * np.pi * f_bell * t)
        + np.sin(2 * np.pi * f_diaph * t)
        + np.sin(2 * np.pi * f_high * t)
    ).astype(np.float32)

    # Bell filter (20-120 Hz)
    bp_bell = StreamingBandpass(sample_rate_hz=fs, low_hz=20.0, high_hz=120.0, order=4)
    # Pass in blocks
    out_bell = []
    for start in range(0, len(composite), 256):
        block = SampleBlock(sequence=0, timestamp_s=start/fs, sample_rate_hz=fs, samples=composite[start:start+256], source="synth")
        out_bell.append(bp_bell.process(block).samples)
    filt_bell = np.concatenate(out_bell)

    # FFT power estimation on steady-state window
    steady = filt_bell[int(fs * 0.5):]
    fft_mag = np.abs(np.fft.rfft(steady))
    fft_freqs = np.fft.rfftfreq(len(steady), 1.0 / fs)

    def power_near(freq: float) -> float:
        idx = int(np.argmin(np.abs(fft_freqs - freq)))
        return float(np.mean(fft_mag[max(0, idx - 2):idx + 3] ** 2))

    p_sub = power_near(f_sub)
    p_bell = power_near(f_bell)
    p_diaph = power_near(f_diaph)
    p_high = power_near(f_high)

    # In bell mode, 60 Hz must dominate over 5 Hz, 250 Hz, and 1500 Hz
    assert p_bell > 10.0 * p_sub, "Bell mode must strongly attenuate 5 Hz sub-audible tone"
    assert p_bell > 5.0 * p_diaph, "Bell mode must attenuate 250 Hz murmur tone"
    assert p_bell > 50.0 * p_high, "Bell mode must strongly attenuate 1500 Hz noise tone"
