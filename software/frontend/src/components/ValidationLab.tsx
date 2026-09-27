import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  Info,
  Clock,
  Layers,
  Database,
  BarChart2,
  Sliders,
  HelpCircle,
} from 'lucide-react';
import {
  ValidationBenchmarkSummary,
  ValidationBenchmarkReport,
  FoldSummaryData,
  LocationBreakdownItem,
} from '../types';
import { bridgeClient } from '../api/bridgeClient';

interface ValidationLabProps {
  isDark: boolean;
  addToast?: (message: string, type?: 'info' | 'success' | 'warning') => void;
}

export const ValidationLab: React.FC<ValidationLabProps> = ({ isDark, addToast }) => {
  const [benchmarks, setBenchmarks] = useState<ValidationBenchmarkSummary[]>([]);
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState<string>('');
  const [report, setReport] = useState<ValidationBenchmarkReport | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(false);
  const [loadingReport, setLoadingReport] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeMetricView, setActiveMetricView] = useState<'end_to_end' | 'conditional'>('end_to_end');
  const [showHelp, setShowHelp] = useState<boolean>(false);

  const fetchBenchmarkList = async () => {
    setLoadingList(true);
    setErrorMsg(null);
    try {
      const list = await bridgeClient.listValidationBenchmarks();
      setBenchmarks(list);
      if (list.length > 0 && !selectedBenchmarkId) {
        setSelectedBenchmarkId(list[0].benchmark_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to list validation benchmarks');
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchBenchmarkList();
  }, []);

  useEffect(() => {
    if (!selectedBenchmarkId) {
      setReport(null);
      return;
    }
    let isMounted = true;
    setLoadingReport(true);
    setErrorMsg(null);

    bridgeClient
      .getValidationBenchmark(selectedBenchmarkId)
      .then(rep => {
        if (isMounted) {
          setReport(rep);
        }
      })
      .catch(err => {
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to load validation benchmark report');
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoadingReport(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedBenchmarkId]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETE_DATASET':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-mono-code font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1.5">
            <CheckCircle2 size={13} />
            COMPLETE DATASET (Full Validation)
          </span>
        );
      case 'PARTIAL_DATASET':
      case 'REAL_DATA_PILOT':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-mono-code font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5">
            <AlertTriangle size={13} />
            PARTIAL REAL-DATA VALIDATION
          </span>
        );
      case 'DATASET_NOT_AVAILABLE':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-mono-code font-bold bg-neutral-500/20 text-neutral-400 border border-neutral-500/40 flex items-center gap-1.5">
            <AlertCircle size={13} />
            DATASET NOT AVAILABLE
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded text-xs font-mono-code font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center gap-1.5">
            <AlertCircle size={13} />
            {status}
          </span>
        );
    }
  };

  const activeEventMetrics =
    report && (activeMetricView === 'end_to_end' ? report.end_to_end_event_metrics : report.conditional_event_metrics);

  return (
    <div className="flex flex-col gap-5">
      {/* Top Header & Benchmark Controls */}
      <div
        className="rounded-xl border p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xs"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-oxblood)] font-bold">
              REAL PCG SEGMENTATION VALIDATION
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
              Stage-C Independent Evaluation
            </span>
          </div>
          <div className="text-sm font-medium text-[var(--on-surface)]">
            Subject-Safe Cross-Validation & Metric Inspection on Real Annotated PCG Recordings
          </div>
        </div>

        {/* Global Controls: Benchmark Report Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
              Persisted Benchmark
            </label>
            <select
              value={selectedBenchmarkId}
              onChange={e => setSelectedBenchmarkId(e.target.value)}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
              disabled={benchmarks.length === 0}
            >
              {benchmarks.length === 0 ? (
                <option value="">No benchmarks found</option>
              ) : (
                benchmarks.map(b => (
                  <option key={b.benchmark_id} value={b.benchmark_id}>
                    {b.benchmark_id} ({b.status}, {b.dataset_id} v{b.dataset_version})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={fetchBenchmarkList}
            disabled={loadingList}
            className="mt-3.5 px-3 py-1.5 rounded text-xs font-mono-code font-bold flex items-center gap-1.5 transition-colors cursor-pointer bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-subtle)] hover:bg-[var(--surface-card)]"
          >
            <RefreshCw size={13} className={loadingList ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setShowHelp(prev => !prev)}
            className="mt-3.5 px-3 py-1.5 rounded text-xs font-mono-code font-bold flex items-center gap-1.5 transition-colors cursor-pointer bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)] hover:text-[var(--on-surface)]"
          >
            <HelpCircle size={13} />
            <span>Protocol Guide</span>
          </button>
        </div>
      </div>

      {/* Protocol Guide Banner */}
      {showHelp && (
        <div
          className="rounded-xl border p-4 flex flex-col gap-2.5 text-xs font-mono-code leading-relaxed"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--on-surface-variant)',
          }}
        >
          <div className="flex items-center gap-2 text-sm font-bold text-[var(--on-surface)]">
            <Info size={16} className="text-[var(--accent-oxblood)]" />
            <span>AuscultaForge Stage-C Validation Protocol & Guardrails</span>
          </div>
          <p>
            This module provides engineering validation of temporal PCG segmentation using independent reference
            annotations from the CirCor DigiScope PCG Dataset (PhysioNet v1.0.3).
          </p>
          <ul className="list-disc pl-5 flex flex-col gap-1">
            <li>
              <strong className="text-[var(--on-surface)]">Anti-Leakage Grouping:</strong> All recordings sharing the same
              numeric subject ID are kept in the same partition. Subjects are never split across training and evaluation.
            </li>
            <li>
              <strong className="text-[var(--on-surface)]">State 0 Semantics:</strong> State 0 marks unannotated / ambiguous
              regions. It is strictly ignored and NEVER converted to diastole.
            </li>
            <li>
              <strong className="text-[var(--on-surface)]">No Test-Time Leakage:</strong> Reference annotations are never provided
              to the model during inference.
            </li>
            <li>
              <strong className="text-[var(--on-surface)]">Anti-Survivorship Bias:</strong> End-to-End metrics count all reference
              events in failed recordings as false negatives.
            </li>
            <li>
              <strong className="text-[var(--on-surface)]">Non-Diagnostic:</strong> Evaluates temporal PCG segmentation only. Does
              not perform murmur classification, disease detection, or clinical diagnosis.
            </li>
          </ul>
        </div>
      )}

      {/* Error Banner */}
      {errorMsg && (
        <div className="rounded-xl border p-3 flex items-center gap-2 text-xs font-mono-code bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30">
          <AlertCircle size={16} />
          <span>Validation Error: {errorMsg}</span>
        </div>
      )}

      {/* Empty State when no benchmarks exist */}
      {benchmarks.length === 0 && !loadingList && (
        <div
          className="rounded-xl border p-8 flex flex-col items-center justify-center text-center gap-3"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <Database size={36} className="text-[var(--on-surface-variant)] opacity-40" />
          <div className="text-sm font-bold text-[var(--on-surface)]">No Persisted Validation Benchmarks Found</div>
          <p className="text-xs font-mono-code text-[var(--on-surface-variant)] max-w-lg">
            No benchmark report files were found in <code className="px-1.5 py-0.5 rounded bg-[var(--surface-muted)]">experiments/benchmarks/</code>.
            To generate benchmarks, run the offline validation CLI on your local PCG dataset.
          </p>
          <div
            className="p-3 rounded-lg border text-left font-mono-code text-[11px] max-w-xl w-full bg-[var(--surface-muted)]"
            style={{ borderColor: 'var(--border-subtle)' }}
          >
            <div className="text-[var(--accent-oxblood)] font-bold mb-1"># Offline Research CLI Usage:</div>
            <div className="text-[var(--on-surface)] select-all">
              python -m pcg_core.segmentation.validation.cli --dataset circor --root &lt;dataset_dir&gt; --profile SPRINGER_PHYSIONET_REFERENCE_V1 --folds 5 --seed 2026
            </div>
            <div className="text-[var(--on-surface-variant)] mt-2">
              # Dry-run / scan without training:
            </div>
            <div className="text-[var(--on-surface)] select-all">
              python -m pcg_core.segmentation.validation.cli --dataset circor --root &lt;dataset_dir&gt; --scan-only
            </div>
          </div>
        </div>
      )}

      {/* Report Loaded */}
      {report && (
        <div className="flex flex-col gap-5">
          {/* Summary Overview Card */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-subtle)' }}>
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                  {report.config.dataset_id} v{report.config.dataset_version}
                </span>
                <span className="font-mono-code text-xs px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                  Profile: {report.config.profile_id}
                </span>
                <span className="font-mono-code text-xs px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
                  Folds: {report.config.fold_count} (Seed: {report.config.random_seed})
                </span>
              </div>
              <div>{getStatusBadge(report.status)}</div>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">Eligible Records</span>
                <span className="font-mono-code text-lg font-bold text-[var(--on-surface)]">
                  {report.coverage.total_eligible_records}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">Successful Segments</span>
                <span className="font-mono-code text-lg font-bold text-emerald-400">
                  {report.coverage.successful_segmentations}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">Failed Segments</span>
                <span className="font-mono-code text-lg font-bold text-rose-400">
                  {report.coverage.failed_segmentations}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">Segmentation Coverage</span>
                <span className="font-mono-code text-lg font-bold text-[var(--on-surface)]">
                  {(report.coverage.coverage_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">Annotated-Frame Agreement</span>
                <span className="font-mono-code text-lg font-bold text-[var(--on-surface)]">
                  {report.state_metrics ? `${(report.state_metrics.annotated_frame_agreement * 100).toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono-code uppercase text-[var(--on-surface-variant)]">State Macro F1</span>
                <span className="font-mono-code text-lg font-bold text-[var(--on-surface)]">
                  {report.state_metrics ? report.state_metrics.macro_f1.toFixed(3) : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Performance Views Selection Bar */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b pb-2" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveMetricView('end_to_end')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono-code font-bold transition-all cursor-pointer ${
                  activeMetricView === 'end_to_end'
                    ? 'bg-[var(--accent-oxblood)] text-white shadow-xs'
                    : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                1. END-TO-END METRICS (Primary Engineering Benchmark)
              </button>
              <button
                onClick={() => setActiveMetricView('conditional')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono-code font-bold transition-all cursor-pointer ${
                  activeMetricView === 'conditional'
                    ? 'bg-[var(--accent-oxblood)] text-white shadow-xs'
                    : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                2. CONDITIONAL SUCCESS METRICS (Successful Runs Only)
              </button>
            </div>
            <div className="text-[11px] font-mono-code text-[var(--on-surface-variant)]">
              {activeMetricView === 'end_to_end'
                ? 'Treats failed segmentations as empty predictions to prevent survivorship bias.'
                : 'Excludes failed recordings to evaluate baseline decoder potential.'}
            </div>
          </div>

          {/* Event-Level Metrics Table across Tolerances (20, 40, 60, 80, 100 ms) */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
                Event-Level Evaluation Across Time Tolerances (S1, S2, Combined)
              </span>
              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                1-to-1 deterministic nearest assignment (anchor: {report.config.primary_event_anchor})
              </span>
            </div>

            {activeEventMetrics ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono-code text-left border-collapse">
                  <thead>
                    <tr className="border-b" style={{ borderColor: 'var(--border-subtle)', color: 'var(--on-surface-variant)' }}>
                      <th className="py-2 px-3">Tolerance</th>
                      <th className="py-2 px-3">S1 Prec</th>
                      <th className="py-2 px-3">S1 Rec</th>
                      <th className="py-2 px-3 text-rose-400 font-bold">S1 F1</th>
                      <th className="py-2 px-3">S2 Prec</th>
                      <th className="py-2 px-3">S2 Rec</th>
                      <th className="py-2 px-3 text-teal-400 font-bold">S2 F1</th>
                      <th className="py-2 px-3">Comb Prec</th>
                      <th className="py-2 px-3">Comb Rec</th>
                      <th className="py-2 px-3 text-[var(--on-surface)] font-bold">Combined F1</th>
                      <th className="py-2 px-3">TP / FP / FN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['20ms', '40ms', '60ms', '80ms', '100ms'].map(tolKey => {
                      const row = activeEventMetrics[tolKey];
                      if (!row) return null;
                      return (
                        <tr
                          key={tolKey}
                          className="border-b hover:bg-[var(--surface-muted)] transition-colors"
                          style={{ borderColor: 'var(--border-subtle)' }}
                        >
                          <td className="py-2 px-3 font-bold text-[var(--on-surface)]">{row.tolerance_ms} ms</td>
                          <td className="py-2 px-3">{(row.s1.precision * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3">{(row.s1.recall * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3 font-bold text-rose-400">{(row.s1.f1 * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3">{(row.s2.precision * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3">{(row.s2.recall * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3 font-bold text-teal-400">{(row.s2.f1 * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3">{(row.combined.precision * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3">{(row.combined.recall * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3 font-bold text-[var(--on-surface)]">{(row.combined.f1 * 100).toFixed(1)}%</td>
                          <td className="py-2 px-3 text-[var(--on-surface-variant)]">
                            {row.combined.tp} / {row.combined.fp} / {row.combined.fn}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)] py-4 text-center">
                No event metrics available for current view.
              </div>
            )}
          </div>

          {/* Two-Column Grid: Timing Errors & State Confusion Matrix */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Column 1: Timing Error Statistics */}
            <div
              className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <span className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
                Event Timing Error Statistics (Correctly Matched Events)
              </span>
              {report.timing_errors ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono-code text-left border-collapse">
                    <thead>
                      <tr className="border-b" style={{ borderColor: 'var(--border-subtle)', color: 'var(--on-surface-variant)' }}>
                        <th className="py-1.5 px-2">Event</th>
                        <th className="py-1.5 px-2">Matched</th>
                        <th className="py-1.5 px-2">Mean Err</th>
                        <th className="py-1.5 px-2">Median Err</th>
                        <th className="py-1.5 px-2">MAE</th>
                        <th className="py-1.5 px-2">Median AE</th>
                        <th className="py-1.5 px-2">95th %ile</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: 'S1', data: report.timing_errors.s1, col: 'text-rose-400' },
                        { label: 'S2', data: report.timing_errors.s2, col: 'text-teal-400' },
                        { label: 'Combined', data: report.timing_errors.combined, col: 'text-[var(--on-surface)]' },
                      ].map(item => (
                        <tr
                          key={item.label}
                          className="border-b"
                          style={{ borderColor: 'var(--border-subtle)' }}
                        >
                          <td className={`py-2 px-2 font-bold ${item.col}`}>{item.label}</td>
                          <td className="py-2 px-2">{item.data.count}</td>
                          <td className="py-2 px-2">{item.data.mean_error_ms.toFixed(1)} ms</td>
                          <td className="py-2 px-2">{item.data.median_error_ms.toFixed(1)} ms</td>
                          <td className="py-2 px-2">{item.data.mean_abs_error_ms.toFixed(1)} ms</td>
                          <td className="py-2 px-2">{item.data.median_abs_error_ms.toFixed(1)} ms</td>
                          <td className="py-2 px-2">{item.data.p95_abs_error_ms.toFixed(1)} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-xs font-mono-code text-[var(--on-surface-variant)] py-4 text-center">
                  No timing error metrics available.
                </div>
              )}
            </div>

            {/* Column 2: State-Level 50 Hz Frame Evaluation */}
            <div
              className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
                  50 Hz State-Level Agreement (Four Cardiac States)
                </span>
                {report.state_metrics && (
                  <span className="text-[10px] font-mono-code text-amber-300">
                    State 0 Ignored: {report.state_metrics.ignored_frames_state0} frames
                  </span>
                )}
              </div>

              {report.state_metrics ? (
                <div className="flex flex-col gap-3">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono-code text-left border-collapse">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--border-subtle)', color: 'var(--on-surface-variant)' }}>
                          <th className="py-1.5 px-2">State</th>
                          <th className="py-1.5 px-2">Precision</th>
                          <th className="py-1.5 px-2">Recall</th>
                          <th className="py-1.5 px-2">F1</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { key: 'S1', label: '1 - S1', col: 'text-rose-400' },
                          { key: 'SYSTOLE', label: '2 - Systole', col: 'text-amber-400' },
                          { key: 'S2', label: '3 - S2', col: 'text-teal-400' },
                          { key: 'DIASTOLE', label: '4 - Diastole', col: 'text-indigo-400' },
                        ].map(st => (
                          <tr
                            key={st.key}
                            className="border-b"
                            style={{ borderColor: 'var(--border-subtle)' }}
                          >
                            <td className={`py-1.5 px-2 font-bold ${st.col}`}>{st.label}</td>
                            <td className="py-1.5 px-2">
                              {((report.state_metrics?.per_state_precision?.[st.key] ?? 0) * 100).toFixed(1)}%
                            </td>
                            <td className="py-1.5 px-2">
                              {((report.state_metrics?.per_state_recall?.[st.key] ?? 0) * 100).toFixed(1)}%
                            </td>
                            <td className="py-1.5 px-2 font-bold">
                              {((report.state_metrics?.per_state_f1?.[st.key] ?? 0) * 100).toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="p-2.5 rounded bg-[var(--surface-muted)] text-[11px] font-mono-code flex items-center justify-between">
                    <span>Annotated-Frame Agreement:</span>
                    <strong className="text-[var(--on-surface)]">
                      {(report.state_metrics.annotated_frame_agreement * 100).toFixed(1)}%
                    </strong>
                  </div>
                </div>
              ) : (
                <div className="text-xs font-mono-code text-[var(--on-surface-variant)] py-4 text-center">
                  No state-level frame metrics available.
                </div>
              )}
            </div>
          </div>

          {/* Auscultation Location Breakdown */}
          {report.location_breakdown && report.location_breakdown.length > 0 && (
            <div
              className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
                  Auscultation Location Descriptive Breakdown
                </span>
                <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                  Descriptive engineering characterization only. Locations are not ranked.
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono-code text-left border-collapse">
                  <thead>
                    <tr className="border-b" style={{ borderColor: 'var(--border-subtle)', color: 'var(--on-surface-variant)' }}>
                      <th className="py-2 px-3">Location Code</th>
                      <th className="py-2 px-3">Records</th>
                      <th className="py-2 px-3">Subjects</th>
                      <th className="py-2 px-3">Coverage</th>
                      <th className="py-2 px-3 text-rose-400">S1 F1 (100ms)</th>
                      <th className="py-2 px-3 text-teal-400">S2 F1 (100ms)</th>
                      <th className="py-2 px-3 font-bold text-[var(--on-surface)]">Combined F1 (100ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.location_breakdown.map((loc: LocationBreakdownItem) => (
                      <tr
                        key={loc.location}
                        className="border-b hover:bg-[var(--surface-muted)] transition-colors"
                        style={{ borderColor: 'var(--border-subtle)' }}
                      >
                        <td className="py-2 px-3 font-bold text-[var(--on-surface)]">{loc.location}</td>
                        <td className="py-2 px-3">{loc.record_count}</td>
                        <td className="py-2 px-3">{loc.subject_count}</td>
                        <td className="py-2 px-3">{(loc.coverage_rate * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 text-rose-400">{(loc.s1_f1_100ms * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 text-teal-400">{(loc.s2_f1_100ms * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 font-bold text-[var(--on-surface)]">
                          {(loc.combined_f1_100ms * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Fold Variation Table */}
          {report.fold_summaries && report.fold_summaries.length > 0 && (
            <div
              className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
              style={{
                backgroundColor: 'var(--surface-card)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono-code text-xs font-bold text-[var(--on-surface)] uppercase">
                  Subject-Grouped Fold Variation
                </span>
                <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                  Fold variation reflects dataset partition variance, not clinical confidence intervals.
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono-code text-left border-collapse">
                  <thead>
                    <tr className="border-b" style={{ borderColor: 'var(--border-subtle)', color: 'var(--on-surface-variant)' }}>
                      <th className="py-2 px-3">Fold Index</th>
                      <th className="py-2 px-3">Train Subjects</th>
                      <th className="py-2 px-3">Eval Subjects</th>
                      <th className="py-2 px-3">Train Records</th>
                      <th className="py-2 px-3">Eval Records</th>
                      <th className="py-2 px-3">Coverage</th>
                      <th className="py-2 px-3 font-bold text-[var(--on-surface)]">End-to-End Comb F1 (100ms)</th>
                      <th className="py-2 px-3">Cond Comb F1 (100ms)</th>
                      <th className="py-2 px-3">State Macro F1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.fold_summaries.map((f: FoldSummaryData) => (
                      <tr
                        key={f.fold_idx}
                        className="border-b hover:bg-[var(--surface-muted)] transition-colors"
                        style={{ borderColor: 'var(--border-subtle)' }}
                      >
                        <td className="py-2 px-3 font-bold text-[var(--on-surface)]">Fold {f.fold_idx}</td>
                        <td className="py-2 px-3">{f.train_subjects_count}</td>
                        <td className="py-2 px-3">{f.eval_subjects_count}</td>
                        <td className="py-2 px-3">{f.train_records_count}</td>
                        <td className="py-2 px-3">{f.eval_records_count}</td>
                        <td className="py-2 px-3">{(f.coverage_rate * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 font-bold text-[var(--on-surface)]">
                          {(f.end_to_end_combined_f1_100ms * 100).toFixed(1)}%
                        </td>
                        <td className="py-2 px-3">{(f.conditional_combined_f1_100ms * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 font-bold">{f.macro_state_f1.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Provenance & Scientific Guardrails */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs text-xs font-mono-code"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--on-surface-variant)',
            }}
          >
            <div className="flex items-center gap-2 font-bold text-[var(--on-surface)]">
              <ShieldCheck size={16} className="text-emerald-400" />
              <span>Scientific Reproducibility & Provenance</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <div>Git Commit SHA: <span className="text-[var(--on-surface)]">{String(report.provenance?.git_commit_sha || 'N/A')}</span></div>
              <div>Python Version: <span className="text-[var(--on-surface)]">{String(report.provenance?.python_version || 'N/A')}</span></div>
              <div>NumPy Version: <span className="text-[var(--on-surface)]">{String(report.provenance?.numpy_version || 'N/A')}</span></div>
            </div>
            {report.warnings && report.warnings.length > 0 && (
              <div className="mt-2 text-amber-300">
                <span className="font-bold">Warnings:</span> {report.warnings.join(' | ')}
              </div>
            )}
            {report.limitations && report.limitations.length > 0 && (
              <div className="mt-1 text-[var(--on-surface-variant)]">
                <span className="font-bold">Scientific Limitations:</span> {report.limitations.join(' | ')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
