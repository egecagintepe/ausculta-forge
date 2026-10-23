import React, { useState, useEffect } from 'react';
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
  Terminal,
  Download,
  Activity,
  Bug,
  Wrench,
  Layers,
  RefreshCw,
  HelpCircle,
  Eye,
  Info,
  Clock,
  ShieldAlert,
} from 'lucide-react';
import {
  DiagnosticState,
  AudioMetrics,
  StethoscopeDevice,
  DeviceRuntimeState,
  DeviceIntegrityStats,
  DeviceEventItem,
  DiagnosticEventRecord,
  DiagnosticCorrelationReport,
} from '../types';
import { bridgeClient } from '../api/bridgeClient';

interface DiagnosticsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  diagnosticState: DiagnosticState;
  audioMetrics: AudioMetrics;
  isPlaybackActive: boolean;
  deviceState: StethoscopeDevice;
  deviceRuntimeState?: DeviceRuntimeState | null;
  deviceStats?: DeviceIntegrityStats | null;
  deviceEvents?: DeviceEventItem[];
  onCopySummary: () => void;
  copySuccess: boolean;
  isDark: boolean;
}

export const DiagnosticsDrawer: React.FC<DiagnosticsDrawerProps> = ({
  isOpen,
  onClose,
  diagnosticState,
  audioMetrics,
  isPlaybackActive,
  deviceState,
  deviceRuntimeState,
  deviceStats,
  deviceEvents = [],
  onCopySummary,
  copySuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'telemetry' | 'timeline' | 'assistant' | 'lab'>('telemetry');
  const [isJuryPresentationMode, setIsJuryPresentationMode] = useState<boolean>(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    source: false,
    audio: false,
    hardware: false,
    dsp: false,
    log: false,
  });

  // Diagnostics API states
  const [flightEvents, setFlightEvents] = useState<DiagnosticEventRecord[]>([]);
  const [correlationReport, setCorrelationReport] = useState<DiagnosticCorrelationReport | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<DiagnosticEventRecord | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('near_silence');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [injectionNotice, setInjectionNotice] = useState<string | null>(null);

  // Poll diagnostic events & correlation when drawer is open
  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;

    const loadData = async () => {
      try {
        const [evts, report] = await Promise.all([
          bridgeClient.fetchDiagnosticEvents({ limit: 40 }),
          bridgeClient.fetchCorrelationReport(),
        ]);
        if (isMounted) {
          setFlightEvents(evts);
          setCorrelationReport(report);
        }
      } catch {
        // Silently tolerate bridge offline
      }
    };

    loadData();
    const timer = setInterval(loadData, 3000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const toggle = (key: string) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleExportBundle = async () => {
    setIsExporting(true);
    try {
      const blob = await bridgeClient.exportDiagnosticsBundle();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      a.download = `auscultaforge_diagnostics_${timestamp}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      console.error('Failed to export bundle:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleInjectFault = async () => {
    setIsInjecting(true);
    setInjectionNotice(null);
    try {
      const res = await bridgeClient.injectFaultScenario(selectedScenario);
      setInjectionNotice(`Injected ${res.target_fault_code}: ${res.diagnostic_message}`);
      // Refresh event list
      const evts = await bridgeClient.fetchDiagnosticEvents({ limit: 40 });
      setFlightEvents(evts);
      const report = await bridgeClient.fetchCorrelationReport();
      setCorrelationReport(report);
    } catch (err: unknown) {
      setInjectionNotice(err instanceof Error ? err.message : 'Injection failed');
    } finally {
      setIsInjecting(false);
    }
  };

  const renderSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[var(--status-danger)] text-white animate-pulse">
            CRITICAL
          </span>
        );
      case 'ERROR':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[var(--status-danger)]/15 text-[var(--status-danger)] border border-[var(--status-danger)]/30">
            ERROR
          </span>
        );
      case 'WARNING':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/30">
            WARN
          </span>
        );
      case 'INFO':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[var(--accent-oxblood)]/10 text-[var(--accent-oxblood)] border border-[var(--border-subtle)]">
            INFO
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)]">
            {sev}
          </span>
        );
    }
  };

  const renderOriginBadge = (origin: string) => {
    const isPhysical = origin === 'OBSERVED_HOST' || origin === 'REPORTED_BY_FIRMWARE';
    return (
      <span
        className={`px-1.5 py-0.2 rounded text-[8px] font-mono-code font-semibold ${
          isPhysical
            ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/30'
            : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border border-[var(--status-warning)]/30'
        }`}
      >
        {origin}
      </span>
    );
  };

  return (
    <aside
      id="diagnostics-drawer"
      className="fixed top-8 right-0 bottom-6 w-full sm:w-[500px] z-50 flex flex-col shadow-2xl border-l select-none transition-all duration-200 overflow-hidden"
      style={{
        backgroundColor: 'var(--surface-card)',
        borderColor: 'var(--border-strong)',
      }}
    >
      {/* Drawer Master Header */}
      <div
        className="p-4 pb-2.5 flex flex-col gap-2 border-b shrink-0"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-[var(--status-warning)] animate-pulse" />
            <h2 className="font-serif-display text-lg font-semibold text-[var(--accent-oxblood)]">
              Engineering &amp; Flight Recorder
            </h2>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setIsJuryPresentationMode(prev => !prev)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono-code font-semibold border transition-colors cursor-pointer ${
                isJuryPresentationMode
                  ? 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)]'
                  : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border-[var(--border-subtle)]'
              }`}
              title="Toggle Jury Presentation vs Full Engineering View"
            >
              {isJuryPresentationMode ? 'Jury View' : 'Engineering'}
            </button>
            <button
              onClick={onClose}
              title="Close Drawer (Esc)"
              className="w-7 h-7 rounded flex items-center justify-center text-[var(--on-surface-variant)] hover:bg-[var(--surface-muted)] hover:text-[var(--on-surface)] transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Action strip: Export Bundle & Copy Summary */}
        <div className="flex items-center justify-between pt-1">
          <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] uppercase tracking-wider font-semibold">
            B/C Protocol &amp; Acoustic Seam
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportBundle}
              disabled={isExporting}
              className="px-2.5 py-1 rounded text-[10px] font-mono-code font-semibold flex items-center gap-1 bg-[var(--accent-oxblood)] text-white hover:opacity-90 transition-opacity cursor-pointer shadow-xs disabled:opacity-50"
              title="Export sanitized engineering diagnostics zip bundle"
            >
              <Download size={11} className={isExporting ? 'animate-bounce' : ''} />
              <span>{isExporting ? 'Exporting...' : 'Export Bundle'}</span>
            </button>

            <button
              onClick={onCopySummary}
              className="flex items-center gap-1 text-[10px] font-mono-code text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] transition-colors px-2 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] cursor-pointer"
              title="Copy Summary to Clipboard"
            >
              {copySuccess ? <Check size={11} className="text-[var(--status-success)]" /> : <Copy size={11} />}
              <span>{copySuccess ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 pt-2 border-t border-[var(--border-subtle)]/40 text-[11px] font-mono-code">
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`px-2.5 py-1 rounded-t transition-colors cursor-pointer ${
              activeTab === 'telemetry'
                ? 'font-bold border-b-2 border-[var(--accent-oxblood)] text-[var(--accent-oxblood)]'
                : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
            }`}
          >
            Telemetry
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`px-2.5 py-1 rounded-t transition-colors cursor-pointer flex items-center gap-1 ${
              activeTab === 'timeline'
                ? 'font-bold border-b-2 border-[var(--accent-oxblood)] text-[var(--accent-oxblood)]'
                : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
            }`}
          >
            <span>Timeline</span>
            {flightEvents.length > 0 && (
              <span className="px-1 rounded-full text-[9px] bg-[var(--surface-muted)] text-[var(--accent-oxblood)] font-bold">
                {flightEvents.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('assistant')}
            className={`px-2.5 py-1 rounded-t transition-colors cursor-pointer ${
              activeTab === 'assistant'
                ? 'font-bold border-b-2 border-[var(--accent-oxblood)] text-[var(--accent-oxblood)]'
                : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
            }`}
          >
            Assistant
          </button>
          <button
            onClick={() => setActiveTab('lab')}
            className={`px-2.5 py-1 rounded-t transition-colors cursor-pointer ${
              activeTab === 'lab'
                ? 'font-bold border-b-2 border-[var(--accent-oxblood)] text-[var(--accent-oxblood)]'
                : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
            }`}
          >
            Fault Lab
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
        {activeTab === 'telemetry' && (
          <div className="flex flex-col divide-y divide-[var(--border-subtle)]">
            {/* 1. Source & Timebase */}
            <div>
              <button
                onClick={() => toggle('source')}
                className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <FolderOpen size={14} className="text-[var(--accent-metal)]" />
                  <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                    1. Source &amp; Timebase
                  </span>
                </div>
                {collapsed.source ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </button>

              {!collapsed.source && (
                <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Active Mode:</span>
                    <span className="font-semibold text-[var(--on-surface)]">
                      {diagnosticState.activeSource || 'None'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Hardware Sample Rate:</span>
                    <span className="font-semibold text-[var(--accent-oxblood)]">
                      {diagnosticState.inputSampleRate || '48,000 Hz (Rev-A Target)'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Session Elapsed:</span>
                    <span className="text-[var(--on-surface)]">{diagnosticState.sessionTime || '0.00s'}</span>
                  </div>
                  <div className="flex items-center justify-between py-1">
                    <span className="text-[var(--on-surface-variant)]">Timebase Provenance:</span>
                    <span className="text-[10px] text-[var(--on-surface-variant)]">
                      Host Monotonic NS · Unsync MCU
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 2. Audio Metrology */}
            <div>
              <button
                onClick={() => toggle('audio')}
                className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Volume2 size={14} className="text-[var(--accent-metal)]" />
                  <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                    2. Signal Quality &amp; Metrology
                  </span>
                </div>
                {collapsed.audio ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </button>

              {!collapsed.audio && (
                <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Digital RMS:</span>
                    <span className="text-[var(--on-surface)] font-semibold">
                      {isPlaybackActive && Number.isFinite(audioMetrics.currentRmsDb) ? `${audioMetrics.currentRmsDb.toFixed(1)} dBFS (playback)` : 'NOT EVALUATED'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Peak Amplitude:</span>
                    <span className="text-[var(--on-surface)] font-semibold">
                      {isPlaybackActive && Number.isFinite(audioMetrics.currentPeakDb) ? `${audioMetrics.currentPeakDb.toFixed(1)} dBFS (playback)` : 'NOT EVALUATED'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Crest Factor:</span>
                    <span className="text-[var(--on-surface)]">
                      {isPlaybackActive && Number.isFinite(audioMetrics.currentPeakDb) && Number.isFinite(audioMetrics.currentRmsDb) ? `${(audioMetrics.currentPeakDb - audioMetrics.currentRmsDb).toFixed(2)} dB (playback)` : 'NOT EVALUATED'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1">
                    <span className="text-[var(--on-surface-variant)]">Acoustic SPL:</span>
                    <span className="text-[10px] text-[var(--on-surface-variant)]">
                      UNAVAILABLE (Requires Calibrated Reference)
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 3. Hardware Bus & Acquisition Seam */}
            <div>
              <button
                onClick={() => toggle('hardware')}
                className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Stethoscope size={14} className="text-[var(--accent-metal)]" />
                  <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                    3. Hardware Bus &amp; Protocol Telemetry
                  </span>
                </div>
                {collapsed.hardware ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </button>

              {!collapsed.hardware && (
                <div className="px-4 py-2 flex flex-col gap-1 font-mono-code text-[11px]">
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Lifecycle State:</span>
                    <span
                      className={`font-semibold uppercase flex items-center gap-1 ${
                        deviceRuntimeState?.connected
                          ? 'text-[var(--status-success)]'
                          : 'text-[var(--status-danger)]'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          deviceRuntimeState?.connected
                            ? 'bg-[var(--status-success)]'
                            : 'bg-[var(--status-danger)]'
                        }`}
                      />
                      {deviceRuntimeState?.state ?? 'absent'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Physical Transport:</span>
                    <span className="text-[var(--on-surface)]">ESP32-S3 Native USB (CDC-ACM)</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                    <span className="text-[var(--on-surface-variant)]">Device Port:</span>
                    <span className="text-[var(--on-surface)] truncate max-w-[200px]">
                      {deviceRuntimeState?.candidate?.port || deviceRuntimeState?.port || 'No device attached'}
                    </span>
                  </div>
                  {deviceStats && (
                    <>
                      <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                        <span className="text-[var(--on-surface-variant)]">Packets / Samples:</span>
                        <span className="text-[var(--on-surface)]">
                          {deviceStats.packets_received} pkts · {deviceStats.samples_received} smp
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                        <span className="text-[var(--on-surface-variant)]">Sequence Gaps / Dup:</span>
                        <span className="text-[var(--on-surface)]">
                          {deviceStats.sequence_gaps} gaps · {deviceStats.repeated_packets} dup
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]/40">
                        <span className="text-[var(--on-surface-variant)]">CRC / Framing:</span>
                        <span className="text-[var(--on-surface)]">
                          {deviceStats.crc_failures} crc · {deviceStats.malformed_frames} malformed
                        </span>
                      </div>
                    </>
                  )}
                  <div className="flex items-center justify-between py-1">
                    <span className="text-[var(--on-surface-variant)]">Hardware Telemetry:</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        deviceRuntimeState?.connected
                          ? 'bg-[var(--status-success)]/10 text-[var(--status-success)]'
                          : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)]'
                      }`}
                    >
                      {deviceRuntimeState?.connected
                        ? 'Hardware Stream Active'
                        : 'No Verified AuscultaForge Hardware'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 4. Processing & Quality */}
            <div>
              <button
                onClick={() => toggle('dsp')}
                className="w-full px-4 py-2 bg-[var(--surface-muted)]/50 hover:bg-[var(--surface-muted)] flex items-center justify-between text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Sliders size={14} className="text-[var(--accent-metal)]" />
                  <span className="font-mono-code text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface)]">
                    4. Processing &amp; DSP Core
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
                  <div className="flex items-center justify-between py-1">
                    <span className="text-[var(--on-surface-variant)]">Signal Stream:</span>
                    <span className="text-[var(--status-success)] font-semibold flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
                      Active Ingestion (DSP Core)
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Live Incident Timeline */}
        {activeTab === 'timeline' && (
          <div className="p-4 flex flex-col gap-3 font-mono-code text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[var(--on-surface)] flex items-center gap-1.5">
                <Clock size={13} className="text-[var(--accent-oxblood)]" />
                <span>Persistent Journal ({flightEvents.length} records)</span>
              </span>
              <button
                onClick={async () => {
                  const evts = await bridgeClient.fetchDiagnosticEvents({ limit: 40 });
                  setFlightEvents(evts);
                }}
                className="p-1 rounded hover:bg-[var(--surface-muted)] text-[var(--on-surface-variant)]"
                title="Refresh Events"
              >
                <RefreshCw size={12} />
              </button>
            </div>

            {flightEvents.length === 0 ? (
              <div className="p-4 text-center text-[var(--on-surface-variant)] bg-[var(--surface-muted)]/30 rounded border border-[var(--border-subtle)]">
                No incidents recorded in journal. System operating normally.
              </div>
            ) : (
              <div className="flex flex-col gap-2 max-h-[460px] overflow-y-auto">
                {flightEvents.map((evt) => {
                  const isSelected = selectedEvent?.event_id === evt.event_id;
                  return (
                    <div
                      key={evt.event_id}
                      onClick={() => setSelectedEvent(isSelected ? null : evt)}
                      className={`p-2.5 rounded border transition-colors cursor-pointer flex flex-col gap-1.5 ${
                        isSelected
                          ? 'border-[var(--accent-oxblood)] bg-[var(--accent-oxblood)]/5'
                          : 'border-[var(--border-subtle)] bg-[var(--surface-muted)]/20 hover:bg-[var(--surface-muted)]/50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {renderSeverityBadge(evt.severity)}
                          <span className="font-bold text-[var(--accent-oxblood)]">{evt.fault_code}</span>
                          <span className="text-[10px] text-[var(--on-surface-variant)]">[{evt.subsystem}]</span>
                          {renderOriginBadge(evt.evidence_origin)}
                        </div>
                        <span className="text-[10px] text-[var(--on-surface-variant)] shrink-0">
                          {evt.timestamp_utc.slice(11, 19)}
                        </span>
                      </div>

                      <p className="text-[11px] text-[var(--on-surface)] leading-snug">{evt.message}</p>

                      {/* Technical Detail Expander */}
                      {isSelected && (
                        <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] flex flex-col gap-1.5 text-[10px]">
                          {evt.session_id && (
                            <div className="flex justify-between">
                              <span className="text-[var(--on-surface-variant)]">Session ID:</span>
                              <span className="font-semibold">{evt.session_id}</span>
                            </div>
                          )}
                          {evt.frame_sequence !== undefined && evt.frame_sequence !== null && (
                            <div className="flex justify-between">
                              <span className="text-[var(--on-surface-variant)]">Frame Sequence:</span>
                              <span className="font-semibold">{evt.frame_sequence}</span>
                            </div>
                          )}
                          {evt.first_sample_index !== undefined && evt.first_sample_index !== null && (
                            <div className="flex justify-between">
                              <span className="text-[var(--on-surface-variant)]">Sample Index:</span>
                              <span className="font-semibold">{evt.first_sample_index}</span>
                            </div>
                          )}
                          {evt.expected_value !== undefined && evt.expected_value !== null && (
                            <div className="flex justify-between">
                              <span className="text-[var(--on-surface-variant)]">Expected vs Observed:</span>
                              <span className="text-[var(--status-danger)]">
                                {String(evt.expected_value)} vs {String(evt.observed_value)}
                              </span>
                            </div>
                          )}

                          {/* Hypotheses */}
                          {evt.possible_causes && evt.possible_causes.length > 0 && (
                            <div className="flex flex-col gap-0.5 pt-1">
                              <span className="font-bold text-[var(--accent-metal)]">
                                Hypotheses (Unconfirmed):
                              </span>
                              <ul className="list-disc list-inside text-[var(--on-surface-variant)] pl-1">
                                {evt.possible_causes.map((c, i) => (
                                  <li key={i}>{c}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Actions */}
                          {evt.suggested_actions && evt.suggested_actions.length > 0 && (
                            <div className="flex flex-col gap-0.5 pt-1">
                              <span className="font-bold text-[var(--status-success)]">
                                Recommended Next Action:
                              </span>
                              <ul className="list-disc list-inside text-[var(--on-surface)] pl-1">
                                {evt.suggested_actions.map((a, i) => (
                                  <li key={i}>{a}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className="pt-2 flex justify-end">
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                await bridgeClient.resolveFault(evt.fault_code);
                                const updated = await bridgeClient.fetchDiagnosticEvents({ limit: 40 });
                                setFlightEvents(updated);
                              }}
                              className="px-2 py-1 rounded bg-[var(--surface-muted)] hover:bg-[var(--border-subtle)] text-[10px] font-semibold text-[var(--on-surface)] border border-[var(--border-subtle)]"
                            >
                              Acknowledge / Mark Resolved
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Troubleshooting Assistant */}
        {activeTab === 'assistant' && (
          <div className="p-4 flex flex-col gap-3 font-mono-code text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[var(--on-surface)] flex items-center gap-1.5">
                <Wrench size={13} className="text-[var(--accent-oxblood)]" />
                <span>Deterministic Correlation Engine</span>
              </span>
              <span className="text-[10px] text-[var(--on-surface-variant)]">Rule-Based Reasoning</span>
            </div>

            {correlationReport && (
              <div className="p-3 rounded bg-[var(--surface-muted)]/30 border border-[var(--border-subtle)] flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[var(--accent-oxblood)]">
                    {correlationReport.case_id}
                  </span>
                  <span className="text-[10px] text-[var(--on-surface-variant)]">
                    {correlationReport.active_incident_count} Active Incidents
                  </span>
                </div>
                <p className="text-[11px] text-[var(--on-surface)]">{correlationReport.summary}</p>
              </div>
            )}

            {/* Ranked Hypotheses */}
            <div className="flex flex-col gap-2">
              <span className="font-bold text-[var(--on-surface)] uppercase tracking-wider text-[10px]">
                Ranked Troubleshooting Checklist
              </span>

              {correlationReport?.ranked_hypotheses && correlationReport.ranked_hypotheses.length > 0 ? (
                correlationReport.ranked_hypotheses.map((h, i) => (
                  <div
                    key={i}
                    className="p-3 rounded border border-[var(--border-subtle)] bg-[var(--surface-card)] flex flex-col gap-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <strong className="text-[var(--on-surface)] text-[11px]">
                        {i + 1}. {h.title}
                      </strong>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          h.probability === 'HIGH'
                            ? 'bg-[var(--status-danger)]/15 text-[var(--status-danger)]'
                            : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]'
                        }`}
                      >
                        {h.probability}
                      </span>
                    </div>

                    <p className="text-[10px] text-[var(--on-surface-variant)] leading-relaxed">
                      {h.reasoning}
                    </p>

                    {h.recommended_actions && h.recommended_actions.length > 0 && (
                      <div className="mt-1 pt-1 border-t border-[var(--border-subtle)]/40 flex flex-col gap-1">
                        <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--status-success)]">
                          Engineering Check:
                        </span>
                        <ul className="list-disc list-inside text-[10px] text-[var(--on-surface)]">
                          {h.recommended_actions.map((act, j) => (
                            <li key={j}>{act}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-3 text-[11px] text-[var(--on-surface-variant)] bg-[var(--surface-muted)]/20 rounded">
                  No active fault signatures detected. Hardware bus and signal pipeline healthy.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Fault Injection Laboratory */}
        {activeTab === 'lab' && (
          <div className="p-4 flex flex-col gap-3 font-mono-code text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[var(--on-surface)] flex items-center gap-1.5">
                <Bug size={13} className="text-[var(--status-warning)]" />
                <span>Deterministic Fault Injection Lab</span>
              </span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--status-warning)]/10 text-[var(--status-warning)] font-bold">
                SIMULATION ONLY
              </span>
            </div>

            <p className="text-[11px] text-[var(--on-surface-variant)] leading-relaxed">
              Inject reproducible failure scenarios into the diagnostic journal to exercise fault
              taxonomy, correlation logic, and senior design jury explanations without physical damage.
            </p>

            <div className="flex flex-col gap-2 pt-1">
              <label className="text-[10px] font-bold text-[var(--on-surface-variant)] uppercase tracking-wider">
                Select Scenario (25 Available):
              </label>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="w-full px-2.5 py-2 rounded bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-strong)] text-xs cursor-pointer focus:outline-hidden"
              >
                <optgroup label="USB Discovery & Transport">
                  <option value="empty_discovery">AF-USB-001: Empty Device Discovery</option>
                  <option value="port_permission_denied">AF-USB-002: Port Permission Denied</option>
                  <option value="busy_com_port">AF-USB-002: Busy COM Port (Locked)</option>
                  <option value="missing_hello_ack">AF-USB-005: Missing HELLO_ACK Timeout</option>
                  <option value="usb_read_timeout">AF-USB-005: USB Read Ingestion Timeout</option>
                  <option value="usb_write_stall">AF-USB-006: USB Write Transmission Stalled</option>
                </optgroup>
                <optgroup label="Canonical B/C Protocol">
                  <option value="invalid_magic">AF-PRT-001: Invalid Packet Sync Magic</option>
                  <option value="corrupted_crc">AF-PRT-002: Corrupted CRC Packet</option>
                  <option value="incompatible_protocol_version">AF-PRT-003: Incompatible Version</option>
                  <option value="wrong_hello_nonce">AF-PRT-004: Wrong HELLO Nonce</option>
                  <option value="wrong_start_encoding">AF-PRT-005: START Config Rejected</option>
                  <option value="zero_session_id">AF-PRT-006: Zero Session ID In START_ACK</option>
                  <option value="stale_stop_ack">AF-PRT-006: Stale Session ID In STOP_ACK</option>
                  <option value="fragmented_packet_stream">AF-PRT-007: Fragmented Packet Ingestion</option>
                </optgroup>
                <optgroup label="Streaming Integrity & Firmware">
                  <option value="dropped_audio_packet">AF-STR-001: Audio Frame Sequence Gap</option>
                  <option value="repeated_audio_packet">AF-STR-002: Duplicate Audio Frame</option>
                  <option value="reordered_sample_index">AF-STR-003: Sample Discontinuity</option>
                  <option value="firmware_ring_overflow">AF-STR-007: Ring Buffer Overflow</option>
                  <option value="incorrect_integer_sample">AF-STR-009: Corrupted PCM Sample</option>
                </optgroup>
                <optgroup label="Signal Quality Metrology">
                  <option value="near_silence">AF-SIG-001: Acoustic Near-Silence</option>
                  <option value="clipping">AF-SIG-002: Signal Rail Clipping</option>
                  <option value="excessive_dc_offset">AF-SIG-003: Excessive DC Offset Bias</option>
                </optgroup>
                <optgroup label="Storage & Application">
                  <option value="insufficient_storage">AF-FILE-003: Low Disk Storage Space</option>
                  <option value="wav_integrity_mismatch">AF-FILE-002: WAV Hash Mismatch</option>
                  <option value="backend_exited">AF-APP-002: Backend Unexpected Exit</option>
                </optgroup>
              </select>

              <button
                onClick={handleInjectFault}
                disabled={isInjecting}
                className="w-full mt-1 py-2 px-3 rounded bg-[var(--accent-oxblood)] hover:opacity-90 text-white font-semibold transition-opacity cursor-pointer shadow-xs disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                <Bug size={13} className={isInjecting ? 'animate-spin' : ''} />
                <span>{isInjecting ? 'Injecting Failure...' : 'Inject Fault Scenario'}</span>
              </button>

              {injectionNotice && (
                <div className="mt-2 p-2.5 rounded bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-subtle)] text-[11px] leading-tight">
                  {injectionNotice}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Drawer Bottom Status Strip */}
      <div
        className="px-4 py-2 flex items-center justify-between font-mono-code text-[10px] text-[var(--on-surface-variant)] border-t shrink-0"
        style={{
          backgroundColor: 'var(--surface-muted)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex items-center gap-1.5">
          <CheckCircle2 size={13} className="text-[var(--status-success)]" />
          <span className="tracking-wider font-semibold">
            {isJuryPresentationMode ? 'JURY EVALUATION MODE' : 'HOST BUFFER STABLE'}
          </span>
        </div>
        <span>
          {deviceStats
            ? `TX: ${deviceStats.packets_received} PKTS · ${deviceStats.samples_received} SMP`
            : 'FLIGHT RECORDER: ACTIVE'}
        </span>
      </div>
    </aside>
  );
};
