import React from 'react';
import {
  ArrowRight,
  ShieldCheck,
  Zap,
  Cpu,
  Radio,
  FileAudio,
  Disc,
  Clock,
  ExternalLink
} from 'lucide-react';
import { StethoscopeDevice, DeviceRuntimeState, AudioSourceType } from '../types';

interface DeviceViewProps {
  deviceState: StethoscopeDevice;
  deviceRuntimeState?: DeviceRuntimeState | null;
  onDetectDevice: () => void;
  onDisconnectDevice: () => void;
  onSimulateInterruption: () => void;
  onUseDevice: () => void;
  isConnecting: boolean;
  isDark: boolean;
  backendConnected: boolean;
  activeSourceName: string;
  sourceType: AudioSourceType;
  onSelectMockSource: () => void;
  onNavigateToSamples?: () => void;
}

export const DeviceView: React.FC<DeviceViewProps> = ({
  deviceState,
  deviceRuntimeState,
  onSimulateInterruption,
  onUseDevice,
  backendConnected,
  activeSourceName,
  sourceType,
  onSelectMockSource,
  onNavigateToSamples,
}) => {
  const isHardwareConnected = deviceRuntimeState?.connected ?? false;
  const hardwareLifecycle = deviceRuntimeState?.state ?? 'absent';

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
              Hardware Channel &amp; Ingestion Runtime
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-xl">
              Truthful ESP32-S3 Native USB hardware lifecycle, discovery telemetry, and explicit offline engineering replay modes.
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

        {/* SECTION 1: LIVE HARDWARE (Truthful, non-fabricated) */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-mono-code text-xs uppercase tracking-wider text-[var(--accent-oxblood)] font-bold flex items-center gap-1.5">
              <Cpu size={14} />
              <span>Live Hardware</span>
            </span>
            <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
              Phase-1 Physical Transport
            </span>
          </div>

          <div
            className="rounded-xl border p-5 flex flex-col justify-between gap-4 shadow-xs relative overflow-hidden transition-all"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: isHardwareConnected ? 'var(--status-success)' : 'var(--border-subtle)'
            }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono-code text-xs font-bold uppercase tracking-wider text-[var(--on-surface)]">
                    Native USB Hardware
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {isHardwareConnected ? (
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/30">
                      CONNECTED · {hardwareLifecycle.toUpperCase()}
                    </span>
                  ) : hardwareLifecycle === 'interrupted' ? (
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/30">
                      CONNECTION INTERRUPTED
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                      WAITING FOR AUSCULTAFORGE DEVICE
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  {isHardwareConnected ? 'ESP32-S3 Physical Transducer Stream' : 'Waiting for AuscultaForge device...'}
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  {isHardwareConnected
                    ? 'Receiving validated semantic PCG packet blocks from ESP32-S3 Native USB link.'
                    : 'No compatible AuscultaForge hardware detected. The application does not synthesize fake hardware.'}
                </p>
              </div>

              {/* Status Note / Telemetry grid */}
              <div
                className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-2 font-mono-code text-xs"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[var(--on-surface-variant)]">DISCOVERY STATUS:</span>
                  <span className="text-[var(--on-surface)] font-semibold">
                    {deviceRuntimeState?.discovery_status ?? 'Hardware discovery configuration pending Phase-1 USB descriptor decision'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--border-subtle)]/50 text-[10px]">
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">TRANSPORT</span>
                    <strong className="text-[var(--on-surface)]">ESP32-S3 Native USB</strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">USB CLASS</span>
                    <strong className="text-[var(--on-surface)]">CDC / Bulk (Pending)</strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">TARGET RATE</span>
                    <strong className="text-[var(--on-surface)]">4000 Hz Mono</strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">PACKET PROTOCOL</span>
                    <strong className="text-[var(--on-surface)]">Semantic v1.0</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)]">
              {isHardwareConnected ? (
                <button
                  onClick={onUseDevice}
                  className="px-3.5 py-1.5 rounded-lg font-mono-code text-xs font-semibold text-white bg-[var(--accent-oxblood)] flex items-center gap-1 shadow-xs cursor-pointer"
                >
                  <span>Stream in Workspace</span>
                  <ArrowRight size={13} />
                </button>
              ) : (
                <span className="font-mono-code text-[11px] text-[var(--on-surface-variant)] flex items-center gap-1.5">
                  <Clock size={13} />
                  <span>Awaiting physical device hot-plug...</span>
                </span>
              )}

              <span className="font-mono-code text-[10px] text-[var(--accent-metal)]">
                ESP32-S3 USB Transducer (Phase 1)
              </span>
            </div>
          </div>
        </div>

        {/* SECTION 2: OFFLINE ENGINEERING (Explicitly separated) */}
        <div className="flex flex-col gap-3 pt-2">
          <div className="flex items-center justify-between">
            <span className="font-mono-code text-xs uppercase tracking-wider text-[var(--accent-metal)] font-bold flex items-center gap-1.5">
              <Radio size={14} />
              <span>Offline Engineering</span>
            </span>
            <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
              Replay, Datasets &amp; DSP Benchmarks
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Option 1: Recorded Session Replay */}
            <div
              className={`rounded-xl border p-4 flex flex-col justify-between gap-3 shadow-xs transition-all ${
                sourceType === 'session' ? 'border-[var(--accent-oxblood)]' : 'border-[var(--border-subtle)]'
              }`}
              style={{ backgroundColor: 'var(--surface-card)' }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono-code text-[10px] font-bold text-[var(--accent-metal)]">
                    <Disc size={13} />
                    <span>SESSION REPLAY</span>
                  </div>
                  {sourceType === 'session' && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono-code font-bold bg-[var(--status-success)]/10 text-[var(--status-success)]">
                      ACTIVE
                    </span>
                  )}
                </div>

                <h4 className="font-serif-display text-sm font-semibold text-[var(--on-surface)]">
                  Recorded Session Replay
                </h4>
                <p className="text-[11px] text-[var(--on-surface-variant)] leading-relaxed">
                  Replay full multi-channel experimental session captures and clinical evaluations from disk.
                </p>
              </div>

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <button
                  onClick={onNavigateToSamples}
                  className="w-full py-1.5 rounded-lg border font-mono-code text-[11px] font-semibold text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer flex items-center justify-center gap-1"
                >
                  <span>Browse Session Archive</span>
                  <ExternalLink size={11} />
                </button>
              </div>
            </div>

            {/* Option 2: WAV Reference File */}
            <div
              className={`rounded-xl border p-4 flex flex-col justify-between gap-3 shadow-xs transition-all ${
                sourceType === 'file' ? 'border-[var(--accent-oxblood)]' : 'border-[var(--border-subtle)]'
              }`}
              style={{ backgroundColor: 'var(--surface-card)' }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono-code text-[10px] font-bold text-[var(--accent-metal)]">
                    <FileAudio size={13} />
                    <span>WAV REPLAY</span>
                  </div>
                  {sourceType === 'file' && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono-code font-bold bg-[var(--status-success)]/10 text-[var(--status-success)]">
                      ACTIVE
                    </span>
                  )}
                </div>

                <h4 className="font-serif-display text-sm font-semibold text-[var(--on-surface)]">
                  WAV Reference Files
                </h4>
                <p className="text-[11px] text-[var(--on-surface-variant)] leading-relaxed">
                  Load standard auscultation acoustic recordings and audition through real-time DSP filters.
                </p>
              </div>

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <button
                  onClick={onNavigateToSamples}
                  className="w-full py-1.5 rounded-lg border font-mono-code text-[11px] font-semibold text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer flex items-center justify-center gap-1"
                >
                  <span>Open Reference Library</span>
                  <ExternalLink size={11} />
                </button>
              </div>
            </div>

            {/* Option 3: Synthetic Development Signal — NOT HARDWARE */}
            <div
              className={`rounded-xl border p-4 flex flex-col justify-between gap-3 shadow-xs transition-all ${
                sourceType === 'synthetic' ? 'border-[var(--accent-oxblood)] ring-1 ring-[var(--accent-oxblood)]' : 'border-[var(--border-subtle)]'
              }`}
              style={{ backgroundColor: 'var(--surface-card)' }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono-code text-[10px] font-bold text-[var(--accent-oxblood)]">
                    <Radio size={13} />
                    <span>DEV BENCHMARK</span>
                  </div>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono-code font-bold bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)] border border-[var(--accent-oxblood)]/30">
                    NOT HARDWARE
                  </span>
                </div>

                <h4 className="font-serif-display text-sm font-semibold text-[var(--on-surface)]">
                  Synthetic Development Signal
                </h4>
                <p className="text-[11px] text-[var(--on-surface-variant)] leading-relaxed">
                  Deterministic mathematical PCG benchmark (S1/S2 acoustic waveform). For filter tuning and DSP unit testing only.
                </p>
              </div>

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <button
                  id="btn-select-synthetic-dev"
                  onClick={onSelectMockSource}
                  className="w-full py-1.5 rounded-lg border font-mono-code text-[11px] font-semibold text-[var(--accent-oxblood)] border-[var(--accent-oxblood)] hover:bg-[var(--accent-oxblood)]/10 transition-colors cursor-pointer flex items-center justify-center gap-1"
                >
                  <span>Activate Synthetic Benchmark</span>
                </button>
              </div>
            </div>
          </div>

          {/* Active Ingestion Summary */}
          <div className="p-3 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] flex items-center justify-between font-mono-code text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[var(--on-surface-variant)] uppercase text-[10px]">CURRENT INGESTION:</span>
              <strong className="text-[var(--on-surface)]">{activeSourceName}</strong>
            </div>
            {sourceType !== 'none' && (
              <button
                onClick={onUseDevice}
                className="px-3 py-1 rounded bg-[var(--accent-oxblood)] text-white text-xs font-semibold flex items-center gap-1 cursor-pointer shadow-xs"
              >
                <span>Go to Workspace</span>
                <ArrowRight size={12} />
              </button>
            )}
          </div>
        </div>

        {/* SECTION 3: FAULT TOLERANCE AND DIAGNOSTIC RESILIENCE */}
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
            Verify application reconnect logic, stream interruption handling, and state recovery upon transient link drop.
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
