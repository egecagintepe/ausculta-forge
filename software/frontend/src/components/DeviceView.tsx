import React from 'react';
import {
  Stethoscope,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Radio,
  Sliders,
  Play
} from 'lucide-react';
import { StethoscopeDevice } from '../types';

interface DeviceViewProps {
  deviceState: StethoscopeDevice;
  onDetectDevice: () => void;
  onDisconnectDevice: () => void;
  onSimulateInterruption: () => void;
  onUseDevice: () => void;
  isConnecting: boolean;
  isDark: boolean;
  backendConnected: boolean;
  activeSourceName: string;
  onSelectMockSource: () => void;
}

export const DeviceView: React.FC<DeviceViewProps> = ({
  deviceState,
  onDetectDevice,
  onDisconnectDevice,
  onSimulateInterruption,
  onUseDevice,
  isConnecting,
  backendConnected,
  activeSourceName,
  onSelectMockSource,
}) => {
  return (
    <div
      id="device-view"
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
              <span>Hardware Channel &amp; Ingestion Mode</span>
              <span>•</span>
              <span>ESP32-S3 Phase-1</span>
            </div>
            <h1 className="font-serif-display text-2xl font-semibold text-[var(--on-surface)] tracking-tight">
              Acoustic Ingestion &amp; Hardware Sources
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-xl">
              Configure active stream ingestion, inspect Python bridge connectivity, and review Phase-1 ESP32-S3 Native USB hardware status.
            </p>
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-mono-code text-[11px] shadow-xs ${
              backendConnected
                ? 'border-[var(--status-success)]/40 bg-[var(--status-success)]/10 text-[var(--status-success)] font-bold'
                : 'border-[var(--status-warning)]/40 bg-[var(--status-warning)]/10 text-[var(--status-warning)]'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-[var(--status-success)] animate-pulse' : 'bg-[var(--status-warning)]'}`} />
            <span>{backendConnected ? 'Bridge Connected (4 kHz)' : 'Bridge Disconnected'}</span>
          </div>
        </div>

        {/* Source Mode Section */}
        <div className="flex flex-col gap-3">
          <span className="font-mono-code text-xs uppercase tracking-wider text-[var(--accent-metal)] font-bold">
            Select Active Ingestion Mode
          </span>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Mode A: Simulation / Replay Mode (ACTIVE) */}
            <div
              className="rounded-xl border p-5 flex flex-col justify-between gap-4 shadow-xs relative overflow-hidden transition-all"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--accent-oxblood)'
              }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono-code text-[10px] uppercase font-bold text-[var(--accent-oxblood)]">
                    <Radio size={14} />
                    <span>Mode 1: Simulation / Python Replay</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/30">
                    ACTIVE INGESTION
                  </span>
                </div>

                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  Python Signal Engine &amp; Replay
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  Real-time DSP stream powered by <code className="font-mono-code text-[11px]">pcg_core</code>.
                  Streams synthetic physiological PCG, benchmark WAV recordings, or replayed acquisition sessions.
                </p>

                <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-1 font-mono-code text-xs mt-1">
                  <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">CURRENT SOURCE:</span>
                  <span className="font-semibold text-[var(--on-surface)]">{activeSourceName}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)]">
                <button
                  onClick={onSelectMockSource}
                  className="px-3 py-1.5 rounded-lg border font-mono-code text-xs font-semibold text-[var(--accent-oxblood)] border-[var(--accent-oxblood)] hover:bg-[var(--accent-oxblood)]/10 transition-colors cursor-pointer"
                >
                  Load Synthetic S1/S2 Stream
                </button>
                <button
                  onClick={onUseDevice}
                  className="px-3 py-1.5 rounded-lg font-mono-code text-xs font-semibold text-white bg-[var(--accent-oxblood)] flex items-center gap-1 shadow-xs cursor-pointer"
                >
                  <span>Open Workspace</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </div>

            {/* Mode B: Native USB Hardware (COMING SOON) */}
            <div
              className="rounded-xl border p-5 flex flex-col justify-between gap-4 shadow-xs relative overflow-hidden transition-all opacity-85"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border-strong)'
              }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono-code text-[10px] uppercase font-bold text-[var(--accent-metal)]">
                    <Cpu size={14} />
                    <span>Mode 2: Native USB Transducer</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/30">
                    COMING SOON · PHASE 1
                  </span>
                </div>

                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  ESP32-S3 Wired Native USB
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  Direct physical streaming from the ESP32-S3-WROOM acquisition dev board via wired Native USB (I2S MEMS mic at ~4 kHz target).
                </p>

                <div className="p-2.5 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)] flex flex-col gap-1 font-mono-code text-xs mt-1">
                  <span className="text-[10px] text-[var(--accent-metal)] uppercase">TEAM DECISION (2026-09-26):</span>
                  <span className="text-[var(--on-surface-variant)] text-[11px] leading-snug">
                    Baud rate and legacy serial assumptions removed. Transport is finalized as Native USB; wire protocol framing benchmarking in progress under Sprint 1.
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)]">
                <button
                  disabled
                  className="px-3.5 py-1.5 rounded-lg border font-mono-code text-xs font-medium border-[var(--border-strong)] text-[var(--on-surface-variant)] opacity-50 cursor-not-allowed"
                >
                  Native USB Driver (Pending Bench Gate)
                </button>
                <span className="font-mono-code text-[10px] text-[var(--accent-metal)]">
                  October Milestone Gate
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Telemetry and Protocol Status */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck size={16} className="text-[var(--status-success)]" />
              <h3 className="font-mono-code text-xs font-bold uppercase tracking-wider text-[var(--on-surface)]">
                Active Bridge Telemetry Parameters
              </h3>
            </div>
            <span className="font-mono-code text-[10px] text-[var(--accent-metal)]">
              Protocol v1.0 (JSON Chunks)
            </span>
          </div>

          <div
            className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 font-mono-code text-xs"
          >
            <div className="flex flex-col p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">TRANSPORT</span>
              <span className="font-semibold text-[var(--on-surface)]">Local WebSocket</span>
            </div>
            <div className="flex flex-col p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">SAMPLE RATE</span>
              <span className="font-semibold text-[var(--on-surface)]">4.0 kHz · 32-BIT FP</span>
            </div>
            <div className="flex flex-col p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">FRAME SIZE</span>
              <span className="font-semibold text-[var(--on-surface)]">128 samples (~32 ms)</span>
            </div>
            <div className="flex flex-col p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">STREAM STATUS</span>
              <span className="font-semibold text-[var(--status-success)]">
                {backendConnected ? 'Synchronized' : 'Standby'}
              </span>
            </div>
          </div>
        </div>

        {/* Fault Tolerance and Diagnostic Testing */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-3 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
            <Zap size={15} className="text-[var(--accent-metal)]" />
            <span>Connection Resilience &amp; Fault Simulation</span>
          </div>

          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            Verify application reconnect logic and error recovery upon transient bridge disconnection.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              onClick={onSimulateInterruption}
              className="px-3.5 py-1.5 rounded-lg border font-mono-code text-xs font-medium border-[var(--status-warning)] text-[var(--status-warning)] hover:bg-[var(--status-warning)]/10 transition-colors cursor-pointer"
            >
              Simulate Connection Drop &amp; Auto-Reconnect
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
