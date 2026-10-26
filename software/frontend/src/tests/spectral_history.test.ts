import assert from 'node:assert/strict';
import { appendSpectrum, spectrumColumn, spectralMaxFrequency, spectrumOrigin, MAX_SPECTRAL_FRAMES } from '../api/spectralHistory';
import type { SpectralFrameData } from '../types';
import { resolveStreamHealthState } from '../components/FooterStatus';
import { bridgeClient } from '../api/bridgeClient';

function frame(end: number, stream = 'A', fs = 48000): SpectralFrameData {
  return { stream_id: stream, window_start_ts: end - 0.1, window_end_ts: end,
    sample_rate_hz: fs, frequencies_hz: [0, 100, fs / 2], power_db: [-80, -10, -80],
    peak_frequency_hz: 100, dominant_band: 'fundamental_pcg' };
}

let history = appendSpectrum([], frame(1));
history = appendSpectrum(history, frame(3));
assert.equal(history.length, 2);
const first = spectrumColumn(history[0], 3);
const second = spectrumColumn(history[1], 3);
assert.ok(Math.abs(second.x - first.x - 2 / 15) < 1e-10, 'Lost UI updates must retain the two-second gap');
assert.ok(Math.abs(second.width - 0.1 / 15) < 1e-10);
assert.equal(appendSpectrum(history, frame(3)).length, 2, 'No duplicate retained PSD');
assert.equal(appendSpectrum(history, frame(4, 'B')).length, 1, 'Session/source reset');
assert.equal(appendSpectrum(history, frame(4, 'A', 4000)).length, 1, 'Rate change');
assert.equal(appendSpectrum(history, frame(0.5)).length, 1, 'Replay rewind');
for (let i = 4; i < 10000; i++) history = appendSpectrum(history, frame(i / 5));
assert.ok(history.length <= MAX_SPECTRAL_FRAMES);
assert.ok(history.every(item => item.window_end_ts! > history.at(-1)!.window_end_ts! - 15));
assert.equal(spectralMaxFrequency(48000), 2000);
assert.equal(spectralMaxFrequency(4000), 2000);
assert.equal(spectralMaxFrequency(1000), 500);
assert.match(spectrumOrigin('physical_deterministic_g1'), /DETERMINISTIC/);
assert.match(spectrumOrigin('software_simulated'), /NOT HARDWARE/);
assert.match(spectrumOrigin('physical_i2s_unqualified'), /UNQUALIFIED/);
assert.match(spectrumOrigin('session'), /REPLAY/);
assert.equal(appendSpectrum([], { ...frame(1), window_end_ts: NaN }).length, 0);
assert.equal(resolveStreamHealthState({ backendConnected: true, sourceType: 'device',
  totalBlocks: 1875, isStreaming: false }).state, 'NO_ACTIVE_ACQUISITION');
assert.equal(resolveStreamHealthState({ backendConnected: true, sourceType: 'device',
  totalBlocks: 1875, isStreaming: true }).state, 'STREAM_HEALTHY');
const observedStates: string[] = [];
const unsubscribe = bridgeClient.onDeviceState(device => observedStates.push(device.state));
// Exercise the actual WebSocket dispatch seam with both supported wire shapes.
const dispatch = bridgeClient as unknown as { handleMessage(message: Record<string, unknown>): void };
dispatch.handleMessage({ type: 'device_state', state: 'streaming', connected: true });
dispatch.handleMessage({ type: 'device_state', state: { state: 'ready', connected: true } });
unsubscribe();
assert.deepEqual(observedStates, ['streaming', 'ready']);
console.log('PASS: timed columns, gaps, reset/rewind/rate change, bounds, Nyquist and origin labels');
