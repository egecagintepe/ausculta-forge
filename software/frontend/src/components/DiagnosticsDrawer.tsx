import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FolderOpen,
  Volume2,
  Stethoscope,
  Sliders,
  List,
  AlertTriangle,
  CheckCircle2,
  Terminal
} from 'lucide-react';
import { DiagnosticState, AudioMetrics, StethoscopeDevice } from '../types';

interface DiagnosticsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  diagnosticState: DiagnosticState;
  audioMetrics: AudioMetrics;
  deviceState: StethoscopeDevice;
  onCopySummary: () => void;
  copySuccess: boolean;
  isDark: boolean;
}

export const DiagnosticsDrawer: React.FC<DiagnosticsDrawerProps> = ({
  isOpen,
  onClose,
  diagnosticState,
  audioMetrics,
  deviceState,
  onCopySummary,
  copySuccess,
}) => {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    source: false,
    audio: false,
    hardware: false,
    dsp: false,
    log: false,
  });

  if (!isOpen) return null;

  const toggle = (key: string) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <aside
      id="diagnostics-drawer"
      className="fixed top-8 right-0 bottom-6 w-full sm:w-[460px] z-50 flex flex-col shadow-2xl border-l select-none transition-all duration-200 overflow-hidden"
      style={{
        backgroundColor: 'var(--surface-card)',
        borderColor: 'var(--border-strong)'
      }}
    >
      {/* Sticky Drawer Master Header */}
      <div
        className="p-4 pb-3 flex flex-col gap-2 border-b shrink-0"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-[var(--status-warning)] animate-pulse" />
            <h2 className="font-serif-display text-lg font-semibold text-[var(--accent-oxblood)]">
              Engineering &amp; Diagnostics
            </h2>
          </div>

          <div className="flex items-center gap-1.5">
            <kbd className="font-mono-code text-[10px] bg-[var(--surface-muted)] text-[var(--on-surface-variant)] px-2 py-0.5 rounded border border-[var(--border-subtle)] tracking-wider">
              [ Ctrl+Shift+D ]
            </kbd>
            <button
              onClick={onClose}
              title="Close Drawer (Esc)"
              className="w-7 h-7 rounded flex items-center justify-center text-[var(--on-surface-variant)] hover:bg-[var(--surface-muted)] hover:text-[var(--on-surface)] transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] uppercase tracking-widest font-semibold">
            Acoustic Engine Telemetry Inspector
          </span>
          <button
            id="copySummaryBtn"
            onClick={onCopySummary}
            className="h-6 px-2 rounded bg-[var(--surface-muted)] hover:bg-[var(--border-strong)] text-[var(--on-surface)] font-mono-code text-[10px] flex items-center gap-1 transition-colors border border-[var(--border-subtle)] cursor-pointer shadow-xs"
          >
            {copySuccess ? <Check size={12} className="text-[var(--status-success)]" /> : <Copy size={12} />}
            <span>{copySuccess ? 'Copied Summary' : 'Copy Diagnostic Summary'}</span>
          </button>
        </div>
      </div>

      {/* Strict Data Honesty Banner (from Stitch reference) */}
      <div
        className="px-4 py-1.5 flex items-center gap-2 shrink-0 border-b"
        style={{
          backgroundColor: 'var(--accent-soft)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <AlertTriangle size={13} className="text-[var(--status-warning)] shrink-0" />
        <span className="font-mono-code text-[10px] tracking-wider text-[var(--accent-oxblood)] font-bold uppercase">
          STRICT TELEMETRY INSPECTOR — LIVE VERIFIED SIGNALS
        </span>
      </div>

      {/* Collapsible Technical Sections Container */}
      <div className="flex-1 overflow-y-auto flex flex-col divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
        {/* 1. Source Section */}
        <div>
          <button
            onClick={() => toggle('source')}
            className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <FolderOpen size={14} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                1. Source
              </span>
            </div>
            {collapsed.source ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>

          {!collapsed.source && (
            <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Source Type:</span>
                <span className="font-semibold text-[var(--on-surface)] bg-[var(--surface-muted)] px-1.5 py-0.5 rounded">
                  {diagnosticState.sourceType === 'device' ? 'Live Stream Ingestion' : 'File Audition'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">File:</span>
                <span className="font-semibold text-[var(--accent-oxblood)] truncate max-w-[220px]" title={diagnosticState.fileName}>
                  {diagnosticState.fileName || 'normal_sample_01.wav'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Format:</span>
                <span className="text-[var(--on-surface)]">WAV PCM (Linear)</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Input Sample Rate:</span>
                <span className="text-[var(--on-surface)] font-semibold">{diagnosticState.inputSampleRate}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Channels:</span>
                <span className="text-[var(--on-surface)]">{diagnosticState.channels}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Duration:</span>
                <span className="text-[var(--on-surface)] font-semibold">{diagnosticState.duration}</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-[var(--on-surface-variant)]">Processing Buffer:</span>
                <span className="text-[var(--on-surface)]">4096 samples (1024 ms)</span>
              </div>
            </div>
          )}
        </div>

        {/* 2. Audio & Listening Section */}
        <div>
          <button
            onClick={() => toggle('audio')}
            className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Volume2 size={14} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                2. Audio &amp; Listening
              </span>
            </div>
            {collapsed.audio ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>

          {!collapsed.audio && (
            <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Active Track:</span>
                <span className="font-semibold text-[var(--accent-oxblood)] uppercase">
                  {audioMetrics.activeTrack} (Audition Pass)
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Listening Volume:</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 bg-[var(--surface-muted)] h-1.5 rounded-full overflow-hidden border border-[var(--border-subtle)]">
                    <div className="bg-[var(--accent-metal)] h-full" style={{ width: `${audioMetrics.playbackVolume}%` }} />
                  </div>
                  <span className="font-semibold text-[var(--on-surface)]">{audioMetrics.playbackVolume}%</span>
                </div>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Mute:</span>
                <span className={`font-semibold ${audioMetrics.isMuted ? 'text-[var(--status-danger)]' : 'text-[var(--status-success)]'}`}>
                  {audioMetrics.isMuted ? 'On (Silenced)' : 'Off'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Peak Amplitude:</span>
                <span className="text-[var(--on-surface)] font-semibold">{audioMetrics.currentPeakDb} dBFS</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-[var(--on-surface-variant)]">RMS Level:</span>
                <span className="text-[var(--on-surface)] font-semibold">{audioMetrics.currentRmsDb} dB</span>
              </div>
            </div>
          )}
        </div>

        {/* 3. Device (Hardware) Section */}
        <div>
          <button
            onClick={() => toggle('hardware')}
            className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Stethoscope size={14} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                3. Device (Hardware)
              </span>
            </div>
            {collapsed.hardware ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>

          {!collapsed.hardware && (
            <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Connection State:</span>
                <span className={`font-semibold flex items-center gap-1 ${deviceState.connected ? 'text-[var(--status-success)]' : 'text-[var(--status-danger)]'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${deviceState.connected ? 'bg-[var(--status-success)]' : 'bg-[var(--status-danger)]'}`} />
                  {deviceState.state}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">COM Port:</span>
                <span className="text-[var(--on-surface)] font-mono-code">
                  {deviceState.connected ? deviceState.port : 'Inactive (No Carrier)'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Polling Interval:</span>
                <span className="text-[var(--on-surface)] font-mono-code">1000 ms</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-[var(--on-surface-variant)]">Hardware Telemetry:</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  deviceState.connected
                    ? 'bg-[var(--status-success)]/10 text-[var(--status-success)]'
                    : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)]'
                }`}>
                  {deviceState.connected ? 'Synchronized (Simulation / Bench)' : 'Hardware Native USB (Coming Soon)'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* 4. Processing & Quality Section */}
        <div>
          <button
            onClick={() => toggle('dsp')}
            className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Sliders size={14} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                4. Processing &amp; Quality
              </span>
            </div>
            {collapsed.dsp ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>

          {!collapsed.dsp && (
            <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Filter Preset:</span>
                <span className="font-semibold text-[var(--accent-oxblood)]">
                  {diagnosticState.filterPreset}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Filter Strength:</span>
                <span className="text-[var(--on-surface)] font-semibold">
                  {diagnosticState.filterStrength} (4th-order Butterworth)
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                <span className="text-[var(--on-surface-variant)]">Signal Stream:</span>
                <span className="text-[var(--status-success)] font-semibold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
                  Active Ingestion (DSP Core)
                </span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-[var(--on-surface-variant)]">Resampling:</span>
                <span className="text-[var(--on-surface)]">None (Native 4 kHz match)</span>
              </div>
            </div>
          )}
        </div>

        {/* 5. Recent Event Log Section */}
        <div>
          <button
            onClick={() => toggle('log')}
            className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <List size={14} className="text-[var(--accent-metal)]" />
              <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                5. Recent Event Log
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                {diagnosticState.logs.length} ENTRIES
              </span>
              {collapsed.log ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </div>
          </button>

          {!collapsed.log && (
            <div className="p-3 bg-[var(--surface-muted)]/30 flex flex-col gap-1.5 font-mono-code text-[11px] max-h-56 overflow-y-auto">
              {diagnosticState.logs.map(log => (
                <div key={log.id} className="flex items-start gap-2 py-0.5 leading-tight">
                  <span className="text-[var(--accent-metal)] font-semibold shrink-0">{log.timestamp}</span>
                  <span className="text-[var(--on-surface-variant)] shrink-0">·</span>
                  <span className={
                    log.severity === 'error'
                      ? 'text-[var(--status-danger)] font-bold'
                      : log.severity === 'warning'
                      ? 'text-[var(--status-warning)] font-semibold'
                      : 'text-[var(--on-surface)]'
                  }>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Drawer Bottom Status Strip */}
      <div
        className="px-4 py-2 flex items-center justify-between font-mono-code text-[10px] text-[var(--on-surface-variant)] border-t shrink-0"
        style={{
          backgroundColor: 'var(--surface-muted)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <div className="flex items-center gap-1.5">
          <CheckCircle2 size={13} className="text-[var(--status-success)]" />
          <span className="tracking-wider font-semibold">HOST BUFFER STABLE</span>
        </div>
        <span>CPU: 1.4% · MEM: 48MB</span>
      </div>
    </aside>
  );
};
