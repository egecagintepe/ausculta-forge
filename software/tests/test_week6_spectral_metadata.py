"""Software-only Week-6 oracles. Never open a physical serial port."""
import hashlib
import json
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.io import wavfile
from scipy.signal import welch

from pcg_app.display_pipeline import DisplayAggregator
from pcg_app.state import StreamManager
from pcg_core.models import SampleBlock
from pcg_core.recording import create_session_source, verify_session_integrity


@pytest.mark.parametrize('fs', [4000, 48000])
@pytest.mark.parametrize('tones', [(125,), (125, 625)])
def test_spectral_window_timing_and_welch_oracle(fs, tones):
    agg = DisplayAggregator()
    n = 4096
    samples = sum(np.sin(2 * np.pi * tone * np.arange(n) / fs) for tone in tones).astype(np.float32)
    block = SampleBlock(sequence=0, timestamp_s=2.5, sample_rate_hz=fs, samples=samples)
    frame = agg.add_block(block, block, {}, False) or agg.force_flush({}, False)
    spec = frame.spectral_frame
    assert spec['window_start_ts'] == pytest.approx(2.5, abs=1 / fs)
    assert spec['window_end_ts'] == pytest.approx(2.5 + n / fs, abs=1 / fs)
    f, p = welch(samples, fs=fs, nperseg=spec['nperseg'], scaling='density')
    np.testing.assert_allclose(spec['frequencies_hz'], f, atol=0.0051)
    np.testing.assert_allclose(spec['power_db'], 10 * np.log10(np.maximum(p, 1e-12)), atol=0.0051)
    assert spec['frequency_bin_spacing_hz'] == fs / spec['nperseg']
    assert spec['frequencies_hz'][-1] == fs / 2
    for tone in tones:
        assert spec['power_db'][int(np.argmin(abs(f - tone))) ] > -35


def test_history_reset_rate_gap_and_large_block_bound():
    agg = DisplayAggregator()
    def feed(seq, ts, fs, n=256):
        block = SampleBlock(sequence=seq, timestamp_s=ts, sample_rate_hz=fs, samples=np.ones(n, dtype=np.float32))
        agg.add_block(block, block, {}, False)
    feed(0, 0, 48000)
    original = agg.stream_id
    feed(1, 256 / 48000, 48000)
    assert agg.stream_id == original
    feed(2, 3, 48000)
    assert agg.stream_id != original
    previous = agg.stream_id
    feed(3, 3 + 256 / 48000, 4000)
    assert agg.stream_id != previous
    previous = agg.stream_id
    feed(0, 0, 4000, 100000)
    assert agg.stream_id != previous
    assert agg._recent_filt_count <= 4096
    agg.reset()
    assert agg._recent_filt_count == 0
    for seq in range(2000):
        feed(seq, seq * 256 / 4000, 4000)
        assert agg._recent_filt_count <= 4096


@pytest.mark.parametrize('simulated,mode,origin', [(True, 1, 'software_simulated'), (False, 1, 'physical_deterministic_g1'), (False, 0, 'physical_i2s_unqualified')])
def test_recording_origin_wav_json_hash_and_replay(tmp_path, simulated, mode, origin):
    manager = StreamManager(sessions_dir=tmp_path)
    manager.source_type = 'hardware'
    manager.is_streaming = True
    # Capability model only: this is not a real hardware run.
    manager.device_runtime.canonical_engine = SimpleNamespace(is_simulated=simulated, get_summary=lambda: {},
        session=SimpleNamespace(active_start_config=SimpleNamespace(source_mode=mode)))
    sid = manager.start_recording()
    samples = np.linspace(-0.5, 0.5, 512, dtype=np.float32)
    for seq in range(2):
        manager.recorder.record_block(SampleBlock(sequence=seq, timestamp_s=seq * 256 / 48000,
            sample_rate_hz=48000, samples=samples[seq * 256:(seq + 1) * 256]))
    meta = manager.stop_recording()
    assert meta.processing_profile['acquisition_origin'] == origin
    assert (meta.device_info is None) == simulated
    fs, audio = wavfile.read(tmp_path / sid / 'raw.wav')
    assert fs == meta.sample_rate_hz == 48000
    assert audio.ndim == 1 and audio.dtype == np.float32 and len(audio) == meta.total_samples == 512
    np.testing.assert_array_equal(audio, samples)
    assert meta.duration_s == pytest.approx(512 / fs, abs=1e-4)
    assert datetime.fromisoformat(meta.ended_at_utc) >= datetime.fromisoformat(meta.started_at_utc)
    assert meta.first_sequence == 0 and meta.last_sequence == 1
    assert meta.first_timestamp_s == 0 and meta.last_timestamp_s == pytest.approx(256 / fs, abs=1e-4)
    assert hashlib.sha256((tmp_path / sid / 'raw.wav').read_bytes()).hexdigest() == meta.raw_wav_sha256
    assert verify_session_integrity(sid, tmp_path)['is_valid']
    replay = create_session_source(sid, sessions_dir=tmp_path, block_size=256, realtime=False)
    np.testing.assert_array_equal(np.concatenate([b.samples for b in replay.blocks()]), samples)
    manager.source_type = 'session'
    manager.source_session_id = sid
    replay_id = manager.start_recording()
    manager.recorder.record_block(SampleBlock(sequence=0, timestamp_s=0, sample_rate_hz=48000, samples=samples))
    replay_meta = manager.stop_recording()
    assert replay_id != sid
    assert replay_meta.processing_profile['replay_session_id'] == sid
    assert replay_meta.processing_profile['replay_origin']['raw_wav_sha256'] == meta.raw_wav_sha256
    assert replay_meta.processing_profile['replay_origin']['processing_profile']['acquisition_origin'] == origin
    assert json.loads((tmp_path / sid / 'session.json').read_text())['total_samples'] == 512
