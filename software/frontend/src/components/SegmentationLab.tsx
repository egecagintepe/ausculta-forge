import React, { useState, useEffect, useCallback } from 'react';
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

  const [showFeatures, setShowFeatures] = useState<boolean>(false);
  const [showHelp, setShowHelp] = useState<boolean>(false);
  const [tableFilter, setTableFilter] = useState<string>('ALL');

  // Load available models on mount
  useEffect(() => {
    let isMounted = true;
    bridgeClient.listSegmentationModels().then(models => {
      if (isMounted) {
        setAvailableModels(models);
        // Default to demo model if available
        const demo = models.find(m => m.model_id === 'springer_demo_3feature_v1');
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
          addToast(`Segmentation completed (${res.segmentation.cycle_count} cycles identified)`, 'success');
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Segmentation failed');
      if (addToast) {
        addToast(err.message || 'Segmentation failed', 'warning');
      }
    } finally {
      setLoading(false);
    }
  }, [selectedSessionId, selectedModelId, selectedProfileId, addToast]);

  const seg = report?.segmentation;
  const isModelRequired = !selectedModelId || seg?.status === 'MODEL_REQUIRED';
  const intervals: StateIntervalItem[] = seg?.state_intervals || [];

  const filteredIntervals = intervals.filter(iv => {
    if (tableFilter === 'ALL') return true;
    if (tableFilter === 'S1') return iv.state === 1;
    if (tableFilter === 'SYSTOLE') return iv.state === 2;
    if (tableFilter === 'S2') return iv.state === 3;
    if (tableFilter === 'DIASTOLE') return iv.state === 4;
    return true;
  });

  const durationS = report?.session?.duration_s || 0.0;

  return (
    <div className="flex flex-col gap-5">
      {/* Top Controls Toolbar */}
      <div
        className="rounded-xl border p-4 shadow-xs flex flex-col gap-3"
        style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-[var(--accent-oxblood)] text-white">
              <Layers size={18} />
            </div>
            <div>
              <h3 className="font-mono-code font-bold text-sm text-[var(--on-surface)]">
                Springer LR-HSMM Heart-Sound Segmentation
              </h3>
              <p className="text-[11px] font-mono-code text-[var(--on-surface-variant)]">
                PhysioNet & Paper Reproduction Pipeline: S1 → Systole → S2 → Diastole → S1
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowHelp(!showHelp)}
            className="px-2.5 py-1.5 rounded text-xs font-mono-code flex items-center gap-1.5 border transition-colors cursor-pointer bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
            style={{ borderColor: 'var(--border-subtle)' }}
          >
            <Info size={13} />
            <span>Algorithm Help & Boundaries</span>
            {showHelp ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {/* Configuration Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2 border-t border-[var(--border-subtle)] items-end">
          {/* Session Selector */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase font-bold">
              PCG Session Audio
            </label>
            <select
              value={selectedSessionId || ''}
              onChange={e => onSelectSessionId(e.target.value)}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              {sessions.length === 0 && <option value="">No sessions available</option>}
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id} ({s.sample_rate_hz} Hz, {s.duration_s?.toFixed(1)}s)
                </option>
              ))}
            </select>
          </div>

          {/* Model Selector */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase font-bold">
              Segmentation Model
            </label>
            <select
              value={selectedModelId}
              onChange={e => setSelectedModelId(e.target.value)}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value="">None (Model Required — No Fabrication)</option>
              {availableModels.map(m => (
                <option key={m.model_id} value={m.model_id}>
                  {m.label} ({m.feature_count} feats @ {m.feature_sample_rate_hz} Hz)
                </option>
              ))}
            </select>
          </div>

          {/* Profile Selector */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase font-bold">
              Method Profile
            </label>
            <select
              value={selectedProfileId}
              onChange={e => setSelectedProfileId(e.target.value)}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value="SPRINGER_PHYSIONET_REFERENCE_V1">
                SPRINGER_PHYSIONET_REFERENCE_V1 (25-400Hz, Spike, 3-feat)
              </option>
              <option value="SPRINGER_PAPER_4FEATURE_V1">
                SPRINGER_PAPER_4FEATURE_V1 (1000Hz, Wavelet, 4-feat)
              </option>
            </select>
          </div>

          {/* Run Button */}
          <button
            onClick={handleExecuteSegmentation}
            disabled={loading || !selectedSessionId}
            className="px-4 py-2 rounded text-xs font-mono-code font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer bg-[var(--accent-oxblood)] text-white hover:opacity-90 disabled:opacity-40"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Execute Segmentation</span>
          </button>
        </div>
      </div>

      {/* Educational & Scientific Boundaries Panel */}
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
                The Springer segmentation pipeline combines four stages:
                1) Multichannel envelope extraction (Homomorphic, Hilbert, PSD 40–60 Hz, and optional Wavelet).
                2) Logistic Regression to estimate state posterior probabilities from acoustic features.
                3) Duration models based on autocorrelation-derived heart rate (Schmidt algorithm).
                4) Extended Viterbi decoding in log-space enforcing cyclic state order (S1 → Systole → S2 → Diastole → S1),
                handling partial cardiac states at recording boundaries.
              </p>
            </div>
            <div>
              <p className="font-bold text-[var(--on-surface)] mb-1">Strict Research Metrology Notice:</p>
              <p>
                The outputs generated are model-derived temporal acoustic segmentations only.
                This module does <strong className="text-[var(--on-surface)]">NOT</strong> perform medical diagnosis,
                disease detection, pathology classification, or clinical decision support.
                State intervals represent mathematical time boundaries, not clinical ground truth.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error Callout */}
      {errorMsg && (
        <div className="rounded-xl border p-3 flex items-center gap-2 text-xs font-mono-code bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30">
          <AlertCircle size={16} />
          <span>Error: {errorMsg}</span>
        </div>
      )}

      {/* Truthful Model Required Banner */}
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
              Without a trained Springer model artifact (logistic regression coefficients and observation covariance),
              cardiac state sequences are <strong className="text-[var(--on-surface)]">never fabricated</strong>.
              Select the synthetic Demo/Reproducibility model or train a model from research data to run inference.
            </p>
          </div>
        </div>
      )}

      {/* Segmentation Metrics Summary */}
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

          <div
            className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
              Decoder Status
            </span>
            <div className="text-sm font-mono-code font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mt-1">
              <CheckCircle2 size={16} />
              <span>{seg.status}</span>
            </div>
            <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              Extended Viterbi (Log)
            </span>
          </div>
        </div>
      )}

      {/* Main Waveform & Segmented Bands Chart */}
      {report?.display?.waveform && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
          style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-[var(--accent-oxblood)]" />
              <span className="font-mono-code font-bold text-xs uppercase text-[var(--on-surface)]">
                PCG Waveform & Model-Derived Cardiac State Bands
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

          {/* SVG Waveform + Bands Canvas */}
          <div className="w-full h-52 bg-[var(--surface-muted)] rounded-lg p-2 relative overflow-hidden border border-[var(--border-subtle)]">
            <svg className="w-full h-full" viewBox="0 0 600 130" preserveAspectRatio="none">
              {/* Zero reference line */}
              <line x1="0" y1="65" x2="600" y2="65" stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3,3" />

              {/* Shaded state interval bands */}
              {durationS > 0 &&
                intervals.map((iv, idx) => {
                  const cfg = STATE_CONFIG[iv.state];
                  if (!cfg) return null;
                  const x = (iv.start_s / durationS) * 600;
                  const w = Math.max(1, ((iv.end_s - iv.start_s) / durationS) * 600);
                  return (
                    <g key={`band-${idx}`}>
                      <rect
                        x={x}
                        y={0}
                        width={w}
                        height={130}
                        fill={cfg.bgFill}
                        stroke={cfg.strokeBorder}
                        strokeWidth="0.8"
                      />
                      {w > 18 && (
                        <text
                          x={x + 3}
                          y={13}
                          fill={cfg.textCol}
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          {cfg.name}
                        </text>
                      )}
                    </g>
                  );
                })}

              {/* PCG Waveform Overlay */}
              {report.display.waveform.amplitude.length > 1 && (
                <polyline
                  fill="none"
                  stroke="var(--on-surface)"
                  strokeWidth="1.4"
                  points={report.display.waveform.amplitude
                    .map((val, idx) => {
                      const totalPts = report.display.waveform.amplitude.length;
                      const x = (idx / (totalPts - 1)) * 600;
                      const y = 65 - Math.max(-1, Math.min(1, val)) * 55;
                      return `${x.toFixed(1)},${y.toFixed(1)}`;
                    })
                    .join(' ')}
                />
              )}
            </svg>

            {/* Time labels footer */}
            <div className="absolute bottom-1 left-2 text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              0.00s
            </div>
            <div className="absolute bottom-1 right-2 text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              {durationS.toFixed(2)}s
            </div>
          </div>
        </div>
      )}

      {/* Feature Traces Inspection Panel (Toggleable) */}
      {report?.display?.feature_traces && Object.keys(report.display.feature_traces).length > 0 && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
          style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-[var(--accent-oxblood)]" />
              <span className="font-mono-code font-bold text-xs uppercase text-[var(--on-surface)]">
                Bounded 50 Hz Observation Envelopes (Feature Inspection)
              </span>
            </div>
            <button
              onClick={() => setShowFeatures(!showFeatures)}
              className="px-2 py-1 rounded text-xs font-mono-code flex items-center gap-1 border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
            >
              <span>{showFeatures ? 'Hide Features' : 'Inspect Features'}</span>
              {showFeatures ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>

          {showFeatures && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              {Object.entries(report.display.feature_traces).map(([featName, featData]) => {
                const feat = featData as { time_s?: number[]; values?: number[] };
                const vals = feat?.values;
                if (!vals || vals.length === 0) return null;
                const minV = Math.min(...vals);
                const maxV = Math.max(...vals);
                const span = maxV - minV > 1e-6 ? maxV - minV : 1.0;

                return (
                  <div
                    key={featName}
                    className="p-3 rounded-lg border bg-[var(--surface-muted)] flex flex-col gap-2"
                    style={{ borderColor: 'var(--border-subtle)' }}
                  >
                    <div className="flex items-center justify-between text-xs font-mono-code">
                      <span className="font-bold text-[var(--on-surface)] uppercase">{featName}</span>
                      <span className="text-[10px] text-[var(--on-surface-variant)]">
                        z-score: [{minV.toFixed(1)}, {maxV.toFixed(1)}]
                      </span>
                    </div>
                    <div className="w-full h-24 bg-[var(--surface-card)] rounded p-1 border border-[var(--border-subtle)]">
                      <svg className="w-full h-full" viewBox="0 0 300 70" preserveAspectRatio="none">
                        <polyline
                          fill="none"
                          stroke="var(--accent-oxblood)"
                          strokeWidth="1.5"
                          points={vals
                            .map((v, idx) => {
                              const x = (idx / (vals.length - 1)) * 300;
                              const norm = (v - minV) / span;
                              const y = 65 - norm * 60;
                              return `${x.toFixed(1)},${y.toFixed(1)}`;
                            })
                            .join(' ')}
                        />
                      </svg>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* State Intervals Event Table */}
      {intervals.length > 0 && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
          style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
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

          {/* Compact Table */}
          <div className="max-h-60 overflow-y-auto border rounded-lg border-[var(--border-subtle)]">
            <table className="w-full text-left text-xs font-mono-code border-collapse">
              <thead className="bg-[var(--surface-muted)] text-[var(--on-surface-variant)] sticky top-0">
                <tr>
                  <th className="p-2 border-b border-[var(--border-subtle)]">#</th>
                  <th className="p-2 border-b border-[var(--border-subtle)]">State</th>
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
