/** Preserve source samples; Web Audio decodeAudioData resamples to the playback device. */
export function decodePcmWav(bytes: ArrayBuffer): { raw: Float32Array; sampleRate: number } | null {
  const v = new DataView(bytes);
  const tag = (offset: number) => String.fromCharCode(...new Uint8Array(bytes, offset, 4));
  if (bytes.byteLength < 12 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE') return null;
  const end = v.getUint32(4, true) + 8;
  if (end > bytes.byteLength || end < 12) throw new Error('Truncated WAV container');
  let format = 0, channels = 0, sampleRate = 0, bits = 0, align = 0;
  let dataStart = 0, dataSize = 0;
  for (let offset = 12; offset + 8 <= end;) {
    const size = v.getUint32(offset + 4, true);
    if (offset + 8 + size > end) throw new Error('Truncated WAV chunk');
    if (tag(offset) === 'fmt ') {
      if (size < 16) throw new Error('Invalid WAV format chunk');
      format = v.getUint16(offset + 8, true);
      channels = v.getUint16(offset + 10, true);
      sampleRate = v.getUint32(offset + 12, true);
      align = v.getUint16(offset + 20, true);
      bits = v.getUint16(offset + 22, true);
    } else if (tag(offset) === 'data') {
      dataStart = offset + 8; dataSize = size;
    }
    offset += 8 + size + (size % 2);
  }
  if (!((format === 1 && bits === 16) || (format === 3 && bits === 32))) {
    throw new Error('Source-preserving WAV import supports PCM16 and IEEE float32');
  }
  if (!channels || sampleRate < 1000 || sampleRate > 192000 || align !== channels * bits / 8
      || !dataStart || !dataSize || dataSize % align) throw new Error('Invalid WAV rate, channels or sample layout');
  const raw = new Float32Array(dataSize / align);
  for (let i = 0; i < raw.length; i++) {
    let value = 0;
    for (let channel = 0; channel < channels; channel++) {
      const offset = dataStart + i * align + channel * bits / 8;
      value += format === 1 ? v.getInt16(offset, true) / 32768 : v.getFloat32(offset, true);
    }
    if (!Number.isFinite(value)) throw new Error('Non-finite WAV sample');
    raw[i] = value / channels;
  }
  return { raw, sampleRate };
}
