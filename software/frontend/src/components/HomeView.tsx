import React, { useRef, useState } from 'react';
import {
  Stethoscope,
  AudioWaveform,
  FolderOpen,
  FolderArchive,
  RefreshCw,
  Terminal,
  ShieldCheck,
  Disc,
  ArrowRight
} from 'lucide-react';
import { NavigationDestination, HeartSoundMetadata } from '../types';
import { STARTER_SAMPLES } from '../audio/samplesData';

interface HomeViewProps {
  onOpenFile: (file: File) => void;
  onNavigate: (dest: NavigationDestination) => void;
  onSelectSample: (sample: HeartSoundMetadata) => void;
  onDetectDevice: () => void;
  deviceConnected: boolean;
  deviceConnecting: boolean;
  onToggleDiagnostics: () => void;
}

export const HomeView: React.FC<HomeViewProps> = ({
  onOpenFile,
  onNavigate,
  onSelectSample,
  onDetectDevice,
  deviceConnected,
  deviceConnecting,
  onToggleDiagnostics,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.wav') || file.name.endsWith('.mp3') || file.type.startsWith('audio/')) {
        onOpenFile(file);
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onOpenFile(e.target.files[0]);
    }
  };

  return (
    <div
      id="home-view"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex-1 flex flex-col h-full overflow-y-auto px-6 py-5 select-none transition-colors"
      style={{
        backgroundColor: 'var(--bg-canvas)'
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,.mp3,audio/*"
        onChange={handleFileInputChange}
        className="hidden"
      />

      <div className="max-w-7xl mx-auto w-full flex flex-col gap-6 pb-8">
        {/* Top Header Section (from Stitch reference) */}
        <section
          className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-col gap-1.5 max-w-2xl">
            <div className="flex items-center gap-2 text-[var(--accent-metal)] font-mono-code text-[11px] uppercase tracking-widest font-semibold">
              <span>Acoustic Metrology System</span>
              <span>•</span>
              <span>Revision IV-C</span>
            </div>
            <h1 className="font-serif-display text-3xl font-medium tracking-tight text-[var(--accent-oxblood)]">
              Smart Digital Stethoscope
            </h1>
            <p className="font-serif-display italic text-sm text-[var(--on-surface-variant)]">
              Heart-sound acquisition, playback and analysis workspace
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border shadow-xs"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <span className={`w-2 h-2 rounded-full ${deviceConnected ? 'bg-[var(--status-success)]' : 'bg-[var(--accent-metal)] animate-pulse'}`} />
              <span className="font-mono-code text-[11px] uppercase tracking-wider font-semibold text-[var(--on-surface-variant)]">
                System State:
              </span>
              <span className="font-mono-code text-[11px] font-bold tracking-wide text-[var(--accent-oxblood)]">
                {deviceConnected ? 'STREAMING' : 'STANDBY'}
              </span>
            </div>

            <button
              onClick={onToggleDiagnostics}
              title="Hardware Diagnostics Terminal (^⇧D)"
              className="flex items-center justify-center w-9 h-9 rounded-lg border shadow-xs text-[var(--accent-metal)] hover:text-[var(--accent-oxblood)] transition-colors cursor-pointer"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <Terminal size={17} />
            </button>
          </div>
        </section>

        {/* Main Grid: Device Panel (Left) & Telemetry Ingestion (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {/* Left Column (5 cols): Hardware Channel Card with Concentric Radial Motif */}
          <div className="lg:col-span-5 flex flex-col">
            <div
              className="relative flex flex-col justify-between h-full p-6 rounded-xl border shadow-xs overflow-hidden group transition-all"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              {/* Physical instrument corner registration marks */}
              <span className="absolute top-2 left-2 w-2 h-2 border-t-2 border-l-2 border-[var(--accent-metal)] opacity-60 pointer-events-none" />
              <span className="absolute top-2 right-2 w-2 h-2 border-t-2 border-r-2 border-[var(--accent-metal)] opacity-60 pointer-events-none" />
              <span className="absolute bottom-2 left-2 w-2 h-2 border-b-2 border-l-2 border-[var(--accent-metal)] opacity-60 pointer-events-none" />
              <span className="absolute bottom-2 right-2 w-2 h-2 border-b-2 border-r-2 border-[var(--accent-metal)] opacity-60 pointer-events-none" />

              {/* Concentric circles radar line art (from Stitch reference) */}
              <svg
                className="absolute -right-16 -bottom-16 w-80 h-80 text-[var(--border-subtle)] opacity-40 pointer-events-none transition-transform duration-700 ease-out group-hover:scale-105"
                fill="none"
                stroke="currentColor"
                strokeWidth="0.75"
                viewBox="0 0 200 200"
              >
                <circle cx="100" cy="100" r="90" strokeDasharray="2 3" />
                <circle cx="100" cy="100" r="78" strokeWidth="1.25" />
                <circle cx="100" cy="100" r="62" />
                <circle cx="100" cy="100" r="44" strokeDasharray="4 2" />
                <circle cx="100" cy="100" r="26" />
                <circle cx="100" cy="100" r="10" strokeWidth="1.5" />
                <line x1="10" y1="100" x2="190" y2="100" strokeDasharray="1 4" />
                <line x1="100" y1="10" x2="100" y2="190" strokeDasharray="1 4" />
                <circle cx="100" cy="100" r="2" fill="currentColor" />
                <path d="M 40,100 A 60,60 0 0,1 160,100" strokeWidth="0.5" />
                <path d="M 60,100 A 40,40 0 0,1 140,100" strokeWidth="0.5" />
              </svg>

              {/* Hardware Information */}
              <div className="relative z-10 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[var(--waveform-raw)]">
                    <Stethoscope size={20} />
                    <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--on-surface-variant)] font-bold">
                      Hardware Channel 01
                    </span>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono-code text-[10px] uppercase tracking-wide border ${
                    deviceConnected
                      ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30 font-bold'
                      : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border-[var(--border-subtle)]'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${deviceConnected ? 'bg-[var(--status-success)]' : 'bg-[var(--waveform-raw)]'}`} />
                    {deviceConnected ? 'COM4 CONNECTED' : 'PORT UNMAPPED'}
                  </span>
                </div>

                <div className="flex flex-col gap-1.5 mt-2">
                  <h2 className="font-serif-display text-2xl text-[var(--on-surface)] font-semibold">
                    {deviceConnected ? 'Stethoscope Hardware Synchronized' : 'No stethoscope connected'}
                  </h2>
                  <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
                    {deviceConnected
                      ? 'Piezoelectric chestpiece transducer is polling at 4.0 kHz over virtual serial bus. Dual mono channels verified.'
                      : 'Connect a precision acoustic transducer when available, or inspect pre-recorded phonocardiograms. Hardware is polled automatically without interrupting the active calibration matrix.'}
                  </p>
                </div>
              </div>

              {/* Hardware Actions */}
              <div
                className="relative z-10 pt-6 mt-6 border-t flex flex-col gap-3"
                style={{ borderColor: 'var(--border-subtle)' }}
              >
                <div className="flex items-center gap-3">
                  {deviceConnected ? (
                    <button
                      onClick={() => onNavigate('live')}
                      className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white font-medium text-xs transition-all shadow-xs cursor-pointer active:scale-[0.98]"
                      style={{ backgroundColor: 'var(--accent-oxblood)' }}
                    >
                      <ArrowRight size={15} />
                      <span>Enter Live Workspace</span>
                    </button>
                  ) : (
                    <button
                      id="detect-device-btn"
                      onClick={onDetectDevice}
                      disabled={deviceConnecting}
                      className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border font-medium text-xs transition-all shadow-xs cursor-pointer active:scale-[0.98] disabled:opacity-50"
                      style={{
                        backgroundColor: 'var(--surface-card)',
                        borderColor: 'var(--accent-metal)',
                        color: 'var(--accent-oxblood)'
                      }}
                    >
                      <RefreshCw size={14} className={deviceConnecting ? 'animate-spin text-[var(--accent-oxblood)]' : ''} />
                      <span>{deviceConnecting ? 'Scanning USB Bus…' : 'Detect Device'}</span>
                    </button>
                  )}

                  <div className="flex items-center gap-1.5 text-[var(--on-surface-variant)] font-mono-code text-[11px]">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--status-success)] opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--status-success)]" />
                    </span>
                    <span>Automatic polling active (500ms)</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[var(--on-surface-variant)] font-mono-code text-[10px] pt-1">
                  <span>BUS PROTOCOL: USB-CDC / HID</span>
                  <span>DEVICE_ID: {deviceConnected ? 'STETH-USB-8842' : 'NULL_VAL'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column (7 cols): File Ingestion & Reference Archive */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            {/* Top Ingestion Drop Zone */}
            <div
              id="drop-zone"
              onClick={() => fileInputRef.current?.click()}
              className={`relative group cursor-pointer flex flex-col items-center justify-center p-7 rounded-xl border-2 border-dashed transition-all shadow-xs min-h-[210px] text-center ${
                isDragOver
                  ? 'border-[var(--accent-oxblood)] bg-[var(--accent-soft)]/40'
                  : 'hover:border-[var(--accent-oxblood)]'
              }`}
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: isDragOver ? 'var(--accent-oxblood)' : 'var(--border-strong)'
              }}
            >
              <div
                className="w-13 h-13 rounded-full flex items-center justify-center mb-2.5 text-[var(--accent-oxblood)] group-hover:scale-110 transition-transform"
                style={{ backgroundColor: 'var(--surface-muted)' }}
              >
                <AudioWaveform size={26} />
              </div>

              <div className="flex items-center gap-2 mb-1">
                <span className="font-serif-display text-lg font-semibold text-[var(--on-surface)] group-hover:text-[var(--accent-oxblood)] transition-colors">
                  Open Telemetry File
                </span>
                <span className="px-2 py-0.5 rounded font-mono-code text-[10px] font-bold bg-[var(--accent-soft)] text-[var(--accent-oxblood)] border border-[var(--border-subtle)]">
                  WAV or MP3
                </span>
              </div>

              <p className="text-xs text-[var(--on-surface-variant)] max-w-md mb-2.5">
                Drop an acoustic specimen or time-series auscultation capture here to decode raw &amp; filtered waveform tracks.
              </p>

              <span className="font-mono-code text-[11px] uppercase tracking-widest text-[var(--accent-metal)] font-semibold flex items-center gap-1 group-hover:underline">
                <FolderOpen size={13} />
                <span>Browse Workstation Drives</span>
              </span>
            </div>

            {/* Auscultation Reference Archive Banner */}
            <div
              className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 rounded-xl border shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center text-[var(--accent-metal)] shrink-0 mt-0.5"
                  style={{ backgroundColor: 'var(--surface-muted)' }}
                >
                  <FolderArchive size={19} />
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                      Auscultation Reference Archive
                    </h3>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-mono-code font-bold bg-[var(--accent-metal)]/10 text-[var(--accent-metal)] border border-[var(--accent-metal)]/20">
                      DEVELOPMENT BENCH
                    </span>
                  </div>
                  <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                    Explore synthetic heart-sound models and recorded sessions with S1, S2, and simulated murmur profiles.
                  </p>
                </div>
              </div>

              <button
                id="browse-samples-btn"
                onClick={() => onNavigate('samples')}
                className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white font-medium text-xs transition-all shadow-xs cursor-pointer active:scale-[0.98]"
                style={{ backgroundColor: 'var(--accent-oxblood)' }}
              >
                <Disc size={15} />
                <span>Browse Starter Signals &amp; Sessions</span>
              </button>
            </div>

            {/* 3 Specimen Quick Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {STARTER_SAMPLES.map((sample, idx) => (
                <button
                  key={sample.id}
                  onClick={() => onSelectSample(sample)}
                  className="p-3.5 rounded-lg border text-left flex flex-col justify-between transition-all hover:border-[var(--accent-oxblood)] hover:shadow-xs group cursor-pointer"
                  style={{
                    backgroundColor: 'var(--background-deep)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] font-semibold uppercase">
                    SPECIMEN {String.fromCharCode(65 + idx)}
                  </span>
                  <span className="font-serif-display text-sm font-semibold text-[var(--accent-oxblood)] truncate mt-1 group-hover:underline">
                    {sample.title}
                  </span>
                  <span className="font-mono-code text-[10px] text-[var(--accent-metal)] mt-2 font-medium">
                    {idx === 0 && '72 BPM · SYNTHETIC'}
                    {idx === 1 && 'MID-SYSTOLIC EJECTION'}
                    {idx === 2 && 'HOLOSYSTOLIC BLOWING'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Reassurance Footer Banner */}
        <section
          className="mt-2 pt-4 border-t flex flex-col md:flex-row items-center justify-between gap-3 text-[var(--on-surface-variant)] font-mono-code text-[11px]"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2 text-center md:text-left">
            <ShieldCheck size={16} className="text-[var(--accent-metal)]" />
            <span>No physical transducer is required to inspect, replay, or bandpass-filter specimen telemetry.</span>
          </div>
          <div className="flex items-center gap-3 text-[var(--accent-metal)] font-medium">
            <span>SOURCE-INDEPENDENT PROCESSING ARCHITECTURE</span>
            <span>•</span>
            <span>OFFLINE CALIBRATION READY</span>
          </div>
        </section>
      </div>
    </div>
  );
};
