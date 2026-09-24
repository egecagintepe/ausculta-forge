import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import pytest

from pcg_core.analysis import analyze_source, analyze_wav, PCGAnalysisResult
from pcg_core.sources import MockPCGSource


def test_analyze_mock_source():
    """Verify analysis pipeline runs on MockPCGSource without filesystem dependencies."""
    source = MockPCGSource(sample_rate_hz=4000, duration_s=1.0, block_size=256)
    result = analyze_source(source, filter_low_hz=20.0, filter_high_hz=600.0, filter_order=4)

    assert isinstance(result, PCGAnalysisResult)
    assert result.sample_rate_hz == 4000
    assert result.total_samples == 4000
    assert result.duration_s == pytest.approx(1.0, rel=1e-2)

    # Metrics verification
    assert result.raw_metrics.rms > 0.0
    assert result.filtered_metrics.rms > 0.0
    assert result.raw_metrics.peak_abs > 0.0
    assert result.filtered_metrics.crest_factor > 0.0

    # Spectrogram verification
    spec = result.spectrogram
    assert spec.shape[0] > 0
    assert spec.shape[1] > 0
    assert spec.f_max_hz == pytest.approx(2000.0, rel=1e-2)
    assert "fundamental_pcg_20_150hz" in spec.band_energy_ratios

    # JSON serialization
    serialized = result.to_json()
    parsed = json.loads(serialized)
    assert parsed["sample_rate_hz"] == 4000
    assert parsed["filter_config"]["is_provisional"] is True


def test_analyze_wav_synthetic(tmp_path: Path):
    """Verify analyze_wav using a generated synthetic 2000 Hz PCG-like sine signal."""
    fs = 2000
    duration_s = 0.5
    n_samples = int(fs * duration_s)
    t = np.arange(n_samples) / fs

    # 50 Hz sine wave inside cardiac fundamental band (20-150 Hz)
    sig = 0.5 * np.sin(2 * np.pi * 50.0 * t).astype(np.float32)
    wav_path = tmp_path / "synthetic_test.wav"

    # Save as 16-bit PCM WAV
    int16_sig = (sig * 32767).astype(np.int16)
    wavfile.write(str(wav_path), fs, int16_sig)

    result = analyze_wav(wav_path, block_size=128)

    assert result.sample_rate_hz == 2000
    assert result.total_samples == n_samples
    assert result.duration_s == pytest.approx(duration_s, rel=1e-2)

    # Dominant peak frequency should detect the 50 Hz tone
    assert abs(result.spectrogram.peak_frequency_hz - 50.0) <= 16.0
    assert result.spectrogram.band_energy_ratios["fundamental_pcg_20_150hz"] > 0.5


def test_analyze_wav_adjusts_high_hz_for_low_sample_rate(tmp_path: Path):
    """Verify that sample rate with low Nyquist adapts high_hz safely below Nyquist."""
    fs = 800  # Nyquist is 400 Hz, lower than provisional default 600 Hz
    t = np.arange(400) / fs
    sig = (0.3 * np.sin(2 * np.pi * 40 * t) * 32767).astype(np.int16)
    wav_path = tmp_path / "low_fs.wav"
    wavfile.write(str(wav_path), fs, sig)

    # Calling with default high_hz=600 Hz should adapt to < 400 Hz without crashing
    result = analyze_wav(wav_path, filter_high_hz=600.0)
    assert result.sample_rate_hz == 800
    assert result.filter_config.high_hz < 400.0


def test_analyze_wav_missing_file():
    """Verify FileNotFoundError is raised on missing file."""
    with pytest.raises(FileNotFoundError):
        analyze_wav("non_existent_file_path.wav")
