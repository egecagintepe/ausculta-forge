import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Layers,
  Activity,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Clock,
  Heart,
  TrendingUp,
  Cpu,
  ShieldAlert,
  ShieldCheck,
  Download,
  Sliders,
  Check,
  Eye,
  EyeOff,
  Crosshair,
} from 'lucide-react';
import {
  SpringerSegmentationModelSummary,
  SpringerSegmentationReport,
  StateIntervalItem,
} from '../types';
import { bridgeClient, SessionItem } from '../api/bridgeClient';

interface SegmentationLabProps {
  isDark: boolean;
  sessions: SessionItem[];
  selectedSessionId: string | null;
  onSelectSessionId: (id: string) => void;
  addToast?: (message: string, type?: 'info' | 'success' | 'warning') => void;
}

const STATE_CONFIG: Record<
  number,
  {
    name: string;
    label: string;
    bgFill: string;
    strokeBorder: string;
    textCol: string;
    badgeCls: string;
  }
> = {
  1: {
    name: 'S1',
    label: 'Model-derived S1 interval',
    bgFill: 'rgba(225, 29, 72, 0.22)',
    strokeBorder: 'rgba(225, 29, 72, 0.85)',
    textCol: '#f43f5e',
    badgeCls: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  },
  2: {
    name: 'SYSTOLE',
    label: 'Estimated systole interval',
    bgFill: 'rgba(217, 119, 6, 0.20)',
    strokeBorder: 'rgba(217, 119, 6, 0.80)',
    textCol: '#fbbf24',
    badgeCls: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  },
  3: {
    name: 'S2',
    label: 'Model-derived S2 interval',
    bgFill: 'rgba(13, 148, 136, 0.22)',
    strokeBorder: 'rgba(13, 148, 136, 0.85)',
    textCol: '#2dd4bf',
    badgeCls: 'bg-teal-500/20 text-teal-300 border-teal-500/40',
  },
  4: {
    name: 'DIASTOLE',
    label: 'Estimated diastole interval',
    bgFill: 'rgba(99, 102, 241, 0.16)',
    strokeBorder: 'rgba(99, 102, 241, 0.70)',
    textCol: '#818cf8',
    badgeCls: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
  },
};

const ENVELOPE_COLORS: Record<string, { stroke: string; label: string }> = {
  homomorphic: { stroke: '#06b6d4', label: 'Homomorphic Envelope' },
  hilbert: { stroke: '#a855f7', label: 'Hilbert Analytic Modulus' },
  psd: { stroke: '#f59e0b', label: 'PSD 40–60 Hz Subband' },
  wavelet: { stroke: '#10b981', label: 'Wavelet Detail (DWT)' },
};

export const SegmentationLab: React.FC<SegmentationLabProps> = ({
  isDark,
  sessions,
  selectedSessionId,
  onSelectSessionId,
  addToast,
}) => {
  const [availableModels, setAvailableModels] = useState<SpringerSegmentationModelSummary[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [selectedProfileId, setSelectedProfileId] = useState<string>('SPRINGER_PHYSIONET_REFERENCE_V1');
  const [report, setReport] = useState<SpringerSegmentationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [showHelp, setShowHelp] = useState<boolean>(false);
  const [tableFilter, setTableFilter] = useState<string>('ALL');

  // Synchronized Multi-Lane Inspection state
  const [hoverTimeS, setHoverTimeS] = useState<number | null>(null);
  const [activeEnvelopes, setActiveEnvelopes] = useState<Record<string, boolean>>({
    homomorphic: true,
    hilbert: true,
    psd: true,
    wavelet: true,
  });

  // Selected session metadata
  const activeSession = useMemo(() => {
    return sessions.find(s => s.session_id === selectedSessionId) || null;
  }, [sessions, selectedSessionId]);

  // Sample rate compatibility guard (< 800 Hz)
  const isSampleRateIncompatible = useMemo(() => {
    if (!activeSession) return false;
    return activeSession.sample_rate_hz > 0 && activeSession.sample_rate_hz < 800;
  }, [activeSession]);

  // Load available models on mount
  useEffect(() => {
    let isMounted = true;
    bridgeClient.listSegmentationModels().then(models => {
      if (isMounted) {
        setAvailableModels(models);
        const demo = models.find(m => m.model_id === 'springer_demo_3feature_v1') || models[0];
        if (demo) {
          setSelectedModelId(demo.model_id);
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleExecuteSegmentation = useCallback(async () => {
    if (!selectedSessionId) {
      setErrorMsg('Please select a recorded PCG session first.');
      return;
    }
    if (isSampleRateIncompatible) {
      setErrorMsg(`Incompatible sample rate (${activeSession?.sample_rate_hz} Hz). Minimum 800 Hz required for 1000 Hz rational resampling.`);
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await bridgeClient.runSegmentation(
        selectedSessionId,
        selectedModelId ? selectedModelId : null,
        selectedProfileId,
        600
      );
      setReport(res);
      if (res.segmentation.status === 'MODEL_REQUIRED') {
        if (addToast) {
          addToast('Truthful Notice: No trained model selected. No state sequence fabricated.', 'info');
        }
      } else if (res.segmentation.status === 'SUCCESS') {
        if (addToast) {
          addToast(`Segmentation complete: ${res.segmentation.cycle_count} cardiac cycles isolated.`, 'success');
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Segmentation execution failed');
      if (addToast) {
        addToast(err.message || 'Segmentation execution failed', 'warning');
      }
    } finally {
      setLoading(false);
    }
  }, [selectedSessionId, selectedModelId, selectedProfileId, isSampleRateIncompatible, activeSession, addToast]);

  const seg = report?.segmentation;
  const intervals = report?.display?.state_intervals || [];
  const durationS = report?.session?.duration_s || 0.0;
  const isModelRequired = seg?.status === 'MODEL_REQUIRED';

  // Selected Model metadata
  const activeModelMeta = useMemo(() => {
    return availableModels.find(m => m.model_id === selectedModelId) || null;
  }, [availableModels, selectedModelId]);

  // Rhythm Regularity Score (derived from Springer cycle count and Schmidt timing)
  const rhythmConfidence = useMemo(() => {
    if (!seg || seg.status !== 'SUCCESS' || !seg.heart_rate_estimate_bpm) {
      return null;
    }
    const hr = seg.heart_rate_estimate_bpm;
    // Healthy physiological bounds: 40 - 150 BPM
    const isPhysiological = hr >= 40 && hr <= 150;
    const hasSufficientCycles = seg.cycle_count >= 2;
    if (isPhysiological && hasSufficientCycles) {
      return { score: 'HIGH', label: 'Regular Rhythm (High Autocorrelation Peak)', badgeCls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' };
    } else if (hr >= 30 && hr <= 180) {
      return { score: 'MODERATE', label: 'Moderate Confidence (Potential Baseline Variance)', badgeCls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
    }
    return { score: 'LOW', label: 'Low Rhythm Confidence (Atypical Periodicity or Noise)', badgeCls: 'bg-rose-500/20 text-rose-300 border-rose-500/40' };
  }, [seg]);

  // Hovered state interval and values
  const hoverDetails = useMemo(() => {
    if (hoverTimeS === null || durationS <= 0) return null;
    const matchedInterval = intervals.find(iv => hoverTimeS >= iv.start_s && hoverTimeS <= iv.end_s);
    return {
      timeS: hoverTimeS,
      interval: matchedInterval || null,
    };
  }, [hoverTimeS, durationS, intervals]);

  // Filter intervals for the table
  const filteredIntervals = useMemo(() => {
    if (tableFilter === 'ALL') return intervals;
    return intervals.filter(iv => iv.state_name === tableFilter);
  }, [intervals, tableFilter]);

  // Export JSON Report
  const handleExportJSON = () => {
    if (!report) return;
    const jsonStr = JSON.stringify(report, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.analysis_id || 'segmentation_report'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    if (addToast) addToast('Exported segmentation report JSON', 'info');
  };

  // Export Intervals CSV
  const handleExportCSV = () => {
    if (!report || intervals.length === 0) return;
    const header = 'Interval_Index,State_Number,State_Name,Start_Time_s,End_Time_s,Duration_ms,Type\n';
    const rows = intervals.map((iv, idx) => {
      const durMs = Math.round(iv.duration_s * 1000);
      return `${idx + 1},${iv.state},"${iv.state_name}",${iv.start_s.toFixed(4)},${iv.end_s.toFixed(4)},${durMs},"PREDICTION"`;
    }).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `segmentation_intervals_${report.session.session_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    if (addToast) addToast('Exported segmentation intervals CSV', 'info');
  };

  return (
    <div className="flex flex-col gap-5">
      {/* 1. Header Card & Session Pipeline Control */}
      <div
        className="rounded-xl border p-4 flex flex-col gap-4 shadow-xs"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center gap-2.5">
            <Layers size={18} className="text-[var(--accent-oxblood)]" />
            <div>
              <h2 className="font-mono-code font-bold text-sm text-[var(--on-surface)]">
                Springer LR-HSMM PCG Segmentation Lab
              </h2>
              <span className="text-[11px] font-mono-code text-[var(--on-surface-variant)]">
                Offline Acoustic Heart Sound Segmentation • S1, Systole, S2, Diastole Time-Axis Alignment
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="px-2.5 py-1 rounded-md text-xs font-mono-code flex items-center gap-1.5 border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
            >
              <Info size={13} />
              <span>{showHelp ? 'Hide Metrological Notes' : 'Metrological Notes'}</span>
              {showHelp ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            {report && (
              <>
                <button
                  onClick={handleExportJSON}
                  className="px-2.5 py-1 rounded-md text-xs font-mono-code flex items-center gap-1 border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
                  title="Export complete report JSON"
                >
                  <Download size={13} />
                  <span>Export JSON</span>
                </button>
                <button
                  onClick={handleExportCSV}
                  className="px-2.5 py-1 rounded-md text-xs font-mono-code flex items-center gap-1 border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
                  title="Export intervals table as CSV"
                >
                  <Download size={13} />
                  <span>Export CSV</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Controls Row: Session, Model, Profile, Action */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Session Picker */}
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-mono-code text-[var(--on-surface-variant)] font-bold">
              Target Recorded Session:
            </label>
            <select
              value={selectedSessionId || ''}
              onChange={e => onSelectSessionId(e.target.value)}
              className="bg-[var(--surface-muted)] border rounded px-2.5 py-1.5 text-xs font-mono-code text-[var(--on-surface)] focus:outline-hidden"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              {sessions.length === 0 && <option value="">No sessions recorded yet</option>}
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id} ({s.duration_s.toFixed(1)}s, {s.sample_rate_hz}Hz)
                </option>
              ))}
            </select>
          </div>

          {/* Model Artifact Picker */}
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-mono-code text-[var(--on-surface-variant)] font-bold">
              Springer Model Artifact:
            </label>
            <select
              value={selectedModelId}
              onChange={e => setSelectedModelId(e.target.value)}
              className="bg-[var(--surface-muted)] border rounded px-2.5 py-1.5 text-xs font-mono-code text-[var(--on-surface)] focus:outline-hidden"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value="">(None - Verify Model-Required Guard)</option>
              {availableModels.map(m => (
                <option key={m.model_id} value={m.model_id}>
                  {m.label} ({m.feature_count} feat)
                </option>
              ))}
            </select>
          </div>

          {/* Analysis Feature Profile */}
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-mono-code text-[var(--on-surface-variant)] font-bold">
              Acoustic Feature Profile:
            </label>
            <select
              value={selectedProfileId}
              onChange={e => setSelectedProfileId(e.target.value)}
              className="bg-[var(--surface-muted)] border rounded px-2.5 py-1.5 text-xs font-mono-code text-[var(--on-surface)] focus:outline-hidden"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value="SPRINGER_PHYSIONET_REFERENCE_V1">
                SPRINGER_PHYSIONET_REFERENCE_V1 (25–400Hz, Spike, 3-feat)
              </option>
              <option value="SPRINGER_PAPER_4FEATURE_V1">
                SPRINGER_PAPER_4FEATURE_V1 (1000Hz, Wavelet, 4-feat)
              </option>
            </select>
          </div>

          {/* Execute Button */}
          <div className="flex flex-col justify-end">
            <button
              onClick={handleExecuteSegmentation}
              disabled={loading || !selectedSessionId || isSampleRateIncompatible}
              className="px-4 py-2 rounded text-xs font-mono-code font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer bg-[var(--accent-oxblood)] text-white hover:opacity-90 disabled:opacity-40"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              <span>{loading ? 'Segmenting...' : 'Execute Segmentation'}</span>
            </button>
          </div>
        </div>

        {/* Sample Rate Pipeline Callout & Warning */}
        {activeSession && (
          <div className="flex flex-wrap items-center justify-between text-[11px] font-mono-code px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] text-[var(--on-surface-variant)]">
            <div className="flex items-center gap-3">
              <span>Native Audio: <strong className="text-[var(--on-surface)]">{activeSession.sample_rate_hz} Hz</strong></span>
              <span>→</span>
              <span>Rational Decimation: <strong className="text-[var(--on-surface)]">1000 Hz</strong></span>
              <span>→</span>
              <span>Feature Hop: <strong className="text-[var(--on-surface)]">50 Hz</strong> (20 ms window)</span>
            </div>
            {isSampleRateIncompatible ? (
              <span className="text-rose-500 font-bold flex items-center gap-1">
                <AlertCircle size={13} />
                INCOMPATIBLE SAMPLE RATE (&lt; 800 Hz)
              </span>
            ) : (
              <span className="text-emerald-500 font-bold flex items-center gap-1">
                <Check size={13} />
                Sample Rate Compatible
              </span>
            )}
          </div>
        )}
      </div>

      {/* 2. Educational & Scientific Boundaries Panel */}
      {showHelp && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs text-xs font-mono-code bg-[var(--surface-card)]"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2 text-[var(--accent-oxblood)] font-bold">
            <Info size={16} />
            <span>Mathematical Principles & Research Boundaries</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[var(--on-surface-variant)] leading-relaxed">
            <div>
              <p className="font-bold text-[var(--on-surface)] mb-1">How Springer LR-HSMM Works:</p>
              <p>
                1. Multi-envelope extraction: Homomorphic, Hilbert analytic modulus, PSD 40–60 Hz subband, and optional Wavelet detail.
                <br />
                2. Logistic Regression: Maps observations to state emission posteriors $P(S_t | O_t)$.
                <br />
                3. Duration priors: Schmidt autocorrelation determines cycle length T_cycle and systolic interval T_sys.
                <br />
                4. Extended Viterbi: Log-space dynamic programming enforcing strict cyclic order (S1 → Systole → S2 → Diastole).
              </p>
            </div>
            <div>
              <p className="font-bold text-[var(--on-surface)] mb-1">Strict Research Metrology Notice:</p>
              <p>
                The outputs generated are model-derived temporal acoustic segmentations only.
                This module does <strong className="text-[var(--on-surface)]">NOT</strong> perform medical diagnosis,
                disease detection, pathology classification, or clinical decision support.
                State intervals represent mathematical acoustic boundaries, not clinical ground truth.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 3. Error Callouts & Model Requirement Banners */}
      {errorMsg && (
        <div className="rounded-xl border p-3 flex items-center gap-2 text-xs font-mono-code bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30">
          <AlertCircle size={16} />
          <span>Error: {errorMsg}</span>
        </div>
      )}

      {isModelRequired && (
        <div
          className="rounded-xl border p-4 flex items-start gap-3 shadow-xs"
          style={{
            backgroundColor: 'rgba(217, 119, 6, 0.08)',
            borderColor: 'rgba(217, 119, 6, 0.35)',
          }}
        >
          <ShieldAlert size={20} className="text-amber-500 shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1 text-xs font-mono-code">
            <span className="font-bold text-amber-600 dark:text-amber-400">
              No trained Springer segmentation model is currently selected.
            </span>
            <p className="text-[var(--on-surface-variant)] leading-relaxed">
              Without a trained Springer model artifact (logistic regression coefficients and duration parameters),
              cardiac state sequences are <strong className="text-[var(--on-surface)]">never fabricated</strong>.
              Select the synthetic Demo/Reproducibility model to run inference.
            </p>
          </div>
        </div>
      )}

      {/* 4. Segmentation Summary & Confidence Metrics */}
      {seg && seg.status === 'SUCCESS' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Heart Rate Est.
            </span>
            <div className="text-xl font-mono-code font-bold text-[var(--accent-oxblood)] flex items-center gap-1">
              <Heart size={16} className="text-rose-500" />
              <span>{seg.heart_rate_estimate_bpm !== null ? Math.round(seg.heart_rate_estimate_bpm) : 'N/A'}</span>
              <span className="text-xs font-normal text-[var(--on-surface-variant)]">BPM</span>
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              Schmidt Autocorr Peak
            </span>
          </div>

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Rhythm Regularity
            </span>
            <div className="mt-1">
              {rhythmConfidence && (
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${rhythmConfidence.badgeCls}`}>
                  {rhythmConfidence.score} CONFIDENCE
                </span>
              )}
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)] mt-1">
              Autocorr Peak Sharpness
            </span>
          </div>

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Systolic Interval
            </span>
            <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
              {seg.systolic_interval_estimate_s !== null
                ? `${(seg.systolic_interval_estimate_s * 1000).toFixed(0)} ms`
                : 'N/A'}
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              Model Timing Parameter
            </span>
          </div>

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Cycle Duration
            </span>
            <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
              {seg.cycle_duration_estimate_s !== null
                ? `${(seg.cycle_duration_estimate_s * 1000).toFixed(0)} ms`
                : 'N/A'}
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              T_cycle = 60 / BPM
            </span>
          </div>

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Cycles Identified
            </span>
            <div className="text-xl font-mono-code font-bold text-[var(--accent-oxblood)]">
              {seg.cycle_count}
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              S1 → Systole → S2 → Diastole
            </span>
          </div>

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Feature Stream
            </span>
            <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
              {seg.feature_sample_rate_hz.toFixed(0)} Hz
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              {seg.total_frames_50hz} 50Hz frames
            </span>
          </div>
        </div>
      )}

      {/* 5. Synchronized Multi-Tier Time-Axis Visualization */}
      {report?.display?.waveform && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-4 shadow-xs"
          style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
        >
          {/* Top Bar: Title & Legend */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-[var(--accent-oxblood)]" />
              <span className="font-mono-code font-bold text-xs uppercase text-[var(--on-surface)]">
                Synchronized Multi-Lane PCG Time-Axis Inspection
              </span>
            </div>

            {/* State Color Chips Legend */}
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono-code">
              {[1, 2, 3, 4].map(st => {
                const cfg = STATE_CONFIG[st];
                const count = intervals.filter(iv => iv.state === st).length;
                return (
                  <div key={st} className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded-xs border"
                      style={{ backgroundColor: cfg.bgFill, borderColor: cfg.strokeBorder }}
                    />
                    <span className="font-bold" style={{ color: cfg.textCol }}>
                      {cfg.name}
                    </span>
                    <span className="text-[10px] text-[var(--on-surface-variant)]">({count})</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Envelope Visibility Toggles */}
          {report.display.feature_traces && Object.keys(report.display.feature_traces).length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono-code px-3 py-1.5 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)]">
              <span className="text-[var(--on-surface-variant)] font-bold">Observation Envelope Toggles (Consistent 50 Hz Time Axis):</span>
              <div className="flex flex-wrap items-center gap-3">
                {Object.keys(report.display.feature_traces).map(featName => {
                  const conf = ENVELOPE_COLORS[featName] || { stroke: '#94a3b8', label: featName };
                  const isVisible = activeEnvelopes[featName] !== false;
                  return (
                    <button
                      key={featName}
                      onClick={() => setActiveEnvelopes(prev => ({ ...prev, [featName]: !isVisible }))}
                      className="flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition-opacity"
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: isVisible ? conf.stroke : 'transparent', border: `1.5px solid ${conf.stroke}` }}
                      />
                      <span className={isVisible ? 'text-[var(--on-surface)] font-bold' : 'text-[var(--on-surface-variant)] line-through'}>
                        {conf.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Synchronized Multi-Lane Canvas */}
          <div
            className="w-full bg-[var(--surface-muted)] rounded-lg p-3 relative overflow-hidden border border-[var(--border-subtle)] flex flex-col gap-3 select-none"
            onMouseMove={e => {
              const rect = e.currentTarget.getBoundingClientRect();
              const relX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
              const t = (relX / rect.width) * durationS;
              setHoverTimeS(roundVal(t, 3));
            }}
            onMouseLeave={() => setHoverTimeS(null)}
          >
            {/* Lane 1: PCG Waveform & Shaded Interval Bands */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                <span className="font-bold uppercase text-[var(--accent-oxblood)]">Lane 1: PCG Waveform & Model-Derived Cardiac Bands</span>
                <span>Amplitude: [-1.0, +1.0] FS</span>
              </div>
              <div className="w-full h-36 bg-[var(--surface-card)] rounded border border-[var(--border-subtle)] relative overflow-hidden">
                <svg className="w-full h-full" viewBox="0 0 600 100" preserveAspectRatio="none">
                  {/* Zero baseline */}
                  <line x1="0" y1="50" x2="600" y2="50" stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3,3" />

                  {/* Shaded State Intervals */}
                  {durationS > 0 &&
                    intervals.map((iv, idx) => {
                      const cfg = STATE_CONFIG[iv.state];
                      if (!cfg) return null;
                      const x = (iv.start_s / durationS) * 600;
                      const w = Math.max(1, ((iv.end_s - iv.start_s) / durationS) * 600);
                      return (
                        <g key={`w-band-${idx}`}>
                          <rect
                            x={x}
                            y={0}
                            width={w}
                            height={100}
                            fill={cfg.bgFill}
                            stroke={cfg.strokeBorder}
                            strokeWidth="0.8"
                          />
                          {w > 20 && (
                            <text
                              x={x + 3}
                              y={12}
                              fill={cfg.textCol}
                              fontSize="8"
                              fontFamily="monospace"
                              fontWeight="bold"
                            >
                              {cfg.name}
                            </text>
                          )}
                        </g>
                      );
                    })}

                  {/* Waveform Trace */}
                  {report.display.waveform.amplitude.length > 1 && (
                    <polyline
                      fill="none"
                      stroke="var(--on-surface)"
                      strokeWidth="1.2"
                      points={report.display.waveform.amplitude
                        .map((val, idx) => {
                          const totalPts = report.display.waveform.amplitude.length;
                          const x = (idx / (totalPts - 1)) * 600;
                          const y = 50 - Math.max(-1, Math.min(1, val)) * 45;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        })
                        .join(' ')}
                    />
                  )}

                  {/* Synchronized Hover Hairline */}
                  {hoverTimeS !== null && durationS > 0 && (
                    <line
                      x1={(hoverTimeS / durationS) * 600}
                      y1="0"
                      x2={(hoverTimeS / durationS) * 600}
                      y2="100"
                      stroke="#ef4444"
                      strokeWidth="1.5"
                      strokeDasharray="2,2"
                    />
                  )}
                </svg>
              </div>
            </div>

            {/* Lane 2: Springer Multi-Channel Observation Envelopes (Consistent Time Axis) */}
            {report.display.feature_traces && Object.keys(report.display.feature_traces).length > 0 && (
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                  <span className="font-bold uppercase text-[var(--on-surface)]">
                    Lane 2: Observation Envelopes (Normalized z-score to [0, 1] relative energy)
                  </span>
                  <span>Time range: 0.00s to {durationS.toFixed(2)}s</span>
                </div>
                <div className="w-full h-24 bg-[var(--surface-card)] rounded border border-[var(--border-subtle)] relative overflow-hidden">
                  <svg className="w-full h-full" viewBox="0 0 600 70" preserveAspectRatio="none">
                    {/* Horizontal grid lines */}
                    <line x1="0" y1="35" x2="600" y2="35" stroke="var(--border-subtle)" strokeWidth="0.8" strokeDasharray="3,3" />

                    {/* Overlaid Envelope Traces */}
                    {Object.entries(report.display.feature_traces).map(([featName, featData]) => {
                      if (activeEnvelopes[featName] === false) return null;
                      const vals: number[] = (featData as any)?.values;
                      if (!vals || vals.length === 0) return null;
                      const minV = Math.min(...vals);
                      const maxV = Math.max(...vals);
                      const span = maxV - minV > 1e-6 ? maxV - minV : 1.0;
                      const color = ENVELOPE_COLORS[featName]?.stroke || '#94a3b8';

                      return (
                        <polyline
                          key={`lane2-${featName}`}
                          fill="none"
                          stroke={color}
                          strokeWidth="1.4"
                          points={vals
                            .map((v, idx) => {
                              const x = (idx / (vals.length - 1)) * 600;
                              const norm = (v - minV) / span;
                              const y = 65 - norm * 58;
                              return `${x.toFixed(1)},${y.toFixed(1)}`;
                            })
                            .join(' ')}
                        />
                      );
                    })}

                    {/* Synchronized Hover Hairline */}
                    {hoverTimeS !== null && durationS > 0 && (
                      <line
                        x1={(hoverTimeS / durationS) * 600}
                        y1="0"
                        x2={(hoverTimeS / durationS) * 600}
                        y2="70"
                        stroke="#ef4444"
                        strokeWidth="1.5"
                        strokeDasharray="2,2"
                      />
                    )}
                  </svg>
                </div>
              </div>
            )}

            {/* Lane 3: Model-Derived State Intervals Sequence Bar */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                <span className="font-bold uppercase text-[var(--on-surface)] flex items-center gap-1.5">
                  <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">
                    PREDICTION
                  </span>
                  <span>Lane 3: Research-Derived State Intervals (S1 / Systole / S2 / Diastole)</span>
                </span>
                <span>{intervals.length} contiguous state blocks</span>
              </div>
              <div className="w-full h-9 bg-[var(--surface-card)] rounded border border-[var(--border-subtle)] relative overflow-hidden flex items-center">
                <svg className="w-full h-full" viewBox="0 0 600 32" preserveAspectRatio="none">
                  {durationS > 0 &&
                    intervals.map((iv, idx) => {
                      const cfg = STATE_CONFIG[iv.state];
                      if (!cfg) return null;
                      const x = (iv.start_s / durationS) * 600;
                      const w = Math.max(1, ((iv.end_s - iv.start_s) / durationS) * 600);
                      const durMs = Math.round(iv.duration_s * 1000);
                      return (
                        <g key={`seq-bar-${idx}`}>
                          <rect
                            x={x}
                            y={2}
                            width={w}
                            height={28}
                            fill={cfg.bgFill}
                            stroke={cfg.strokeBorder}
                            strokeWidth="1"
                            rx="2"
                          />
                          {w > 26 && (
                            <text
                              x={x + w / 2}
                              y={19}
                              fill={cfg.textCol}
                              fontSize="8.5"
                              fontFamily="monospace"
                              fontWeight="bold"
                              textAnchor="middle"
                            >
                              {cfg.name} {w > 45 ? `${durMs}ms` : ''}
                            </text>
                          )}
                        </g>
                      );
                    })}

                  {/* Synchronized Hover Hairline */}
                  {hoverTimeS !== null && durationS > 0 && (
                    <line
                      x1={(hoverTimeS / durationS) * 600}
                      y1="0"
                      x2={(hoverTimeS / durationS) * 600}
                      y2="32"
                      stroke="#ef4444"
                      strokeWidth="1.5"
                    />
                  )}
                </svg>
              </div>
            </div>

            {/* Time Labels Axis Footer */}
            <div className="flex items-center justify-between text-[10px] font-mono-code text-[var(--on-surface-variant)] px-1 pt-1 border-t border-[var(--border-subtle)]">
              <span>0.00s</span>
              <span>{(durationS * 0.25).toFixed(2)}s</span>
              <span>{(durationS * 0.50).toFixed(2)}s</span>
              <span>{(durationS * 0.75).toFixed(2)}s</span>
              <span>{durationS.toFixed(2)}s</span>
            </div>

            {/* Synchronized Hover HUD / Crosshair Tooltip */}
            {hoverDetails && (
              <div
                className="p-2.5 rounded-lg border text-xs font-mono-code bg-[var(--surface-card)] shadow-md flex flex-wrap items-center justify-between gap-3 text-[var(--on-surface)]"
                style={{ borderColor: 'var(--accent-oxblood)' }}
              >
                <div className="flex items-center gap-2">
                  <Crosshair size={14} className="text-rose-500" />
                  <span>Time: <strong>{hoverDetails.timeS.toFixed(3)}s</strong></span>
                </div>
                {hoverDetails.interval ? (
                  <div className="flex items-center gap-2">
                    <span>Active State:</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${STATE_CONFIG[hoverDetails.interval.state]?.badgeCls}`}>
                      {hoverDetails.interval.state_name}
                    </span>
                    <span className="text-[var(--on-surface-variant)]">
                      ({(hoverDetails.interval.duration_s * 1000).toFixed(0)} ms from {hoverDetails.interval.start_s.toFixed(3)}s to {hoverDetails.interval.end_s.toFixed(3)}s)
                    </span>
                  </div>
                ) : (
                  <span className="text-[var(--on-surface-variant)]">No active cardiac state</span>
                )}
                <div className="text-[10px] text-[var(--on-surface-variant)]">
                  Scrubbing enabled across all lanes
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. Explicit Metrological Distinction: Prediction vs Reference Annotation */}
      <div
        className="rounded-xl border p-4 flex flex-col gap-2 shadow-xs text-xs font-mono-code bg-[var(--surface-card)]"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2 font-bold text-[var(--on-surface)]">
          <ShieldCheck size={16} className="text-emerald-400" />
          <span>Scientific Metrology Guardrails: Reference Annotations vs. Model Predictions</span>
        </div>
        <p className="text-[var(--on-surface-variant)] leading-relaxed">
          1. <strong className="text-rose-400">[PREDICTION]</strong> intervals displayed above represent the statistical output of the Extended Viterbi log-space decoder applied to Springer LR-HSMM observation envelopes.
          <br />
          2. <strong className="text-teal-400">[REFERENCE ANNOTATION]</strong> labels in scientific datasets (such as PhysioNet CinC 2016 and CirCor DigiScope) represent human clinician consensus markings. Because clinicians exhibit inter-observer timing differences of up to 40–80 ms, reference annotations are evaluated under tolerance windows and are <strong className="text-[var(--on-surface)]">not absolute physical ground truth</strong>.
          <br />
          3. Neither model predictions nor reference annotations shall be treated as diagnostic classifications.
        </p>
      </div>

      {/* 7. State Intervals Event Table with Filter & Export */}
      {intervals.length > 0 && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
          style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-[var(--accent-oxblood)]" />
              <span className="font-mono-code font-bold text-xs uppercase text-[var(--on-surface)]">
                Model-Derived Cardiac State Intervals ({intervals.length} Events)
              </span>
            </div>

            {/* Filter pills */}
            <div className="flex items-center gap-1.5 text-xs font-mono-code">
              {['ALL', 'S1', 'SYSTOLE', 'S2', 'DIASTOLE'].map(f => (
                <button
                  key={f}
                  onClick={() => setTableFilter(f)}
                  className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors cursor-pointer ${
                    tableFilter === f
                      ? 'bg-[var(--accent-oxblood)] text-white border-transparent'
                      : 'border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="max-h-60 overflow-y-auto border rounded-lg border-[var(--border-subtle)]">
            <table className="w-full text-left text-xs font-mono-code border-collapse">
              <thead className="bg-[var(--surface-muted)] text-[var(--on-surface-variant)] sticky top-0">
                <tr>
                  <th className="p-2 border-b border-[var(--border-subtle)]">#</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">State</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">Type</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">Start (s)</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">End (s)</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">Duration (ms)</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">Frames @ 50Hz</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {filteredIntervals.map((iv, idx) => {
                  const cfg = STATE_CONFIG[iv.state];
                  return (
                    <tr key={idx} className="hover:bg-[var(--surface-muted)]/50 transition-colors">
                      <td className="p-2 text-[var(--on-surface-variant)]">{idx + 1}</td>
                      <td className="p-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${cfg?.badgeCls || ''}`}>
                          {iv.state_name}
                        </span>
                      </td>
                      <td className="p-2">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-neutral-500/20 text-[var(--on-surface-variant)] border border-neutral-500/30">
                          PREDICTION
                        </span>
                      </td>
                      <td className="p-2 text-[var(--on-surface)]">{iv.start_s.toFixed(3)}s</td>
                      <td className="p-2 text-[var(--on-surface)]">{iv.end_s.toFixed(3)}s</td>
                      <td className="p-2 font-bold text-[var(--on-surface)]">
                        {(iv.duration_s * 1000).toFixed(0)} ms
                      </td>
                      <td className="p-2 text-[var(--on-surface-variant)]">
                        [{iv.start_frame_50hz}, {iv.end_frame_50hz}]
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

function roundVal(num: number, decimals: number = 2): number {
  const factor = Math.pow(10, decimals);
  return Math.round(num * factor) / factor;
}
