import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  FileAudio,
  Sliders,
  Terminal,
  Maximize2,
  Minimize2,
  Play,
  Pause,
  SkipBack,
  FastForward,
  Volume2,
  VolumeX,
  Volume1,
  Download,
  Check,
  ChevronDown,
  Activity,
  Layers,
  Radio,
  Disc
} from 'lucide-react';
import {
  AudioSourceType,
  FilterPreset,
  FilterStrength,
  ListeningTrack,
  HeartSoundMetadata,
  SpectralFrameData,
} from '../types';
import { resolveStreamHealthState } from './FooterStatus';

interface LiveWorkspaceProps {
  sourceType: AudioSourceType;
  activeMetadata: HeartSoundMetadata | null;
  rawData: Float32Array;
  filteredData: Float32Array;
  sampleRate: number;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onRestart: () => void;
  onStepForwardCycle: () => void;
  onSeek: (time: number) => void;
  volume: number;
  onVolumeChange: (vol: number) => void;
  isMuted: boolean;
  onToggleMute: () => void;
  filterPreset: FilterPreset;
  onChangeFilterPreset: (preset: FilterPreset) => void;
  filterStrength: FilterStrength;
  onChangeFilterStrength: (strength: FilterStrength) => void;
  showRaw: boolean;
  onToggleShowRaw: () => void;
  listeningTrack: ListeningTrack;
  onToggleListeningTrack: (track: ListeningTrack) => void;
  visibleWindowSec: number;
  onChangeWindowSec: (sec: number) => void;
  isDark: boolean;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onToggleDiagnostics: () => void;
  onExportFiltered: () => void;
  liveMetrics?: { rms: number; peak: number; crest_factor: number };
  streamQuality?: { total_blocks: number; dropped_blocks: number; repeated_sequences: number; sequence_discontinuities: number; is_healthy: boolean };
  backendConnected?: boolean;
  isRecording?: boolean;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  recordingElapsedSeconds?: number;
  droppedDisplayFrames?: number;
  spectralFrame?: SpectralFrameData | null;
  displayPointsPerSec?: number;
}

export const LiveWorkspace: React.FC<LiveWorkspaceProps> = ({
  sourceType,
  activeMetadata,
  rawData,
  filteredData,
  sampleRate,
  duration,
  currentTime,
  isPlaying,
  onTogglePlay,
  onRestart,
  onStepForwardCycle,
  onSeek,
  volume,
  onVolumeChange,
  isMuted,
  onToggleMute,
  filterPreset,
  onChangeFilterPreset,
  filterStrength,
  onChangeFilterStrength,
  showRaw,
  onToggleShowRaw,
  listeningTrack,
  onToggleListeningTrack,
  visibleWindowSec,
  onChangeWindowSec,
  isDark,
  isFullscreen,
  onToggleFullscreen,
  onToggleDiagnostics,
  onExportFiltered,
  liveMetrics,
  streamQuality,
  backendConnected,
  isRecording,
  onStartRecording,
  onStopRecording,
  recordingElapsedSeconds,
  droppedDisplayFrames = 0,
  spectralFrame = null,
  displayPointsPerSec,
}) => {
  const [viewMode, setViewMode] = useState<'oscilloscope' | 'fft'>('oscilloscope');
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const [rawMuted, setRawMuted] = useState(false);
  const filterDropdownRef = useRef<HTMLDivElement>(null);
  const mainCanvasRef = useRef<HTMLCanvasElement>(null);
  const rawCanvasRef = useRef<HTMLCanvasElement>(null);
  const overviewCanvasRef = useRef<HTMLCanvasElement>(null);
  const fftCanvasRef = useRef<HTMLCanvasElement>(null);
  const spectrogramCanvasRef = useRef<HTMLCanvasElement>(null);
  const spectralHistoryRef = useRef<Array<{ freqs: number[]; powers: number[] }>>([]);

  // Close filter menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (filterDropdownRef.current && !filterDropdownRef.current.contains(e.target as Node)) {
        setFilterMenuOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // Format time (00:08.4)
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = (secs % 60).toFixed(1);
    return `${m.toString().padStart(2, '0')}:${s.padStart(4, '0')}`;
  };

  // Calculate window start for scrolling view
  let windowStart = Math.max(0, currentTime - visibleWindowSec * 0.7);
  if (windowStart + visibleWindowSec > duration && duration > visibleWindowSec) {
    windowStart = Math.max(0, duration - visibleWindowSec);
  }
  const windowEnd = Math.min(duration, windowStart + visibleWindowSec);

  // Playhead percentage in visible window
  const playheadPercent = visibleWindowSec > 0
    ? Math.max(0, Math.min(100, ((currentTime - windowStart) / visibleWindowSec) * 100))
    : 0;

  // Viewport window percentage in full file
  const viewportStartPercent = duration > 0 ? (windowStart / duration) * 100 : 0;
  const viewportWidthPercent = duration > 0 ? Math.min(100, (visibleWindowSec / duration) * 100) : 66.6;
  const overviewPlayheadPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Draw Primary Filtered Waveform on Canvas
  useEffect(() => {
    const canvas = mainCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const waveColor = isDark ? '#D19AA3' : '#7A3842';

    const ptsRate = displayPointsPerSec && displayPointsPerSec > 0
      ? displayPointsPerSec
      : (filteredData.length > 0 && duration > 0 ? filteredData.length / Math.min(15.0, duration) : sampleRate);
    const bufferSpan = filteredData.length > 0 && ptsRate > 0 ? filteredData.length / ptsRate : visibleWindowSec;
    const bufferStart = Math.max(0, duration - bufferSpan);

    if (sourceType !== 'none' && filteredData.length > 0 && ptsRate > 0) {
      const startIndex = Math.max(0, Math.floor((windowStart - bufferStart) * ptsRate));
      const endIndex = Math.min(filteredData.length, Math.ceil((windowEnd - bufferStart) * ptsRate));
      const count = endIndex - startIndex;

      if (count > 0) {
        ctx.beginPath();
        ctx.strokeStyle = waveColor;
        ctx.lineWidth = 2.0;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        const bins = Math.floor(w);
        const samplesPerBin = count / bins;

        let started = false;
        for (let b = 0; b < bins; b++) {
          const bStart = startIndex + Math.floor(b * samplesPerBin);
          const bEnd = Math.min(filteredData.length, startIndex + Math.floor((b + 1) * samplesPerBin));

          let min = 0;
          let max = 0;
          for (let s = bStart; s < bEnd; s++) {
            const val = filteredData[s];
            if (val < min) min = val;
            if (val > max) max = val;
          }

          const x = b;
          const yMin = (h / 2) - (max * (h * 0.44));
          const yMax = (h / 2) - (min * (h * 0.44));

          if (!started) {
            ctx.moveTo(x, yMin);
            started = true;
          } else {
            ctx.lineTo(x, yMin);
            ctx.lineTo(x, yMax);
          }
        }
        ctx.stroke();
      }
    }
  }, [filteredData, sampleRate, windowStart, windowEnd, isDark, visibleWindowSec, sourceType, displayPointsPerSec, duration]);

  // Draw Raw Waveform on Canvas
  useEffect(() => {
    if (!showRaw) return;
    const canvas = rawCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const waveColor = isDark ? '#948E84' : '#93897C';

    const ptsRate = displayPointsPerSec && displayPointsPerSec > 0
      ? displayPointsPerSec
      : (rawData.length > 0 && duration > 0 ? rawData.length / Math.min(15.0, duration) : sampleRate);
    const bufferSpan = rawData.length > 0 && ptsRate > 0 ? rawData.length / ptsRate : visibleWindowSec;
    const bufferStart = Math.max(0, duration - bufferSpan);

    if (sourceType !== 'none' && rawData.length > 0 && ptsRate > 0) {
      const startIndex = Math.max(0, Math.floor((windowStart - bufferStart) * ptsRate));
      const endIndex = Math.min(rawData.length, Math.ceil((windowEnd - bufferStart) * ptsRate));
      const count = endIndex - startIndex;

      if (count > 0) {
        ctx.beginPath();
        ctx.strokeStyle = waveColor;
        ctx.lineWidth = 1.6;
        ctx.lineJoin = 'round';

        const bins = Math.floor(w);
        const samplesPerBin = count / bins;

        let started = false;
        for (let b = 0; b < bins; b++) {
          const bStart = startIndex + Math.floor(b * samplesPerBin);
          const bEnd = Math.min(rawData.length, startIndex + Math.floor((b + 1) * samplesPerBin));

          let min = 0;
          let max = 0;
          for (let s = bStart; s < bEnd; s++) {
            const val = rawData[s];
            if (val < min) min = val;
            if (val > max) max = val;
          }

          const x = b;
          const yMin = (h / 2) - (max * (h * 0.44));
          const yMax = (h / 2) - (min * (h * 0.44));

          if (!started) {
            ctx.moveTo(x, yMin);
            started = true;
          } else {
            ctx.lineTo(x, yMin);
            ctx.lineTo(x, yMax);
          }
        }
        ctx.stroke();
      }
    }
  }, [rawData, sampleRate, windowStart, windowEnd, isDark, showRaw, visibleWindowSec, sourceType, displayPointsPerSec, duration]);

  // Accumulate spectral history for the waterfall spectrogram heatmap
  useEffect(() => {
    if (!spectralFrame || !spectralFrame.frequencies_hz || spectralFrame.frequencies_hz.length === 0) return;
    const history = spectralHistoryRef.current;
    history.push({
      freqs: spectralFrame.frequencies_hz,
      powers: spectralFrame.power_db,
    });
    if (history.length > 80) {
      history.shift();
    }
  }, [spectralFrame]);

  // Draw FFT / Power Spectral Density on Canvas
  useEffect(() => {
    if (viewMode !== 'fft') return;
    const canvas = fftCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    if (spectralFrame && spectralFrame.frequencies_hz && spectralFrame.frequencies_hz.length > 0) {
      const freqs = spectralFrame.frequencies_hz;
      const powers = spectralFrame.power_db;
      const maxFreq = 2000;
      const minDb = -85;
      const maxDb = 0;

      const freqToX = (f: number) => Math.max(0, Math.min(w, (f / maxFreq) * w));
      const dbToY = (db: number) => {
        const clamped = Math.max(minDb, Math.min(maxDb, db));
        return h - ((clamped - minDb) / (maxDb - minDb)) * h;
      };

      // 1. Shaded clinical acoustic zones
      // S1/S2 Primary PCG: 20-150 Hz
      const s1X1 = freqToX(20);
      const s1X2 = freqToX(150);
      ctx.fillStyle = isDark ? 'rgba(197, 155, 39, 0.12)' : 'rgba(183, 154, 112, 0.15)';
      ctx.fillRect(s1X1, 0, s1X2 - s1X1, h);

      // Murmur/Turbulence: 150-600 Hz
      const mX1 = freqToX(150);
      const mX2 = freqToX(600);
      ctx.fillStyle = isDark ? 'rgba(209, 154, 163, 0.10)' : 'rgba(122, 29, 46, 0.10)';
      ctx.fillRect(mX1, 0, mX2 - mX1, h);

      // 2. Graticules
      ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';
      ctx.lineWidth = 1;

      [-20, -40, -60, -80].forEach(db => {
        const y = dbToY(db);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      });

      [50, 100, 200, 500, 1000, 1500].forEach(f => {
        const x = freqToX(f);
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      });

      // 3. Curve fill
      ctx.beginPath();
      let first = true;
      for (let i = 0; i < freqs.length; i++) {
        if (freqs[i] > maxFreq) break;
        const x = freqToX(freqs[i]);
        const y = dbToY(powers[i]);
        if (first) {
          ctx.moveTo(x, y);
          first = false;
        } else {
          ctx.lineTo(x, y);
        }
      }

      const grad = ctx.createLinearGradient(0, 0, 0, h);
      if (isDark) {
        grad.addColorStop(0, 'rgba(209, 154, 163, 0.40)');
        grad.addColorStop(0.7, 'rgba(197, 155, 39, 0.12)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        grad.addColorStop(0, 'rgba(122, 56, 66, 0.35)');
        grad.addColorStop(0.7, 'rgba(183, 154, 112, 0.12)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      }

      ctx.save();
      const lastIdx = Math.min(freqs.length - 1, freqs.findIndex(f => f > maxFreq));
      const endX = freqToX(freqs[lastIdx >= 0 ? lastIdx : freqs.length - 1]);
      ctx.lineTo(endX, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();

      // Stroke curve line
      ctx.beginPath();
      first = true;
      for (let i = 0; i < freqs.length; i++) {
        if (freqs[i] > maxFreq) break;
        const x = freqToX(freqs[i]);
        const y = dbToY(powers[i]);
        if (first) {
          ctx.moveTo(x, y);
          first = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.strokeStyle = isDark ? '#D19AA3' : '#7A3842';
      ctx.lineWidth = 2.2;
      ctx.stroke();

      // Peak crosshair marker
      const peakFreq = spectralFrame.peak_frequency_hz;
      if (peakFreq > 0 && peakFreq <= maxFreq) {
        const peakX = freqToX(peakFreq);
        let closestPower = -80;
        let minDiff = Infinity;
        for (let i = 0; i < freqs.length; i++) {
          const diff = Math.abs(freqs[i] - peakFreq);
          if (diff < minDiff) {
            minDiff = diff;
            closestPower = powers[i];
          }
        }
        const peakY = dbToY(closestPower);

        ctx.strokeStyle = isDark ? 'rgba(253, 224, 71, 0.7)' : 'rgba(122, 29, 46, 0.8)';
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(peakX, 0);
        ctx.lineTo(peakX, h);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.beginPath();
        ctx.arc(peakX, peakY, 4, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? '#FDE047' : '#7A1D2E';
        ctx.fill();
        ctx.strokeStyle = isDark ? '#FFFFFF' : '#000000';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    } else {
      ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.35)' : 'rgba(0, 0, 0, 0.35)';
      ctx.font = '11px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(sourceType === 'none' ? 'NO ACQUISITION SOURCE ACTIVE' : 'AWAITING SPECTRAL FRAME TICKS...', w / 2, h / 2);
    }
  }, [viewMode, spectralFrame, isDark, sourceType]);

  // Draw Waterfall Spectrogram Heatmap on Canvas
  useEffect(() => {
    if (viewMode !== 'fft') return;
    const canvas = spectrogramCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const history = spectralHistoryRef.current;
    if (history.length === 0) return;

    const maxFreq = 2000;
    const minDb = -85;
    const maxDb = 0;
    const colW = w / Math.max(1, history.length);

    history.forEach((frame, colIdx) => {
      const x = colIdx * colW;
      const freqs = frame.freqs;
      const powers = frame.powers;
      const nBins = freqs.length;
      if (nBins === 0) return;

      for (let i = 0; i < nBins; i++) {
        if (freqs[i] > maxFreq) break;
        const freqNext = i < nBins - 1 ? freqs[i + 1] : maxFreq;
        const yTop = h - (freqNext / maxFreq) * h;
        const yBottom = h - (freqs[i] / maxFreq) * h;
        const binH = Math.max(1, yBottom - yTop);

        const norm = Math.max(0, Math.min(1, (powers[i] - minDb) / (maxDb - minDb)));
        let color = '#1a1816';
        if (norm < 0.25) {
          color = `rgb(${Math.round(norm * 4 * 74)},${Math.round(norm * 4 * 18)},${Math.round(norm * 4 * 26)})`;
        } else if (norm < 0.55) {
          const t = (norm - 0.25) / 0.3;
          color = `rgb(${Math.round(74 + t * 48)},${Math.round(18 + t * 11)},${Math.round(26 + t * 20)})`;
        } else if (norm < 0.85) {
          const t = (norm - 0.55) / 0.3;
          color = `rgb(${Math.round(122 + t * 75)},${Math.round(29 + t * 126)},${Math.round(46 - t * 7)})`;
        } else {
          const t = (norm - 0.85) / 0.15;
          color = `rgb(${Math.round(197 + t * 56)},${Math.round(155 + t * 69)},${Math.round(39 + t * 32)})`;
        }

        ctx.fillStyle = color;
        ctx.fillRect(x, yTop, colW + 0.5, binH);
      }
    });
  }, [viewMode, spectralFrame, isDark]);

  // Draw Full Overview mini-waveform
  useEffect(() => {
    const canvas = overviewCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    if (sourceType !== 'none' && filteredData.length > 0) {
      ctx.fillStyle = isDark ? 'rgba(183, 154, 112, 0.6)' : 'rgba(141, 116, 80, 0.6)';
      const step = Math.ceil(filteredData.length / w);
      for (let x = 0; x < w; x++) {
        const start = x * step;
        const end = Math.min(filteredData.length, start + step);
        let max = 0;
        for (let i = start; i < end; i++) {
          const abs = Math.abs(filteredData[i]);
          if (abs > max) max = abs;
        }
        const barH = Math.max(1, max * (h * 0.75));
        ctx.fillRect(x, (h - barH) / 2, 1, barH);
      }
    }
  }, [filteredData, isDark, sourceType]);

  // Click on main canvas to seek
  const handleMainCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const seekTime = windowStart + ratio * visibleWindowSec;
    onSeek(seekTime);
  };

  // Click on overview timeline to seek
  const handleOverviewClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeek(ratio * duration);
  };

  // Preset labels map
  const presetLabels: Record<FilterPreset, { title: string; range: string }> = {
    recommended: { title: 'Narrow [20–200 Hz]', range: '20 Hz – 200 Hz · 4th Order Chebyshev (Dev Preset)' },
    bell: { title: 'Bell Acoustic Mode', range: '20 Hz – 100 Hz · Low Rumble Emphasized' },
    diaphragm: { title: 'Diaphragm Modality', range: '100 Hz – 500 Hz · Murmur / Regurgitation' },
    extended: { title: 'Extended Unfiltered Feed', range: '10 Hz – 2000 Hz · Direct Transducer' }
  };

  const resolvedPreset = presetLabels[filterPreset] ?? {
    title: `Unknown backend preset (${String(filterPreset)})`,
    range: 'Filter range not verified',
  };

  return (
    <div
      id="live-workspace-view"
      className="flex-1 flex flex-col h-full overflow-y-auto px-5 py-4 select-none transition-colors"
      style={{
        backgroundColor: 'var(--bg-canvas)'
      }}
    >
      <div className="max-w-full mx-auto w-full flex flex-col gap-3.5 pb-8">
        {/* 1. Top Specimen & Modality Status Strip */}
        <div
          className="flex flex-col md:flex-row md:items-center justify-between gap-3 rounded-xl p-3.5 shadow-xs relative overflow-hidden border"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          {/* Subtle Brass Accent Backdrop */}
          <div className="absolute -right-20 -top-20 w-64 h-64 rounded-full bg-[var(--accent-metal)]/5 pointer-events-none blur-2xl" />
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--accent-oxblood)]" />

          <div className="flex flex-wrap items-center gap-3 pl-2">
            {/* File Metadata Indicator */}
            <div className="flex items-center gap-2">
              <FileAudio size={22} className="text-[var(--accent-oxblood)] shrink-0" />
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-sans-ui text-sm font-semibold text-[var(--on-surface)] tracking-tight">
                    {sourceType === 'none' ? 'No Active Source' : (activeMetadata?.filename || 'Live Stream')}
                  </span>
                  <span className="bg-[var(--surface-muted)] text-[var(--on-surface-variant)] font-mono-code text-[10px] px-2 py-0.5 rounded font-semibold border border-[var(--border-subtle)]">
                    {sourceType === 'device'
                      ? 'LIVE HARDWARE'
                      : sourceType === 'synthetic'
                      ? 'SYNTHETIC BENCHMARK (NOT HARDWARE)'
                      : sourceType === 'session'
                      ? 'SESSION REPLAY'
                      : sourceType === 'sample'
                      ? 'REFERENCE SPECIMEN'
                      : sourceType === 'file'
                      ? 'FILE AUDITION'
                      : 'NO SOURCE'}
                  </span>
                </div>
                <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] uppercase tracking-wider font-medium">
                  {sourceType === 'none'
                    ? 'ACQUISITION IDLE · NO REAL-TIME SIGNAL MEASURED'
                    : `PCM STREAM · ${(sampleRate / 1000).toFixed(1)} KHZ · FLOAT32 APP · LIVE BENCH`}
                </span>
              </div>
            </div>

            <div className="h-6 w-px bg-[var(--border-subtle)] hidden sm:block mx-1" />

            {/* Backend Offline Alert Badge */}
            {backendConnected === false && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--status-danger)]/15 text-[var(--status-danger)] border border-[var(--status-danger)]/30 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-danger)]" />
                <span className="font-mono-code text-[11px] font-semibold tracking-wide">
                  BACKEND OFFLINE — RECONNECTING...
                </span>
              </div>
            )}

            {/* Signal / Stream Quality Badge with Truthful MCU vs UI Separation */}
            {backendConnected && (() => {
              const streamStatus = resolveStreamHealthState({
                backendConnected,
                sourceType,
                totalBlocks: streamQuality?.total_blocks,
                isHealthy: streamQuality?.is_healthy,
                droppedBlocks: streamQuality?.dropped_blocks,
                uiDroppedFrames: droppedDisplayFrames,
              });
              const isNeutral = streamStatus.state === 'NO_ACTIVE_ACQUISITION' || streamStatus.state === 'NOT_EVALUATED';
              const isHealthyState = streamStatus.state === 'STREAM_HEALTHY' || streamStatus.state === 'SYNTHETIC_ACTIVE' || streamStatus.state === 'FILE_ACTIVE';

              return (
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded ${
                  isNeutral
                    ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]'
                    : isHealthyState
                    ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/25'
                    : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border border-[var(--status-warning)]/25'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    isNeutral
                      ? 'bg-[var(--border-strong)]'
                      : isHealthyState
                      ? 'bg-[var(--status-success)]'
                      : 'bg-[var(--status-warning)]'
                  }`} />
                  <span className="font-mono-code text-[11px] font-semibold tracking-wide">
                    STREAM: {streamStatus.label}
                    {streamStatus.telemetrySummary ? ` · ${streamStatus.telemetrySummary}` : ''}
                  </span>
                </div>
              );
            })()}

            {!backendConnected && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                <span className="font-mono-code text-[11px] font-semibold tracking-wide">
                  {activeMetadata?.quality.score != null
                    ? `QUALITY: ${activeMetadata.quality.rating.toUpperCase()} (${activeMetadata.quality.score}%)`
                    : `SOURCE: ${activeMetadata?.quality.message || 'OFFLINE SPECIMEN'}`}
                </span>
              </div>
            )}

            {/* Filter Preset Chip */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-subtle)]">
              <Sliders size={13} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] tracking-wide">
                FILTER: {filterPreset === 'recommended' ? 'NARROW 20–200 Hz (DEV PRESET)' : resolvedPreset.title.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Secondary Utilities & Registration Controls */}
          <div className="flex items-center gap-2 self-end md:self-auto">
            <div className="flex items-center bg-[var(--surface-muted)] rounded p-0.5 border border-[var(--border-subtle)]">
              <button
                onClick={() => setViewMode('fft')}
                className={`px-2 py-1 rounded font-mono-code text-[11px] flex items-center gap-1 cursor-pointer transition-colors ${
                  viewMode === 'fft'
                    ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                    : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                }`}
                title="Spectrogram Inspection"
              >
                <span>FFT</span>
              </button>
              <button
                onClick={() => setViewMode('oscilloscope')}
                className={`px-2 py-1 rounded font-mono-code text-[11px] flex items-center gap-1 cursor-pointer transition-colors ${
                  viewMode === 'oscilloscope'
                    ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                    : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                }`}
              >
                <Activity size={13} />
                <span>OSCILLOSCOPE</span>
              </button>
            </div>

            <button
              onClick={onToggleDiagnostics}
              title="Diagnostics Terminal (^⇧D)"
              className="h-8 px-2 rounded bg-[var(--surface-card)] hover:bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] transition-colors flex items-center gap-1 border border-[var(--border-subtle)] shadow-xs cursor-pointer"
            >
              <Terminal size={14} className="text-[var(--accent-metal)]" />
              <kbd className="font-mono-code text-[10px] bg-[var(--surface-muted)] px-1 rounded text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                ^⇧D
              </kbd>
            </button>

            <button
              onClick={onToggleFullscreen}
              title={isFullscreen ? 'Exit Fullscreen (F11)' : 'Fullscreen Modality (F11)'}
              className="w-8 h-8 rounded bg-[var(--surface-card)] hover:bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] transition-colors flex items-center justify-center border border-[var(--border-subtle)] shadow-xs cursor-pointer"
            >
              {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          </div>
        </div>

        {/* 2. Primary Canvas Enclosure: Oscilloscope & Acoustic Graph */}
        <div
          className="flex flex-col rounded-xl p-4 shadow-xs relative overflow-hidden border"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          {/* Cyber-Baroque Brass Crosshairs (Corner Registration Marks) */}
          <div className="absolute top-2 left-2 text-[var(--accent-metal)] opacity-50 select-none pointer-events-none font-mono-code text-[9px] leading-none">
            ┌ ┼ 0.000
          </div>
          <div className="absolute top-2 right-2 text-[var(--accent-metal)] opacity-50 select-none pointer-events-none font-mono-code text-[9px] leading-none">
            10.000 ┼ ┐
          </div>
          <div className="absolute bottom-2 left-2 text-[var(--accent-metal)] opacity-50 select-none pointer-events-none font-mono-code text-[9px] leading-none">
            └ ┼ -1.0FS
          </div>
          <div className="absolute bottom-2 right-2 text-[var(--accent-metal)] opacity-50 select-none pointer-events-none font-mono-code text-[9px] leading-none">
            +1.0FS ┼ ┘
          </div>

          {/* Graph Header Bar: Track Identifiers & View Controls */}
          <div className="flex items-center justify-between pb-2 px-1">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className={`w-2.5 h-2.5 rounded-full ${viewMode === 'fft' ? 'bg-[var(--accent-metal)]' : 'bg-[var(--accent-oxblood)]'}`} />
                <span className="font-mono-code text-[11px] text-[var(--on-surface)] font-bold tracking-wider uppercase">
                  {viewMode === 'fft' ? 'Track S: Real-Time Acoustic Spectral Density (PSD)' : 'Track A: Processed Phonocardiogram (PCG)'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 font-mono-code text-[10px]">
                {viewMode === 'oscilloscope' ? (
                  <>
                    <span className="px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--accent-oxblood)] font-bold border border-[var(--border-subtle)]">
                      {resolvedPreset.title} ({resolvedPreset.range})
                    </span>
                    {liveMetrics && (
                      <span className="text-[var(--on-surface-variant)] hidden md:inline">
                        RMS: <strong className="text-[var(--on-surface)]">{liveMetrics.rms.toFixed(4)}</strong> · PEAK: <strong className="text-[var(--on-surface)]">{liveMetrics.peak.toFixed(4)}</strong> · CREST: <strong className="text-[var(--on-surface)]">{liveMetrics.crest_factor.toFixed(2)}</strong>
                      </span>
                    )}
                    {streamQuality && (
                      <span className={`px-2 py-0.5 rounded font-mono-code text-[10px] font-semibold border ${
                        streamQuality.is_healthy && (droppedDisplayFrames || 0) === 0
                          ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                          : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border-[var(--status-warning)]/30'
                      }`}>
                        {streamQuality.is_healthy ? 'MCU: 0 LOSS' : `MCU: ${streamQuality.dropped_blocks} LOSS`}
                        {' · '}
                        {(droppedDisplayFrames || 0) === 0 ? 'UI: 0 DROPS' : `UI: ${droppedDisplayFrames} DROPS`}
                      </span>
                    )}
                  </>
                ) : (
                  <>
                    <span className={`px-2 py-0.5 rounded font-mono-code text-[10px] font-bold border ${
                      spectralFrame?.dominant_band === 'fundamental_pcg'
                        ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30'
                        : spectralFrame?.dominant_band === 'extended_pcg'
                        ? 'bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)] border-[var(--accent-oxblood)]/30'
                        : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-subtle)]'
                    }`}>
                      {spectralFrame?.dominant_band === 'fundamental_pcg'
                        ? 'S1/S2 PCG BAND (20–150 Hz)'
                        : spectralFrame?.dominant_band === 'extended_pcg'
                        ? 'MURMUR / TURBULENCE (150–600 Hz)'
                        : spectralFrame?.dominant_band === 'sub_audible'
                        ? 'INFRASOUND (<20 Hz)'
                        : spectralFrame?.dominant_band ? spectralFrame.dominant_band.toUpperCase() : 'AWAITING TICKS'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--on-surface)] font-mono-code text-[10px] border border-[var(--border-subtle)]">
                      PEAK: <strong className="text-[var(--accent-oxblood)]">{spectralFrame?.peak_frequency_hz ? spectralFrame.peak_frequency_hz.toFixed(1) + ' Hz' : '-- Hz'}</strong>
                    </span>
                    <span className="text-[var(--on-surface-variant)] hidden md:inline">
                      WELCH PSD · ADAPTIVE 48 kHz BINS · 5.0 Hz CADENCE
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {viewMode === 'oscilloscope' && (
                <>
                  <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">SPAN:</span>
                  <div className="flex items-center bg-[var(--surface-muted)] rounded p-0.5 border border-[var(--border-subtle)]">
                    {[2, 5, 10].map(sec => (
                      <button
                        key={sec}
                        onClick={() => onChangeWindowSec(sec)}
                        className={`px-2 py-0.5 rounded font-mono-code text-[10px] cursor-pointer transition-colors ${
                          visibleWindowSec === sec
                            ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                            : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                        }`}
                      >
                        {sec} s
                      </button>
                    ))}
                  </div>

                  <button
                    id="toggle-raw-btn"
                    onClick={onToggleShowRaw}
                    className={`px-3 py-1 rounded transition-colors font-mono-code text-[10px] font-semibold flex items-center gap-1.5 border cursor-pointer ${
                      showRaw
                        ? 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-strong)]'
                        : 'bg-[var(--surface-card)] text-[var(--on-surface-variant)] border-[var(--border-subtle)] hover:border-[var(--border-strong)]'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--waveform-raw)]" />
                    <span>{showRaw ? 'SHOW RAW (ACTIVE)' : 'SHOW RAW'}</span>
                  </button>
                </>
              )}

              {viewMode === 'fft' && (
                <div className="font-mono-code text-[10px] px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--accent-metal)] border border-[var(--border-subtle)] font-semibold">
                  PASSBAND: 0–2000 Hz
                </div>
              )}
            </div>
          </div>

          {/* Reticle Area (Recessed Tray) */}
          <div
            className="relative w-full rounded-lg overflow-hidden flex flex-col shadow-inner border"
            style={{
              backgroundColor: 'var(--bg-deep)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            {/* Top Axis Ruler: Dynamic physical timestamps for Oscilloscope, Frequency ticks for FFT */}
            <div
              className="h-6 w-full flex items-center justify-between px-6 font-mono-code text-[10px] tracking-wider select-none relative border-b"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--on-surface-variant)'
              }}
            >
              {viewMode === 'oscilloscope' ? (
                <>
                  {(() => {
                    const numTicks = 6;
                    const ticks = [];
                    for (let i = 0; i < numTicks; i++) {
                      const t = windowStart + (i * visibleWindowSec) / (numTicks - 1);
                      ticks.push(t);
                    }
                    return ticks.map((t, idx) => (
                      <div key={idx} className="flex items-center gap-1">
                        <span>{t.toFixed(1)}s</span>
                        <div className="w-px h-2 bg-[var(--border-strong)]" />
                      </div>
                    ));
                  })()}

                  <div
                    className="absolute right-3 top-1 px-2 py-0.5 rounded text-[9px] font-mono-code font-semibold shadow-xs border"
                    style={{
                      backgroundColor: 'var(--surface-card)',
                      borderColor: 'var(--border-subtle)',
                      color: 'var(--accent-metal)'
                    }}
                  >
                    {sourceType === 'none' ? 'INPUT: NO ACQUISITION SOURCE' : `INPUT: ACTIVE STREAM (${(sampleRate / 1000).toFixed(1)} kHz)`}
                  </div>
                </>
              ) : (
                <>
                  {[0, 100, 200, 500, 1000, 1500, 2000].map(f => (
                    <div key={f} className="flex items-center gap-1">
                      <span>{f} Hz</span>
                      <div className="w-px h-2 bg-[var(--border-strong)]" />
                    </div>
                  ))}

                  <div
                    className="absolute right-3 top-1 px-2 py-0.5 rounded text-[9px] font-mono-code font-semibold shadow-xs border"
                    style={{
                      backgroundColor: 'var(--surface-card)',
                      borderColor: 'var(--border-subtle)',
                      color: 'var(--accent-metal)'
                    }}
                  >
                    ACOUSTIC BAND: 0–2000 Hz · WELCH PSD
                  </div>
                </>
              )}
            </div>

            {/* Active Reticle Screen */}
            <div
              className="relative h-64 w-full cursor-crosshair overflow-hidden"
              onClick={viewMode === 'oscilloscope' ? handleMainCanvasClick : undefined}
            >
              {viewMode === 'oscilloscope' ? (
                <>
                  {/* Millimeter Reticle Grid Backdrop */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none" height="100%" width="100%">
                    <defs>
                      <pattern id="millimeter-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--grid-line)" strokeWidth="0.5" opacity="0.6" />
                      </pattern>
                      <pattern id="major-grid" width="100" height="100" patternUnits="userSpaceOnUse">
                        <rect width="100" height="100" fill="url(#millimeter-grid)" />
                        <path d="M 100 0 L 0 0 0 100" fill="none" stroke="var(--grid-line)" strokeWidth="1.2" opacity="0.9" />
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#major-grid)" />
                    <line x1="0" y1="50%" x2="100%" y2="50%" stroke="var(--accent-metal)" strokeWidth="1" strokeDasharray="4,2" opacity="0.7" />
                  </svg>

                  {/* Amplitude Graticule Scale Labels (dBFS) */}
                  <div className="absolute left-2 inset-y-0 flex flex-col justify-between py-2 pointer-events-none font-mono-code text-[9px] text-[var(--on-surface-variant)]/70 font-semibold select-none z-10">
                    <span>+1.00</span>
                    <span>+0.50</span>
                    <span className="text-[var(--accent-metal)] font-bold">0.00FS</span>
                    <span>-0.50</span>
                    <span>-1.00</span>
                  </div>

                  {/* High-Resolution Waveform Canvas */}
                  <canvas ref={mainCanvasRef} className="absolute inset-0 w-full h-full z-10" />

                  {/* Acoustic Playhead (Vertical hairline) */}
                  {sourceType !== 'none' && (
                    <div
                      className="absolute top-0 bottom-0 w-px bg-[var(--accent-oxblood)] z-20 pointer-events-none flex flex-col items-center transition-all duration-75"
                      style={{ left: `${playheadPercent}%` }}
                    >
                      <div className="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[8px] border-t-[var(--accent-oxblood)] -mt-0.5" />
                      <div
                        className="mt-auto mb-1 px-1 rounded shadow-xs font-mono-code text-[9px] font-bold border"
                        style={{
                          backgroundColor: 'var(--surface-card)',
                          borderColor: 'var(--border-subtle)',
                          color: 'var(--accent-oxblood)'
                        }}
                      >
                        {currentTime.toFixed(2)}s
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* FFT Power Scale Labels */}
                  <div className="absolute left-2 inset-y-0 flex flex-col justify-between py-2 pointer-events-none font-mono-code text-[9px] text-[var(--on-surface-variant)]/70 font-semibold select-none z-10">
                    <span>0 dB</span>
                    <span>-20 dB</span>
                    <span>-40 dB</span>
                    <span>-60 dB</span>
                    <span>-80 dB</span>
                  </div>

                  {/* High-Resolution FFT PSD Canvas */}
                  <canvas ref={fftCanvasRef} className="absolute inset-0 w-full h-full z-10" />
                </>
              )}

              {/* Honest empty state overlay when no source is selected */}
              {sourceType === 'none' && (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[var(--bg-canvas)]/80 backdrop-blur-[2px] p-6 text-center select-none">
                  <div className="w-12 h-12 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--accent-oxblood)] mb-3 shadow-xs">
                    <Activity size={24} className="opacity-80" />
                  </div>
                  <h4 className="font-serif-display text-base font-semibold text-[var(--on-surface)] tracking-tight mb-1">
                    No Acquisition Source Active
                  </h4>
                  <p className="font-mono-code text-xs text-[var(--on-surface-variant)] max-w-md leading-relaxed mb-4">
                    No real-time signal has been measured. Select a test specimen or connect hardware to initiate streaming.
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-2 max-w-lg">
                    <div className="px-3 py-1.5 rounded text-[11px] font-mono-code border border-[var(--border-subtle)] bg-[var(--surface-card)] text-[var(--on-surface)] flex items-center gap-1.5 shadow-2xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-metal)]" />
                      <span>Recorded Sessions Drawer (Left)</span>
                    </div>
                    <div className="px-3 py-1.5 rounded text-[11px] font-mono-code border border-[var(--border-subtle)] bg-[var(--surface-card)] text-[var(--on-surface)] flex items-center gap-1.5 shadow-2xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-oxblood)]" />
                      <span>Hardware USB / CDC-ACM Device</span>
                    </div>
                    <div className="px-3 py-1.5 rounded text-[11px] font-mono-code border border-[var(--border-subtle)] bg-[var(--surface-card)] text-[var(--on-surface)] flex items-center gap-1.5 shadow-2xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
                      <span>Virtual Bench Scenarios</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Secondary Track in FFT Mode: Continuous Waterfall Spectrogram Heatmap */}
          {viewMode === 'fft' && (
            <div
              id="spectrogram-track-container"
              className="mt-3 flex flex-col rounded-lg border-t-2 pt-2 transition-all"
              style={{
                borderColor: 'var(--border-subtle)'
              }}
            >
              <div className="flex items-center justify-between pb-1 px-1">
                <div className="flex items-center gap-2">
                  <Layers size={16} className="text-[var(--accent-metal)]" />
                  <span className="font-mono-code text-[11px] text-[var(--on-surface-variant)] font-semibold tracking-wider uppercase">
                    Track S2: Continuous Waterfall Spectrogram Heatmap
                  </span>
                  <span className="font-mono-code text-[10px] text-[var(--border-strong)]">
                    [0–2000 Hz · TIME-FREQUENCY ROLLING STFT]
                  </span>
                </div>
                <div className="text-[var(--on-surface-variant)] font-mono-code text-[10px]">
                  INTENSITY: -85 dBFS (BURGUNDY) → 0 dBFS (GOLD)
                </div>
              </div>

              <div
                className="relative h-28 w-full rounded overflow-hidden shadow-inner border"
                style={{
                  backgroundColor: '#121110',
                  borderColor: 'var(--border-subtle)'
                }}
              >
                <canvas ref={spectrogramCanvasRef} className="absolute inset-0 w-full h-full z-10" />
                <div className="absolute right-2 top-1 font-mono-code text-[9px] text-white/50 select-none pointer-events-none z-20">
                  ▲ 2000 Hz
                </div>
                <div className="absolute right-2 bottom-1 font-mono-code text-[9px] text-white/50 select-none pointer-events-none z-20">
                  ▼ 0 Hz
                </div>
              </div>
            </div>
          )}

          {/* Secondary Track in Oscilloscope Mode: Synchronized Raw Sensor Waveform */}
          {viewMode === 'oscilloscope' && showRaw && (
            <div
              id="raw-track-container"
              className="mt-3 flex flex-col rounded-lg border-t-2 pt-2 transition-all"
              style={{
                borderColor: 'var(--border-subtle)'
              }}
            >
              {/* Raw Track Header & Controls */}
              <div className="flex items-center justify-between pb-1 px-1">
                <div className="flex items-center gap-2">
                  <Radio size={17} className="text-[var(--waveform-raw)]" />
                  <span className="font-mono-code text-[11px] text-[var(--on-surface-variant)] font-semibold tracking-wider uppercase">
                    Track B: Synchronized Raw Sensor Stream
                  </span>
                  <span className="font-mono-code text-[10px] text-[var(--border-strong)]">
                    [UNFILTERED DIRECT STREAM · FLOAT32 APP]
                  </span>
                </div>

                {/* Raw Track Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onToggleListeningTrack(listeningTrack === 'raw' ? 'filtered' : 'raw')}
                    className={`px-2 py-0.5 rounded font-mono-code text-[11px] font-semibold cursor-pointer transition-colors ${
                      listeningTrack === 'raw'
                        ? 'bg-[var(--accent-oxblood)] text-white'
                        : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                    }`}
                  >
                    {listeningTrack === 'raw' ? 'SOLO ACTIVE' : 'AUDITION / SOLO'}
                  </button>

                  <button
                    onClick={() => setRawMuted(!rawMuted)}
                    className={`px-2 py-0.5 rounded font-mono-code text-[11px] flex items-center gap-1 cursor-pointer transition-colors ${
                      rawMuted
                        ? 'bg-[var(--status-danger)]/20 text-[var(--status-danger)]'
                        : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                    }`}
                  >
                    <VolumeX size={13} />
                    <span>MUTE</span>
                  </button>

                  <div className="text-[var(--on-surface-variant)] font-mono-code text-[10px] pl-2">
                    RMS: {liveMetrics && liveMetrics.rms > 0 ? (20 * Math.log10(Math.max(liveMetrics.rms, 1e-4))).toFixed(1) + ' dBFS' : '-- dBFS'}
                  </div>
                </div>
              </div>

              {/* Raw Waveform Viewport (#EAE5D9) */}
              <div
                className="relative h-24 w-full rounded overflow-hidden shadow-inner border cursor-crosshair"
                style={{
                  backgroundColor: 'var(--bg-deep)',
                  borderColor: 'var(--border-subtle)'
                }}
                onClick={handleMainCanvasClick}
              >
                {/* Reticle Grid for Raw Canvas */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" height="100%" width="100%">
                  <rect width="100%" height="100%" fill="url(#millimeter-grid)" />
                  <line x1="0" y1="50%" x2="100%" y2="50%" stroke="var(--border-strong)" strokeWidth="0.8" strokeDasharray="2,2" />
                </svg>

                {/* Unfiltered Raw Waveform Canvas */}
                <canvas ref={rawCanvasRef} className="absolute inset-0 w-full h-full z-10" />

                {/* Synchronized Vertical Playhead Line on Raw Track */}
                <div
                  className="absolute top-0 bottom-0 w-px bg-[var(--accent-oxblood)]/80 z-20 pointer-events-none"
                  style={{ left: `${playheadPercent}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* 4. Audacity-Style Specimen Overview Strip (Entire 15.0s File Timeline) */}
        <div
          className="flex flex-col rounded-xl p-3 shadow-xs gap-1 border"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2 font-mono-code text-[11px]">
              <span className="text-[var(--on-surface)] font-semibold tracking-wider">
                FULL RECORDING OVERVIEW (15.0s ARCHIVE)
              </span>
              <span className="text-[var(--on-surface-variant)]">
                L-44100-RAW
              </span>
            </div>
            <span className="font-mono-code text-[10px] text-[var(--accent-metal)]">
              WINDOW: {formatTime(windowStart)} - {formatTime(windowEnd)} [{visibleWindowSec}s SPAN | {sampleRate} Hz]
            </span>
          </div>

          {/* Mini Overview Waveform Track with Viewport Highlight Rectangle */}
          <div
            className="relative h-12 w-full rounded overflow-hidden shadow-inner border cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-deep)',
              borderColor: 'var(--border-subtle)'
            }}
            onClick={handleOverviewClick}
          >
            {/* Mini Compressed Full Signal Trace Canvas */}
            <canvas ref={overviewCanvasRef} className="absolute inset-0 w-full h-full" />

            {/* Viewport Enclosure Highlight */}
            <div
              className="absolute inset-y-0 bg-[var(--accent-oxblood)]/10 border-r-2 border-[var(--accent-oxblood)] pointer-events-none flex items-center justify-end pr-1 transition-all duration-75"
              style={{
                left: `${viewportStartPercent}%`,
                width: `${viewportWidthPercent}%`
              }}
            >
              <span className="font-mono-code text-[9px] text-[var(--accent-oxblood)] font-bold tracking-wider opacity-80">
                ACTIVE VIEWPORT
              </span>
            </div>

            {/* Overview Playhead Indicator */}
            <div
              className="absolute inset-y-0 w-0.5 bg-[var(--accent-oxblood)] z-30 pointer-events-none shadow-xs"
              style={{ left: `${overviewPlayheadPercent}%` }}
            />
          </div>

          {/* Timeline Ticks (0s, 3s, 6s, 9s, 12s, 15s) */}
          <div className="flex justify-between px-1 font-mono-code text-[9px] text-[var(--on-surface-variant)]">
            <span>00:00.0</span>
            <span>00:03.0</span>
            <span>00:06.0</span>
            <span>00:09.0</span>
            <span>00:12.0</span>
            <span>00:15.0</span>
          </div>
        </div>

        {/* 5. Bottom Tactile Scientific Transport & Control Console */}
        <div
          className="flex flex-wrap items-center justify-between gap-4 rounded-xl p-4 shadow-xs border-t-2 border"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
            borderTopColor: 'var(--accent-metal)'
          }}
        >
          {/* Playback Navigation & Transport Cluster */}
          <div className="flex items-center gap-3">
            {/* Skip to Start Button */}
            <button
              id="skip-start-btn"
              onClick={onRestart}
              title="Skip to Origin [|<]"
              className="w-10 h-10 rounded bg-[var(--surface-muted)] hover:bg-[var(--border-strong)] text-[var(--on-surface)] transition-all flex items-center justify-center active:scale-95 shadow-xs cursor-pointer border border-[var(--border-subtle)]"
            >
              <SkipBack size={18} />
            </button>

            {/* Play / Pause Primary CTA Button */}
            <button
              id="play-pause-btn"
              onClick={onTogglePlay}
              disabled={sourceType === 'none'}
              title={sourceType === 'none' ? 'No active acquisition source' : (isPlaying ? 'Pause stream' : 'Play stream')}
              className={`px-5 h-10 rounded text-white font-semibold flex items-center gap-2 transition-all shadow-md ${
                sourceType === 'none' ? 'opacity-40 cursor-not-allowed' : 'active:scale-95 cursor-pointer'
              }`}
              style={{
                backgroundColor: 'var(--accent-oxblood)'
              }}
            >
              {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
              <span className="font-mono-code text-xs uppercase tracking-wider">
                {isPlaying ? 'PAUSE' : 'PLAY'}
              </span>
            </button>

            {/* Step Forward by Cycle (S1/S2 Interval Jump ~0.8s) */}
            <button
              id="step-cycle-btn"
              onClick={onStepForwardCycle}
              title="Next Cardiac Complex (~0.8s)"
              className="w-10 h-10 rounded bg-[var(--surface-muted)] hover:bg-[var(--border-strong)] text-[var(--on-surface)] transition-all flex items-center justify-center active:scale-95 shadow-xs cursor-pointer border border-[var(--border-subtle)]"
            >
              <FastForward size={18} />
            </button>

            {/* Tabular Monospace High-Legibility Timecode Readout */}
            <div
              className="flex flex-col ml-2 px-3 py-1 rounded border-l-2 border border-[var(--border-subtle)]"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderLeftColor: 'var(--accent-oxblood)'
              }}
            >
              <span className="font-mono-code text-[9px] uppercase tracking-widest text-[var(--on-surface-variant)]">
                POSITION / RUNTIME
              </span>
              <div className="font-mono-code text-base font-semibold tracking-tight text-[var(--on-surface)]">
                <span className="text-[var(--accent-oxblood)]">{formatTime(currentTime)}</span>{' '}
                <span className="text-[var(--border-strong)]">/</span>{' '}
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>

          {/* Acoustic Monitoring Volume & Filter Adjustment Popover Cluster */}
          <div className="flex items-center gap-4">
            {/* Volume Slider Control */}
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded border"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <button
                id="vol-mute-btn"
                onClick={onToggleMute}
                className="text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] transition-colors flex items-center cursor-pointer"
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX size={17} />
                ) : volume < 0.5 ? (
                  <Volume1 size={17} />
                ) : (
                  <Volume2 size={17} />
                )}
              </button>

              <input
                id="volume-slider"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={isMuted ? 0 : volume}
                onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
                className="w-24 accent-[var(--accent-oxblood)] cursor-pointer h-1.5 bg-[var(--border-strong)] rounded"
              />

              <span className="font-mono-code text-xs text-[var(--on-surface)] font-semibold w-8 text-right">
                {Math.round((isMuted ? 0 : volume) * 100)}%
              </span>
            </div>

            {/* Filter Controls Popover Trigger */}
            <div ref={filterDropdownRef} className="relative">
              <button
                id="filter-dropdown-btn"
                onClick={() => setFilterMenuOpen(!filterMenuOpen)}
                className="h-10 px-3 rounded text-[var(--on-surface)] transition-colors flex items-center gap-2 shadow-xs text-xs font-medium border cursor-pointer"
                style={{
                  backgroundColor: 'var(--surface-card)',
                  borderColor: 'var(--border-subtle)'
                }}
              >
                <Sliders size={16} className="text-[var(--accent-metal)]" />
                <span>
                  Filter: <strong className="text-[var(--accent-oxblood)]">{resolvedPreset.title}</strong>
                </span>
                <ChevronDown size={14} className="text-[var(--on-surface-variant)]" />
              </button>

              {/* Filter Selection Flyout Menu */}
              {filterMenuOpen && (
                <div
                  id="filter-menu"
                  className="absolute bottom-full mb-2 left-0 w-80 rounded-lg shadow-xl p-3 z-50 flex flex-col gap-2 border animate-in fade-in zoom-in-95 duration-100"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-strong)'
                  }}
                >
                  <div className="font-mono-code text-[10px] text-[var(--accent-metal)] uppercase tracking-wider border-b pb-1 font-bold" style={{ borderColor: 'var(--border-subtle)' }}>
                    DSP Passband Topologies
                  </div>

                  {(['recommended', 'bell', 'diaphragm', 'extended'] as FilterPreset[]).map(key => {
                    const preset = presetLabels[key];
                    const isSelected = filterPreset === key;
                    return (
                      <button
                        key={key}
                        onClick={() => {
                          onChangeFilterPreset(key);
                          setFilterMenuOpen(false);
                        }}
                        className={`flex flex-col text-left p-2 rounded transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-strong)]'
                            : 'hover:bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`font-mono-code text-xs font-bold ${isSelected ? 'text-[var(--accent-oxblood)]' : ''}`}>
                            {preset.title}
                          </span>
                          {isSelected && <Check size={15} className="text-[var(--accent-oxblood)]" />}
                        </div>
                        <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                          {preset.range}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Session Recording CTA Button */}
            {isRecording ? (
              <button
                id="btn-stop-recording"
                onClick={onStopRecording}
                className="h-10 px-4 rounded text-white font-medium text-xs flex items-center gap-2 cursor-pointer shadow-md active:scale-95 animate-pulse"
                style={{ backgroundColor: 'var(--status-danger)' }}
              >
                <span className="w-2.5 h-2.5 rounded-full bg-white" />
                <span>Stop Recording ({formatTime(recordingElapsedSeconds || 0)})</span>
              </button>
            ) : (
              <button
                id="btn-start-recording"
                onClick={onStartRecording}
                disabled={sourceType === 'none'}
                title={sourceType === 'none' ? 'Cannot record: no active acquisition source' : 'Start Session Recording'}
                className={`h-10 px-4 rounded transition-all flex items-center gap-2 shadow-xs text-xs font-medium border ${
                  sourceType === 'none'
                    ? 'opacity-40 cursor-not-allowed text-[var(--on-surface-variant)]'
                    : 'text-[var(--on-surface)] active:scale-95 cursor-pointer hover:bg-[var(--surface-muted)]'
                }`}
                style={{
                  backgroundColor: 'var(--surface-card)',
                  borderColor: 'var(--border-subtle)'
                }}
              >
                <Disc size={16} className={sourceType === 'none' ? 'text-[var(--on-surface-variant)]' : 'text-[var(--status-danger)]'} />
                <span>Record Session</span>
              </button>
            )}

            {/* Primary Export Action Button */}
            <button
              id="export-audio-btn"
              onClick={onExportFiltered}
              className="h-10 px-4 rounded text-[var(--on-surface)] transition-all flex items-center gap-2 shadow-xs text-xs font-medium active:scale-95 border cursor-pointer hover:bg-[var(--surface-muted)]"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <Download size={16} className="text-[var(--accent-metal)]" />
              <span>Export Filtered Audio...</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
