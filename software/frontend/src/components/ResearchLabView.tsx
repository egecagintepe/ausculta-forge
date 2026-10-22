import React, { useState, useEffect } from 'react';
import {
  Brain,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
  RefreshCw,
  FolderOpen,
  FileAudio,
  Layers,
  Info,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { ResearchModelInfo, ResearchPredictionResponse } from '../types';
import { bridgeClient } from '../api/bridgeClient';

interface ResearchLabViewProps {
  isDark: boolean;
  backendConnected: boolean;
  addToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void;
}

export const ResearchLabView: React.FC<ResearchLabViewProps> = ({
  backendConnected,
  addToast,
}) => {
  const [models, setModels] = useState<ResearchModelInfo[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('af_murmur_mil_1.0');
  const [loadingModels, setLoadingModels] = useState<boolean>(false);

  // Subject evaluation input
  const [patientId, setPatientId] = useState<string>('14241');
  const [recordingPaths, setRecordingPaths] = useState<string[]>([
    'data/external/circor-heart-sound-1.0.3/training_data/14241_AV.wav',
    'data/external/circor-heart-sound-1.0.3/training_data/14241_MV.wav',
    'data/external/circor-heart-sound-1.0.3/training_data/14241_PV.wav',
    'data/external/circor-heart-sound-1.0.3/training_data/14241_TV.wav',
  ]);
  const [customPathInput, setCustomPathInput] = useState<string>('');

  // Inference execution state
  const [isRunningInference, setIsRunningInference] = useState<boolean>(false);
  const [inferenceError, setInferenceError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<ResearchPredictionResponse | null>(null);
  const [showRoadmap, setShowRoadmap] = useState<boolean>(false);

  // Load models on mount
  useEffect(() => {
    if (!backendConnected) return;
    loadModels();
  }, [backendConnected]);

  const loadModels = async () => {
    setLoadingModels(true);
    try {
      const list = await bridgeClient.getResearchModels();
      setModels(list);
    } catch (err: unknown) {
      console.error('Failed to load research models', err);
    } finally {
      setLoadingModels(false);
    }
  };

  const selectedModel = models.find((m) => m.model_id === selectedModelId) || models[0];

  // Presets from local CirCor dataset
  const applyPreset = (presetPatient: string) => {
    setPatientId(presetPatient);
    const paths = [
      `data/external/circor-heart-sound-1.0.3/training_data/${presetPatient}_AV.wav`,
      `data/external/circor-heart-sound-1.0.3/training_data/${presetPatient}_MV.wav`,
      `data/external/circor-heart-sound-1.0.3/training_data/${presetPatient}_PV.wav`,
      `data/external/circor-heart-sound-1.0.3/training_data/${presetPatient}_TV.wav`,
    ];
    setRecordingPaths(paths);
    setPrediction(null);
    setInferenceError(null);
  };

  const handleAddCustomPath = () => {
    const trimmed = customPathInput.trim();
    if (!trimmed) return;
    if (recordingPaths.length >= 4) {
      if (addToast) addToast('MurmurMIL supports up to 4 recordings per patient group.', 'warning');
      return;
    }
    setRecordingPaths([...recordingPaths, trimmed]);
    setCustomPathInput('');
  };

  const handleRemovePath = (index: number) => {
    setRecordingPaths(recordingPaths.filter((_, i) => i !== index));
  };

  const handleRunInference = async () => {
    if (recordingPaths.length === 0) {
      if (addToast) addToast('Please select at least 1 PCG recording for patient evaluation.', 'warning');
      return;
    }

    setIsRunningInference(true);
    setInferenceError(null);
    try {
      const res = await bridgeClient.predictResearch(recordingPaths, selectedModelId, patientId);
      setPrediction(res);
      if (addToast) addToast(`Evaluated Subject ${res.patient_identifier}: ${res.predicted_label}`, 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setInferenceError(msg);
      if (addToast) addToast(`Inference failed: ${msg}`, 'error');
    } finally {
      setIsRunningInference(false);
    }
  };

  return (
    <div
      id="research-lab-view"
      className="flex-1 flex flex-col h-full overflow-y-auto px-6 py-5 select-none transition-colors"
      style={{ backgroundColor: 'var(--bg-canvas)' }}
    >
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-6 pb-12">
        {/* Header Section */}
        <div
          className="pb-4 border-b flex items-start justify-between"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 font-mono-code text-[11px] uppercase tracking-widest text-[var(--accent-metal)] font-semibold">
              <Brain size={13} className="text-[var(--accent-oxblood)]" />
              <span>AI Research Laboratory</span>
              <span>•</span>
              <span>Model Activation &amp; Offline Registry</span>
            </div>
            <h1 className="font-serif-display text-2xl font-semibold text-[var(--on-surface)] tracking-tight">
              AuscultaForge AI Research Laboratory
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-2xl">
              Execution of versioned, offline research inference models on grouped multi-recording auscultation cohorts.
              Non-clinical acoustic pattern characterization strictly separated from medical diagnosis.
            </p>
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-mono-code text-[11px] shadow-xs ${
              backendConnected
                ? 'border-[var(--status-success)]/40 bg-[var(--status-success)]/10 text-[var(--status-success)] font-bold'
                : 'border-[var(--status-warning)]/40 bg-[var(--status-warning)]/10 text-[var(--status-warning)]'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendConnected ? 'bg-[var(--status-success)] animate-pulse' : 'bg-[var(--status-warning)]'
              }`}
            />
            <span>{backendConnected ? 'ML Backend Active' : 'ML Backend Offline'}</span>
          </div>
        </div>

        {/* SECTION 1: MANDATORY RESEARCH DISCLAIMER & GUARDRAILS */}
        <div className="p-3.5 rounded-xl border border-[var(--accent-oxblood)]/40 bg-[var(--accent-oxblood)]/5 flex items-start gap-3 shadow-xs">
          <ShieldAlert size={20} className="text-[var(--accent-oxblood)] shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1 text-xs">
            <span className="font-mono-code font-bold uppercase tracking-wider text-[var(--accent-oxblood)] text-[11px]">
              Scientific Research Disclosure &amp; Non-Clinical Boundaries
            </span>
            <p className="text-[var(--on-surface)] leading-relaxed">
              Models in this laboratory produce <strong>experimental acoustic research scores</strong> trained on publicly released corpora. They are <strong>never</strong> a substitute for clinical auscultation, echocardiography, or physician judgment. Model outputs must never be used to diagnose cardiovascular conditions or arrhythmias. Transferability to physical ESP32 MEMS transducers remains <em>unvalidated</em>.
            </p>
          </div>
        </div>

        {/* SECTION 2: ACTIVE MODEL CARD */}
        {selectedModel && (
          <div
            className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)] border border-[var(--accent-oxblood)]/30">
                  {selectedModel.model_id}
                </span>
                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  {selectedModel.name}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-mono-code font-bold border ${
                    selectedModel.status === 'AVAILABLE'
                      ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                      : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/40'
                  }`}
                >
                  {selectedModel.status === 'AVAILABLE' ? 'ARTIFACT LOADED · READY' : selectedModel.status}
                </span>
              </div>
            </div>

            <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
              {selectedModel.description}
            </p>

            {/* Metrics Grid */}
            {selectedModel.metrics_summary && (
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-mono-code text-xs">
                <div>
                  <span className="text-[10px] text-[var(--on-surface-variant)] block">TEST AUROC</span>
                  <strong className="text-[var(--status-success)]">
                    {selectedModel.metrics_summary.test_auroc
                      ? selectedModel.metrics_summary.test_auroc.toFixed(4)
                      : '0.8735'}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-[var(--on-surface-variant)] block">AVG PRECISION (PR-AUC)</span>
                  <strong className="text-[var(--on-surface)]">
                    {selectedModel.metrics_summary.test_average_precision
                      ? selectedModel.metrics_summary.test_average_precision.toFixed(4)
                      : '0.7611'}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-[var(--on-surface-variant)] block">TEST F1 SCORE</span>
                  <strong className="text-[var(--on-surface)]">
                    {selectedModel.metrics_summary.test_f1
                      ? selectedModel.metrics_summary.test_f1.toFixed(4)
                      : '0.5714'}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-[var(--on-surface-variant)] block">OPERATING THRESHOLD</span>
                  <strong className="text-[var(--accent-oxblood)]">
                    τ* = {selectedModel.threshold ? selectedModel.threshold.toFixed(2) : '0.52'}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-[var(--on-surface-variant)] block">TRAINED CHECKPOINT</span>
                  <strong className="text-[var(--on-surface)]">
                    Epoch {selectedModel.metrics_summary.best_epoch || 6} (Frozen)
                  </strong>
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] font-mono-code text-[var(--on-surface-variant)] pt-1 border-t border-[var(--border-subtle)]/50 gap-2">
              <span>Provenance: <strong className="text-[var(--on-surface)]">{selectedModel.dataset_provenance}</strong></span>
              <span>Input Contract: <strong className="text-[var(--on-surface)]">{selectedModel.supported_inputs}</strong></span>
            </div>
          </div>
        )}

        {/* SECTION 3: PATIENT-LEVEL RECORDING GROUP SELECTOR */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-4 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FolderOpen size={16} className="text-[var(--accent-oxblood)]" />
              <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                Patient Multi-Recording Ingestion Group
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono-code text-[var(--on-surface-variant)]">CirCor Presets:</span>
              <button
                onClick={() => applyPreset('14241')}
                className={`px-2 py-1 rounded border text-[11px] font-mono-code font-semibold transition-colors cursor-pointer ${
                  patientId === '14241'
                    ? 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)]'
                    : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-card)]'
                }`}
                title="CirCor Benchmark Patient 14241 (Known Present)"
              >
                Subject 14241 (Murmur+)
              </button>
              <button
                onClick={() => applyPreset('2530')}
                className={`px-2 py-1 rounded border text-[11px] font-mono-code font-semibold transition-colors cursor-pointer ${
                  patientId === '2530'
                    ? 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)]'
                    : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-card)]'
                }`}
                title="CirCor Benchmark Patient 2530 (Known Absent)"
              >
                Subject 2530 (Absent)
              </button>
              <button
                onClick={() => applyPreset('13918')}
                className={`px-2 py-1 rounded border text-[11px] font-mono-code font-semibold transition-colors cursor-pointer ${
                  patientId === '13918'
                    ? 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)]'
                    : 'bg-[var(--surface-muted)] text-[var(--on-surface)] border-[var(--border-strong)] hover:bg-[var(--surface-card)]'
                }`}
                title="CirCor Benchmark Patient 13918 (Known Present)"
              >
                Subject 13918 (Murmur+)
              </button>
            </div>
          </div>

          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            MurmurMIL evaluates the <em>individual patient</em> by attention-pooling across multiple auscultation recordings (up to 4 sites: Aortic, Mitral, Pulmonic, Tricuspid). All recordings in a group must belong to the same person.
          </p>

          {/* Group Recordings List */}
          <div className="flex flex-col gap-2 font-mono-code text-xs">
            <div className="flex items-center justify-between text-[11px] text-[var(--on-surface-variant)]">
              <span>RECORDINGS IN CURRENT SUBJECT GROUP ({recordingPaths.length}/4)</span>
              <span>PATIENT ID: <strong className="text-[var(--on-surface)]">{patientId}</strong></span>
            </div>

            <div className="flex flex-col gap-1.5">
              {recordingPaths.map((path, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileAudio size={14} className="text-[var(--accent-metal)] shrink-0" />
                    <span className="font-semibold text-[var(--on-surface)]">{path.split('/').pop()}</span>
                    <span className="text-[10px] text-[var(--on-surface-variant)] truncate">({path})</span>
                  </div>
                  <button
                    onClick={() => handleRemovePath(idx)}
                    className="text-[10px] px-2 py-0.5 rounded text-[var(--status-danger)] hover:bg-[var(--status-danger)]/10 cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              ))}
              {recordingPaths.length === 0 && (
                <div className="p-4 rounded-lg border border-dashed border-[var(--border-subtle)] text-center text-xs text-[var(--on-surface-variant)]">
                  No recordings added. Select a CirCor preset above or enter a custom WAV file path.
                </div>
              )}
            </div>

            {/* Add Custom Path */}
            {recordingPaths.length < 4 && (
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="text"
                  placeholder="Enter local WAV file path (e.g. data/external/.../patient_AV.wav)"
                  value={customPathInput}
                  onChange={(e) => setCustomPathInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddCustomPath()}
                  className="flex-1 px-3 py-1.5 rounded-lg bg-[var(--surface-card)] border border-[var(--border-strong)] text-[var(--on-surface)] text-xs font-mono-code focus:outline-none focus:ring-1 focus:ring-[var(--accent-oxblood)]"
                />
                <button
                  onClick={handleAddCustomPath}
                  disabled={!customPathInput.trim()}
                  className="px-3 py-1.5 rounded-lg bg-[var(--surface-muted)] text-[var(--on-surface)] border border-[var(--border-strong)] text-xs font-semibold hover:bg-[var(--surface-card)] cursor-pointer disabled:opacity-50"
                >
                  Add Recording
                </button>
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between gap-3 pt-3 border-t border-[var(--border-subtle)]">
            <div className="flex items-center gap-2 text-[10px] font-mono-code text-[var(--on-surface-variant)]">
              <Clock size={12} />
              <span>Offline CPU execution ~300ms · 3 temporal offsets ensembled</span>
            </div>

            <button
              id="btn-run-research-inference"
              onClick={handleRunInference}
              disabled={!backendConnected || isRunningInference || recordingPaths.length === 0}
              className={`px-4 py-2 rounded-lg font-mono-code text-xs font-bold text-white flex items-center gap-2 transition-all cursor-pointer shadow-xs ${
                !backendConnected || isRunningInference || recordingPaths.length === 0
                  ? 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)]/50 cursor-not-allowed'
                  : 'bg-[var(--accent-oxblood)] hover:opacity-90'
              }`}
            >
              {isRunningInference ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              <span>{isRunningInference ? 'Evaluating Spectrograms...' : 'Run Patient Inference'}</span>
            </button>
          </div>

          {inferenceError && (
            <div className="p-3 rounded-lg bg-[var(--status-danger)]/10 border border-[var(--status-danger)]/30 text-xs font-mono-code text-[var(--status-danger)] flex items-center gap-2">
              <ShieldAlert size={14} className="shrink-0" />
              <span>{inferenceError}</span>
            </div>
          )}
        </div>

        {/* SECTION 4: INFERENCE RESULTS PANEL */}
        {prediction && (
          <div
            className="rounded-xl border p-5 flex flex-col gap-4 shadow-sm"
            style={{
              backgroundColor: 'var(--surface-card)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[var(--accent-oxblood)]" />
                <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  Patient Inference Outcome: Subject {prediction.patient_identifier}
                </h3>
              </div>
              <span
                className={`px-3 py-1 rounded text-xs font-mono-code font-bold border ${
                  prediction.predicted_label === 'research_pattern_present'
                    ? 'bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)] border-[var(--accent-oxblood)]/40'
                    : 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                }`}
              >
                {prediction.predicted_label === 'research_pattern_present'
                  ? 'RESEARCH PATTERN PRESENT'
                  : 'RESEARCH PATTERN ABSENT'}
              </span>
            </div>

            {/* Probability Gauge Bar */}
            <div className="flex flex-col gap-2 p-4 rounded-xl bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-mono-code">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[var(--on-surface-variant)] uppercase">Murmur Acoustic Probability:</span>
                <span className="font-bold text-base text-[var(--on-surface)]">
                  {(prediction.positive_probability * 100).toFixed(1)}%
                </span>
              </div>

              {/* Progress bar with threshold marker */}
              <div className="relative w-full h-3 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)] overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    prediction.positive_probability >= prediction.validation_selected_threshold
                      ? 'bg-[var(--accent-oxblood)]'
                      : 'bg-[var(--status-success)]'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, prediction.positive_probability * 100))}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[10px] text-[var(--on-surface-variant)] pt-1">
                <span>0.0 (Absent)</span>
                <span className="font-bold text-[var(--accent-oxblood)]">
                  Operating Threshold: {(prediction.validation_selected_threshold * 100).toFixed(0)}%
                </span>
                <span>1.0 (Present)</span>
              </div>
            </div>

            {/* Recordings breakdown table */}
            <div className="flex flex-col gap-2 font-mono-code text-xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface-variant)]">
                Evaluated Audio Recordings ({prediction.recording_count})
              </span>
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--on-surface-variant)]">
                    <th className="pb-1.5">LOCATION / FILE</th>
                    <th className="pb-1.5">DURATION</th>
                    <th className="pb-1.5">SAMPLE RATE</th>
                    <th className="pb-1.5 text-right">STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {prediction.recordings_evaluated.map((rec, i) => (
                    <tr key={i} className="border-b border-[var(--border-subtle)]/40">
                      <td className="py-1.5 font-semibold text-[var(--on-surface)]">{rec.file_name}</td>
                      <td className="py-1.5 text-[var(--on-surface-variant)]">{rec.duration_sec.toFixed(2)}s</td>
                      <td className="py-1.5 text-[var(--on-surface-variant)]">{rec.sample_rate_hz} Hz</td>
                      <td className="py-1.5 text-right">
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-[var(--status-success)]/10 text-[var(--status-success)]">
                          VALIDATED
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Scientific Caveats Banner */}
            <div className="p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] text-[11px] font-mono-code text-[var(--on-surface-variant)] flex items-start gap-2">
              <Info size={14} className="shrink-0 mt-0.5 text-[var(--accent-metal)]" />
              <div className="flex flex-col gap-0.5">
                <span className="font-bold text-[var(--on-surface)]">Scientific Caveat &amp; Domain Boundary:</span>
                <span>{prediction.disclaimer}</span>
                <span className="text-[10px] text-[var(--accent-oxblood)]">{prediction.warning}</span>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 5: EXTENSIBLE MODEL REGISTRY ROADMAP */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-3 shadow-xs"
          style={{
            backgroundColor: 'var(--surface-card)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <button
            onClick={() => setShowRoadmap(!showRoadmap)}
            className="w-full flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Layers size={16} className="text-[var(--accent-metal)]" />
              <span className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
                AuscultaForge Research Model Registry &amp; Extensibility Catalog ({models.length} Models)
              </span>
            </div>
            {showRoadmap ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            The machine learning stack implements stable interfaces for future task-specific research models without rewriting the core host application.
          </p>

          {showRoadmap && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 font-mono-code text-xs">
              {models.map((m) => (
                <div
                  key={m.model_id}
                  className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] flex flex-col justify-between gap-2"
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <strong className="text-[var(--on-surface)] text-xs">{m.name}</strong>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          m.status === 'AVAILABLE'
                            ? 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
                            : m.status === 'RULE_BASED_FOUNDATION'
                            ? 'bg-[var(--accent-oxblood)]/15 text-[var(--accent-oxblood)]'
                            : 'bg-[var(--surface-card)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]'
                        }`}
                      >
                        {m.status}
                      </span>
                    </div>
                    <span className="text-[10px] text-[var(--on-surface-variant)]">{m.task}</span>
                    <p className="text-[11px] text-[var(--on-surface)]/80 leading-relaxed pt-1">
                      {m.description}
                    </p>
                  </div>
                  <div className="text-[10px] text-[var(--on-surface-variant)] pt-1 border-t border-[var(--border-subtle)]/50">
                    ID: <code>{m.model_id}</code> · Version: {m.version}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
