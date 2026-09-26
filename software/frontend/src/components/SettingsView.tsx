import React from 'react';
import {
  Sun,
  Moon,
  Sliders,
  Volume2,
  Activity,
  Terminal,
  Trash2,
  Check,
  ShieldCheck
} from 'lucide-react';
import { FilterPreset, FilterStrength } from '../types';

interface SettingsViewProps {
  isDark: boolean;
  onToggleTheme: () => void;
  volume: number;
  onVolumeChange: (vol: number) => void;
  defaultWindowSec: number;
  onChangeDefaultWindowSec: (sec: number) => void;
  defaultFilterPreset: FilterPreset;
  onChangeDefaultFilterPreset: (preset: FilterPreset) => void;
  onToggleDiagnostics: () => void;
  onClearLogs: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  isDark,
  onToggleTheme,
  volume,
  onVolumeChange,
  defaultWindowSec,
  onChangeDefaultWindowSec,
  defaultFilterPreset,
  onChangeDefaultFilterPreset,
  onToggleDiagnostics,
  onClearLogs,
}) => {
  return (
    <div
      id="settings-view"
      className="flex-1 flex flex-col h-full overflow-y-auto px-6 py-5 select-none transition-colors"
      style={{
        backgroundColor: 'var(--bg-canvas)'
      }}
    >
      <div className="max-w-4xl mx-auto w-full flex flex-col gap-6 pb-8">
        {/* Header Section */}
        <div
          className="pb-4 border-b flex items-start justify-between"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 font-mono-code text-[11px] uppercase tracking-widest text-[var(--accent-metal)] font-semibold">
              <span>Instrument Configuration</span>
              <span>•</span>
              <span>DSP &amp; Calibration</span>
            </div>
            <h1 className="font-serif-display text-2xl font-semibold text-[var(--on-surface)] tracking-tight">
              Settings &amp; Calibration Matrix
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-xl">
              Configure instrument appearance, default acoustic bandpass passbands, waveform temporal windowing, and audio output.
            </p>
          </div>
        </div>

        {/* Settings Cards Container */}
        <div className="flex flex-col gap-5">
          {/* 1. Appearance / Theme */}
          <div
            className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
              <Sun size={15} className="text-[var(--accent-metal)]" />
              <span>Illumination &amp; Palette Theme</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => isDark && onToggleTheme()}
                className={`p-4 rounded-xl border text-left flex flex-col gap-2 transition-all cursor-pointer ${
                  !isDark
                    ? 'border-[var(--accent-oxblood)] bg-[var(--accent-soft)]/25 shadow-xs ring-1 ring-[var(--accent-oxblood)]'
                    : 'border-[var(--border-subtle)] hover:border-[var(--border-strong)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                    Porcelain Light (Primary Instrument Identity)
                  </span>
                  {!isDark && <Check size={16} className="text-[var(--accent-oxblood)]" />}
                </div>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  Warm sepia rag canvas (#F3F0E8), aged porcelain cards (#FBFAF6), patinated brass scales, and rich oxblood (#7A3842) acoustic traces.
                </p>
              </button>

              <button
                onClick={() => !isDark && onToggleTheme()}
                className={`p-4 rounded-xl border text-left flex flex-col gap-2 transition-all cursor-pointer ${
                  isDark
                    ? 'border-[var(--accent-oxblood)] bg-[var(--accent-soft)]/25 shadow-xs ring-1 ring-[var(--accent-oxblood)]'
                    : 'border-[var(--border-subtle)] hover:border-[var(--border-strong)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                    Charcoal Laboratory Dark
                  </span>
                  {isDark && <Check size={16} className="text-[var(--accent-oxblood)]" />}
                </div>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  Subdued dark equipment canvas (#1B1A18), softened rose traces (#D19AA3), and anti-glare laboratory contrast for night shifts.
                </p>
              </button>
            </div>
          </div>

          {/* 2. Waveform Window & Time Window */}
          <div
            className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
              <Activity size={15} className="text-[var(--accent-metal)]" />
              <span>Waveform Display &amp; Temporal Window</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b text-xs" style={{ borderColor: 'var(--border-subtle)' }}>
              <div>
                <div className="font-medium text-[var(--on-surface)]">Default Reticle Visible Span</div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">Horizontal window span displayed across the oscilloscope screen</div>
              </div>

              <div className="flex items-center bg-[var(--surface-muted)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
                {[5, 10, 15].map(sec => (
                  <button
                    key={sec}
                    onClick={() => onChangeDefaultWindowSec(sec)}
                    className={`px-3 py-1 rounded font-mono-code text-xs font-semibold cursor-pointer transition-colors ${
                      defaultWindowSec === sec
                        ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] shadow-xs'
                        : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                    }`}
                  >
                    {sec}s
                  </button>
                ))}
              </div>
            </div>

            {/* Default Filter Preset */}
            <div className="flex items-center justify-between py-1 text-xs">
              <div>
                <div className="font-medium text-[var(--on-surface)]">Default DSP Passband Topology</div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">Acoustic isolation band for phonocardiographic inspection</div>
              </div>

              <select
                value={defaultFilterPreset}
                onChange={(e) => onChangeDefaultFilterPreset(e.target.value as FilterPreset)}
                className="bg-[var(--surface-muted)] text-[var(--on-surface)] font-mono-code text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] cursor-pointer outline-none focus:border-[var(--accent-oxblood)]"
              >
                <option value="recommended">Narrow 20–200 Hz (Development Preset)</option>
                <option value="bell">Bell Acoustic Mode [20-100 Hz]</option>
                <option value="diaphragm">Diaphragm Modality [100-500 Hz]</option>
                <option value="extended">Extended Unfiltered Feed [10-2000 Hz]</option>
              </select>
            </div>
          </div>

          {/* 3. Audio Monitoring Output */}
          <div
            className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
              <Volume2 size={15} className="text-[var(--accent-metal)]" />
              <span>Acoustic Monitoring DAC Output</span>
            </div>

            <div className="flex items-center justify-between py-1 text-xs">
              <div>
                <div className="font-medium text-[var(--on-surface)]">Acoustic Audition Volume</div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">DAC headphone audition level (RMS gain scaled)</div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={volume}
                  onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
                  className="w-32 accent-[var(--accent-oxblood)] h-1.5 bg-[var(--border-strong)] rounded cursor-pointer"
                />
                <span className="font-mono-code text-xs text-[var(--on-surface)] font-bold w-10 text-right">
                  {Math.round(volume * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* 4. Engineering & Diagnostics Shortcut */}
          <div
            className="rounded-xl border p-5 flex items-center justify-between gap-4 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <div className="flex flex-col gap-0.5">
              <div className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase flex items-center gap-1.5">
                <Terminal size={14} className="text-[var(--accent-metal)]" />
                <span>Diagnostics &amp; Real-Time Telemetry</span>
              </div>
              <div className="text-xs text-[var(--on-surface-variant)]">
                Inspect DSP buffers, peak/RMS amplitude, serial transport frames, and chronological event logs.
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={onClearLogs}
                title="Clear chronological log history"
                className="px-3 py-1.5 rounded-lg border font-mono-code text-xs border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--status-danger)] transition-colors flex items-center gap-1 cursor-pointer"
              >
                <Trash2 size={13} />
                <span>Clear Logs</span>
              </button>

              <button
                onClick={onToggleDiagnostics}
                className="px-3.5 py-1.5 rounded-lg border font-medium text-xs border-[var(--accent-oxblood)] text-[var(--accent-oxblood)] hover:bg-[var(--accent-soft)] transition-colors cursor-pointer shadow-xs"
              >
                Open Terminal (Ctrl+Shift+D)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
