import { FilterPreset, FilterStrength, ListeningTrack, AudioMetrics } from '../types';
import { decodePcmWav } from './pcmWav';

export const FRONTEND_FILTER_PRESETS: Record<FilterPreset, { lowHz: number; highHz: number }> = {
  recommended: { lowHz: 20, highHz: 200 },
  bell: { lowHz: 20, highHz: 120 },
  diaphragm: { lowHz: 100, highHz: 500 },
  extended: { lowHz: 20, highHz: 600 },
  custom: { lowHz: 20, highHz: 200 },
};

/**
 * Causal cascaded 2nd-order Biquad filter (Highpass + Lowpass).
 * Numerically matches WebAudio BiquadFilterNode's bilinear transform transfer function.
 */
export function computeBiquadFilteredAudio(
  input: Float32Array,
  sampleRate: number,
  fLow: number,
  fHigh: number
): Float32Array {
  const nyquist = sampleRate / 2;
  const safeLow = Math.max(1.0, Math.min(fLow, nyquist - 2.0));
  const safeHigh = Math.max(safeLow + 1.0, Math.min(fHigh, nyquist - 1.0));
  const q = 0.7071;

  // Biquad Highpass
  const wHp = (2 * Math.PI * safeLow) / sampleRate;
  const alphaHp = Math.sin(wHp) / (2 * q);
  const cosHp = Math.cos(wHp);
  const a0Hp = 1 + alphaHp;
  const hpB0 = (1 + cosHp) / (2 * a0Hp);
  const hpB1 = -(1 + cosHp) / a0Hp;
  const hpB2 = (1 + cosHp) / (2 * a0Hp);
  const hpA1 = (-2 * cosHp) / a0Hp;
  const hpA2 = (1 - alphaHp) / a0Hp;

  // Biquad Lowpass
  const wLp = (2 * Math.PI * safeHigh) / sampleRate;
  const alphaLp = Math.sin(wLp) / (2 * q);
  const cosLp = Math.cos(wLp);
  const a0Lp = 1 + alphaLp;
  const lpB0 = (1 - cosLp) / (2 * a0Lp);
  const lpB1 = (1 - cosLp) / a0Lp;
  const lpB2 = (1 - cosLp) / (2 * a0Lp);
  const lpA1 = (-2 * cosLp) / a0Lp;
  const lpA2 = (1 - alphaLp) / a0Lp;

  const out = new Float32Array(input.length);
  let hpX1 = 0, hpX2 = 0, hpY1 = 0, hpY2 = 0;
  let lpX1 = 0, lpX2 = 0, lpY1 = 0, lpY2 = 0;

  for (let i = 0; i < input.length; i++) {
    const x = input[i];
    const hpOut = hpB0 * x + hpB1 * hpX1 + hpB2 * hpX2 - hpA1 * hpY1 - hpA2 * hpY2;
    hpX2 = hpX1; hpX1 = x;
    hpY2 = hpY1; hpY1 = hpOut;

    const lpOut = lpB0 * hpOut + lpB1 * lpX1 + lpB2 * lpX2 - lpA1 * lpY1 - lpA2 * lpY2;
    lpX2 = lpX1; lpX1 = hpOut;
    lpY2 = lpY1; lpY1 = lpOut;

    out[i] = lpOut;
  }
  return out;
}

class HeartAudioEngine {
  private ctx: AudioContext | null = null;
  private sourceNode: AudioBufferSourceNode | null = null;
  private gainNode: GainNode | null = null;
  private filterHighPass: BiquadFilterNode | null = null;
  private filterLowPass: BiquadFilterNode | null = null;
  private rawGainNode: GainNode | null = null;
  private filteredGainNode: GainNode | null = null;
  private analyser: AnalyserNode | null = null;

  private currentAudioBuffer: AudioBuffer | null = null;
  private rawData: Float32Array = new Float32Array(0);
  private filteredData: Float32Array = new Float32Array(0);

  private isPlaying: boolean = false;
  private startTime: number = 0;
  private pauseOffset: number = 0;
  private volume: number = 0.78;
  private isMuted: boolean = false;
  private activeTrack: ListeningTrack = 'filtered';
  private filterPreset: FilterPreset = 'recommended';
  private filterStrength: FilterStrength = 'Normal';
  private duration: number = 15.0;
  private sampleRate: number = 4000;

  private playbackCallbacks: Set<(currentTime: number) => void> = new Set();
  private animFrameId: number | null = null;

  public init() {
    if (!this.ctx) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioContextClass();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  public setAudioData(raw: Float32Array, filtered: Float32Array, sampleRate: number = 4000) {
    this.init();
    if (!this.ctx) return;

    this.stop();
    this.rawData = raw;
    this.filteredData = filtered;
    this.duration = raw.length / sampleRate;
    this.sampleRate = sampleRate;
    this.pauseOffset = 0;

    // Create 2-channel AudioBuffer: Channel 0 = Filtered, Channel 1 = Raw
    // Playback-only interpolation for low-rate PCG; analysis/export retain source samples.
    const playbackRate = Math.max(8000, sampleRate);
    const playbackLength = Math.ceil(raw.length * playbackRate / sampleRate);
    const buffer = this.ctx.createBuffer(2, playbackLength, playbackRate);
    for (const [channel, data] of [filtered, raw].entries()) {
      const playback = new Float32Array(playbackLength);
      for (let i = 0; i < playbackLength; i++) {
        const position = i * sampleRate / playbackRate;
        const left = Math.floor(position), right = Math.min(left + 1, data.length - 1);
        playback[i] = data[left] + (data[right] - data[left]) * (position - left);
      }
      buffer.copyToChannel(playback, channel);
    }
    this.currentAudioBuffer = buffer;
  }

  public async decodeUserFile(file: File): Promise<{ raw: Float32Array; filtered: Float32Array; sampleRate: number; duration: number }> {
    this.init();
    if (!this.ctx) throw new Error('Audio Context unavailable');

    const arrayBuffer = await file.arrayBuffer();
    const wav = decodePcmWav(arrayBuffer);
    const decodedBuffer = wav ? null : await this.ctx.decodeAudioData(arrayBuffer);
    const sampleRate = wav?.sampleRate ?? decodedBuffer!.sampleRate;
    const channel0 = wav?.raw ?? decodedBuffer!.getChannelData(0);
    const length = channel0.length;
    const raw = new Float32Array(length);
    raw.set(channel0);

    const { lowHz, highHz } = FRONTEND_FILTER_PRESETS[this.filterPreset] ?? FRONTEND_FILTER_PRESETS.recommended;
    const filtered = computeBiquadFilteredAudio(raw, sampleRate, lowHz, highHz);

    this.setAudioData(raw, filtered, sampleRate);
    return {
      raw,
      filtered,
      sampleRate,
      duration: raw.length / sampleRate
    };
  }

  public play() {
    this.init();
    if (!this.ctx || !this.currentAudioBuffer) return;
    if (this.isPlaying) return;

    if (this.pauseOffset >= this.duration) {
      this.pauseOffset = 0;
    }

    // Build audio routing graph
    this.sourceNode = this.ctx.createBufferSource();
    this.sourceNode.buffer = this.currentAudioBuffer;

    const splitter = this.ctx.createChannelSplitter(2);
    this.sourceNode.connect(splitter);

    // Biquad filters for physiological heart sounds
    this.filterHighPass = this.ctx.createBiquadFilter();
    this.filterHighPass.type = 'highpass';
    this.filterLowPass = this.ctx.createBiquadFilter();
    this.filterLowPass.type = 'lowpass';
    this.updateFilterParams();

    this.filteredGainNode = this.ctx.createGain();
    this.rawGainNode = this.ctx.createGain();

    splitter.connect(this.filterHighPass, 0);
    this.filterHighPass.connect(this.filterLowPass);
    this.filterLowPass.connect(this.filteredGainNode);

    splitter.connect(this.rawGainNode, 1);

    this.gainNode = this.ctx.createGain();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;

    this.updateTrackGain();
    this.updateMasterVolume();

    this.filteredGainNode.connect(this.gainNode);
    this.rawGainNode.connect(this.gainNode);
    this.gainNode.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    this.startTime = this.ctx.currentTime - this.pauseOffset;
    this.sourceNode.start(0, this.pauseOffset);
    this.isPlaying = true;

    this.sourceNode.onended = () => {
      if (this.getCurrentTime() >= this.duration - 0.05) {
        this.pause();
        this.pauseOffset = 0;
        this.notifyTime(0);
      }
    };

    this.startTracking();
  }

  public pause() {
    if (!this.isPlaying) return;
    this.pauseOffset = this.getCurrentTime();
    if (this.sourceNode) {
      try {
        this.sourceNode.stop();
        this.sourceNode.disconnect();
      } catch {
        // ignore
      }
      this.sourceNode = null;
    }
    this.isPlaying = false;
    this.stopTracking();
    this.notifyTime(this.pauseOffset);
  }

  public stop() {
    this.pause();
    this.pauseOffset = 0;
    this.notifyTime(0);
  }

  public seek(timeInSeconds: number) {
    const clamped = Math.max(0, Math.min(this.duration, timeInSeconds));
    const wasPlaying = this.isPlaying;
    if (wasPlaying) {
      this.pause();
      this.pauseOffset = clamped;
      this.play();
    } else {
      this.pauseOffset = clamped;
      this.notifyTime(clamped);
    }
  }

  public stepForwardCycle() {
    // Step by ~0.83s (one cardiac cycle at 72 BPM)
    const newTime = Math.min(this.duration, this.getCurrentTime() + 0.83);
    this.seek(newTime);
  }

  public setVolume(vol: number) {
    this.volume = Math.max(0, Math.min(1, vol));
    this.updateMasterVolume();
  }

  public getVolume(): number {
    return this.volume;
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    this.updateMasterVolume();
    return this.isMuted;
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  public setListeningTrack(track: ListeningTrack) {
    this.activeTrack = track;
    this.updateTrackGain();
  }

  public getListeningTrack(): ListeningTrack {
    return this.activeTrack;
  }

  public setFilterPreset(preset: FilterPreset) {
    this.filterPreset = preset;
    this.updateFilterParams();
    if (this.rawData.length > 0) {
      const { lowHz, highHz } = FRONTEND_FILTER_PRESETS[preset] ?? FRONTEND_FILTER_PRESETS.recommended;
      this.filteredData = computeBiquadFilteredAudio(this.rawData, this.sampleRate, lowHz, highHz);
      if (this.ctx) {
        this.setAudioData(this.rawData, this.filteredData, this.sampleRate);
      }
    }
  }

  public getFilterPreset(): FilterPreset {
    return this.filterPreset;
  }

  public setFilterStrength(strength: FilterStrength) {
    this.filterStrength = strength;
    this.updateFilterParams();
  }

  public getFilterStrength(): FilterStrength {
    return this.filterStrength;
  }

  public getCurrentTime(): number {
    if (!this.isPlaying || !this.ctx) {
      return this.pauseOffset;
    }
    const elapsed = this.ctx.currentTime - this.startTime;
    return Math.min(this.duration, Math.max(0, elapsed));
  }

  public getDuration(): number {
    return this.duration;
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }

  public getMetrics(): AudioMetrics {
    let peak = -2.4;
    let rms = -18.6;
    let clipping = false;

    if (this.analyser && this.isPlaying) {
      const data = new Float32Array(this.analyser.fftSize);
      this.analyser.getFloatTimeDomainData(data);

      let sumSquares = 0;
      let maxAbs = 0;
      for (let i = 0; i < data.length; i++) {
        const val = Math.abs(data[i]);
        if (val > maxAbs) maxAbs = val;
        sumSquares += val * val;
      }
      const rmsLinear = Math.sqrt(sumSquares / data.length);
      peak = maxAbs > 0.0001 ? 20 * Math.log10(maxAbs) : -72;
      rms = rmsLinear > 0.0001 ? 20 * Math.log10(rmsLinear) : -72;
      if (maxAbs >= 0.99) clipping = true;
    }

    return {
      currentPeakDb: Math.round(peak * 10) / 10,
      currentRmsDb: Math.round(rms * 10) / 10,
      clippingDetected: clipping,
      activeTrack: this.activeTrack,
      playbackVolume: Math.round(this.volume * 100),
      isMuted: this.isMuted
    };
  }

  public subscribeTime(cb: (currentTime: number) => void) {
    this.playbackCallbacks.add(cb);
    return () => this.playbackCallbacks.delete(cb);
  }

  private notifyTime(time: number) {
    this.playbackCallbacks.forEach(cb => cb(time));
  }

  private startTracking() {
    const loop = () => {
      if (this.isPlaying) {
        this.notifyTime(this.getCurrentTime());
        this.animFrameId = requestAnimationFrame(loop);
      }
    };
    this.animFrameId = requestAnimationFrame(loop);
  }

  private stopTracking() {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }

  private updateMasterVolume() {
    if (this.gainNode && this.ctx) {
      const target = this.isMuted ? 0 : this.volume;
      this.gainNode.gain.setTargetAtTime(target, this.ctx.currentTime, 0.015);
    }
  }

  private updateTrackGain() {
    if (!this.ctx) return;
    if (this.filteredGainNode) {
      const target = this.activeTrack === 'filtered' ? 1.0 : 0.0;
      this.filteredGainNode.gain.setTargetAtTime(target, this.ctx.currentTime, 0.02);
    }
    if (this.rawGainNode) {
      const target = this.activeTrack === 'raw' ? 1.0 : 0.0;
      this.rawGainNode.gain.setTargetAtTime(target, this.ctx.currentTime, 0.02);
    }
  }

  private updateFilterParams() {
    if (!this.filterHighPass || !this.filterLowPass || !this.ctx) return;
    const { lowHz, highHz } = FRONTEND_FILTER_PRESETS[this.filterPreset] ?? FRONTEND_FILTER_PRESETS.recommended;
    this.filterHighPass.frequency.setTargetAtTime(lowHz, this.ctx.currentTime, 0.03);
    this.filterLowPass.frequency.setTargetAtTime(highHz, this.ctx.currentTime, 0.03);
    this.filterLowPass.Q.setTargetAtTime(0.7071, this.ctx.currentTime, 0.03);
  }

  // Export 16-bit PCM WAV
  public exportWav(track: 'filtered' | 'raw' = 'filtered'): Blob {
    const data = track === 'filtered' ? this.filteredData : this.rawData;
    const sampleRate = this.sampleRate;
    const numChannels = 1;
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = data.length * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');

    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);

    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    let offset = 44;
    for (let i = 0; i < data.length; i++) {
      const s = Math.max(-1, Math.min(1, data[i]));
      const val = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(offset, val, true);
      offset += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

export const audioEngine = new HeartAudioEngine();
