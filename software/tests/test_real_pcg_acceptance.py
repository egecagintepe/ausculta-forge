"""Optional real-data acceptance: provide a local manifest; never commit the audio."""
import asyncio
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from pcg_app.app import create_app
from pcg_app.protocol import FILTER_PRESETS
from pcg_app.state import StreamManager
from pcg_core.recording import create_session_source, verify_session_integrity
from pcg_core.sources import WavSource


@pytest.mark.parametrize('fs', [2000, 4000])
def test_wav_selection_rate_source_reset_and_recording_origin(tmp_path, fs):
    path = tmp_path / 'input.wav'
    wavfile.write(path, fs, np.arange(512, dtype=np.int16))
    manager = StreamManager(sessions_dir=tmp_path / 'sessions')
    state = manager.select_source('realtime_wav', path=str(path))
    assert state['sample_rate_hz'] == fs
    previous = manager.display_aggregator.stream_id
    sid = manager.start_recording()
    for block in manager._create_source_generator():
        asyncio.run(manager._dispatch_sample_block(block))
    meta = manager.stop_recording()
    assert meta.processing_profile['source_wav_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    state = manager.select_source('session', session_id=sid)
    assert state['sample_rate_hz'] == fs
    assert manager.display_aggregator.stream_id != previous
    for block in manager._create_source_generator():
        asyncio.run(manager._dispatch_sample_block(block))
    assert manager.pipeline.quality_monitor.report.dropped_blocks == 0


manifest_path = os.environ.get('AUSCULTA_PCG_MANIFEST')
records = json.loads(Path(manifest_path).read_text())['records'] if manifest_path else [None]


@pytest.mark.parametrize('record', records, ids=lambda r: r['alias'] if r else 'local-data-not-provided')
def test_real_recording_display_filters_and_replay(record, tmp_path):
    if record is None:
        pytest.skip('Set AUSCULTA_PCG_MANIFEST to a local licensed collection; no medical fixtures in Git')
    output = Path(os.environ['AUSCULTA_PCG_EVIDENCE']) / record['alias']
    output.mkdir(parents=True, exist_ok=False)
    source = Path(record['files'][0]['path']).resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == record['files'][0]['sha256']
    fs, pcm = wavfile.read(source)
    expected = pcm.astype(np.float32) / 32768
    app = create_app(sessions_dir=output / 'sessions', assets_dir=output / 'assets', analysis_dir=output / 'analysis')
    manager = app.state.stream_manager
    # No lifespan/background pacing: drive one complete file through production dispatch deterministically.
    client = TestClient(app)
    selected = client.post('/api/stream/source', json={'source_type': 'realtime_wav', 'path': str(source)})
    assert selected.status_code == 200 and selected.json()['sample_rate_hz'] == fs
    started = client.post('/api/recording/start', json={})
    assert started.status_code == 200
    frames = []
    original_publish = manager.publish_display_frame
    def capture(frame):
        original_publish(frame)
        frames.append(frame.to_dict())
    manager.publish_display_frame = capture
    async def drive():
        for block in manager._create_source_generator():
            await manager._dispatch_sample_block(block)
    asyncio.run(drive())
    stopped = client.post('/api/recording/stop')
    assert stopped.status_code == 200
    sid = manager.recorder.session_id
    session = output / 'sessions' / sid
    metadata = json.loads((session / 'session.json').read_text())
    out_fs, audio = wavfile.read(session / 'raw.wav')
    assert out_fs == fs == metadata['sample_rate_hz']
    assert audio.ndim == 1 and audio.dtype == np.float32
    assert len(audio) == len(pcm) == metadata['total_samples']
    np.testing.assert_array_equal(audio, expected)
    assert metadata['duration_s'] == pytest.approx(len(pcm) / fs, abs=1e-4)
    assert datetime.fromisoformat(metadata['ended_at_utc']) >= datetime.fromisoformat(metadata['started_at_utc'])
    assert metadata['device_info'] is None and metadata['acquisition_mode'] == 'realtime_wav'
    assert metadata['processing_profile']['source_wav_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert metadata['processing_profile']['acquisition_origin'] == 'realtime_wav'
    assert metadata['first_sequence'] == 0
    assert metadata['last_sequence'] == (len(pcm) - 1) // manager.block_size
    assert metadata['first_timestamp_s'] == 0
    assert metadata['last_timestamp_s'] == pytest.approx(((len(pcm) - 1) // manager.block_size) * manager.block_size / fs, abs=1e-4)
    assert all(metadata['stream_quality'][key] == 0 for key in
        ('dropped_blocks', 'repeated_sequences', 'sequence_discontinuities', 'timestamp_regressions', 'sample_rate_changes'))
    assert verify_session_integrity(sid, output / 'sessions')['is_valid']
    assert metadata['raw_wav_sha256'] == hashlib.sha256((session / 'raw.wav').read_bytes()).hexdigest()
    assert metadata['raw_wav_sha256'] != record['files'][0]['sha256'], 'Source PCM16 hash and float32 session hash are distinct'
    replay = create_session_source(sid, sessions_dir=output / 'sessions', realtime=False)
    np.testing.assert_array_equal(np.concatenate([b.samples for b in replay.blocks()]), expected)
    spectra = [f['spectral_frame'] for f in frames if 'spectral_frame' in f]
    assert spectra
    for spec in spectra:
        assert spec['sample_rate_hz'] == fs
        assert spec['frequencies_hz'][-1] == fs / 2
        assert spec['frequency_bin_spacing_hz'] == fs / spec['nperseg']
        assert -1 / fs <= spec['window_start_ts'] < spec['window_end_ts'] <= len(pcm) / fs + 1e-8
        assert spec['acquisition_origin'] == 'realtime_wav'
    filters = {}
    for preset, band in FILTER_PRESETS.items():
        manager.set_filter(preset=preset)
        filtered = np.concatenate([manager.pipeline.process_block(b).filtered_block.samples for b in WavSource(source).blocks()])
        assert len(filtered) == len(pcm) and np.isfinite(filtered).all()
        filters[preset] = {'band_hz': band, 'rms': float(np.sqrt(np.mean(filtered ** 2)))}
    selected = client.post('/api/stream/source', json={'source_type': 'session', 'session_id': sid})
    assert selected.status_code == 200 and selected.json()['sample_rate_hz'] == fs
    assert client.post('/api/stream/stop').status_code == 200
    copy = output / 'sessions' / 'tampered-copy'
    shutil.copytree(session, copy)
    with (copy / 'raw.wav').open('ab') as handle:
        handle.write(b'tamper')
    assert not verify_session_integrity('tampered-copy', output / 'sessions')['is_valid']
    result = {'alias': record['alias'], 'filename': record['filename'], 'sample_rate_hz': int(fs),
        'samples': len(pcm), 'duration_s': len(pcm) / fs, 'source_sha256': record['files'][0]['sha256'],
        'session_wav_sha256': metadata['raw_wav_sha256'], 'session_id': sid, 'spectra': len(spectra),
        'first_spectral_window': [spectra[0]['window_start_ts'], spectra[0]['window_end_ts']],
        'last_spectral_window': [spectra[-1]['window_start_ts'], spectra[-1]['window_end_ts']],
        'nyquist_hz': fs / 2, 'frequency_bin_spacing_hz': spectra[-1]['frequency_bin_spacing_hz'],
        'filters': filters, 'recording_replay_integrity': 'PASS', 'tamper_detection': 'PASS', 'scope': 'BACKEND SOFTWARE/API; NOT GUI RECORDING'}
    (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
