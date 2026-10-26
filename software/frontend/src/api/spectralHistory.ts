import type { SpectralFrameData } from '../types';

export const SPECTRAL_WINDOW_SECONDS = 15;
export const MAX_SPECTRAL_FRAMES = 80;

export function appendSpectrum(history: SpectralFrameData[], frame: SpectralFrameData): SpectralFrameData[] {
  const start = frame.window_start_ts;
  const end = frame.window_end_ts;
  if (!frame.stream_id || !Number.isFinite(start) || !Number.isFinite(end) || end! <= start!
      || !frame.sample_rate_hz || !frame.frequencies_hz.length
      || frame.frequencies_hz.length !== frame.power_db.length) return history;
  const last = history.at(-1);
  if (last && (last.stream_id !== frame.stream_id || last.sample_rate_hz !== frame.sample_rate_hz
      || end! < last.window_end_ts!)) history = [];
  if (history.at(-1)?.window_end_ts === end) return history;
  return [...history.filter(item => item.window_end_ts! > end! - SPECTRAL_WINDOW_SECONDS), frame]
    .slice(-MAX_SPECTRAL_FRAMES);
}

export function spectrumColumn(frame: SpectralFrameData, latestEnd: number): { x: number; width: number } {
  const start = latestEnd - SPECTRAL_WINDOW_SECONDS;
  const left = Math.max(start, frame.window_start_ts!);
  return { x: (left - start) / SPECTRAL_WINDOW_SECONDS,
    width: Math.max(0, frame.window_end_ts! - left) / SPECTRAL_WINDOW_SECONDS };
}

export function spectralMaxFrequency(sampleRate: number): number {
  return Math.min(2000, sampleRate / 2);
}

export function spectrumOrigin(origin?: string): string {
  switch (origin) {
    case 'physical_deterministic_g1': return 'PHYSICAL USB · DETERMINISTIC G1';
    case 'physical_i2s_unqualified': return 'PHYSICAL I2S · ACOUSTICS UNQUALIFIED';
    case 'software_simulated': return 'SOFTWARE SIMULATION · NOT HARDWARE';
    case 'synthetic_dev': return 'SYNTHETIC · NOT HARDWARE';
    case 'session': return 'SESSION REPLAY';
    case 'realtime_wav': return 'FILE REPLAY';
    default: return 'SOURCE UNVERIFIED';
  }
}
