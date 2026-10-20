import React, { useState } from 'react';
import {
  ArrowRight,
  Cpu,
  Radio,
  FileAudio,
  Disc,
  Clock,
  ExternalLink,
  RefreshCw,
  PowerOff,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  Terminal,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Play,
} from 'lucide-react';
import { StethoscopeDevice, DeviceRuntimeState, DeviceIntegrityStats, AudioSourceType, VirtualBenchReport } from '../types';
import { bridgeClient } from '../api/bridgeClient';

interface DeviceViewProps {
  deviceState: StethoscopeDevice;
  deviceRuntimeState?: DeviceRuntimeState | null;
  deviceStats?: DeviceIntegrityStats | null;
  onDetectDevice: () => void;
  onDisconnectDevice: () => void;
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
  deviceStats,
  onDetectDevice,
  onDisconnectDevice,
  onUseDevice,
  isConnecting,
  backendConnected,
  activeSourceName,
  sourceType,
  onSelectMockSource,
  onNavigateToSamples,
}) => {
  const isHardwareConnected = deviceRuntimeState?.connected ?? false;
  const hardwareLifecycle = (deviceRuntimeState?.state ?? 'absent').toLowerCase();

  // Virtual Bench state
  const [benchRunning, setBenchRunning] = useState(false);
  const [benchReport, setBenchReport] = useState<VirtualBenchReport | null>(null);
  const [benchError, setBenchError] = useState<string | null>(null);
  const [expandedScenarioId, setExpandedScenarioId] = useState<string | null>(null);

  const handleRunBench = async () => {
    setBenchRunning(true);
    setBenchError(null);
    try {
      const rep = await bridgeClient.runBenchScenario('all');
      setBenchReport(rep);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Virtual bench execution failed';
      setBenchError(msg);
    } finally {
      setBenchRunning(false);
    }
  };

  // Helper for rendering truthful state badges
  const renderStateBadge = () => {
    switch (hardwareLifecycle) {
      case 'ready':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
            <span>READY · IDLE</span>
          </span>
        );
      case 'streaming':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)] animate-pulse" />
            <span>LIVE HARDWARE STREAMING</span>
          </span>
        );
      case 'detected':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)]" />
            <span>CANDIDATE DETECTED</span>
          </span>
        );
      case 'opening':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)]" />
            <span>OPENING USB PORT...</span>
          </span>
        );
      case 'handshaking':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)]" />
            <span>PROTOCOL HANDSHAKE...</span>
          </span>
        );
      case 'interrupted':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/20 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
            <AlertTriangle size={12} />
            <span>CONNECTION INTERRUPTED</span>
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-danger)]/15 text-[var(--status-danger)] border border-[var(--status-danger)]/40">
            <ShieldAlert size={12} />
            <span>HARDWARE ERROR</span>
          </span>
        );
      case 'incompatible':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-danger)]/15 text-[var(--status-danger)] border border-[var(--status-danger)]/40">
            <AlertTriangle size={12} />
            <span>INCOMPATIBLE DESCRIPTOR</span>
          </span>
        );
      case 'absent':
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--on-surface-variant)]/40" />
            <span>WAITING FOR HARDWARE (ABSENT)</span>
          </span>
        );
    }
  };

  // Helper for title & description based on state
  const getStateCopy = () => {
    switch (hardwareLifecycle) {
      case 'ready':
      case 'streaming':
        return {
          title: 'ESP32-S3 Physical Transducer Stream',
          desc: 'Connected to physical AuscultaForge ESP32-S3 Native USB link. Ready for real-time acoustic phonocardiographic streaming.'
        };
      case 'detected':
        return {
          title: 'Compatible USB Candidate Found',
          desc: `Candidate device detected on ${deviceRuntimeState?.candidate?.port || 'USB bus'}. Initializing protocol handshake.`
        };
      case 'opening':
      case 'handshaking':
        return {
          title: 'Negotiating Hardware Link...',
          desc: 'Establishing CDC-ACM transport and verifying device descriptors.'
        };
      case 'interrupted':
        return {
          title: 'USB Transport Interrupted',
          desc: 'Physical USB link dropped or stalled. Rolling buffers are preserved. Re-seat the USB cable or scan the bus.'
        };
      case 'error':
        return {
          title: 'Hardware Transport Error',
          desc: 'Communication failure encountered on USB endpoint. Check wiring, descriptor integrity, or power supply.'
        };
      case 'incompatible':
        return {
          title: 'Incompatible Device Protocol',
          desc: 'A USB candidate was detected, but its descriptor or semantic version does not match AuscultaForge requirements.'
        };
      case 'absent':
      default:
        return {
          title: 'Waiting for AuscultaForge device...',
          desc: 'No compatible ESP32-S3 hardware detected on host bus. The application strictly reflects real hardware state and never fabricates fake hardware telemetry.'
        };
    }
  };

  const stateCopy = getStateCopy();

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
            <span>{backendConnected ? 'Bridge Online' : 'Bridge Offline'}</span>
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
              Authoritative Host Runtime State
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
                    Native USB Hardware Channel
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {renderStateBadge()}
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  {stateCopy.title}
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                  {stateCopy.desc}
                </p>
              </div>

              {/* Status Note / Telemetry grid */}
              <div
                className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-2 font-mono-code text-xs"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[var(--on-surface-variant)]">DISCOVERY STATUS:</span>
                  <span className="text-[var(--on-surface)] font-semibold text-right max-w-md">
                    {deviceRuntimeState?.discovery_status ?? 'No discovery scan executed or bridge offline'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--border-subtle)]/50 text-[10px]">
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">TRANSPORT</span>
                    <strong className="text-[var(--on-surface)]">ESP32-S3 Native USB</strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">USB PORT / PATH</span>
                    <strong className="text-[var(--on-surface)] truncate block" title={deviceRuntimeState?.candidate?.port || deviceRuntimeState?.port || 'None'}>
                      {deviceRuntimeState?.candidate?.port || deviceRuntimeState?.port || 'Scanning / None'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">DEVICE ID</span>
                    <strong className="text-[var(--on-surface)] truncate block" title={deviceRuntimeState?.device_id || 'None'}>
                      {deviceRuntimeState?.device_id || (deviceRuntimeState?.candidate ? deviceRuntimeState.candidate.description || 'USB Candidate' : 'None')}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">PACKET PROTOCOL</span>
                    <strong className="text-[var(--on-surface)]">Semantic v1.0</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[var(--border-subtle)]">
              <div className="flex items-center gap-2">
                {/* Scan Button */}
                <button
                  id="btn-scan-usb-bus"
                  onClick={onDetectDevice}
                  disabled={!backendConnected || isConnecting}
                  className={`px-3 py-1.5 rounded-lg font-mono-code text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer border ${
                    !backendConnected || isConnecting
                      ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)]/50 border-[var(--border-subtle)] cursor-not-allowed'
                      : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-card)]'
                  }`}
                  title={!backendConnected ? 'Python Bridge must be connected to scan' : 'Scan system USB bus for AuscultaForge device'}
                >
                  <RefreshCw size={12} className={isConnecting ? 'animate-spin' : ''} />
                  <span>{isConnecting ? 'Scanning...' : 'Scan USB Bus'}</span>
                </button>

                {/* Disconnect Button (Enabled only when connected) */}
                {isHardwareConnected && (
                  <button
                    id="btn-disconnect-device"
                    onClick={onDisconnectDevice}
                    className="px-3 py-1.5 rounded-lg font-mono-code text-xs font-semibold text-[var(--status-danger)] bg-[var(--status-danger)]/10 border border-[var(--status-danger)]/30 hover:bg-[var(--status-danger)]/20 flex items-center gap-1.5 cursor-pointer transition-colors"
                  >
                    <PowerOff size={12} />
                    <span>Disconnect</span>
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                {isHardwareConnected ? (
                  <button
                    id="btn-stream-in-workspace"
                    onClick={onUseDevice}
                    className="px-3.5 py-1.5 rounded-lg font-mono-code text-xs font-semibold text-white bg-[var(--accent-oxblood)] hover:opacity-90 flex items-center gap-1 shadow-xs cursor-pointer transition-opacity"
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
              </div>
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
              Replay, Datasets &amp; DSP Benchmarks (Not Live Hardware)
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
                sourceType === 'file' || sourceType === 'sample' ? 'border-[var(--accent-oxblood)]' : 'border-[var(--border-subtle)]'
              }`}
              style={{ backgroundColor: 'var(--surface-card)' }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono-code text-[10px] font-bold text-[var(--accent-metal)]">
                    <FileAudio size={13} />
                    <span>WAV REPLAY</span>
                  </div>
                  {(sourceType === 'file' || sourceType === 'sample') && (
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

        {/* SECTION 2.5: DETERMINISTIC VIRTUAL BENCH (Known-Answer Test Harness) */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
              <Terminal size={15} className="text-[var(--accent-oxblood)]" />
              <span>Deterministic Virtual Bench</span>
              <span className="px-2 py-0.5 rounded text-[9px] font-mono-code font-bold bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)] border border-[var(--accent-oxblood)]/30">
                SOFTWARE BENCH · TEST ONLY (NOT HARDWARE)
              </span>
            </div>
            <span className="font-mono-code text-[10px] text-[var(--status-warning)] font-bold">
              Tag: SOFTWARE_KNOWN_ANSWER
            </span>
          </div>

          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            A software-only integration harness executing the complete host acquisition seam, DSP filtering, display ring-buffer publication, and session recording without requiring an ESP32-S3. All 8 scenarios test deterministic inputs against independent mathematical known-answer oracles.
          </p>

          <div className="p-2.5 rounded-lg bg-[var(--status-warning)]/10 border border-[var(--status-warning)]/30 text-[11px] font-mono-code font-bold text-[var(--status-warning)] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--status-warning)] animate-pulse" />
            <span>SOFTWARE SIMULATION — NO PHYSICAL ESP32 ATTACHED</span>
          </div>

          <div className="flex items-center justify-between gap-3 pt-2 border-t border-[var(--border-subtle)]">
            <div className="flex items-center gap-2">
              <button
                id="btn-run-virtual-bench"
                onClick={handleRunBench}
                disabled={!backendConnected || benchRunning}
                className={`px-3.5 py-1.5 rounded-lg font-mono-code text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer border ${
                  !backendConnected || benchRunning
                    ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)]/50 border-[var(--border-subtle)] cursor-not-allowed'
                    : 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)] hover:opacity-90 shadow-xs'
                }`}
              >
                {benchRunning ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Play size={13} />
                )}
                <span>{benchRunning ? 'Running 8 Scenarios...' : 'Run Known-Answer Test Suite'}</span>
              </button>

              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                Seed: 42 (Fully Declared Deterministic)
              </span>
            </div>

            {benchReport && (
              <div className="flex items-center gap-2">
                <span
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono-code font-bold border ${
                    benchReport.all_passed
                      ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                      : 'bg-[var(--status-danger)]/15 text-[var(--status-danger)] border-[var(--status-danger)]/40'
                  }`}
                >
                  {benchReport.all_passed ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                  <span>
                    {benchReport.all_passed ? 'ALL PASSED' : 'TESTS FAILED'} ({benchReport.passed_scenarios}/{benchReport.total_scenarios})
                  </span>
                </span>
              </div>
            )}
          </div>

          {benchError && (
            <div className="p-3 rounded-lg bg-[var(--status-danger)]/10 border border-[var(--status-danger)]/30 text-xs font-mono-code text-[var(--status-danger)]">
              {benchError}
            </div>
          )}

          {benchReport && (
            <div className="flex flex-col gap-2 pt-2 border-t border-[var(--border-subtle)] font-mono-code text-xs">
              <div className="flex items-center justify-between text-[11px] text-[var(--on-surface-variant)] pb-1">
                <span>SCENARIOS EXECUTED ({benchReport.scenarios.length})</span>
                <span>STATUS / DURATION</span>
              </div>

              <div className="flex flex-col gap-1.5">
                {benchReport.scenarios.map((scen) => {
                  const isExpanded = expandedScenarioId === scen.scenario_id;
                  return (
                    <div
                      key={scen.scenario_id}
                      className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-muted)] overflow-hidden"
                    >
                      <button
                        onClick={() => setExpandedScenarioId(isExpanded ? null : scen.scenario_id)}
                        className="w-full p-2.5 flex items-center justify-between gap-2 text-left hover:bg-[var(--surface-card)] transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          {scen.passed ? (
                            <CheckCircle2 size={14} className="text-[var(--status-success)] shrink-0" />
                          ) : (
                            <XCircle size={14} className="text-[var(--status-danger)] shrink-0" />
                          )}
                          <span className="font-semibold text-[var(--on-surface)]">{scen.title}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-card)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                            {scen.category}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-[var(--on-surface-variant)]">
                            {scen.duration_ms.toFixed(1)}ms
                          </span>
                          <span className="text-[10px] font-bold text-[var(--status-success)]">
                            [{scen.metrics.filter((m) => m.passed).length}/{scen.metrics.length} CHECKS]
                          </span>
                          {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-3 border-t border-[var(--border-subtle)]/60 bg-[var(--surface-card)] flex flex-col gap-2 text-[11px]">
                          <div className="text-[10px] text-[var(--on-surface-variant)] flex items-center justify-between">
                            <span>ID: <code>{scen.scenario_id}</code></span>
                            <span>LABEL: <code className="text-[var(--status-warning)]">{scen.status_label}</code></span>
                          </div>

                          <table className="w-full text-left border-collapse text-[11px] mt-1">
                            <thead>
                              <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--on-surface-variant)]">
                                <th className="pb-1">CHECK</th>
                                <th className="pb-1">EXPECTED</th>
                                <th className="pb-1">OBSERVED</th>
                                <th className="pb-1 text-right">STATUS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {scen.metrics.map((m, idx) => (
                                <tr key={idx} className="border-b border-[var(--border-subtle)]/40">
                                  <td className="py-1 text-[var(--on-surface)]">{m.name}</td>
                                  <td className="py-1 text-[var(--on-surface-variant)] truncate max-w-[120px]" title={String(m.expected)}>
                                    {String(m.expected)} {m.unit}
                                  </td>
                                  <td className="py-1 text-[var(--on-surface)] font-semibold truncate max-w-[120px]" title={String(m.observed)}>
                                    {String(m.observed)} {m.unit}
                                  </td>
                                  <td className="py-1 text-right">
                                    <span
                                      className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                        m.passed
                                          ? 'text-[var(--status-success)] bg-[var(--status-success)]/10'
                                          : 'text-[var(--status-danger)] bg-[var(--status-danger)]/10'
                                      }`}
                                    >
                                      {m.passed ? 'PASS' : 'FAIL'}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>

                          {Object.keys(scen.artifacts).length > 0 && (
                            <div className="pt-2 border-t border-[var(--border-subtle)]/50 text-[10px] text-[var(--on-surface-variant)]">
                              <span className="font-bold text-[var(--on-surface)]">Artifacts Generated: </span>
                              {Object.entries(scen.artifacts).map(([k, v]) => (
                                <span key={k} className="mr-3">
                                  {k}: <code className="text-[var(--on-surface)]">{v}</code>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] text-[10px] font-mono-code text-[var(--on-surface-variant)]">
            <strong className="text-[var(--on-surface)]">Isolation Guarantee: </strong>
            Software bench operates purely in-memory via double transports. It cannot alter production USB discovery or report physical hardware connected.
          </div>
        </div>

        {/* SECTION 3: HARDWARE RESILIENCE & TRANSPORT INTEGRITY */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-3 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
              <CheckCircle size={15} className="text-[var(--status-success)]" />
              <span>Hardware Resilience &amp; Transport Diagnostics</span>
            </div>
            <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
              Continuous Stream Integrity
            </span>
          </div>

          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            The host runtime maintains strict transport integrity counters. In the event of a physical USB cable pull or link stall, the backend enters <code className="font-mono-code text-[var(--accent-oxblood)]">INTERRUPTED</code> state, preserves audio buffer continuity, and prepares for graceful recovery without crashing the UI.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-mono-code text-xs">
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">PACKETS RECEIVED</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.packets_received ?? 0}</strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">SAMPLES RECEIVED</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.samples_received ?? 0}</strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">SEQUENCE GAPS</span>
              <strong className={deviceStats && deviceStats.sequence_gaps > 0 ? 'text-[var(--status-warning)]' : 'text-[var(--on-surface)]'}>
                {deviceStats?.sequence_gaps ?? 0}
              </strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">CRC FAILURES</span>
              <strong className={deviceStats && deviceStats.crc_failures > 0 ? 'text-[var(--status-danger)]' : 'text-[var(--on-surface)]'}>
                {deviceStats?.crc_failures ?? 0}
              </strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">OUT OF ORDER</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.out_of_order_packets ?? 0}</strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">TIMESTAMP REGRESSIONS</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.timestamp_regressions ?? 0}</strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">DISCONNECT COUNT</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.disconnect_count ?? 0}</strong>
            </div>
            <div>
              <span className="text-[10px] text-[var(--on-surface-variant)] block">RECONNECT COUNT</span>
              <strong className="text-[var(--on-surface)]">{deviceStats?.reconnect_count ?? 0}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
