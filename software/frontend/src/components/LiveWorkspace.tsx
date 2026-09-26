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
  HeartSoundMetadata
} from '../types';

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
}) => {
  const [viewMode, setViewMode] = useState<'oscilloscope' | 'fft'>('oscilloscope');
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const [rawMuted, setRawMuted] = useState(false);
  const filterDropdownRef = useRef<HTMLDivElement>(null);
  const mainCanvasRef = useRef<HTMLCanvasElement>(null);
  const rawCanvasRef = useRef<HTMLCanvasElement>(null);
  const overviewCanvasRef = useRef<HTMLCanvasElement>(null);

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

    if (sourceType !== 'none' && filteredData.length > 0 && sampleRate > 0) {
      const startIndex = Math.max(0, Math.floor(windowStart * sampleRate));
      const endIndex = Math.min(filteredData.length, Math.ceil(windowEnd * sampleRate));
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
  }, [filteredData, sampleRate, windowStart, windowEnd, isDark, visibleWindowSec, sourceType]);

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

    if (sourceType !== 'none' && rawData.length > 0 && sampleRate > 0) {
      const startIndex = Math.max(0, Math.floor(windowStart * sampleRate));
      const endIndex = Math.min(rawData.length, Math.ceil(windowEnd * sampleRate));
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
  }, [rawData, sampleRate, windowStart, windowEnd, isDark, showRaw, visibleWindowSec, sourceType]);

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
                    {activeMetadata?.filename || 'normal_sample_01.wav'}
                  </span>
                  <span className="bg-[var(--surface-muted)] text-[var(--on-surface-variant)] font-mono-code text-[10px] px-2 py-0.5 rounded font-semibold border border-[var(--border-subtle)]">
                    {sourceType === 'device' ? 'HARDWARE TELEMETRY' : 'FILE AUDITION'}
                  </span>
                </div>
                <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] uppercase tracking-wider">
                  PCM STREAM · {(sampleRate / 1000).toFixed(1)} KHZ · FLOAT32 APP · LIVE BENCH
                </span>
              </div>
            </div>

            <div className="h-6 w-px bg-[var(--border-subtle)] hidden sm:block mx-1" />

            {/* Signal / Stream Quality Badge */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded ${
              streamQuality?.is_healthy !== false
                ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/25'
                : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border border-[var(--status-warning)]/25'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                streamQuality?.is_healthy !== false ? 'bg-[var(--status-success)]' : 'bg-[var(--status-warning)]'
              }`} />
              <span className="font-mono-code text-[11px] font-semibold tracking-wide">
                {backendConnected
                  ? `STREAM: ${streamQuality?.is_healthy !== false ? 'OPTIMAL' : 'DEGRADED'} (${streamQuality?.dropped_blocks || 0} DROPS)`
                  : (activeMetadata?.quality.score != null
                      ? `QUALITY: ${activeMetadata.quality.rating.toUpperCase()} (${activeMetadata.quality.score}%)`
                      : `SOURCE: ${activeMetadata?.quality.message || 'SYNTHETIC BENCH'}`)}
              </span>
            </div>

            {/* Filter Preset Chip */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-subtle)]">
              <Sliders size={13} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] tracking-wide">
                FILTER: {filterPreset === 'recommended' ? 'NARROW 20–200 Hz (DEV PRESET)' : presetLabels[filterPreset].title.toUpperCase()}
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
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-oxblood)]" />
                <span className="font-mono-code text-[11px] text-[var(--on-surface)] font-bold tracking-wider uppercase">
                  Track A: Processed Phonocardiogram (PCG)
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 font-mono-code text-[10px]">
                <span className="px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--accent-oxblood)] font-bold border border-[var(--border-subtle)]">
                  {presetLabels[filterPreset].title} ({presetLabels[filterPreset].range})
                </span>
                {liveMetrics && (
                  <span className="text-[var(--on-surface-variant)] hidden md:inline">
                    RMS: <strong className="text-[var(--on-surface)]">{liveMetrics.rms.toFixed(4)}</strong> · PEAK: <strong className="text-[var(--on-surface)]">{liveMetrics.peak.toFixed(4)}</strong> · CREST: <strong className="text-[var(--on-surface)]">{liveMetrics.crest_factor.toFixed(2)}</strong>
                  </span>
                )}
                {streamQuality && (
                  <span className={`px-2 py-0.5 rounded font-mono-code text-[10px] font-semibold border ${
                    streamQuality.is_healthy
                      ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                      : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border-[var(--status-warning)]/30'
                  }`}>
                    {streamQuality.is_healthy ? 'STREAM HEALTHY' : `${streamQuality.dropped_blocks} DROPPED`}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
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
            </div>
          </div>

          {/* Waveform Reticle Area (Recessed Tray #EAE5D9) */}
          <div
            className="relative w-full rounded-lg overflow-hidden flex flex-col shadow-inner border"
            style={{
              backgroundColor: 'var(--bg-deep)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            {/* Timecode Top Axis Ruler */}
            <div
              className="h-6 w-full flex items-center justify-between px-6 font-mono-code text-[10px] tracking-wider select-none relative border-b"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--on-surface-variant)'
              }}
            >
              {[0, 2, 4, 6, 8, 10].map(s => (
                <div key={s} className="flex items-center gap-1">
                  <span>{s}.0s</span>
                  <div className="w-px h-2 bg-[var(--border-strong)]" />
                </div>
              ))}

              {/* Metric Floating Stamp */}
              <div
                className="absolute right-3 top-1 px-2 py-0.5 rounded text-[9px] font-mono-code font-semibold shadow-xs border"
                style={{
                  backgroundColor: 'var(--surface-card)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--accent-metal)'
                }}
              >
                {sourceType === 'none' ? 'INPUT: NO ACQUISITION SOURCE' : 'INPUT: ACTIVE STREAM (4.0 kHz)'}
              </div>
            </div>

            {/* Active Reticle Waveform Screen */}
            <div
              className="relative h-64 w-full cursor-crosshair overflow-hidden"
              onClick={handleMainCanvasClick}
            >
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

              {/* Empty state overlay when no source is selected */}
              {sourceType === 'none' && (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[var(--bg-canvas)]/65 backdrop-blur-[2px] p-6 text-center select-none pointer-events-none">
                  <div className="w-10 h-10 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--accent-metal)] mb-3 shadow-xs">
                    <Activity size={20} className="opacity-70" />
                  </div>
                  <h4 className="font-serif-display text-sm font-semibold text-[var(--on-surface)] tracking-tight mb-1">
                    No live acquisition source
                  </h4>
                  <p className="font-mono-code text-[11px] text-[var(--on-surface-variant)] max-w-sm leading-relaxed">
                    Connect an AuscultaForge device<br />or select an offline recorded session.
                  </p>
                </div>
              )}

              {/* Frequency Scrubbing Selection Bounding Region (when source active) */}
              {sourceType !== 'none' && (
                <div className="absolute top-0 bottom-0 left-[80%] w-[12%] bg-[var(--selection-window)]/35 border-x border-dashed border-[var(--accent-oxblood)]/60 pointer-events-none z-10">
                  <span className="absolute top-1 left-1.5 font-mono-code text-[9px] text-[var(--accent-oxblood)] font-bold tracking-wider">
                    Δt: 1.20 s
                  </span>
                </div>
              )}

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
            </div>
          </div>

          {/* 3. Secondary Track: Synchronized Raw Sensor Waveform (#93897C) */}
          {showRaw && (
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
                    RMS: {liveMetrics ? (20 * Math.log10(Math.max(liveMetrics.rms, 1e-4))).toFixed(1) + ' dBFS' : '-24.6 dBFS'}
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
                  Filter: <strong className="text-[var(--accent-oxblood)]">{presetLabels[filterPreset].title}</strong>
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
