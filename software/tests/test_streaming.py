import numpy as np
from pathlib import Path
from scipy.io import wavfile
import pytest

from pcg_core.models import SampleBlock
from pcg_core.buffers import RollingBuffer
from pcg_core.sources import RealtimeWavSource
from pcg_core.streaming import (
    StreamQualityMonitor,
    LiveStreamingPipeline,
    compute_spectral_frame,
    compute_rolling_spectrogram,
)


def test_realtime_wav_source_fast(tmp_path: Path):
    """Verify RealtimeWavSource emits sequential SampleBlocks with valid timestamps in fast mode."""
    fs = 1000
    n_samples = 512
    sig = (0.5 * np.sin(2 * np.pi * 50 * np.arange(n_samples) / fs) * 32767).astype(np.int16)
    wav_path = tmp_path / "fast_source_test.wav"
    wavfile.write(str(wav_path), fs, sig)

    source = RealtimeWavSource(wav_path, block_size=128, realtime=False)
    blocks = list(source.blocks())

    assert len(blocks) == 4
    for i, b in enumerate(blocks):
        assert b.sequence == i
        assert b.sample_rate_hz == fs
        assert len(b.samples) == 128
        assert b.timestamp_s == pytest.approx(i * 128 / fs)


def test_realtime_wav_source_short_final_block(tmp_path: Path):
    """Verify RealtimeWavSource correctly handles a final block shorter than block_size."""
    fs = 1000
    n_samples = 300  # 128 + 128 + 44
    sig = (0.5 * np.sin(2 * np.pi * 50 * np.arange(n_samples) / fs) * 32767).astype(np.int16)
    wav_path = tmp_path / "short_final_block.wav"
    wavfile.write(str(wav_path), fs, sig)

    source = RealtimeWavSource(wav_path, block_size=128, realtime=False)
    blocks = list(source.blocks())

    assert len(blocks) == 3
    assert len(blocks[0].samples) == 128
    assert blocks[0].timestamp_s == pytest.approx(0.0)

    assert len(blocks[1].samples) == 128
    assert blocks[1].timestamp_s == pytest.approx(128 / fs)

    # Final partial block
    assert len(blocks[2].samples) == 44
    assert blocks[2].timestamp_s == pytest.approx(256 / fs)

    total_samples = sum(len(b.samples) for b in blocks)
    assert total_samples == 300


def test_rolling_buffer_capacity_and_truncation():
    """Verify RollingBuffer strictly bounds duration and maintains chronological FIFO ordering."""
    buf = RollingBuffer(capacity_seconds=1.0, sample_rate_hz=100)
    assert buf.capacity_samples == 100
    assert buf.count == 0
    assert not buf.is_full

    # Append 60 samples
    chunk1 = np.ones(60, dtype=np.float32)
    buf.append(chunk1)
    assert buf.count == 60
    assert buf.duration_s == pytest.approx(0.6)
    assert np.all(buf.get_samples() == 1.0)

    # Append another 60 samples (total 120, capacity 100)
    chunk2 = 2.0 * np.ones(60, dtype=np.float32)
    buf.append(chunk2)
    assert buf.count == 100
    assert buf.is_full
    assert buf.duration_s == pytest.approx(1.0)

    samples = buf.get_samples()
    # First 40 should be ones, last 60 should be twos
    assert len(samples) == 100
    assert np.all(samples[:40] == 1.0)
    assert np.all(samples[40:] == 2.0)

    # Append chunk larger than buffer capacity
    chunk3 = 3.0 * np.ones(150, dtype=np.float32)
    buf.append(chunk3)
    assert buf.count == 100
    assert np.all(buf.get_samples() == 3.0)


def test_rolling_buffer_sample_rate_mismatch():
    """Verify RollingBuffer raises ValueError on sample rate mismatch unless adaptation enabled."""
    buf = RollingBuffer(capacity_seconds=1.0, sample_rate_hz=1000)
    b_bad = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(50))
    with pytest.raises(ValueError, match="Sample rate mismatch"):
        buf.append(b_bad, adapt_sample_rate=False)

    # With adapt_sample_rate=True, it re-initializes for the new rate
    buf.append(b_bad, adapt_sample_rate=True)
    assert buf.sample_rate_hz == 2000
    assert buf.capacity_samples == 2000
    assert buf.count == 50


def test_stream_quality_monitor_gap_and_regression():
    """Verify StreamQualityMonitor flags sequence gaps, regressions, and sample-rate changes."""
    monitor = StreamQualityMonitor()

    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(256))
    issues0 = monitor.inspect_block(b0)
    assert len(issues0) == 0
    assert monitor.report.is_healthy

    # Block with dropped sequence: 0 -> 3 (dropped 2 blocks: 1 and 2)
    b3 = SampleBlock(sequence=3, timestamp_s=0.3, sample_rate_hz=2000, samples=np.zeros(256))
    issues3 = monitor.inspect_block(b3)
    assert len(issues3) == 1
    assert "Dropped 2 block(s)" in issues3[0]
    assert monitor.report.dropped_blocks == 2
    assert monitor.report.sequence_discontinuities == 1
    assert not monitor.report.is_healthy

    # Block with timestamp regression: 0.3s -> 0.1s
    b4_regress = SampleBlock(sequence=4, timestamp_s=0.1, sample_rate_hz=2000, samples=np.zeros(256))
    issues_regress = monitor.inspect_block(b4_regress)
    assert any("Timestamp regression" in s for s in issues_regress)
    assert monitor.report.timestamp_regressions == 1

    # Block with sample rate change: 2000 -> 4000
    b5_rate = SampleBlock(sequence=5, timestamp_s=0.5, sample_rate_hz=4000, samples=np.zeros(256))
    issues_rate = monitor.inspect_block(b5_rate)
    assert any("Sample rate mismatch" in s for s in issues_rate)
    assert monitor.report.sample_rate_changes == 1


def test_stream_quality_monitor_repeated_and_out_of_order():
    """Verify StreamQualityMonitor distinguishes repeated blocks and out-of-order arrivals."""
    monitor = StreamQualityMonitor()

    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(128))
    b1 = SampleBlock(sequence=1, timestamp_s=0.1, sample_rate_hz=2000, samples=np.zeros(128))
    monitor.inspect_block(b0)
    monitor.inspect_block(b1)

    # Repeat sequence 1
    b1_repeat = SampleBlock(sequence=1, timestamp_s=0.1, sample_rate_hz=2000, samples=np.zeros(128))
    issues_rep = monitor.inspect_block(b1_repeat)
    assert any("Repeated sequence" in s for s in issues_rep)
    assert monitor.report.repeated_sequences == 1

    # Out-of-order sequence (e.g. sequence jumps back to 0)
    b0_late = SampleBlock(sequence=0, timestamp_s=0.2, sample_rate_hz=2000, samples=np.zeros(128))
    issues_late = monitor.inspect_block(b0_late)
    assert any("Out-of-order sequence" in s for s in issues_late)
    assert not monitor.report.is_healthy


def test_spectral_frame_small_buffer_safety():
    """Verify spectral analysis handles small or empty buffers without exceptions."""
    # Under 16 samples
    empty_frame = compute_spectral_frame(np.zeros(8, dtype=np.float32), fs=2000)
    assert empty_frame.peak_frequency_hz == 0.0
    assert empty_frame.dominant_band == "unknown"
    assert len(empty_frame.frequencies_hz) == 0

    # Under 32 samples for spectrogram
    empty_spec = compute_rolling_spectrogram(np.zeros(16, dtype=np.float32), fs=2000)
    assert empty_spec["shape"] == [0, 0]


def test_live_streaming_pipeline(tmp_path: Path):
    """Verify LiveStreamingPipeline processes blocks, calculates metrics and spectral frames."""
    fs = 2000
    duration_s = 0.5
    n_samples = int(fs * duration_s)
    t = np.arange(n_samples) / fs
    sig = (0.4 * np.sin(2 * np.pi * 60 * t) * 32767).astype(np.int16)

    wav_path = tmp_path / "live_pipeline_test.wav"
    wavfile.write(str(wav_path), fs, sig)

    source = RealtimeWavSource(wav_path, block_size=128, realtime=False)
    pipeline = LiveStreamingPipeline(
        buffer_duration_s=2.0,
        filter_low_hz=20.0,
        filter_high_hz=300.0,
        filter_order=4,
    )

    frames = [pipeline.process_block(b) for b in source.blocks()]
    assert len(frames) == 8  # 1000 / 128 = 7 full + 1 partial = 8 blocks

    last_frame = frames[-1]
    assert last_frame.metrics.rms > 0.0
    assert last_frame.metrics.peak_abs > 0.0
    assert last_frame.metrics.crest_factor > 0.0
    assert last_frame.metrics.sample_count == n_samples

    # Check spectral output
    assert last_frame.spectral_frame is not None
    assert abs(last_frame.spectral_frame.peak_frequency_hz - 60.0) <= 15.0
    assert last_frame.spectral_frame.dominant_band == "fundamental_pcg"

    # Check rolling spectrogram computation
    spec_dict = compute_rolling_spectrogram(pipeline.buffer.get_samples(), fs=fs)
    assert spec_dict["shape"][0] > 0
    assert spec_dict["shape"][1] > 0


def test_live_streaming_pipeline_sample_rate_adaptation():
    """Verify LiveStreamingPipeline adapts filter and buffer when sample rate changes."""
    pipeline = LiveStreamingPipeline(buffer_duration_s=1.0)

    # Initial 2000 Hz blocks
    b0 = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=2000, samples=np.zeros(200))
    f0 = pipeline.process_block(b0)
    assert pipeline._fs == 2000
    assert pipeline.buffer.sample_rate_hz == 2000
    assert pipeline.buffer.count == 200

    # Stream switches to 4000 Hz
    b1 = SampleBlock(sequence=1, timestamp_s=0.1, sample_rate_hz=4000, samples=np.zeros(400))
    f1 = pipeline.process_block(b1)
    assert pipeline._fs == 4000
    assert pipeline.buffer.sample_rate_hz == 4000
    assert pipeline.buffer.count == 400
    assert pipeline.quality_monitor.report.sample_rate_changes == 1
