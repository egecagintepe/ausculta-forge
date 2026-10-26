import assert from 'node:assert/strict';
import { audioEngine } from '../audio/audioEngine';
import { decodePcmWav } from '../audio/pcmWav';

function wav(sampleRate: number, count: number): ArrayBuffer {
  const bytes = new ArrayBuffer(44 + count * 2);
  const view = new DataView(bytes);
  const text = (offset: number, value: string) => [...value].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  text(0, 'RIFF'); view.setUint32(4, bytes.byteLength - 8, true); text(8, 'WAVE');
  text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, 'data'); view.setUint32(40, count * 2, true);
  for (let i = 0; i < count; i++) view.setInt16(44 + i * 2, i % 2 ? 16384 : -16384, true);
  return bytes;
}

class DeviceAudioContext {
  state = 'running'; sampleRate = 48000;
  decodeAudioData = async () => ({ sampleRate: 48000, duration: 0.032,
    getChannelData: () => new Float32Array(1536) });
  createBuffer = (_channels: number, _length: number, _rate: number) => ({ copyToChannel() {} });
}
(globalThis as unknown as { window: unknown }).window = { AudioContext: DeviceAudioContext };

for (const fs of [2000, 4000]) {
  const input = wav(fs, 128);
  const decoded = await audioEngine.decodeUserFile({ arrayBuffer: async () => input } as File);
  assert.equal(decoded.sampleRate, fs, 'WAV source rate must survive a 48 kHz playback device');
  assert.equal(decoded.raw.length, 128, 'Source sample count must not become playback sample count');
  assert.equal(decoded.duration, 128 / fs);
  assert.equal(decoded.raw[0], -0.5);
  assert.equal(decoded.raw[1], 0.5);
  const exported = decodePcmWav(await audioEngine.exportWav('raw').arrayBuffer());
  assert.equal(exported?.sampleRate, fs);
  assert.equal(exported?.raw.length, 128);
}
assert.throws(() => decodePcmWav(wav(4000, 128).slice(0, 80)), /Truncated/);
const invalid = wav(4000, 128); new DataView(invalid).setUint16(32, 3, true);
assert.throws(() => decodePcmWav(invalid), /layout/);
const floating = new ArrayBuffer(44 + 8);
new Uint8Array(floating).set(new Uint8Array(wav(4000, 4)).subarray(0, 44));
const fv = new DataView(floating);
fv.setUint16(20, 3, true); fv.setUint16(32, 4, true); fv.setUint16(34, 32, true);
fv.setFloat32(44, 0.125, true); fv.setFloat32(48, -0.25, true);
assert.deepEqual([...decodePcmWav(floating)!.raw], [0.125, -0.25]);
fv.setFloat32(44, NaN, true);
assert.throws(() => decodePcmWav(floating), /Non-finite/);
console.log('PASS: original 2/4 kHz WAV rate, count, duration and PCM values preserved');
