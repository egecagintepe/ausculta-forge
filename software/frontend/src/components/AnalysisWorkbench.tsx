import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Layers,
  Activity,
  FileAudio,
  UploadCloud,
  Trash2,
  Play,
  CheckCircle2,
  AlertCircle,
  Info,
  Download,
  RefreshCw,
  Sliders,
  ArrowRight,
  FileText,
  Check,
  Zap,
  Clock,
  HardDrive,
  BarChart2,
  ExternalLink,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';
import {
  ReferenceAssetItem,
  SessionAnalysisSummary,
  AnalysisComparisonResult
} from '../types';
import { bridgeClient, SessionItem } from '../api/bridgeClient';

interface AnalysisWorkbenchProps {
  initialSessionId?: string | null;
  isDark: boolean;
  onNavigateToLive?: () => void;
  onNavigateToSamples?: () => void;
  addToast?: (message: string, type?: 'info' | 'success' | 'warning') => void;
}

export const AnalysisWorkbench: React.FC<AnalysisWorkbenchProps> = ({
  initialSessionId,
  isDark,
  onNavigateToLive,
  onNavigateToSamples,
  addToast
}) => {
  // Navigation / sub-tabs within Workbench
  const [activeTab, setActiveTab] = useState<'compare' | 'sessions' | 'references' | 'history'>('compare');

  // Selection state
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(initialSessionId || null);
  const [sessionSummary, setSessionSummary] = useState<SessionAnalysisSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState<boolean>(false);

  // Reference Assets state
  const [referenceAssets, setReferenceAssets] = useState<ReferenceAssetItem[]>([]);
  const [loadingAssets, setLoadingAssets] = useState<boolean>(false);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [uploadingAsset, setUploadingAsset] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Comparison State
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<AnalysisComparisonResult | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [pastReports, setPastReports] = useState<AnalysisComparisonResult[]>([]);
  const [loadingPastReports, setLoadingPastReports] = useState<boolean>(false);

  // Trace visibility toggles
  const [showRefTrace, setShowRefTrace] = useState<boolean>(true);
  const [showCapTrace, setShowCapTrace] = useState<boolean>(true);
  const [showErrorTrace, setShowErrorTrace] = useState<boolean>(true);

  // Fetch session list
  const refreshSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const list = await bridgeClient.fetchSessions();
      setSessions(list);
      if (!selectedSessionId && list.length > 0) {
        setSelectedSessionId(list[0].session_id);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
  }, [selectedSessionId]);

  // Fetch reference assets
  const refreshAssets = useCallback(async () => {
    setLoadingAssets(true);
    try {
      const assets = await bridgeClient.listReferenceAssets();
      setReferenceAssets(assets);
      if (!selectedAssetId && assets.length > 0) {
        setSelectedAssetId(assets[0].asset_id);
      }
    } catch (err) {
      console.error('Failed to load reference assets:', err);
    } finally {
      setLoadingAssets(false);
    }
  }, [selectedAssetId]);

  // Load session analysis summary when selected
  useEffect(() => {
    if (!selectedSessionId) {
      setSessionSummary(null);
      return;
    }
    let cancelled = false;
    setLoadingSummary(true);
    bridgeClient.getSessionAnalysisSummary(selectedSessionId)
      .then((summary) => {
        if (!cancelled) {
          setSessionSummary(summary);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to fetch session summary:', err);
          setSessionSummary(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingSummary(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSessionId]);

  // Load initial data
  useEffect(() => {
    refreshSessions();
    refreshAssets();
  }, [refreshSessions, refreshAssets]);

  // Handle WAV Upload
  const handleWavUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.name.toLowerCase().endsWith('.wav')) {
      setUploadError('Only WAV audio files are supported for PCG references.');
      return;
    }

    setUploadingAsset(true);
    setUploadError(null);
    try {
      const asset = await bridgeClient.uploadReferenceAsset(file);
      await refreshAssets();
      setSelectedAssetId(asset.asset_id);
      if (addToast) addToast(`Imported reference: ${asset.filename}`, 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setUploadError(msg);
      if (addToast) addToast(`Upload failed: ${msg}`, 'warning');
    } finally {
      setUploadingAsset(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Delete reference asset
  const handleDeleteAsset = async (assetId: string) => {
    try {
      await bridgeClient.deleteReferenceAsset(assetId);
      if (selectedAssetId === assetId) {
        setSelectedAssetId(null);
      }
      await refreshAssets();
      if (addToast) addToast('Reference asset removed', 'info');
    } catch (err) {
      console.error('Failed to delete asset:', err);
    }
  };

  // Run Comparison
  const handleRunComparison = async () => {
    if (!selectedAssetId || !selectedSessionId) {
      setComparisonError('Please select both a reference WAV and a capture session.');
      return;
    }

    setIsComparing(true);
    setComparisonError(null);
    try {
      const result = await bridgeClient.compareReferenceAndCapture(selectedAssetId, selectedSessionId, 600);
      setComparisonResult(result);
      setActiveTab('compare');
      if (addToast) addToast('Engineering comparison completed', 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setComparisonError(msg);
      if (addToast) addToast(`Comparison failed: ${msg}`, 'warning');
    } finally {
      setIsComparing(false);
    }
  };

  // Export report download
  const handleExportReport = () => {
    if (!comparisonResult) return;
    const url = bridgeClient.getExportReportUrl(comparisonResult.analysis_id);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison_${comparisonResult.analysis_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    if (addToast) addToast('Exporting comparison report (JSON)', 'info');
  };

  // SVG Helper: decimate or plot points
  const renderSvgWaveform = (
    refPoints: number[],
    capPoints: number[],
    errPoints: number[],
    timeMs: number[],
    width: number,
    height: number
  ) => {
    if (!timeMs || timeMs.length < 2) return null;

    const padding = { top: 20, right: 30, bottom: 30, left: 55 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    const tMin = timeMs[0];
    const tMax = timeMs[timeMs.length - 1];
    const tSpan = Math.max(1, tMax - tMin);

    // Compute amplitude scale
    let yMax = 0.05;
    for (let i = 0; i < timeMs.length; i++) {
      if (showRefTrace && refPoints[i] !== undefined) yMax = Math.max(yMax, Math.abs(refPoints[i]));
      if (showCapTrace && capPoints[i] !== undefined) yMax = Math.max(yMax, Math.abs(capPoints[i]));
      if (showErrorTrace && errPoints[i] !== undefined) yMax = Math.max(yMax, Math.abs(errPoints[i]));
    }
    yMax = yMax * 1.15; // 15% head room

    const toX = (t: number) => padding.left + ((t - tMin) / tSpan) * plotW;
    const toY = (val: number) => padding.top + plotH / 2 - (val / yMax) * (plotH / 2);

    // Generate path data
    const makePath = (data: number[]) => {
      if (!data || data.length === 0) return '';
      return data.reduce((acc, val, idx) => {
        const x = toX(timeMs[idx]);
        const y = toY(val);
        return idx === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : `${acc} L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }, '');
    };

    const refPath = showRefTrace ? makePath(refPoints) : '';
    const capPath = showCapTrace ? makePath(capPoints) : '';
    const errPath = showErrorTrace ? makePath(errPoints) : '';

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible select-none">
        {/* Background Grid */}
        <line
          x1={padding.left}
          y1={padding.top + plotH / 2}
          x2={padding.left + plotW}
          y2={padding.top + plotH / 2}
          stroke="var(--border-subtle)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={padding.top + plotH}
          stroke="var(--border-strong)"
          strokeWidth="1"
        />
        <line
          x1={padding.left}
          y1={padding.top + plotH}
          x2={padding.left + plotW}
          y2={padding.top + plotH}
          stroke="var(--border-strong)"
          strokeWidth="1"
        />

        {/* Amplitude Y-Axis labels */}
        <text x={padding.left - 8} y={padding.top + 4} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          +{yMax.toFixed(2)}
        </text>
        <text x={padding.left - 8} y={padding.top + plotH / 2 + 3} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          0.00
        </text>
        <text x={padding.left - 8} y={padding.top + plotH} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          -{yMax.toFixed(2)}
        </text>

        {/* Time X-Axis labels */}
        <text x={padding.left} y={padding.top + plotH + 18} textAnchor="start" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          {tMin.toFixed(0)} ms
        </text>
        <text x={padding.left + plotW / 2} y={padding.top + plotH + 18} textAnchor="middle" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          {((tMin + tMax) / 2).toFixed(0)} ms
        </text>
        <text x={padding.left + plotW} y={padding.top + plotH + 18} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">
          {tMax.toFixed(0)} ms
        </text>

        {/* Traces */}
        {refPath && (
          <path d={refPath} fill="none" stroke="var(--status-info)" strokeWidth="1.5" strokeLinecap="round" />
        )}
        {capPath && (
          <path d={capPath} fill="none" stroke="var(--accent-oxblood)" strokeWidth="1.5" strokeLinecap="round" />
        )}
        {errPath && (
          <path d={errPath} fill="none" stroke="var(--status-warning)" strokeWidth="1.2" strokeDasharray="3 2" />
        )}
      </svg>
    );
  };

  // SVG Helper: PSD comparison
  const renderSvgPsd = (
    freqs: number[],
    refDb: number[],
    capDb: number[],
    width: number,
    height: number
  ) => {
    if (!freqs || freqs.length < 2) return null;

    const padding = { top: 20, right: 30, bottom: 30, left: 55 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    const fMin = 0;
    const fMax = Math.min(1000, freqs[freqs.length - 1]);
    const fSpan = Math.max(1, fMax - fMin);

    const validDb = [...refDb, ...capDb].filter(v => isFinite(v));
    const minDb = validDb.length > 0 ? Math.max(-100, Math.min(...validDb)) : -80;
    const maxDb = validDb.length > 0 ? Math.min(20, Math.max(...validDb) + 5) : 0;
    const dbSpan = Math.max(10, maxDb - minDb);

    const toX = (f: number) => padding.left + ((f - fMin) / fSpan) * plotW;
    const toY = (db: number) => padding.top + plotH - ((Math.max(minDb, Math.min(maxDb, db)) - minDb) / dbSpan) * plotH;

    const makePath = (data: number[]) => {
      let p = '';
      for (let i = 0; i < freqs.length; i++) {
        if (freqs[i] > fMax) break;
        const x = toX(freqs[i]);
        const y = toY(data[i]);
        p += i === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
      return p;
    };

    const refPsdPath = makePath(refDb);
    const capPsdPath = makePath(capDb);

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible select-none">
        {/* Band divider indicators */}
        <line x1={toX(20)} y1={padding.top} x2={toX(20)} y2={padding.top + plotH} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
        <line x1={toX(150)} y1={padding.top} x2={toX(150)} y2={padding.top + plotH} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
        <line x1={toX(600)} y1={padding.top} x2={toX(600)} y2={padding.top + plotH} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3 3" />

        <text x={toX(20)} y={padding.top - 6} textAnchor="middle" className="text-[9px] font-mono-code fill-[var(--text-tertiary)]">20Hz</text>
        <text x={toX(150)} y={padding.top - 6} textAnchor="middle" className="text-[9px] font-mono-code fill-[var(--text-tertiary)]">150Hz</text>
        <text x={toX(600)} y={padding.top - 6} textAnchor="middle" className="text-[9px] font-mono-code fill-[var(--text-tertiary)]">600Hz</text>

        {/* Axes */}
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + plotH} stroke="var(--border-strong)" strokeWidth="1" />
        <line x1={padding.left} y1={padding.top + plotH} x2={padding.left + plotW} y2={padding.top + plotH} stroke="var(--border-strong)" strokeWidth="1" />

        {/* Labels */}
        <text x={padding.left - 8} y={padding.top + 5} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">{maxDb.toFixed(0)} dB</text>
        <text x={padding.left - 8} y={padding.top + plotH} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">{minDb.toFixed(0)} dB</text>

        <text x={padding.left} y={padding.top + plotH + 18} textAnchor="start" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">0 Hz</text>
        <text x={padding.left + plotW / 2} y={padding.top + plotH + 18} textAnchor="middle" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">500 Hz</text>
        <text x={padding.left + plotW} y={padding.top + plotH + 18} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">{fMax.toFixed(0)} Hz</text>

        {refPsdPath && <path d={refPsdPath} fill="none" stroke="var(--status-info)" strokeWidth="1.5" />}
        {capPsdPath && <path d={capPsdPath} fill="none" stroke="var(--accent-oxblood)" strokeWidth="1.5" />}
      </svg>
    );
  };

  // SVG Helper: Coherence
  const renderSvgCoherence = (
    freqs: number[],
    coherence: number[],
    width: number,
    height: number
  ) => {
    if (!freqs || freqs.length < 2) return null;

    const padding = { top: 20, right: 30, bottom: 30, left: 55 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    const fMin = 0;
    const fMax = Math.min(1000, freqs[freqs.length - 1]);
    const fSpan = Math.max(1, fMax - fMin);

    const toX = (f: number) => padding.left + ((f - fMin) / fSpan) * plotW;
    const toY = (val: number) => padding.top + plotH - (Math.max(0, Math.min(1, val))) * plotH;

    // Shaded 20-600 Hz PCG band
    const bandX1 = toX(20);
    const bandX2 = toX(600);

    let p = '';
    for (let i = 0; i < freqs.length; i++) {
      if (freqs[i] > fMax) break;
      const x = toX(freqs[i]);
      const y = toY(coherence[i]);
      p += i === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible select-none">
        {/* Shaded PCG band */}
        <rect
          x={bandX1}
          y={padding.top}
          width={bandX2 - bandX1}
          height={plotH}
          fill="var(--selection-window)"
          opacity="0.25"
        />

        {/* Grid lines */}
        <line x1={padding.left} y1={padding.top + plotH * 0.5} x2={padding.left + plotW} y2={padding.top + plotH * 0.5} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + plotH} stroke="var(--border-strong)" strokeWidth="1" />
        <line x1={padding.left} y1={padding.top + plotH} x2={padding.left + plotW} y2={padding.top + plotH} stroke="var(--border-strong)" strokeWidth="1" />

        {/* Labels */}
        <text x={padding.left - 8} y={padding.top + 4} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">1.00</text>
        <text x={padding.left - 8} y={padding.top + plotH * 0.5 + 3} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">0.50</text>
        <text x={padding.left - 8} y={padding.top + plotH} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">0.00</text>

        <text x={padding.left} y={padding.top + plotH + 18} textAnchor="start" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">0 Hz</text>
        <text x={toX(20)} y={padding.top - 5} textAnchor="middle" className="text-[9px] font-mono-code fill-[var(--accent-metal)]">20Hz</text>
        <text x={toX(600)} y={padding.top - 5} textAnchor="middle" className="text-[9px] font-mono-code fill-[var(--accent-metal)]">600Hz Passband</text>
        <text x={padding.left + plotW} y={padding.top + plotH + 18} textAnchor="end" className="text-[10px] font-mono-code fill-[var(--on-surface-variant)]">{fMax.toFixed(0)} Hz</text>

        {p && <path d={p} fill="none" stroke="var(--accent-metal)" strokeWidth="1.8" strokeLinecap="round" />}
      </svg>
    );
  };

  const selectedAsset = referenceAssets.find(a => a.asset_id === selectedAssetId);
  const selectedSession = sessions.find(s => s.session_id === selectedSessionId);

  return (
    <div
      id="analysis-workbench"
      className="flex-1 flex flex-col h-full overflow-y-auto px-6 py-5 select-none transition-colors"
      style={{ backgroundColor: 'var(--bg-canvas)' }}
    >
      <div className="max-w-6xl mx-auto w-full flex flex-col gap-6 pb-12">
        {/* Header Section */}
        <div className="pb-4 border-b flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 font-mono-code text-[11px] uppercase tracking-widest text-[var(--accent-metal)] font-semibold">
              <span>Phantom Validation Laboratory</span>
              <span>•</span>
              <span>Session Analysis &amp; Workbench</span>
            </div>
            <h1 className="font-serif-display text-2xl font-semibold text-[var(--on-surface)] tracking-tight">
              Engineering Comparison &amp; Validation Workbench
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-2xl">
              Inspect session acquisition integrity, align captures against verified reference signals, and quantify acoustic response.
            </p>
          </div>

          {/* Sub-tab Navigation */}
          <div
            className="flex items-center p-1 rounded-lg border font-mono-code text-xs shadow-xs"
            style={{
              backgroundColor: 'var(--surface-muted)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <button
              onClick={() => setActiveTab('compare')}
              className={`px-3 py-1.5 rounded transition-colors cursor-pointer font-medium flex items-center gap-1.5 ${
                activeTab === 'compare'
                  ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
              }`}
            >
              <Zap size={14} />
              <span>Comparison</span>
            </button>
            <button
              onClick={() => setActiveTab('sessions')}
              className={`px-3 py-1.5 rounded transition-colors cursor-pointer font-medium flex items-center gap-1.5 ${
                activeTab === 'sessions'
                  ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
              }`}
            >
              <HardDrive size={14} />
              <span>Session Inspector ({sessions.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('references')}
              className={`px-3 py-1.5 rounded transition-colors cursor-pointer font-medium flex items-center gap-1.5 ${
                activeTab === 'references'
                  ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
              }`}
            >
              <FileAudio size={14} />
              <span>Reference Signals ({referenceAssets.length})</span>
            </button>
          </div>
        </div>

        {/* Phantom Workflow Banner */}
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)'
          }}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
              Controlled Laboratory Workflow
            </span>
            <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
              Phase-1 Phantom Integration Model
            </span>
          </div>

          {/* Workflow Diagram */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono-code text-[var(--on-surface)]">
            <span className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-medium">
              Known Reference WAV
            </span>
            <ArrowRight size={13} className="text-[var(--accent-metal)]" />
            <span className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-medium">
              Phantom Playback
            </span>
            <ArrowRight size={13} className="text-[var(--accent-metal)]" />
            <span className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-medium">
              Chestpiece / Mic
            </span>
            <ArrowRight size={13} className="text-[var(--accent-metal)]" />
            <span className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-medium">
              ESP32-S3 Stream
            </span>
            <ArrowRight size={13} className="text-[var(--accent-metal)]" />
            <span className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-medium">
              Session Recorder
            </span>
            <ArrowRight size={13} className="text-[var(--accent-metal)]" />
            <span className="px-2.5 py-1 rounded bg-[var(--accent-soft)] text-[var(--accent-oxblood)] border border-[var(--accent-oxblood)] font-bold">
              Engineering Comparison
            </span>
          </div>

          {/* Mandatory Engineering Validation Disclaimer */}
          <div className="flex items-start gap-2 text-xs text-[var(--on-surface-variant)] pt-1 border-t border-[var(--border-subtle)]/60">
            <Info size={14} className="text-[var(--accent-metal)] shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Engineering Validation Notice:</strong> Reference-vs-capture analysis is intended for controlled engineering validation. Results depend on the playback transducer, acoustic coupling, sensor transfer function, and acquisition conditions. <em>No clinical diagnosis or medical quality score is implied.</em>
            </p>
          </div>
        </div>

        {/* Tab 1: Comparison & Workbench View */}
        {activeTab === 'compare' && (
          <div className="flex flex-col gap-6">
            {/* Pair Selection Strip */}
            <div
              className="rounded-xl border p-5 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-5 shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              {/* Reference Selector */}
              <div className="flex-1 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--status-info)] font-bold flex items-center gap-1.5">
                    <FileAudio size={14} />
                    <span>Known Reference Input (Reference Stimulus)</span>
                  </label>
                  <button
                    onClick={() => setActiveTab('references')}
                    className="font-mono-code text-[11px] text-[var(--accent-metal)] hover:underline flex items-center gap-0.5 cursor-pointer"
                  >
                    <span>Manage / Upload</span>
                    <ChevronRight size={12} />
                  </button>
                </div>

                <select
                  value={selectedAssetId || ''}
                  onChange={(e) => setSelectedAssetId(e.target.value || null)}
                  className="w-full px-3 py-2 rounded-lg border text-xs font-mono-code focus:outline-none focus:ring-1 focus:ring-[var(--accent-oxblood)] cursor-pointer"
                  style={{
                    backgroundColor: 'var(--surface-muted)',
                    borderColor: 'var(--border-strong)',
                    color: 'var(--on-surface)'
                  }}
                >
                  <option value="">-- Choose Known Reference WAV --</option>
                  {referenceAssets.map(asset => (
                    <option key={asset.asset_id} value={asset.asset_id}>
                      {asset.filename} ({asset.sample_rate_hz} Hz · {asset.duration_s.toFixed(2)}s)
                    </option>
                  ))}
                </select>

                {selectedAsset ? (
                  <div className="font-mono-code text-[10px] text-[var(--on-surface-variant)] flex items-center gap-2">
                    <span>Asset: <code>{selectedAsset.asset_id}</code></span>
                    <span>•</span>
                    <span className="truncate max-w-[200px]" title={selectedAsset.sha256}>SHA: {selectedAsset.sha256.slice(0, 12)}…</span>
                  </div>
                ) : (
                  <span className="font-mono-code text-[10px] text-[var(--status-warning)]">
                    No reference selected. Import or choose a known reference WAV.
                  </span>
                )}
              </div>

              {/* Comparison Arrow / Action */}
              <div className="flex flex-col items-center justify-center shrink-0 px-2">
                <button
                  onClick={handleRunComparison}
                  disabled={!selectedAssetId || !selectedSessionId || isComparing}
                  className={`px-5 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2 shadow-xs transition-all cursor-pointer ${
                    selectedAssetId && selectedSessionId && !isComparing
                      ? 'bg-[var(--accent-oxblood)] text-white hover:opacity-90 active:scale-95'
                      : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] opacity-50 cursor-not-allowed border border-[var(--border-subtle)]'
                  }`}
                >
                  <Zap size={14} className={isComparing ? 'animate-spin' : ''} />
                  <span>{isComparing ? 'Aligning Signals…' : 'Run Engineering Comparison'}</span>
                </button>
              </div>

              {/* Capture Session Selector */}
              <div className="flex-1 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-oxblood)] font-bold flex items-center gap-1.5">
                    <HardDrive size={14} />
                    <span>Captured Auscultation Session</span>
                  </label>
                  <button
                    onClick={() => setActiveTab('sessions')}
                    className="font-mono-code text-[11px] text-[var(--accent-metal)] hover:underline flex items-center gap-0.5 cursor-pointer"
                  >
                    <span>Inspect Sessions</span>
                    <ChevronRight size={12} />
                  </button>
                </div>

                <select
                  value={selectedSessionId || ''}
                  onChange={(e) => setSelectedSessionId(e.target.value || null)}
                  className="w-full px-3 py-2 rounded-lg border text-xs font-mono-code focus:outline-none focus:ring-1 focus:ring-[var(--accent-oxblood)] cursor-pointer"
                  style={{
                    backgroundColor: 'var(--surface-muted)',
                    borderColor: 'var(--border-strong)',
                    color: 'var(--on-surface)'
                  }}
                >
                  <option value="">-- Choose Recorded Session --</option>
                  {sessions.map(s => (
                    <option key={s.session_id} value={s.session_id}>
                      {s.session_id} ({s.duration_s.toFixed(1)}s · {s.sample_rate_hz} Hz · {s.source})
                    </option>
                  ))}
                </select>

                {selectedSession ? (
                  <div className="font-mono-code text-[10px] text-[var(--on-surface-variant)] flex items-center gap-2">
                    <span>Mode: <strong className="uppercase">{selectedSession.acquisition_mode}</strong></span>
                    <span>•</span>
                    <span>{selectedSession.stream_quality.is_healthy ? '0 drops' : `${selectedSession.stream_quality.dropped_blocks} drops`}</span>
                  </div>
                ) : (
                  <span className="font-mono-code text-[10px] text-[var(--status-warning)]">
                    No session selected. Record a session in Live Workspace first.
                  </span>
                )}
              </div>
            </div>

            {/* Error Message Banner */}
            {comparisonError && (
              <div className="p-4 rounded-xl border border-[var(--status-danger)] bg-[var(--surface-card)] flex items-center gap-3 text-xs text-[var(--status-danger)]">
                <AlertCircle size={16} className="shrink-0" />
                <span>{comparisonError}</span>
              </div>
            )}

            {/* Comparison Results Section */}
            {comparisonResult && (
              <div className="flex flex-col gap-6">
                {/* Result Top Action Bar */}
                <div
                  className="rounded-xl border p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[var(--status-success)]/15 text-[var(--status-success)] flex items-center justify-center">
                      <CheckCircle2 size={18} />
                    </div>
                    <div>
                      <div className="font-serif-display font-semibold text-base text-[var(--on-surface)]">
                        Analysis Complete: {comparisonResult.analysis_id}
                      </div>
                      <div className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                        Aligned at {new Date(comparisonResult.created_at_utc).toLocaleString()} · Schema v{comparisonResult.version}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleExportReport}
                      className="px-4 py-2 rounded-lg border font-mono-code text-xs text-[var(--on-surface)] border-[var(--border-strong)] hover:border-[var(--accent-oxblood)] hover:text-[var(--accent-oxblood)] flex items-center gap-2 shadow-xs cursor-pointer"
                    >
                      <Download size={14} />
                      <span>Export Comparison Report (JSON)</span>
                    </button>
                  </div>
                </div>

                {/* Alignment Parameters Panel */}
                <div
                  className="rounded-xl border p-5 flex flex-col gap-3 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold flex items-center gap-2">
                    <Sliders size={14} />
                    <span>Temporal Alignment &amp; Resampling Parameters</span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1 font-mono-code">
                    <div className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">Estimated Delay</span>
                      <span className="text-base font-bold text-[var(--accent-oxblood)]">
                        {comparisonResult.alignment.delay_ms >= 0 ? `+${comparisonResult.alignment.delay_ms.toFixed(2)}` : comparisonResult.alignment.delay_ms.toFixed(2)} ms
                      </span>
                      <span className="text-[10px] text-[var(--accent-metal)]">
                        {comparisonResult.alignment.delay_samples} samples
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">Overlap Window</span>
                      <span className="text-base font-bold text-[var(--on-surface)]">
                        {comparisonResult.alignment.overlap_duration_s.toFixed(2)} s
                      </span>
                      <span className="text-[10px] text-[var(--accent-metal)]">
                        {comparisonResult.alignment.overlap_samples} samples
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">Resampling Status</span>
                      <span className="text-base font-bold text-[var(--on-surface)]">
                        {comparisonResult.alignment.resampled ? 'Resampled' : 'Native Match'}
                      </span>
                      <span className="text-[10px] text-[var(--accent-metal)]">
                        Target: {comparisonResult.alignment.effective_sample_rate_hz} Hz
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase">Acquisition Mode</span>
                      <span className="text-base font-bold text-[var(--accent-oxblood)] uppercase truncate">
                        {comparisonResult.capture.acquisition_mode}
                      </span>
                      <span className="text-[10px] text-[var(--accent-metal)] truncate">
                        {comparisonResult.capture.source}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Similarity & Engineering Metrics Grid */}
                <div
                  className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                      Quantitative Signal Similarity &amp; Amplitude Metrics
                    </span>
                    <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                      Engineering metrics · Evaluated on full-rate audio
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono-code">
                    {/* NCC */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] group relative">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Normalized Cross-Corr</span>
                        <Info size={12} className="text-[var(--accent-metal)]" />
                      </div>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.normalized_cross_correlation.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        1.000 = identical shape after alignment
                      </span>
                    </div>

                    {/* Least-Squares Gain */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] group relative">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Least-Squares Gain (g)</span>
                        <Info size={12} className="text-[var(--accent-metal)]" />
                      </div>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.least_squares_gain.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Linear amplitude scaling estimate
                      </span>
                    </div>

                    {/* RMS Gain Ratio */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] group relative">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">RMS Gain Ratio</span>
                        <Info size={12} className="text-[var(--status-warning)]" />
                      </div>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.rms_gain_ratio.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--status-warning)]">
                        Influenced by additive noise
                      </span>
                    </div>

                    {/* Peak Gain Ratio */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Peak Gain Ratio</span>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.peak_gain_ratio.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Ratio of extreme absolute peaks
                      </span>
                    </div>

                    {/* SER dB */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Signal-to-Error (SER)</span>
                      <span className="text-xl font-bold text-[var(--accent-oxblood)]">
                        {comparisonResult.metrics.signal_to_error_ratio_db.toFixed(2)} dB
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Reference vs residual error energy
                      </span>
                    </div>

                    {/* RMSE */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">RMSE</span>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.rmse.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Root Mean Square Error
                      </span>
                    </div>

                    {/* NRMSE */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Normalized RMSE</span>
                      <span className="text-xl font-bold text-[var(--on-surface)]">
                        {comparisonResult.metrics.normalized_rmse.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Error normalized to reference RMS
                      </span>
                    </div>

                    {/* Mean Coherence */}
                    <div className="flex flex-col gap-1 p-3.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                      <span className="text-[10px] text-[var(--on-surface-variant)] uppercase font-semibold">Mean Coherence (20–600Hz)</span>
                      <span className="text-xl font-bold text-[var(--accent-oxblood)]">
                        {comparisonResult.metrics.mean_coherence_pcg_band.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[var(--on-surface-variant)]">
                        Spectral linear correlation
                      </span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded bg-[var(--surface-muted)] text-[11px] font-mono-code text-[var(--on-surface-variant)] flex items-center gap-2">
                    <Info size={13} className="text-[var(--accent-metal)] shrink-0" />
                    <span><strong>Technical Note:</strong> RMS gain ratio is influenced by additive noise and is not a pure linear gain estimator. Use Least-Squares Gain for optimal amplitude scale estimation.</span>
                  </div>
                </div>

                {/* Aligned Waveforms Visualizer */}
                <div
                  className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                        Aligned PCG Waveforms &amp; Residual Error
                      </h3>
                      <p className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                        Reference vs Capture aligned along common time axis (ms). Display-decimated (≤600 points).
                      </p>
                    </div>

                    {/* Trace Toggles */}
                    <div className="flex items-center gap-3 font-mono-code text-xs">
                      <button
                        onClick={() => setShowRefTrace(!showRefTrace)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded border transition-colors cursor-pointer ${
                          showRefTrace ? 'bg-[var(--status-info)]/15 border-[var(--status-info)] text-[var(--status-info)] font-bold' : 'opacity-40 border-[var(--border-subtle)] text-[var(--on-surface-variant)]'
                        }`}
                      >
                        <span className="w-2 h-2 rounded-full bg-[var(--status-info)]" />
                        <span>Reference</span>
                      </button>

                      <button
                        onClick={() => setShowCapTrace(!showCapTrace)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded border transition-colors cursor-pointer ${
                          showCapTrace ? 'bg-[var(--accent-oxblood)]/15 border-[var(--accent-oxblood)] text-[var(--accent-oxblood)] font-bold' : 'opacity-40 border-[var(--border-subtle)] text-[var(--on-surface-variant)]'
                        }`}
                      >
                        <span className="w-2 h-2 rounded-full bg-[var(--accent-oxblood)]" />
                        <span>Capture</span>
                      </button>

                      <button
                        onClick={() => setShowErrorTrace(!showErrorTrace)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded border transition-colors cursor-pointer ${
                          showErrorTrace ? 'bg-[var(--status-warning)]/15 border-[var(--status-warning)] text-[var(--status-warning)] font-bold' : 'opacity-40 border-[var(--border-subtle)] text-[var(--on-surface-variant)]'
                        }`}
                      >
                        <span className="w-2 h-2 rounded-full bg-[var(--status-warning)]" />
                        <span>Residual Error</span>
                      </button>
                    </div>
                  </div>

                  <div className="w-full h-64 border rounded-lg bg-[var(--bg-deep)] p-2">
                    {renderSvgWaveform(
                      comparisonResult.display.aligned_reference,
                      comparisonResult.display.aligned_capture,
                      comparisonResult.display.error,
                      comparisonResult.display.time_ms,
                      800,
                      240
                    )}
                  </div>
                </div>

                {/* Spectral Comparison & Coherence Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Spectral PSD Comparison */}
                  <div
                    className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
                    style={{
                      backgroundColor: 'var(--surface-card)',
                      borderColor: 'var(--border-subtle)'
                    }}
                  >
                    <div>
                      <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                        Power Spectral Density (PSD)
                      </h3>
                      <p className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                        Welch PSD comparison (dB/Hz) across 0–1000 Hz. Band boundaries at 20, 150, 600 Hz.
                      </p>
                    </div>

                    <div className="w-full h-52 border rounded-lg bg-[var(--bg-deep)] p-2">
                      {renderSvgPsd(
                        comparisonResult.display.spectrum_frequencies_hz,
                        comparisonResult.display.spectrum_reference_db,
                        comparisonResult.display.spectrum_capture_db,
                        500,
                        200
                      )}
                    </div>

                    {/* Dominant Frequency Comparison */}
                    <div className="grid grid-cols-3 gap-2 font-mono-code text-xs pt-1 border-t border-[var(--border-subtle)]">
                      <div>
                        <span className="text-[10px] text-[var(--status-info)] uppercase font-semibold">Ref Dominant</span>
                        <div className="font-bold text-[var(--on-surface)]">{comparisonResult.metrics.dominant_frequency_reference_hz.toFixed(1)} Hz</div>
                      </div>
                      <div>
                        <span className="text-[10px] text-[var(--accent-oxblood)] uppercase font-semibold">Cap Dominant</span>
                        <div className="font-bold text-[var(--on-surface)]">{comparisonResult.metrics.dominant_frequency_capture_hz.toFixed(1)} Hz</div>
                      </div>
                      <div>
                        <span className="text-[10px] text-[var(--accent-metal)] uppercase font-semibold">Difference (Δf)</span>
                        <div className="font-bold text-[var(--accent-oxblood)]">{comparisonResult.metrics.dominant_frequency_difference_hz.toFixed(1)} Hz</div>
                      </div>
                    </div>
                  </div>

                  {/* Magnitude-Squared Coherence Curve */}
                  <div
                    className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
                    style={{
                      backgroundColor: 'var(--surface-card)',
                      borderColor: 'var(--border-subtle)'
                    }}
                  >
                    <div>
                      <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                        Magnitude-Squared Coherence γ²(f)
                      </h3>
                      <p className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                        Linear acoustic relationship across frequency. Shaded region: 20–600 Hz PCG passband.
                      </p>
                    </div>

                    <div className="w-full h-52 border rounded-lg bg-[var(--bg-deep)] p-2">
                      {renderSvgCoherence(
                        comparisonResult.display.coherence_frequencies_hz,
                        comparisonResult.display.coherence_values,
                        500,
                        200
                      )}
                    </div>

                    {/* Band Energy Ratio Differences */}
                    <div className="flex flex-col gap-1 pt-1 border-t border-[var(--border-subtle)] font-mono-code text-[11px]">
                      <span className="text-[10px] text-[var(--accent-metal)] uppercase font-semibold">Band Energy Ratio Differences (Capture - Reference)</span>
                      <div className="grid grid-cols-4 gap-2 text-center pt-1">
                        <div className="p-1 rounded bg-[var(--surface-muted)]">
                          <div className="text-[9px] text-[var(--on-surface-variant)]">0–20 Hz</div>
                          <div className="font-bold text-[var(--on-surface)]">{((comparisonResult.metrics.band_energy_ratio_diffs?.['0_20'] || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div className="p-1 rounded bg-[var(--surface-muted)]">
                          <div className="text-[9px] text-[var(--on-surface-variant)]">20–150 Hz</div>
                          <div className="font-bold text-[var(--on-surface)]">{((comparisonResult.metrics.band_energy_ratio_diffs?.['20_150'] || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div className="p-1 rounded bg-[var(--surface-muted)]">
                          <div className="text-[9px] text-[var(--on-surface-variant)]">150–600 Hz</div>
                          <div className="font-bold text-[var(--on-surface)]">{((comparisonResult.metrics.band_energy_ratio_diffs?.['150_600'] || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div className="p-1 rounded bg-[var(--surface-muted)]">
                          <div className="text-[9px] text-[var(--on-surface-variant)]">&gt;600 Hz</div>
                          <div className="font-bold text-[var(--on-surface)]">{((comparisonResult.metrics.band_energy_ratio_diffs?.['600_plus'] || 0) * 100).toFixed(1)}%</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Provenance Strip */}
                <div
                  className="rounded-xl border p-4 flex flex-wrap items-center justify-between gap-3 font-mono-code text-[10px] text-[var(--on-surface-variant)]"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span>App: <strong>v{comparisonResult.provenance.app_version}</strong></span>
                    <span>•</span>
                    <span>Git: <strong>{comparisonResult.provenance.git_commit_sha || 'N/A'}</strong></span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span>Python: <strong>{comparisonResult.provenance.python_version}</strong></span>
                    <span>•</span>
                    <span>NumPy: <strong>{comparisonResult.provenance.numpy_version}</strong></span>
                    <span>•</span>
                    <span>SciPy: <strong>{comparisonResult.provenance.scipy_version}</strong></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Session Inspector View */}
        {activeTab === 'sessions' && (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                Acquisition Sessions &amp; Integrity Inspector
              </h2>
              <button
                onClick={refreshSessions}
                disabled={loadingSessions}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono-code text-xs text-[var(--accent-oxblood)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)] cursor-pointer"
              >
                <RefreshCw size={13} className={loadingSessions ? 'animate-spin' : ''} />
                <span>Refresh Sessions</span>
              </button>
            </div>

            {sessions.length === 0 ? (
              <div
                className="rounded-xl border p-12 text-center flex flex-col items-center gap-3 shadow-xs"
                style={{
                  backgroundColor: 'var(--surface-card)',
                  borderColor: 'var(--border-subtle)'
                }}
              >
                <HardDrive size={36} className="text-[var(--accent-metal)]" />
                <h4 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  No recorded sessions available
                </h4>
                <p className="text-xs text-[var(--on-surface-variant)] max-w-md">
                  Record an acquisition session in Live Workspace, or replay a synthetic specimen to create an analysis session.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Session List Column */}
                <div className="flex flex-col gap-3 md:col-span-1">
                  <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                    Recorded Sessions ({sessions.length})
                  </span>
                  <div className="flex flex-col gap-2 max-h-[500px] overflow-y-auto pr-1">
                    {sessions.map(s => {
                      const isSelected = s.session_id === selectedSessionId;
                      return (
                        <div
                          key={s.session_id}
                          onClick={() => setSelectedSessionId(s.session_id)}
                          className={`p-3 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5 shadow-xs ${
                            isSelected
                              ? 'border-[var(--accent-oxblood)] bg-[var(--surface-card)] ring-1 ring-[var(--accent-oxblood)]'
                              : 'border-[var(--border-subtle)] bg-[var(--surface-card)] hover:border-[var(--border-strong)]'
                          }`}
                        >
                          <div className="flex items-center justify-between font-mono-code text-xs">
                            <span className="font-bold text-[var(--accent-oxblood)]">{s.session_id}</span>
                            <span className="text-[10px] text-[var(--on-surface-variant)]">{s.duration_s.toFixed(1)}s</span>
                          </div>

                          <div className="flex items-center justify-between font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                            <span className="uppercase font-semibold">{s.acquisition_mode}</span>
                            <span className={s.stream_quality.is_healthy ? 'text-[var(--status-success)]' : 'text-[var(--status-warning)]'}>
                              {s.stream_quality.is_healthy ? 'Optimal' : `${s.stream_quality.dropped_blocks} drops`}
                            </span>
                          </div>

                          <div className="font-mono-code text-[9px] text-[var(--text-tertiary)] truncate">
                            {new Date(s.started_at_utc).toLocaleString()}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Session Inspector Details Column */}
                <div className="md:col-span-2 flex flex-col gap-4">
                  {loadingSummary && (
                    <div className="p-8 text-center font-mono-code text-xs text-[var(--accent-metal)]">
                      Loading session analysis summary…
                    </div>
                  )}

                  {!loadingSummary && sessionSummary && (
                    <div
                      className="rounded-xl border p-5 flex flex-col gap-5 shadow-xs"
                      style={{
                        backgroundColor: 'var(--surface-card)',
                        borderColor: 'var(--border-subtle)'
                      }}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-mono-code text-[11px] text-[var(--accent-metal)] uppercase font-bold">
                            Session Inspector
                          </div>
                          <h3 className="font-serif-display text-xl font-bold text-[var(--on-surface)]">
                            {sessionSummary.session_id}
                          </h3>
                        </div>

                        <button
                          onClick={() => {
                            setSelectedSessionId(sessionSummary.session_id);
                            setActiveTab('compare');
                          }}
                          className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-[var(--accent-oxblood)] hover:opacity-90 flex items-center gap-1.5 shadow-xs cursor-pointer"
                        >
                          <Zap size={14} />
                          <span>Select for Comparison</span>
                        </button>
                      </div>

                      {/* Metadata Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono-code text-xs">
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Sample Rate</span>
                          <div className="font-bold text-[var(--on-surface)]">{sessionSummary.sample_rate_hz} Hz</div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Duration / Samples</span>
                          <div className="font-bold text-[var(--on-surface)]">{sessionSummary.duration_s.toFixed(2)}s ({sessionSummary.total_samples} smp)</div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Acquisition Mode</span>
                          <div className="font-bold text-[var(--accent-oxblood)] uppercase">{sessionSummary.acquisition_mode}</div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Source</span>
                          <div className="font-bold text-[var(--on-surface)]">{sessionSummary.source}</div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Stream Health</span>
                          <div className={`font-bold ${sessionSummary.stream_quality.is_healthy ? 'text-[var(--status-success)]' : 'text-[var(--status-warning)]'}`}>
                            {sessionSummary.stream_quality.is_healthy ? 'Healthy (0 gaps)' : `${sessionSummary.stream_quality.dropped_blocks} drops`}
                          </div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
                          <span className="text-[9px] text-[var(--on-surface-variant)] uppercase">Termination</span>
                          <div className="font-bold text-[var(--on-surface)]">{sessionSummary.termination_reason}</div>
                        </div>
                      </div>

                      {/* Integrity Check */}
                      <div className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] font-mono-code text-[10px] flex flex-col gap-1">
                        <div className="text-[var(--accent-metal)] font-bold uppercase tracking-wider">Acquisition Integrity Signatures</div>
                        <div className="truncate text-[var(--on-surface-variant)]">WAV SHA-256: <code>{sessionSummary.raw_wav_sha256}</code></div>
                        <div className="text-[var(--on-surface-variant)]">Git Commit: <code>{sessionSummary.git_commit_sha || 'N/A'}</code></div>
                      </div>

                      {/* Signal Metrics */}
                      <div className="flex flex-col gap-2">
                        <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                          Signal Metrics (Raw vs Filtered 20–600 Hz)
                        </span>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono-code text-xs">
                          <div className="p-2.5 rounded bg-[var(--surface-muted)]">
                            <span className="text-[9px] text-[var(--on-surface-variant)]">Raw RMS</span>
                            <div className="font-bold text-[var(--on-surface)]">{sessionSummary.metrics.raw_rms.toFixed(4)}</div>
                          </div>
                          <div className="p-2.5 rounded bg-[var(--surface-muted)]">
                            <span className="text-[9px] text-[var(--on-surface-variant)]">Filtered RMS</span>
                            <div className="font-bold text-[var(--accent-oxblood)]">{sessionSummary.metrics.filtered_rms.toFixed(4)}</div>
                          </div>
                          <div className="p-2.5 rounded bg-[var(--surface-muted)]">
                            <span className="text-[9px] text-[var(--on-surface-variant)]">Crest Factor</span>
                            <div className="font-bold text-[var(--on-surface)]">{sessionSummary.metrics.filtered_crest_factor.toFixed(2)}</div>
                          </div>
                          <div className="p-2.5 rounded bg-[var(--surface-muted)]">
                            <span className="text-[9px] text-[var(--on-surface-variant)]">Dominant Freq</span>
                            <div className="font-bold text-[var(--accent-oxblood)]">{sessionSummary.metrics.dominant_frequency_hz.toFixed(1)} Hz</div>
                          </div>
                        </div>
                      </div>

                      {/* Decimated Preview Waveform */}
                      {sessionSummary.display.raw_points && sessionSummary.display.raw_points.length > 0 && (
                        <div className="flex flex-col gap-2">
                          <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                            Waveform Preview (Bounded Display Series)
                          </span>
                          <div className="w-full h-36 border rounded-lg bg-[var(--bg-deep)] p-2">
                            {renderSvgWaveform(
                              sessionSummary.display.raw_points,
                              sessionSummary.display.filtered_points,
                              [],
                              sessionSummary.display.time_points_s.map(t => t * 1000),
                              600,
                              130
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Reference Signals Library */}
        {activeTab === 'references' && (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  Reference PCG Signal Library
                </h2>
                <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)]">
                  Known reference audio files used for phantom acoustic playback and transfer function validation.
                </p>
              </div>

              <button
                onClick={refreshAssets}
                disabled={loadingAssets}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono-code text-xs text-[var(--accent-oxblood)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)] cursor-pointer"
              >
                <RefreshCw size={13} className={loadingAssets ? 'animate-spin' : ''} />
                <span>Refresh Library</span>
              </button>
            </div>

            {/* Upload Box */}
            <div
              className="rounded-xl border border-dashed p-6 flex flex-col items-center justify-center gap-3 text-center transition-colors shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-strong)'
              }}
            >
              <UploadCloud size={32} className="text-[var(--accent-metal)]" />
              <div className="flex flex-col gap-1">
                <span className="font-serif-display font-semibold text-sm text-[var(--on-surface)]">
                  Import Reference PCG Signal
                </span>
                <span className="font-mono-code text-[11px] text-[var(--on-surface-variant)]">
                  Upload standard WAV PCG audio. Mono channels only. Maximum 100 MB.
                </span>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,audio/wav"
                onChange={handleWavUpload}
                className="hidden"
                id="wav-file-input"
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingAsset}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-[var(--accent-oxblood)] hover:opacity-90 flex items-center gap-2 shadow-xs cursor-pointer active:scale-95"
              >
                <FileAudio size={14} className={uploadingAsset ? 'animate-spin' : ''} />
                <span>{uploadingAsset ? 'Validating & Importing…' : 'Choose WAV File'}</span>
              </button>

              {uploadError && (
                <div className="font-mono-code text-xs text-[var(--status-danger)] flex items-center gap-1.5 pt-1">
                  <AlertCircle size={14} />
                  <span>{uploadError}</span>
                </div>
              )}
            </div>

            {/* Reference Asset Cards */}
            <div className="flex flex-col gap-3">
              <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                Imported Reference Assets ({referenceAssets.length})
              </span>

              {referenceAssets.length === 0 ? (
                <div
                  className="rounded-xl border p-8 text-center flex flex-col items-center gap-2 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <FileAudio size={28} className="text-[var(--accent-metal)]" />
                  <span className="text-xs text-[var(--on-surface-variant)] font-mono-code">
                    No reference assets imported yet. Upload a verified PCG WAV above.
                  </span>
                </div>
              ) : (
                referenceAssets.map(asset => {
                  const isSelected = asset.asset_id === selectedAssetId;
                  return (
                    <div
                      key={asset.asset_id}
                      className={`rounded-xl border p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all shadow-xs ${
                        isSelected
                          ? 'border-[var(--accent-oxblood)] ring-1 ring-[var(--accent-oxblood)]'
                          : 'hover:border-[var(--border-strong)]'
                      }`}
                      style={{
                        backgroundColor: 'var(--surface-card)',
                        borderColor: isSelected ? 'var(--accent-oxblood)' : 'var(--border-subtle)'
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className="w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 text-[var(--status-info)]"
                          style={{
                            backgroundColor: 'var(--surface-muted)',
                            borderColor: 'var(--border-subtle)'
                          }}
                        >
                          <FileAudio size={20} />
                        </div>

                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2 font-mono-code text-xs">
                            <span className="font-bold text-[var(--on-surface)]">{asset.filename}</span>
                            <span className="text-[var(--accent-metal)]">•</span>
                            <span className="text-[var(--on-surface-variant)]">{asset.sample_rate_hz} Hz</span>
                            <span className="text-[var(--accent-metal)]">•</span>
                            <span className="text-[var(--on-surface-variant)]">{asset.duration_s.toFixed(2)}s</span>
                          </div>

                          <div className="font-mono-code text-[10px] text-[var(--on-surface-variant)] flex items-center gap-2">
                            <span>ID: <code>{asset.asset_id}</code></span>
                            <span>•</span>
                            <span className="truncate max-w-[280px]">SHA-256: <code>{asset.sha256}</code></span>
                          </div>

                          <div className="font-mono-code text-[9px] text-[var(--text-tertiary)]">
                            Imported: {new Date(asset.created_at_utc).toLocaleString()} · {(asset.file_size_bytes / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                        <button
                          onClick={() => {
                            setSelectedAssetId(asset.asset_id);
                            setActiveTab('compare');
                          }}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-xs cursor-pointer ${
                            isSelected
                              ? 'bg-[var(--accent-oxblood)] text-white'
                              : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-strong)] hover:border-[var(--accent-oxblood)]'
                          }`}
                        >
                          {isSelected ? <Check size={13} /> : <Zap size={13} />}
                          <span>{isSelected ? 'Active Reference' : 'Select'}</span>
                        </button>

                        <button
                          onClick={() => handleDeleteAsset(asset.asset_id)}
                          className="p-1.5 rounded-lg border border-[var(--border-subtle)] text-[var(--status-danger)] hover:bg-[var(--surface-muted)] cursor-pointer"
                          title="Delete reference asset"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
