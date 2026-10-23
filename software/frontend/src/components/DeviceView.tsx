import React, { useState, useEffect, useRef } from 'react';
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
  Square,
  Activity,
  Layers,
  ShieldCheck,
  Check,
} from 'lucide-react';
import {
  StethoscopeDevice,
  DeviceRuntimeState,
  DeviceIntegrityStats,
  AudioSourceType,
  VirtualBenchReport,
  UsbPortDescriptorItem,
  UsbSessionSummary,
  G1EvidenceData,
} from '../types';
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

export function g1ResultLabel(session: Pick<UsbSessionSummary, 'session_state' | 'is_simulated'> | null,
  evidence: Pick<G1EvidenceData, 'conclusion' | 'verification_result' | 'is_simulated'> | null): string | null {
  if (!session || !evidence || session.session_state === 'STREAMING') return null;
  if (evidence.verification_result === 'FAIL') return 'G1 FAILED — EXPORT EVIDENCE';
  if (session.is_simulated || evidence.is_simulated) return 'SOFTWARE SIMULATION PASS — PHYSICAL G1 PENDING';
  if (session.session_state === 'COMPLETE' && evidence.conclusion === 'PHYSICAL_G1_PASSED') return 'G1 PASSED — PHYSICAL USB';
  return null;
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
  // Virtual Bench state
  const [benchRunning, setBenchRunning] = useState(false);
  const [benchReport, setBenchReport] = useState<VirtualBenchReport | null>(null);
  const [benchError, setBenchError] = useState<string | null>(null);
  const [expandedScenarioId, setExpandedScenarioId] = useState<string | null>(null);

  // USB Discovery Doctor & Port Selection state
  const [detectedPorts, setDetectedPorts] = useState<UsbPortDescriptorItem[]>([]);
  const [selectedPort, setSelectedPort] = useState<string>('');
  const [sourceMode, setSourceMode] = useState<number>(1); // 1 = G1, 0 = Real Acoustic
  const [isScanningPorts, setIsScanningPorts] = useState(false);

  // Real USB Session Engine State
  const [usbSession, setUsbSession] = useState<UsbSessionSummary | null>(null);
  const [g1Evidence, setG1Evidence] = useState<G1EvidenceData | null>(null);
  const [usbActionLoading, setUsbActionLoading] = useState(false);
  const [usbActionError, setUsbActionError] = useState<string | null>(null);
  const automaticStopRequested = useRef(false);

  // Polling USB Session
  useEffect(() => {
    if (!backendConnected) return;
    let isMounted = true;

    const pollSession = async () => {
      try {
        const session = await bridgeClient.getUsbSession();
        if (isMounted) {
          setUsbSession(session);
          if (session?.has_g1_evidence) setG1Evidence(await bridgeClient.getG1Evidence());
        }
      } catch (_) {}
    };

    pollSession();
    const interval = setInterval(pollSession, 1200);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [backendConnected]);

  // Initial port scan
  useEffect(() => {
    if (!backendConnected) return;
    handleScanPorts();
  }, [backendConnected]);

  const handleScanPorts = async () => {
    setIsScanningPorts(true);
    setUsbActionError(null);
    try {
      const ports = await bridgeClient.getUsbPorts();
      setDetectedPorts(ports);
      onDetectDevice();
    } catch (err) {
      console.error('Scan ports failed', err);
    } finally {
      setIsScanningPorts(false);
    }
  };

  const handleConnectUsb = async () => {
    if (!selectedPort) return;
    setUsbActionLoading(true);
    setUsbActionError(null);
    try {
      const summary = await bridgeClient.connectUsbDevice(selectedPort);
      setUsbSession(summary.summary ?? summary);
      onDetectDevice();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setUsbActionError(`Connect failed: ${msg}`);
    } finally {
      setUsbActionLoading(false);
    }
  };

  const handleDisconnectUsb = async () => {
    setUsbActionLoading(true);
    setUsbActionError(null);
    try {
      const summary = await bridgeClient.disconnectUsbDevice();
      setUsbSession(summary.summary ?? summary);
      onDisconnectDevice();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setUsbActionError(`Disconnect failed: ${msg}`);
    } finally {
      setUsbActionLoading(false);
    }
  };

  const handleStartAcquisition = async () => {
    automaticStopRequested.current = false;
    setG1Evidence(null);
    setUsbActionLoading(true);
    setUsbActionError(null);
    try {
      const summary = await bridgeClient.startUsbAcquisition({ sourceMode, targetSamples: 480000 });
      setUsbSession(summary.summary ?? summary);
      onUseDevice();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setUsbActionError(`Start acquisition failed: ${msg}`);
    } finally {
      setUsbActionLoading(false);
    }
  };

  const handleStopAcquisition = async () => {
    setUsbActionLoading(true);
    setUsbActionError(null);
    try {
      const summary = await bridgeClient.stopUsbAcquisition();
      setUsbSession(summary.summary ?? summary);
      if (sourceMode === 1) {
        try {
          const ev = await bridgeClient.getG1Evidence();
          setG1Evidence(ev);
        } catch (_) {}
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setUsbActionError(`Stop acquisition failed: ${msg}`);
    } finally {
      setUsbActionLoading(false);
    }
  };

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

  const isSessionStreaming = usbSession?.session_state === 'STREAMING';
  const isSessionReady = ['READY', 'COMPLETE'].includes(usbSession?.session_state ?? '');
  const isSessionConnected = isSessionReady || isSessionStreaming;
  const isHardwareConnected = isSessionConnected || (deviceRuntimeState?.connected ?? false);
  useEffect(() => {
    if (isSessionStreaming && usbSession?.active_config &&
        usbSession.counters.host_samples_accepted >= usbSession.active_config.target_samples && !automaticStopRequested.current) {
      automaticStopRequested.current = true;
      void handleStopAcquisition();
    }
  }, [isSessionStreaming, usbSession?.counters.host_samples_accepted]);
  const effectiveLifecycle = usbSession ? usbSession.session_state.toLowerCase() : (deviceRuntimeState?.state ?? 'absent').toLowerCase();

  // Helper for rendering truthful state badges
  const renderStateBadge = () => {
    const resultLabel = g1ResultLabel(usbSession, g1Evidence);
    if (resultLabel) {
      return <span className={g1Evidence?.verification_result === 'FAIL' ? 'text-[var(--status-danger)] font-bold' : 'text-[var(--on-surface-variant)] font-bold'}>{resultLabel}</span>;
    }
    if (isSessionStreaming) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)] animate-pulse" />
          <span>{usbSession?.is_simulated ? 'SOFTWARE SIMULATION · ' : ''}ACQUIRING · {usbSession?.active_config?.source_mode === 1 ? 'G1 DETERMINISTIC' : 'REAL ACOUSTIC'}</span>
        </span>
      );
    }
    if (isSessionReady) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
          <span>{usbSession?.is_simulated ? 'SOFTWARE SIMULATION / ' : ''}FIRMWARE HANDSHAKE VERIFIED / READY FOR G1</span>
        </span>
      );
    }
    if (effectiveLifecycle === 'opening' || effectiveLifecycle === 'hello_pending' || effectiveLifecycle === 'start_pending' || effectiveLifecycle === 'handshaking') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)]" />
          <span>NEGOTIATING HANDSHAKE...</span>
        </span>
      );
    }
    if (effectiveLifecycle === 'interrupted') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/20 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
          <AlertTriangle size={12} />
          <span>CONNECTION INTERRUPTED</span>
        </span>
      );
    }
    if (effectiveLifecycle === 'error') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-danger)]/15 text-[var(--status-danger)] border border-[var(--status-danger)]/40">
          <ShieldAlert size={12} />
          <span>HARDWARE ERROR</span>
        </span>
      );
    }
    if (detectedPorts.some(port => port.port_name !== 'SIMULATED_ESP32_S3')) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)]" />
          <span>PORT AVAILABLE — DEVICE NOT VERIFIED</span>
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--on-surface-variant)]/40" />
        <span>HARDWARE DISCONNECTED</span>
      </span>
    );
  };

  // Helper for title & description based on state
  const getStateCopy = () => {
    if (isSessionStreaming) {
      return {
        title: usbSession?.is_simulated ? 'Simulated ESP32-S3 Canonical Stream' : 'ESP32-S3 Physical Transducer Stream',
        desc: usbSession?.active_config?.source_mode === 1
          ? 'Streaming 48 kHz mono signed PCM via deterministic G1 known-answer generator. Host is verifying frame integrity and sample exactness in real-time.'
          : 'Streaming live acoustic transducer samples via Profile B canonical frames. Stateful DSP filtering active.'
      };
    }
    if (isSessionReady) {
      return {
        title: 'Hardware Link Verified & Ready',
        desc: `Canonical HELLO handshake succeeded on ${usbSession?.port || 'port'}. Protocol semantic v0.1 accepted. Ready to configure acquisition mode and initiate session.`
      };
    }
    if (effectiveLifecycle === 'opening' || effectiveLifecycle === 'hello_pending' || effectiveLifecycle === 'start_pending') {
      return {
        title: 'Negotiating Canonical Link...',
        desc: 'Opening transport adapter, sending HELLO request with cryptographic nonce, and awaiting verified capabilities.'
      };
    }
    if (effectiveLifecycle === 'interrupted') {
      return {
        title: 'USB Transport Interrupted',
        desc: 'Physical USB link dropped or stalled. Rolling buffers are preserved. Re-seat the USB cable or scan the bus.'
      };
    }
    if (effectiveLifecycle === 'error') {
      return {
        title: 'Hardware Transport Error',
        desc: 'Communication failure encountered on USB endpoint. Check wiring, descriptor integrity, or power supply.'
      };
    }
    if (detectedPorts.length > 0) {
      return {
        title: 'Serial Port(s) Detected — Device Not Verified',
        desc: `${detectedPorts.length} serial interface(s) available on host bus. Select port and connect to execute canonical HELLO handshake.`
      };
    }
    return {
      title: 'Hardware Disconnected',
      desc: 'No AuscultaForge ESP32-S3 detected on host USB bus. Connect device or use SIMULATED_ESP32_S3 for in-memory protocol loopback.'
    };
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

              <p className="text-xs text-[var(--on-surface-variant)]">
                {usbSession?.is_simulated ? 'SOFTWARE SIMULATION — no physical acceptance' : 'First contact: inspect board → select native CDC → HELLO → deterministic G1 → STOP → export evidence.'}
                {' '}Firmware: {usbSession?.device_capabilities?.firmware_version ?? 'NOT VERIFIED'}.
                {' '}A detected COM port alone does not verify firmware. If it disappears, check cable/connector and rescan after BOOT/RESET.
                {' '}Live I²S requires a reviewed board profile and separate electrical qualification.
              </p>
              {/* Canonical Port Selection & Session Control Card */}
              <div className="p-3.5 rounded-lg bg-[var(--surface-muted)]/70 border border-[var(--border-subtle)] flex flex-col gap-3 font-mono-code text-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent-oxblood)]">
                      Target Interface:
                    </span>
                    <select
                      id="usb-port-selector"
                      value={selectedPort}
                      onChange={(e) => setSelectedPort(e.target.value)}
                      disabled={isSessionConnected || usbActionLoading}
                      className="px-2.5 py-1 rounded bg-[var(--surface-card)] border border-[var(--border-strong)] text-[var(--on-surface)] text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[var(--accent-oxblood)] disabled:opacity-50"
                    >
                      <option value="">Select the inspected data port</option>
                      <option value="SIMULATED_ESP32_S3">
                        SIMULATED_ESP32_S3 (In-Memory CDC Loopback)
                      </option>
                      {detectedPorts.filter((p) => p.port_name !== 'SIMULATED_ESP32_S3').map((p) => (
                        <option key={p.port_name} value={p.port_name}>
                          {p.port_name} {p.is_espressif_candidate ? '★ [ESP32 Candidate]' : ''} - {p.description}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      id="btn-scan-usb-bus"
                      onClick={handleScanPorts}
                      disabled={!backendConnected || isConnecting || isScanningPorts || isSessionConnected}
                      className={`px-2.5 py-1 rounded font-mono-code text-[11px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer border ${
                        !backendConnected || isConnecting || isScanningPorts || isSessionConnected
                          ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)]/50 border-[var(--border-subtle)] cursor-not-allowed'
                          : 'bg-[var(--surface-card)] text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)]'
                      }`}
                    >
                      <RefreshCw size={11} className={isScanningPorts ? 'animate-spin' : ''} />
                      <span>{isScanningPorts ? 'Scanning...' : 'Scan USB'}</span>
                    </button>

                    {!isSessionConnected ? (
                      <button
                        id="btn-connect-usb"
                        onClick={handleConnectUsb}
                        disabled={!backendConnected || usbActionLoading || !selectedPort}
                        className={`px-3 py-1 rounded font-mono-code text-[11px] font-bold text-white flex items-center gap-1.5 transition-colors cursor-pointer ${
                          !backendConnected || usbActionLoading || !selectedPort
                            ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)]/50 cursor-not-allowed'
                            : 'bg-[var(--status-success)] hover:opacity-90 shadow-xs'
                        }`}
                      >
                        {usbActionLoading ? <RefreshCw size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                        <span>Connect &amp; HELLO</span>
                      </button>
                    ) : (
                      <button
                        id="btn-disconnect-usb"
                        onClick={handleDisconnectUsb}
                        disabled={usbActionLoading}
                        className="px-3 py-1 rounded font-mono-code text-[11px] font-bold text-[var(--status-danger)] bg-[var(--status-danger)]/10 border border-[var(--status-danger)]/30 hover:bg-[var(--status-danger)]/20 flex items-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <PowerOff size={11} />
                        <span>Disconnect</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Acquisition Mode & Start/Stop controls */}
                <div className="pt-2 border-t border-[var(--border-subtle)]/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-bold uppercase text-[var(--on-surface-variant)]">Mode:</span>
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="acquisition-source-mode"
                        checked={sourceMode === 1}
                        onChange={() => setSourceMode(1)}
                        disabled={isSessionStreaming || usbActionLoading}
                        className="accent-[var(--accent-oxblood)]"
                      />
                      <span className="text-[11px] text-[var(--on-surface)] font-medium">
                        Deterministic G1 (Mode 1)
                      </span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="acquisition-source-mode"
                        checked={sourceMode === 0}
                        onChange={() => setSourceMode(0)}
                        disabled={isSessionStreaming || usbActionLoading}
                        className="accent-[var(--accent-oxblood)]"
                      />
                      <span className="text-[11px] text-[var(--on-surface)] font-medium">
                        Live microphone (reviewed profile only)
                      </span>
                    </label>
                  </div>

                  <div className="flex items-center gap-2">
                    {isSessionReady && !isSessionStreaming && (
                      <button
                        id="btn-start-usb-acquisition"
                        onClick={handleStartAcquisition}
                        disabled={usbActionLoading}
                        className="px-3.5 py-1 rounded bg-[var(--accent-oxblood)] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs hover:opacity-90 cursor-pointer"
                      >
                        {usbActionLoading ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} />}
                        <span>Start Acquisition</span>
                      </button>
                    )}

                    {isSessionStreaming && (
                      <button
                        id="btn-stop-usb-acquisition"
                        onClick={handleStopAcquisition}
                        disabled={usbActionLoading}
                        className="px-3.5 py-1 rounded bg-[var(--status-danger)] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs hover:opacity-90 cursor-pointer"
                      >
                        {usbActionLoading ? <RefreshCw size={12} className="animate-spin" /> : <Square size={12} />}
                        <span>Stop Acquisition</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Error Banner */}
                {usbActionError && (
                  <div className="p-2 rounded bg-[var(--status-danger)]/10 border border-[var(--status-danger)]/30 text-[11px] text-[var(--status-danger)] flex items-center gap-1.5">
                    <ShieldAlert size={12} className="shrink-0" />
                    <span>{usbActionError}</span>
                  </div>
                )}
              </div>

              {/* Status Note / Telemetry grid */}
              <div
                className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-2 font-mono-code text-xs"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[var(--on-surface-variant)]">ACTIVE INTERFACE:</span>
                  <span className="text-[var(--on-surface)] font-semibold text-right max-w-md">
                    {usbSession?.is_simulated ? 'SIMULATED_ESP32_S3 (In-Memory Loopback)' : (usbSession?.port || deviceRuntimeState?.port || 'Not connected')}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--border-subtle)]/50 text-[10px]">
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">TRANSPORT</span>
                    <strong className="text-[var(--on-surface)]">
                      {usbSession?.is_simulated ? 'Duplex Loopback Adapter' : 'CDC-ACM Host (pyserial)'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">SESSION ID</span>
                    <strong className="text-[var(--on-surface)] truncate block">
                      {usbSession?.active_session_id ? usbSession.active_session_id : 'None (Idle)'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">RATE / ENCODING</span>
                    <strong className="text-[var(--on-surface)]">48 kHz · S32_LE (24b)</strong>
                  </div>
                  <div>
                    <span className="text-[var(--on-surface-variant)] block">CANONICAL PROTOCOL</span>
                    <strong className="text-[var(--on-surface)]">Profile B v0.1 (CRC-32)</strong>
                  </div>
                </div>
              </div>

              {/* Live Canonical Counters Panel */}
              {usbSession && (
                <div className="p-3 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)] flex flex-col gap-2 font-mono-code text-xs">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold uppercase tracking-wider text-[var(--accent-metal)] flex items-center gap-1.5">
                      <Activity size={13} />
                      <span>Live Transport &amp; Frame Counters</span>
                    </span>
                    <span className="text-[10px] text-[var(--on-surface-variant)]">
                      State: <strong>{usbSession.session_state}</strong>
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1 text-[11px]">
                    <div>
                      <span className="text-[10px] text-[var(--on-surface-variant)] block">SAMPLES ACCEPTED</span>
                      <strong className="text-[var(--on-surface)]">{usbSession.counters.host_samples_accepted.toLocaleString()}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--on-surface-variant)] block">VALIDATED FRAMES</span>
                      <strong className="text-[var(--on-surface)]">{usbSession.counters.host_frames_accepted.toLocaleString()}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--on-surface-variant)] block">SEQUENCE GAPS</span>
                      <strong className={usbSession.counters.sequence_gaps > 0 ? 'text-[var(--status-warning)]' : 'text-[var(--on-surface)]'}>
                        {usbSession.counters.sequence_gaps}
                      </strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--on-surface-variant)] block">CRC ERRORS</span>
                      <strong className={usbSession.counters.crc_errors > 0 ? 'text-[var(--status-danger)]' : 'text-[var(--on-surface)]'}>
                        {usbSession.counters.crc_errors}
                      </strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--on-surface-variant)] block">DEVICE DROPS</span>
                      <strong className={(usbSession.latest_telemetry?.dropped_samples ?? 0) > 0 ? 'text-[var(--status-danger)]' : 'text-[var(--on-surface)]'}>
                        {(usbSession.latest_telemetry?.dropped_samples ?? 0)}
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              {/* G1 Evidence Report Card */}
              {g1Evidence && (
                <button className="text-sm underline text-[var(--on-surface)]" onClick={async () => {
                  try { await bridgeClient.exportG1Evidence(); }
                  catch (error) { setUsbActionError(String(error)); }
                }}>Export auditable G1 evidence</button>
              )}
              {g1Evidence && (
                <div className="p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-2.5 font-mono-code text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck size={14} className={(g1Evidence.verification_result === 'PASS') ? 'text-[var(--status-success)]' : 'text-[var(--status-danger)]'} />
                      <span className="font-bold uppercase tracking-wider text-[var(--on-surface)]">
                        G1 Acceptance Evidence
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        (g1Evidence.verification_result === 'PASS')
                          ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                          : 'bg-[var(--status-danger)]/15 text-[var(--status-danger)] border-[var(--status-danger)]/40'
                      }`}
                    >
                      {g1Evidence.conclusion}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] pt-1 border-t border-[var(--border-subtle)]/50">
                    <div>
                      <span className="text-[var(--on-surface-variant)] block">EVIDENCE ID</span>
                      <strong className="text-[var(--on-surface)] truncate block" title={g1Evidence.session_id}>
                        {g1Evidence.session_id}
                      </strong>
                    </div>
                    <div>
                      <span className="text-[var(--on-surface-variant)] block">EXACT SAMPLES</span>
                      <strong className="text-[var(--on-surface)]">
                        {g1Evidence.host_samples_accepted} / {g1Evidence.target_samples}
                      </strong>
                    </div>
                    <div>
                      <span className="text-[var(--on-surface-variant)] block">SESSION TIME</span>
                      <strong className="text-[var(--on-surface)]">{g1Evidence.timing.elapsed_since_start_command_s.toFixed(2)}s</strong>
                    </div>
                    <div>
                      <span className="text-[var(--on-surface-variant)] block">PROVENANCE</span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${g1Evidence.is_simulated ? 'bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)]' : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'}`}>
                        {g1Evidence.is_simulated ? 'SOFTWARE SIMULATED' : 'PHYSICAL HARDWARE'}
                      </span>
                    </div>
                  </div>

                  <div className="text-[10px] text-[var(--on-surface-variant)] flex items-center justify-between pt-1">
                    <span>SHA-256 Digest: <code className="text-[var(--on-surface)] select-all">{g1Evidence.sha256_hash.substring(0, 32)}...</code></span>
                    <span>Bit-exact match: <strong className={(g1Evidence.verification_result === 'PASS') ? 'text-[var(--status-success)]' : 'text-[var(--status-danger)]'}>{(g1Evidence.verification_result === 'PASS') ? '100.00%' : 'MISMATCH'}</strong></span>
                  </div>
                </div>
              )}
            </div>

            {/* Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[var(--border-subtle)]">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                  Session State: <strong>{usbSession?.session_state || 'DISCONNECTED'}</strong>
                </span>
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
