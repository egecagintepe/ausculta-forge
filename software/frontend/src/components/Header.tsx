import React from 'react';
import {
  Activity,
  Terminal,
  Sun,
  Moon,
  Maximize2,
  Minimize2,
  Minus,
  Square,
  X,
  User
} from 'lucide-react';

interface HeaderProps {
  isDark: boolean;
  onToggleTheme: () => void;
  onToggleDiagnostics: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  backendConnected?: boolean;
  isRecording?: boolean;
  recordingElapsedSeconds?: number;
  recordingSessionId?: string | null;
  onStopRecording?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isDark,
  onToggleTheme,
  onToggleDiagnostics,
  isFullscreen,
  onToggleFullscreen,
  backendConnected = false,
  isRecording = false,
  recordingElapsedSeconds = 0,
  recordingSessionId,
  onStopRecording,
}) => {
  return (
    <header
      id="app-header"
      className="fixed top-0 left-0 right-0 z-50 h-8 flex items-center justify-between px-3 select-none border-b transition-colors"
      style={{
        backgroundColor: 'var(--surface-card)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--on-surface)'
      }}
    >
      {/* Left: Concentric Emblem & Application Title */}
      <div className="flex items-center gap-2">
        {/* Concentric Circle Scientific Emblem (from Stitch Reference) */}
        <div className="w-5 h-5 relative flex items-center justify-center">
          <svg viewBox="0 0 100 100" className="w-5 h-5 text-[var(--accent-metal)]">
            <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="4 3" opacity="0.6" />
            <circle cx="50" cy="50" r="38" fill="none" stroke="var(--accent-oxblood)" strokeWidth="3" />
            <circle cx="50" cy="50" r="26" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.5" />
            <circle cx="50" cy="50" r="14" fill="var(--accent-oxblood)" />
            <circle cx="50" cy="50" r="6" fill="var(--surface-card)" />
            <line x1="50" y1="2" x2="50" y2="14" stroke="currentColor" strokeWidth="3" />
            <line x1="50" y1="86" x2="50" y2="98" stroke="currentColor" strokeWidth="3" />
            <line x1="2" y1="50" x2="14" y2="50" stroke="currentColor" strokeWidth="3" />
            <line x1="86" y1="50" x2="98" y2="50" stroke="currentColor" strokeWidth="3" />
          </svg>
        </div>

        <span className="font-mono-code text-[11px] uppercase tracking-widest font-bold text-[var(--accent-metal)]">
          Acoustic Phonocardiography
        </span>
        <span className="font-sans-ui text-xs font-semibold text-[var(--on-surface)] ml-1">
          Smart Digital Stethoscope
        </span>
      </div>

      {/* Right: Telemetry status, Theme, Diagnostics, Window controls */}
      <div className="flex items-center gap-3">
        {/* Live Recording Indicator */}
        {isRecording && (
          <div className="flex items-center gap-2 px-2.5 py-0.5 rounded bg-[var(--status-danger)]/15 border border-[var(--status-danger)]/40 font-mono-code text-[11px] text-[var(--status-danger)] font-bold shadow-xs">
            <span className="w-2 h-2 rounded-full bg-[var(--status-danger)] animate-ping" />
            <span>REC {(recordingElapsedSeconds || 0).toFixed(1)}s</span>
            {onStopRecording && (
              <button
                onClick={onStopRecording}
                className="underline hover:opacity-80 text-[10px] ml-1 cursor-pointer"
              >
                STOP
              </button>
            )}
          </div>
        )}

        {/* Python Bridge Status Indicator */}
        <div className="hidden sm:flex items-center gap-1.5 font-mono-code text-[11px] text-[var(--on-surface-variant)]">
          <span className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-[var(--status-success)] animate-pulse' : 'bg-[var(--status-warning)]'}`} />
          <span className="tracking-wide">{backendConnected ? 'PYTHON BRIDGE · 4.0 kHz' : 'BRIDGE STANDBY'}</span>
        </div>

        {/* Theme Quick Toggle */}
        <button
          id="btn-header-theme"
          onClick={onToggleTheme}
          title={isDark ? 'Switch to Porcelain Light' : 'Switch to Laboratory Dark'}
          className="p-1 rounded text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
        >
          {isDark ? <Sun size={15} className="text-[var(--status-warning)]" /> : <Moon size={15} />}
        </button>

        {/* Diagnostics Terminal Button */}
        <button
          id="btn-header-diagnostics"
          onClick={onToggleDiagnostics}
          title="Diagnostics Terminal (Ctrl+Shift+D)"
          className="hidden sm:flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono-code bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] border border-[var(--border-subtle)] transition-colors cursor-pointer"
        >
          <Terminal size={12} className="text-[var(--accent-metal)]" />
          <span>^⇧D</span>
        </button>

        {/* User avatar indicator */}
        <div className="w-6 h-6 rounded-full bg-[var(--accent-oxblood)] flex items-center justify-center text-white text-[11px]">
          <User size={13} />
        </div>

        {/* Desktop window controls */}
        <div className="flex items-center ml-1 border-l border-[var(--border-subtle)] pl-1">
          <button
            onClick={onToggleFullscreen}
            title={isFullscreen ? 'Restore Window (F11)' : 'Maximize Window (F11)'}
            className="w-7 h-7 flex items-center justify-center text-[var(--on-surface-variant)] hover:bg-[var(--surface-muted)] hover:text-[var(--on-surface)] transition-colors"
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Square size={12} />}
          </button>
          <button
            onClick={() => {}}
            title="Minimize"
            className="w-7 h-7 flex items-center justify-center text-[var(--on-surface-variant)] hover:bg-[var(--surface-muted)] hover:text-[var(--on-surface)] transition-colors"
          >
            <Minus size={13} />
          </button>
          <button
            onClick={() => {}}
            title="Close Application"
            className="w-7 h-7 flex items-center justify-center text-[var(--on-surface-variant)] hover:bg-[var(--status-danger)] hover:text-white transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </header>
  );
};
