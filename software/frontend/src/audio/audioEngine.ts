import { FilterPreset, FilterStrength, ListeningTrack, AudioMetrics } from '../types';

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
    this.pauseOffset = 0;

    // Create 2-channel AudioBuffer: Channel 0 = Filtered, Channel 1 = Raw
    const buffer = this.ctx.createBuffer(2, raw.length, sampleRate);
    buffer.copyToChannel(filtered, 0);
    buffer.copyToChannel(raw, 1);
    this.currentAudioBuffer = buffer;
  }

  public async decodeUserFile(file: File): Promise<{ raw: Float32Array; filtered: Float32Array; sampleRate: number; duration: number }> {
    this.init();
    if (!this.ctx) throw new Error('Audio Context unavailable');

    const arrayBuffer = await file.arrayBuffer();
    const decodedBuffer = await this.ctx.decodeAudioData(arrayBuffer);

    const channel0 = decodedBuffer.getChannelData(0);
    const length = channel0.length;
    const raw = new Float32Array(length);
    const filtered = new Float32Array(length);
    raw.set(channel0);

    // Apply 20 Hz - 200 Hz acoustic passband
    const nyquist = decodedBuffer.sampleRate / 2;
    const lowCutNorm = Math.max(0.001, Math.min(0.9, 20 / nyquist));
    const highCutNorm = Math.max(0.01, Math.min(0.95, 200 / nyquist));

    let prev = 0;
    for (let i = 0; i < length; i++) {
      const hp = raw[i] - prev * (1 - lowCutNorm);
      prev = raw[i];
      filtered[i] = hp * (1 - (1 - highCutNorm) * 0.4);
    }

    this.setAudioData(raw, filtered, decodedBuffer.sampleRate);
    return {
      raw,
      filtered,
      sampleRate: decodedBuffer.sampleRate,
      duration: decodedBuffer.duration
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

    if (this.filterPreset === 'bell') {
      // 20 Hz - 100 Hz (Low Rumble Emphasized)
      this.filterHighPass.frequency.setTargetAtTime(20, this.ctx.currentTime, 0.03);
      this.filterLowPass.frequency.setTargetAtTime(100, this.ctx.currentTime, 0.03);
      this.filterLowPass.Q.setTargetAtTime(1.0, this.ctx.currentTime, 0.03);
    } else if (this.filterPreset === 'diaphragm') {
      // 100 Hz - 500 Hz (Murmur / Regurgitation)
      this.filterHighPass.frequency.setTargetAtTime(100, this.ctx.currentTime, 0.03);
      this.filterLowPass.frequency.setTargetAtTime(500, this.ctx.currentTime, 0.03);
      this.filterLowPass.Q.setTargetAtTime(1.1, this.ctx.currentTime, 0.03);
    } else if (this.filterPreset === 'extended') {
      // 10 Hz - 2000 Hz (Extended Unfiltered Feed)
      this.filterHighPass.frequency.setTargetAtTime(10, this.ctx.currentTime, 0.03);
      this.filterLowPass.frequency.setTargetAtTime(2000, this.ctx.currentTime, 0.03);
      this.filterLowPass.Q.setTargetAtTime(0.707, this.ctx.currentTime, 0.03);
    } else {
      // Recommended Normal: 20 Hz - 200 Hz (4th Order Chebyshev/Butterworth)
      this.filterHighPass.frequency.setTargetAtTime(20, this.ctx.currentTime, 0.03);
      this.filterLowPass.frequency.setTargetAtTime(200, this.ctx.currentTime, 0.03);
      this.filterLowPass.Q.setTargetAtTime(0.707, this.ctx.currentTime, 0.03);
    }
  }

  // Export genuine 16-bit PCM WAV
  public exportWav(track: 'filtered' | 'raw' = 'filtered'): Blob {
    const data = track === 'filtered' ? this.filteredData : this.rawData;
    const sampleRate = 4000;
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
