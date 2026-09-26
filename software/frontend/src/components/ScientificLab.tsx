import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  BarChart2,
  Sliders,
  Zap,
  Info,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Radio
} from 'lucide-react';
import {
  ReferenceAssetItem,
  ScientificSessionAnalysisResult,
  SystemIdReport,
} from '../types';
import { bridgeClient, SessionItem } from '../api/bridgeClient';

interface ScientificLabProps {
  isDark: boolean;
  sessions: SessionItem[];
  referenceAssets: ReferenceAssetItem[];
  selectedSessionId: string | null;
  onSelectSessionId: (id: string) => void;
  addToast?: (message: string, type?: 'info' | 'success' | 'warning') => void;
}

export type ScientificSection = 'signal' | 'spectrum' | 'envelopes' | 'system_id';

interface MetrologyCardData {
  title: string;
  whatIsIt: string;
  whyUseful: string;
  largeSmallMeaning: string;
  whatItDoesNotProve: string;
}

const METROLOGY_EXPLANATIONS: Record<string, MetrologyCardData> = {
  crest_factor: {
    title: 'Crest Factor (Peak / RMS)',
    whatIsIt: 'The ratio of instantaneous absolute peak amplitude to the root-mean-square (RMS) level: CF = |x_peak| / x_rms.',
    whyUseful: 'Identifies impulsive acoustic bursts (e.g. S1/S2 heart sound transients) versus steady continuous background noise.',
    largeSmallMeaning: 'A high value indicates sharp, transient peaks with low baseline noise; a small value (~1.41 for pure tone, lower for noise) indicates continuous energy without distinct spikes.',
    whatItDoesNotProve: 'A high crest factor does NOT automatically prove heart sound presence or motion artifact; it is purely a mathematical wave shape statistic.'
  },
  digital_fs_utilization: {
    title: 'Digital Full-Scale Utilization',
    whatIsIt: 'Peak absolute sample amplitude normalized against +/- 1.0 digital full-scale (FS).',
    whyUseful: 'Ensures the ADC / I2S word dynamic range is appropriately utilized without digital clipping or excessive quantization noise floor.',
    largeSmallMeaning: 'Values between 0.40 and 0.85 indicate healthy operational headroom; values approaching 1.0 risk digital rail saturation.',
    whatItDoesNotProve: 'Does NOT indicate acoustic microphone sound pressure level (Pa or dB SPL) without certified acoustic sensitivity calibration.'
  },
  digital_saturation_hits: {
    title: 'Digital Saturation Hits (>= 0.999 FS)',
    whatIsIt: 'The absolute count and fraction of samples reaching or exceeding 0.999 of digital normalized full-scale.',
    whyUseful: 'Detects digital signal rail contact where waveform peaks are artificially flattened, creating harmonic distortion.',
    largeSmallMeaning: 'Zero hits indicates clean linear digital transport; non-zero hits prove digital ceiling contact.',
    whatItDoesNotProve: 'Proves DIGITAL rail saturation ONLY; does NOT prove physical acoustic microphone membrane overload or acoustic sound distortion.'
  },
  zero_crossing_rate: {
    title: 'Zero-Crossing Rate (ZCR)',
    whatIsIt: 'The rate of sign changes along the waveform, computed on the mean-centered (AC) signal.',
    whyUseful: 'Provides a coarse summary of dominant spectral crossing density in noise and speech processing.',
    largeSmallMeaning: 'Higher values reflect higher-frequency components or high-frequency hiss; lower values reflect slow acoustic transients.',
    whatItDoesNotProve: 'Explicitly NOT a reliable heart-sound quality classifier or pathology detector. Heart sound transients are non-stationary and multimodal.'
  },
  welch_psd: {
    title: 'Welch Power Spectral Density & Bin Spacing',
    whatIsIt: 'Averaged periodogram using windowed, overlapping segments. Displays power spectral density in normalized amplitude squared per Hertz (FS^2 / Hz) and relative dB.',
    whyUseful: 'Reveals frequency content (e.g., 20–150 Hz heart sound fundamental band) with reduced spectral variance compared to raw FFT.',
    largeSmallMeaning: 'Peaks indicate frequency concentrations of acoustic energy. Bin spacing Delta_f = fs / N_fft defines discrete grid resolution.',
    whatItDoesNotProve: 'Coarse FFT does NOT destroy physical components; zero-padding interpolates the display but does NOT increase true physical resolving power. Does NOT prove absolute acoustic sound pressure (Pa^2/Hz).'
  },
  hilbert_envelope: {
    title: 'Hilbert Instantaneous Envelope',
    whatIsIt: 'The modulus of the analytic signal: e(t) = |x(t) + j * H{x(t)}|, where H is the Hilbert transform.',
    whyUseful: 'Extracts the continuous time-domain envelope of acoustic bursts without group-delay distortion.',
    largeSmallMeaning: 'Peaks mark localized acoustic burst energy concentrations.',
    whatItDoesNotProve: 'Does NOT classify S1 versus S2, nor does it guarantee physiological timing boundaries without statistical segmentation models.'
  },
  tkeo: {
    title: 'Teager-Kaiser Energy Operator (TKEO)',
    whatIsIt: 'Discrete nonlinear energy tracking operator: Psi[x[n]] = x[n]^2 - x[n-1] * x[n+1]. For x[n] = A * cos(omega_0 * n), Psi[x[n]] = A^2 * sin^2(omega_0) approx A^2 * omega_0^2.',
    whyUseful: 'Simultaneously sensitive to instantaneous amplitude AND instantaneous frequency, highlighting abrupt acoustic onset transitions.',
    largeSmallMeaning: 'Sharp peaks pinpoint rapid energy state changes.',
    whatItDoesNotProve: 'TKEO is an experimental feature comparator. A TKEO peak is NOT automatically S1 or S2, and NOT a clinical diagnostic feature.'
  },
  psd_band_envelope: {
    title: 'PSD-Band Envelope (Springer 40–60 Hz Research Profile)',
    whatIsIt: 'Short-time windowed energy extracted in the 40–60 Hz subband (50 ms Hamming window, 50% overlap).',
    whyUseful: 'Implements the deterministic spectral feature stream from Springer et al. (2016) PCG segmentation literature.',
    largeSmallMeaning: 'Reflects localized energy in the fundamental S1/S2 frequency band.',
    whatItDoesNotProve: '40–60 Hz is a segmentation research convention; it is NOT a universal PCG standard band and does not capture murmurs or higher-frequency murmurs.'
  },
  system_id_frf: {
    title: 'SISO Best-Linear FRF Estimate (H1)',
    whatIsIt: 'Best-linear frequency response function estimate: H1(f) = S_xy(f) / S_xx(f), computed via cross-spectrum and input autospectrum.',
    whyUseful: 'Characterizes the electroacoustic transmission gain and phase relationship between input stimulus and captured signal.',
    largeSmallMeaning: 'Magnitude shows relative amplification/attenuation; phase shows phase delay. Evaluated over excited-frequency bins.',
    whatItDoesNotProve: 'Characterizes the COMPLETE END-TO-END transmission chain (DAC -> amp -> exciter -> acoustic coupling -> chestpiece -> sensor -> ESP32 -> USB -> host). It is NOT an isolated stethoscope FRF, and NOT anatomical chest response.'
  },
  coherence: {
    title: 'Ordinary Magnitude-Squared Coherence (gamma_xy^2)',
    whatIsIt: 'Frequency-dependent linear association: gamma_xy^2(f) = |S_xy(f)|^2 / (S_xx(f) * S_yy(f)), strictly bounded between 0.0 and 1.0.',
    whyUseful: 'Identifies frequency bands where capture response is linearly related to the reference stimulus versus bands dominated by extraneous noise or non-linearity.',
    largeSmallMeaning: 'Values near 1.0 indicate strong linear relationship under the spectral model; low values indicate noise or unexcited frequencies.',
    whatItDoesNotProve: 'High coherence does NOT prove physical causality. Coherence is an association metric under a linear stochastic model.'
  }
};

export const ScientificLab: React.FC<ScientificLabProps> = ({
  isDark,
  sessions,
  referenceAssets,
  selectedSessionId,
  onSelectSessionId,
  addToast,
}) => {
  const [activeSection, setActiveSection] = useState<ScientificSection>('signal');
  const [selectedProfile, setSelectedProfile] = useState<string>('GENERAL_PCG_V1');
  const [welchNperseg, setWelchNperseg] = useState<number>(2048);

  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<ScientificSessionAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Selected Envelope view
  const [selectedEnvelopeAlgo, setSelectedEnvelopeAlgo] = useState<'all' | 'hilbert' | 'moving_rms' | 'tkeo' | 'psd_band'>('all');

  // Metrology card explanation expander
  const [expandedExplanation, setExpandedExplanation] = useState<string | null>(null);

  // System ID State
  const [systemIdAssetId, setSystemIdAssetId] = useState<string | null>(null);
  const [systemIdRunning, setSystemIdRunning] = useState<boolean>(false);
  const [systemIdResult, setSystemIdResult] = useState<SystemIdReport | null>(null);
  const [systemIdError, setSystemIdError] = useState<string | null>(null);
  const [excitedBandMin, setExcitedBandMin] = useState<number>(20);
  const [excitedBandMax, setExcitedBandMax] = useState<number>(1000);
  const [energyThresholdDb, setEnergyThresholdDb] = useState<number>(-30);

  // Auto-select first asset for System ID if available
  useEffect(() => {
    if (!systemIdAssetId && referenceAssets.length > 0) {
      setSystemIdAssetId(referenceAssets[0].asset_id);
    }
  }, [referenceAssets, systemIdAssetId]);

  // Run scientific analysis when session or parameters change
  const executeScientificAnalysis = useCallback(async () => {
    if (!selectedSessionId) {
      setAnalysisResult(null);
      return;
    }
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await bridgeClient.analyzeSessionScientific(
        selectedSessionId,
        selectedProfile,
        welchNperseg,
        600
      );
      setAnalysisResult(res);
    } catch (err: any) {
      console.error('Scientific analysis failed:', err);
      setAnalysisError(err.message || 'Analysis failed');
      if (addToast) addToast(`Scientific analysis error: ${err.message}`, 'warning');
    } finally {
      setAnalyzing(false);
    }
  }, [selectedSessionId, selectedProfile, welchNperseg, addToast]);

  useEffect(() => {
    executeScientificAnalysis();
  }, [executeScientificAnalysis]);

  // Run System ID execution
  const executeSystemId = async () => {
    if (!systemIdAssetId || !selectedSessionId) {
      if (addToast) addToast('Select both a reference stimulus and a capture session.', 'warning');
      return;
    }
    setSystemIdRunning(true);
    setSystemIdError(null);
    try {
      const res = await bridgeClient.runSystemIdentification(systemIdAssetId, selectedSessionId, {
        nperseg: 1024,
        noverlap: 512,
        excited_band_min_hz: excitedBandMin,
        excited_band_max_hz: excitedBandMax,
        energy_threshold_db_rel_max: energyThresholdDb,
        max_display_points: 300,
      });
      setSystemIdResult(res);
      if (addToast) addToast('System identification completed successfully.', 'success');
    } catch (err: any) {
      console.error('System ID failed:', err);
      setSystemIdError(err.message || 'System identification failed');
      if (addToast) addToast(`System ID error: ${err.message}`, 'warning');
    } finally {
      setSystemIdRunning(false);
    }
  };

  const toggleExplanation = (key: string) => {
    setExpandedExplanation(prev => (prev === key ? null : key));
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Top Header & Engineering Preset Controls */}
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
              SCIENTIFIC ANALYSIS ENGINE
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)]">
              Stage-A Deterministic
            </span>
          </div>
          <div className="text-sm font-medium text-[var(--on-surface)]">
            Defensible Engineering Characterization & System Identification Foundation
          </div>
        </div>

        {/* Global Controls: Session & Profile */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Session Selector */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
              Target Session
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
                  {s.session_id} ({s.sample_rate_hz} Hz, {s.total_samples} samples)
                </option>
              ))}
            </select>
          </div>

          {/* Analysis Profile Selector */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
              Analysis Profile
            </label>
            <select
              value={selectedProfile}
              onChange={e => setSelectedProfile(e.target.value)}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value="GENERAL_PCG_V1">GENERAL_PCG_V1 (20–600 Hz Butterworth)</option>
              <option value="RAW_INTEGRITY_V1">RAW_INTEGRITY_V1 (Full Bandwidth)</option>
              <option value="BROADBAND_SYSTEM_ID_V1">BROADBAND_SYSTEM_ID_V1 (No Filter)</option>
              <option value="SPRINGER_SEGMENTATION_RESEARCH_V1">SPRINGER_SEGMENTATION_RESEARCH_V1</option>
            </select>
          </div>

          {/* Welch NPERSEG */}
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
              Welch NFFT / Seg
            </label>
            <select
              value={welchNperseg}
              onChange={e => setWelchNperseg(Number(e.target.value))}
              className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <option value={512}>512 (Δf ≈ 93.75 Hz @ 48k)</option>
              <option value={1024}>1024 (Δf ≈ 46.88 Hz @ 48k)</option>
              <option value={2048}>2048 (Δf ≈ 23.44 Hz @ 48k)</option>
              <option value={4096}>4096 (Δf ≈ 11.72 Hz @ 48k)</option>
            </select>
          </div>

          {/* Re-run button */}
          <button
            onClick={executeScientificAnalysis}
            disabled={analyzing || !selectedSessionId}
            className="mt-3.5 px-3 py-1.5 rounded text-xs font-mono-code font-bold flex items-center gap-1.5 transition-colors cursor-pointer bg-[var(--accent-oxblood)] text-white hover:opacity-90 disabled:opacity-40"
          >
            <RefreshCw size={13} className={analyzing ? 'animate-spin' : ''} />
            <span>Recalculate</span>
          </button>
        </div>
      </div>

      {/* Sub-Section Navigation Tabs */}
      <div className="flex items-center gap-2 border-b pb-2" style={{ borderColor: 'var(--border-subtle)' }}>
        {[
          { id: 'signal', label: '1. SIGNAL QUALITY', icon: <Activity size={15} /> },
          { id: 'spectrum', label: '2. WELCH SPECTRUM', icon: <BarChart2 size={15} /> },
          { id: 'envelopes', label: '3. ENVELOPE LAB', icon: <TrendingUp size={15} /> },
          { id: 'system_id', label: '4. SYSTEM IDENTIFICATION', icon: <Cpu size={15} /> },
        ].map(tab => {
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id as ScientificSection)}
              className={`px-3 py-2 rounded-lg text-xs font-mono-code font-bold flex items-center gap-2 transition-all cursor-pointer ${
                isActive
                  ? 'bg-[var(--accent-oxblood)] text-white shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)]'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Error Banner */}
      {analysisError && (
        <div className="rounded-xl border p-3 flex items-center gap-2 text-xs font-mono-code bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30">
          <AlertCircle size={16} />
          <span>Analysis Error: {analysisError}</span>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 1: SIGNAL QUALITY CHARACTERIZATION                            */}
      {/* ===================================================================== */}
      {activeSection === 'signal' && analysisResult && (
        <div className="flex flex-col gap-4">
          {/* Engineering Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Metric 1: RMS & Peak */}
            <div
              className="rounded-xl border p-3.5 flex flex-col gap-1.5 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                  RMS & Peak Absolute
                </span>
                <button
                  onClick={() => toggleExplanation('crest_factor')}
                  className="text-[var(--accent-metal)] hover:text-[var(--accent-oxblood)]"
                  title="Learn about Crest Factor & RMS"
                >
                  <HelpCircle size={13} />
                </button>
              </div>
              <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
                {analysisResult.signal_quality.rms.toFixed(5)} FS
              </div>
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)]">
                Peak: {analysisResult.signal_quality.peak_absolute.toFixed(5)} FS (Pk-Pk: {analysisResult.signal_quality.peak_to_peak.toFixed(5)})
              </div>
            </div>

            {/* Metric 2: Crest Factor */}
            <div
              className="rounded-xl border p-3.5 flex flex-col gap-1.5 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                  Crest Factor
                </span>
                <button
                  onClick={() => toggleExplanation('crest_factor')}
                  className="text-[var(--accent-metal)] hover:text-[var(--accent-oxblood)]"
                >
                  <HelpCircle size={13} />
                </button>
              </div>
              <div className="text-xl font-mono-code font-bold text-[var(--accent-oxblood)]">
                {analysisResult.signal_quality.crest_factor.toFixed(3)}
              </div>
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)]">
                Impulsiveness Ratio (Peak / RMS)
              </div>
            </div>

            {/* Metric 3: Digital Headroom & Full-Scale Utilization */}
            <div
              className="rounded-xl border p-3.5 flex flex-col gap-1.5 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                  Full-Scale Utilization
                </span>
                <button
                  onClick={() => toggleExplanation('digital_fs_utilization')}
                  className="text-[var(--accent-metal)] hover:text-[var(--accent-oxblood)]"
                >
                  <HelpCircle size={13} />
                </button>
              </div>
              <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
                {(analysisResult.signal_quality.digital_full_scale_utilization * 100).toFixed(1)}%
              </div>
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)]">
                Mean DC Bias: {analysisResult.signal_quality.mean_dc.toFixed(6)} FS
              </div>
            </div>

            {/* Metric 4: Digital Saturation Hits */}
            <div
              className="rounded-xl border p-3.5 flex flex-col gap-1.5 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                  Digital Saturation Hits
                </span>
                <button
                  onClick={() => toggleExplanation('digital_saturation_hits')}
                  className="text-[var(--accent-metal)] hover:text-[var(--accent-oxblood)]"
                >
                  <HelpCircle size={13} />
                </button>
              </div>
              <div className={`text-xl font-mono-code font-bold ${
                analysisResult.signal_quality.digital_saturation_count > 0 ? 'text-amber-600' : 'text-emerald-600'
              }`}>
                {analysisResult.signal_quality.digital_saturation_count} samples
              </div>
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)]">
                Fraction: {(analysisResult.signal_quality.digital_saturation_fraction * 100).toFixed(4)}% (at >= 0.999 FS)
              </div>
            </div>
          </div>

          {/* Metrology Deep-Dive Callout if expanded */}
          {expandedExplanation && METROLOGY_EXPLANATIONS[expandedExplanation] && (
            <div
              className="rounded-xl border p-4 flex flex-col gap-2 bg-[var(--surface-muted)] shadow-xs animate-in fade-in"
              style={{ borderColor: 'var(--accent-oxblood)' }}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono-code text-xs font-bold text-[var(--accent-oxblood)]">
                  {METROLOGY_EXPLANATIONS[expandedExplanation].title}
                </span>
                <button
                  onClick={() => setExpandedExplanation(null)}
                  className="text-xs font-mono-code text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
                >
                  Close [x]
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono-code">
                <div>
                  <span className="font-bold text-[var(--on-surface)]">What is this? </span>
                  <span className="text-[var(--on-surface-variant)]">{METROLOGY_EXPLANATIONS[expandedExplanation].whatIsIt}</span>
                </div>
                <div>
                  <span className="font-bold text-[var(--on-surface)]">Why is it useful here? </span>
                  <span className="text-[var(--on-surface-variant)]">{METROLOGY_EXPLANATIONS[expandedExplanation].whyUseful}</span>
                </div>
                <div>
                  <span className="font-bold text-[var(--on-surface)]">What does a large/small value mean? </span>
                  <span className="text-[var(--on-surface-variant)]">{METROLOGY_EXPLANATIONS[expandedExplanation].largeSmallMeaning}</span>
                </div>
                <div>
                  <span className="font-bold text-[var(--accent-oxblood)]">What does it NOT prove? </span>
                  <span className="text-[var(--on-surface-variant)]">{METROLOGY_EXPLANATIONS[expandedExplanation].whatItDoesNotProve}</span>
                </div>
              </div>
            </div>
          )}

          {/* Waveform Preview Card */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                Acquisition Signal vs Analysis Signal ({analysisResult.analysis_profile})
              </span>
              <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                {analysisResult.total_samples} full-rate samples ({analysisResult.duration_s}s @ {analysisResult.sample_rate_hz} Hz)
              </span>
            </div>

            {/* SVG Waveform Rendering */}
            <div className="w-full h-44 bg-[var(--surface-muted)] rounded-lg p-2 relative overflow-hidden border border-[var(--border-subtle)]">
              <svg className="w-full h-full" viewBox="0 0 600 120" preserveAspectRatio="none">
                {/* Zero line */}
                <line x1="0" y1="60" x2="600" y2="60" stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3,3" />

                {/* Raw Acquisition Signal (Silver/Muted) */}
                <polyline
                  fill="none"
                  stroke="var(--accent-metal)"
                  strokeWidth="1.2"
                  strokeOpacity="0.6"
                  points={analysisResult.display.raw_signal
                    .map((val, idx) => {
                      const x = (idx / (analysisResult.display.raw_signal.length - 1)) * 600;
                      const y = 60 - val * 55;
                      return `${x.toFixed(1)},${y.toFixed(1)}`;
                    })
                    .join(' ')}
                />

                {/* Analysis Signal (Oxblood) */}
                <polyline
                  fill="none"
                  stroke="var(--accent-oxblood)"
                  strokeWidth="1.8"
                  points={analysisResult.display.analysis_signal
                    .map((val, idx) => {
                      const x = (idx / (analysisResult.display.analysis_signal.length - 1)) * 600;
                      const y = 60 - val * 55;
                      return `${x.toFixed(1)},${y.toFixed(1)}`;
                    })
                    .join(' ')}
                />
              </svg>

              <div className="absolute bottom-1 right-2 flex items-center gap-3 text-[10px] font-mono-code bg-[var(--surface-card)]/80 px-2 py-0.5 rounded border border-[var(--border-subtle)]">
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[var(--accent-metal)] inline-block"></span>
                  <span>Acquisition (Raw)</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[var(--accent-oxblood)] inline-block"></span>
                  <span>Analysis Signal</span>
                </div>
              </div>
            </div>

            {/* Zero-Crossing Rate & Metrology Notice */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between text-xs font-mono-code p-2.5 rounded bg-[var(--surface-muted)] gap-2">
              <div>
                <span className="text-[var(--on-surface-variant)]">Zero-Crossing Rate (AC): </span>
                <span className="font-bold text-[var(--on-surface)]">
                  {analysisResult.signal_quality.zero_crossing_rate !== null
                    ? analysisResult.signal_quality.zero_crossing_rate.toFixed(5)
                    : 'N/A'}
                </span>
              </div>
              <div className="text-[11px] text-[var(--on-surface-variant)] flex items-center gap-1">
                <Info size={12} className="text-[var(--accent-metal)]" />
                <span>Non-diagnostic waveform statistic; does NOT classify heart sounds or pathological murmurs.</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 2: WELCH SPECTRAL ANALYSIS                                    */}
      {/* ===================================================================== */}
      {activeSection === 'spectrum' && analysisResult && (
        <div className="flex flex-col gap-4">
          {/* Spectral Metadata Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div
              className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                Frequency-Bin Spacing (Δf)
              </span>
              <div className="text-xl font-mono-code font-bold text-[var(--accent-oxblood)]">
                {analysisResult.display.psd.delta_f_hz.toFixed(2)} Hz
              </div>
              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                Δf = fs / N_fft ({analysisResult.sample_rate_hz} Hz / {welchNperseg})
              </span>
            </div>

            <div
              className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                Welch Segments
              </span>
              <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
                {analysisResult.display.psd.n_segments} segments
              </div>
              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                50% Hann Overlap Averaging
              </span>
            </div>

            <div
              className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                Equivalent Noise BW (ENBW)
              </span>
              <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
                {analysisResult.spectral.enbw_hz.toFixed(2)} Hz
              </div>
              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                Hann window window bandwidth
              </span>
            </div>

            <div
              className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
              style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
            >
              <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                Spectral Density Reference
              </span>
              <div className="text-xl font-mono-code font-bold text-[var(--on-surface)]">
                1.0 FS² / Hz
              </div>
              <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                Relative logarithmic scaling (dB)
              </span>
            </div>
          </div>

          {/* Welch PSD Plot */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                Welch Power Spectral Density (Relative Power vs Frequency)
              </span>
              <button
                onClick={() => toggleExplanation('welch_psd')}
                className="text-xs font-mono-code text-[var(--accent-oxblood)] hover:underline flex items-center gap-1"
              >
                <HelpCircle size={13} />
                <span>Metrology Notes</span>
              </button>
            </div>

            {/* SVG Spectrum Curve */}
            <div className="w-full h-56 bg-[var(--surface-muted)] rounded-lg p-3 relative overflow-hidden border border-[var(--border-subtle)]">
              {analysisResult.display.psd.frequencies_hz.length > 1 ? (
                <svg className="w-full h-full" viewBox="0 0 600 160" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  {[-20, -40, -60, -80].map(db => {
                    const y = ((db - 0) / (-100)) * 160;
                    return (
                      <g key={db}>
                        <line x1="0" y1={y} x2="600" y2={y} stroke="var(--border-subtle)" strokeWidth="0.8" strokeDasharray="3,3" />
                        <text x="5" y={y - 2} fill="var(--on-surface-variant)" fontSize="9" fontFamily="monospace">
                          {db} dB
                        </text>
                      </g>
                    );
                  })}

                  {/* PSD Curve */}
                  <polyline
                    fill="none"
                    stroke="var(--accent-oxblood)"
                    strokeWidth="2"
                    points={analysisResult.display.psd.frequencies_hz
                      .map((f, idx) => {
                        const maxF = Math.max(1000, analysisResult.display.psd.frequencies_hz[analysisResult.display.psd.frequencies_hz.length - 1]);
                        const x = (f / maxF) * 600;
                        const dbVal = analysisResult.display.psd.psd_db[idx];
                        // Map 0 to -100 dB to 0..160 px
                        const clampedDb = Math.max(-100, Math.min(0, dbVal));
                        const y = (-clampedDb / 100) * 160;
                        return `${x.toFixed(1)},${y.toFixed(1)}`;
                      })
                      .join(' ')}
                  />
                </svg>
              ) : (
                <div className="flex items-center justify-center h-full text-xs font-mono-code text-[var(--on-surface-variant)]">
                  Insufficient samples for Welch spectral estimation
                </div>
              )}
            </div>

            {/* Metrology Disclaimer */}
            <div className="p-3 rounded bg-[var(--surface-muted)] text-[11px] font-mono-code text-[var(--on-surface-variant)] leading-relaxed">
              <strong>Spectral Resolution Notice:</strong> Frequency-bin spacing Δf = fs / N_fft defines the spacing of discrete frequency bins.
              Finer bin spacing through zero-padding interpolates samples in frequency but does <em>not</em> create new physical resolving power without sufficient signal duration.
              Units are dimensionless normalized amplitude² / Hz, not absolute Pa²/Hz.
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 3: ENVELOPE LAB                                               */}
      {/* ===================================================================== */}
      {activeSection === 'envelopes' && analysisResult && (
        <div className="flex flex-col gap-4">
          {/* Envelope Selector Controls */}
          <div
            className="rounded-xl border p-3 flex flex-wrap items-center justify-between gap-3 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono-code font-bold text-[var(--on-surface)]">
                Select Deterministic Feature:
              </span>
              <div className="flex items-center gap-1">
                {(['all', 'hilbert', 'moving_rms', 'tkeo', 'psd_band'] as const).map(algo => (
                  <button
                    key={algo}
                    onClick={() => setSelectedEnvelopeAlgo(algo)}
                    className={`px-2.5 py-1 rounded text-xs font-mono-code font-medium cursor-pointer transition-colors ${
                      selectedEnvelopeAlgo === algo
                        ? 'bg-[var(--accent-oxblood)] text-white font-bold'
                        : 'bg-[var(--surface-muted)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] border border-[var(--border-subtle)]'
                    }`}
                  >
                    {algo === 'all' ? 'All Traces' : algo.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px] font-mono-code text-[var(--on-surface-variant)]">
              <span>Homomorphic:</span>
              <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 font-bold border border-amber-500/30">
                DEFERRED_STAGE_B
              </span>
            </div>
          </div>

          {/* Envelope Multi-Trace Display */}
          <div
            className="rounded-xl border p-4 flex flex-col gap-3 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                Acoustic Envelope Traces (Bounded Peak-Preserving Display Representation)
              </span>
              <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                Quantitative algorithms evaluate on full-rate arrays; display is bounded
              </span>
            </div>

            <div className="w-full h-64 bg-[var(--surface-muted)] rounded-lg p-3 relative overflow-hidden border border-[var(--border-subtle)]">
              <svg className="w-full h-full" viewBox="0 0 600 180" preserveAspectRatio="none">
                {/* Baseline */}
                <line x1="0" y1="160" x2="600" y2="160" stroke="var(--border-subtle)" strokeWidth="1" />

                {/* Analysis Waveform background */}
                <polyline
                  fill="none"
                  stroke="var(--accent-metal)"
                  strokeWidth="0.9"
                  strokeOpacity="0.4"
                  points={analysisResult.display.analysis_signal
                    .map((val, idx) => {
                      const x = (idx / (analysisResult.display.analysis_signal.length - 1)) * 600;
                      const y = 90 - val * 70;
                      return `${x.toFixed(1)},${y.toFixed(1)}`;
                    })
                    .join(' ')}
                />

                {/* Hilbert Envelope (Green) */}
                {(selectedEnvelopeAlgo === 'all' || selectedEnvelopeAlgo === 'hilbert') &&
                  analysisResult.display.envelopes.hilbert && (
                    <polyline
                      fill="none"
                      stroke="#059669"
                      strokeWidth="1.8"
                      points={analysisResult.display.envelopes.hilbert.values
                        .map((val, idx) => {
                          const x = (idx / (analysisResult.display.envelopes.hilbert.values.length - 1)) * 600;
                          const y = 160 - Math.min(1.0, val) * 140;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        })
                        .join(' ')}
                    />
                  )}

                {/* Moving RMS Envelope (Blue) */}
                {(selectedEnvelopeAlgo === 'all' || selectedEnvelopeAlgo === 'moving_rms') &&
                  analysisResult.display.envelopes.moving_rms && (
                    <polyline
                      fill="none"
                      stroke="#2563eb"
                      strokeWidth="1.8"
                      points={analysisResult.display.envelopes.moving_rms.values
                        .map((val, idx) => {
                          const x = (idx / (analysisResult.display.envelopes.moving_rms.values.length - 1)) * 600;
                          const y = 160 - Math.min(1.0, val) * 140;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        })
                        .join(' ')}
                    />
                  )}

                {/* TKEO Envelope (Oxblood / Red) */}
                {(selectedEnvelopeAlgo === 'all' || selectedEnvelopeAlgo === 'tkeo') &&
                  analysisResult.display.envelopes.tkeo && (
                    <polyline
                      fill="none"
                      stroke="var(--accent-oxblood)"
                      strokeWidth="2"
                      points={(() => {
                        const vals = analysisResult.display.envelopes.tkeo.values;
                        const maxVal = Math.max(1e-6, ...vals);
                        return vals.map((val, idx) => {
                          const x = (idx / (vals.length - 1)) * 600;
                          const norm = Math.max(0, val) / maxVal;
                          const y = 160 - norm * 140;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        }).join(' ');
                      })()}
                    />
                  )}

                {/* Springer PSD-Band 40-60 Hz Envelope (Amber) */}
                {(selectedEnvelopeAlgo === 'all' || selectedEnvelopeAlgo === 'psd_band') &&
                  analysisResult.display.envelopes.psd_band && (
                    <polyline
                      fill="none"
                      stroke="#d97706"
                      strokeWidth="1.8"
                      strokeDasharray="4,2"
                      points={(() => {
                        const vals = analysisResult.display.envelopes.psd_band.values;
                        const maxVal = Math.max(1e-6, ...vals);
                        return vals.map((val, idx) => {
                          const x = (idx / (vals.length - 1)) * 600;
                          const norm = Math.max(0, val) / maxVal;
                          const y = 160 - norm * 140;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        }).join(' ');
                      })()}
                    />
                  )}
              </svg>

              {/* Legend Overlay */}
              <div className="absolute top-2 right-2 flex flex-wrap items-center gap-2 text-[10px] font-mono-code bg-[var(--surface-card)]/90 p-1.5 rounded border border-[var(--border-subtle)]">
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[#059669] inline-block"></span>
                  <span>Hilbert</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[#2563eb] inline-block"></span>
                  <span>RMS (25ms)</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[var(--accent-oxblood)] inline-block"></span>
                  <span>TKEO</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-[#d97706] inline-block"></span>
                  <span>Springer 40–60Hz</span>
                </div>
              </div>
            </div>

            {/* Metrology Cards for Envelopes */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono-code">
              <div className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-1">
                <div className="flex items-center justify-between font-bold text-[var(--on-surface)]">
                  <span>TKEO Policy</span>
                  <button onClick={() => toggleExplanation('tkeo')} className="text-[var(--accent-oxblood)]">
                    <HelpCircle size={13} />
                  </button>
                </div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">
                  Discrete operator Psi[x] = x[n]² - x[n-1]x[n+1]. Replicate boundary padding. Non-diagnostic comparator; does NOT prove S1/S2 heart sound labels.
                </div>
              </div>

              <div className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-1">
                <div className="flex items-center justify-between font-bold text-[var(--on-surface)]">
                  <span>Springer 40–60 Hz Feature</span>
                  <button onClick={() => toggleExplanation('psd_band_envelope')} className="text-[var(--accent-oxblood)]">
                    <HelpCircle size={13} />
                  </button>
                </div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">
                  50 ms Hamming window, 50% overlap. Replicates Springer et al. (2016) research feature. NOT a universal PCG band.
                </div>
              </div>

              <div className="p-3 rounded bg-[var(--surface-muted)] border border-[var(--border-subtle)] flex flex-col gap-1">
                <div className="flex items-center justify-between font-bold text-[var(--on-surface)]">
                  <span>Homomorphic Status</span>
                </div>
                <div className="text-[11px] text-[var(--on-surface-variant)]">
                  Deferred to Stage-B pending verified primary-source parameterization (R005/R006). A small correct milestone is preferred over an unverified heuristic.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 4: SYSTEM IDENTIFICATION FOUNDATION                          */}
      {/* ===================================================================== */}
      {activeSection === 'system_id' && (
        <div className="flex flex-col gap-4">
          {/* System ID Setup Controls */}
          <div
            className="rounded-xl border p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xs"
            style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
          >
            <div className="flex flex-col gap-1">
              <span className="font-mono-code text-[11px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
                SISO Best-Linear Transfer Function & Coherence Setup
              </span>
              <div className="text-xs font-mono-code text-[var(--on-surface-variant)]">
                Input: Reference Stimulus WAV | Output: Recorded Capture Session
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Reference Asset Selector */}
              <div className="flex flex-col gap-0.5">
                <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
                  Reference Asset (Input x)
                </label>
                <select
                  value={systemIdAssetId || ''}
                  onChange={e => setSystemIdAssetId(e.target.value)}
                  className="px-2.5 py-1.5 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
                  style={{ borderColor: 'var(--border-subtle)' }}
                >
                  {referenceAssets.length === 0 && <option value="">No reference assets</option>}
                  {referenceAssets.map(a => (
                    <option key={a.asset_id} value={a.asset_id}>
                      {a.filename} ({a.sample_rate_hz} Hz)
                    </option>
                  ))}
                </select>
              </div>

              {/* Excited Band Config */}
              <div className="flex flex-col gap-0.5">
                <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
                  Excited Band (Hz)
                </label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    value={excitedBandMin}
                    onChange={e => setExcitedBandMin(Number(e.target.value))}
                    className="w-16 px-1.5 py-1 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
                    style={{ borderColor: 'var(--border-subtle)' }}
                  />
                  <span className="text-xs text-[var(--on-surface-variant)]">-</span>
                  <input
                    type="number"
                    value={excitedBandMax}
                    onChange={e => setExcitedBandMax(Number(e.target.value))}
                    className="w-16 px-1.5 py-1 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
                    style={{ borderColor: 'var(--border-subtle)' }}
                  />
                </div>
              </div>

              {/* Energy Threshold Mask */}
              <div className="flex flex-col gap-0.5">
                <label className="text-[10px] font-mono-code text-[var(--on-surface-variant)] uppercase">
                  Mask Threshold (dB)
                </label>
                <input
                  type="number"
                  value={energyThresholdDb}
                  onChange={e => setEnergyThresholdDb(Number(e.target.value))}
                  className="w-16 px-1.5 py-1 rounded text-xs font-mono-code border bg-[var(--surface-muted)] text-[var(--on-surface)]"
                  style={{ borderColor: 'var(--border-subtle)' }}
                />
              </div>

              {/* Run System ID Button */}
              <button
                onClick={executeSystemId}
                disabled={systemIdRunning || !systemIdAssetId || !selectedSessionId}
                className="mt-3.5 px-3 py-1.5 rounded text-xs font-mono-code font-bold flex items-center gap-1.5 transition-colors cursor-pointer bg-[var(--accent-oxblood)] text-white hover:opacity-90 disabled:opacity-40"
              >
                <Cpu size={13} className={systemIdRunning ? 'animate-spin' : ''} />
                <span>Estimate H1 FRF</span>
              </button>
            </div>
          </div>

          {/* End-to-End Transmission Metrology Notice Banner */}
          <div
            className="rounded-xl border p-3.5 flex flex-col gap-1.5 bg-blue-500/10 border-blue-500/30 text-blue-900 dark:text-blue-300 text-xs font-mono-code"
          >
            <div className="flex items-center gap-2 font-bold">
              <ShieldCheck size={16} />
              <span>END-TO-END PHYSICAL TRANSMISSION CHAIN METROLOGY BOUNDARY</span>
            </div>
            <div className="text-[11px] leading-relaxed">
              In Tier-1 phantom testing (Stimulus WAV → DAC → Amplifier → Speaker/Exciter → Phantom Medium → Mechanical Coupling → Chestpiece → Sensor → ESP32 → USB → Host),
              the H1 estimate describes the <strong>complete end-to-end transmission chain</strong>.
              It is NOT an isolated stethoscope transfer function, NOT an anatomical chest wall response, and ordinary coherence does NOT prove causality.
            </div>
          </div>

          {/* System ID Error */}
          {systemIdError && (
            <div className="rounded-xl border p-3 flex items-center gap-2 text-xs font-mono-code bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30">
              <AlertCircle size={16} />
              <span>System ID Error: {systemIdError}</span>
            </div>
          )}

          {/* System ID Results */}
          {systemIdResult && (
            <div className="flex flex-col gap-4">
              {/* System ID Scalar Readouts */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div
                  className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
                  style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
                >
                  <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                    Mean Coherence (Excited Band)
                  </span>
                  <div className="text-xl font-mono-code font-bold text-[var(--accent-oxblood)]">
                    {systemIdResult.system_id.mean_coherence_over_excited_band !== null
                      ? systemIdResult.system_id.mean_coherence_over_excited_band.toFixed(4)
                      : 'N/A'}
                  </div>
                  <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                    Over {systemIdResult.system_id.excited_bins_count} excited frequency bins
                  </span>
                </div>

                <div
                  className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
                  style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
                >
                  <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                    Estimator & Convention
                  </span>
                  <div className="text-sm font-mono-code font-bold text-[var(--on-surface)] truncate">
                    H1(f) = S_xy / S_xx
                  </div>
                  <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                    scipy.signal.csd(x, y) = &lt;X* Y&gt; verified convention
                  </span>
                </div>

                <div
                  className="rounded-xl border p-3 flex flex-col gap-1 shadow-xs"
                  style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
                >
                  <span className="text-[10px] font-mono-code uppercase text-[var(--accent-metal)] font-bold">
                    Analysis Provenance ID
                  </span>
                  <div className="text-xs font-mono-code font-bold text-[var(--on-surface)] truncate">
                    {systemIdResult.analysis_id}
                  </div>
                  <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                    {systemIdResult.created_at_utc}
                  </span>
                </div>
              </div>

              {/* Bode Plots (Magnitude & Phase) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* H1 Magnitude (dB) */}
                <div
                  className="rounded-xl border p-4 flex flex-col gap-2 shadow-xs"
                  style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                      H1 Magnitude Response |H(f)| (dB)
                    </span>
                    <button onClick={() => toggleExplanation('system_id_frf')} className="text-[var(--accent-oxblood)]">
                      <HelpCircle size={13} />
                    </button>
                  </div>

                  <div className="w-full h-44 bg-[var(--surface-muted)] rounded-lg p-2 relative overflow-hidden border border-[var(--border-subtle)]">
                    <svg className="w-full h-full" viewBox="0 0 300 120" preserveAspectRatio="none">
                      {/* Zero dB line */}
                      <line x1="0" y1="60" x2="300" y2="60" stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3,3" />
                      <polyline
                        fill="none"
                        stroke="var(--accent-oxblood)"
                        strokeWidth="1.8"
                        points={(() => {
                          const freqs = systemIdResult.display.frequency_hz;
                          const mags = systemIdResult.display.h1_magnitude_db;
                          const maxF = Math.max(1000, freqs[freqs.length - 1]);
                          return freqs.map((f, i) => {
                            const x = (f / maxF) * 300;
                            // Map -40 to +40 dB to 120..0 px
                            const clamped = Math.max(-40, Math.min(40, mags[i]));
                            const y = 60 - (clamped / 40) * 50;
                            return `${x.toFixed(1)},${y.toFixed(1)}`;
                          }).join(' ');
                        })()}
                      />
                    </svg>
                  </div>
                  <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                    Relative transmission gain in dB across frequency spectrum
                  </span>
                </div>

                {/* H1 Phase (Degrees) */}
                <div
                  className="rounded-xl border p-4 flex flex-col gap-2 shadow-xs"
                  style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                      H1 Phase Response ∠H(f) (Degrees)
                    </span>
                  </div>

                  <div className="w-full h-44 bg-[var(--surface-muted)] rounded-lg p-2 relative overflow-hidden border border-[var(--border-subtle)]">
                    <svg className="w-full h-full" viewBox="0 0 300 120" preserveAspectRatio="none">
                      <line x1="0" y1="60" x2="300" y2="60" stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3,3" />
                      <polyline
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="1.8"
                        points={(() => {
                          const freqs = systemIdResult.display.frequency_hz;
                          const phases = systemIdResult.display.h1_phase_deg;
                          const maxF = Math.max(1000, freqs[freqs.length - 1]);
                          return freqs.map((f, i) => {
                            const x = (f / maxF) * 300;
                            // Phase in [-180, 180] deg mapped to 120..0 px
                            const y = 60 - (phases[i] / 180) * 55;
                            return `${x.toFixed(1)},${y.toFixed(1)}`;
                          }).join(' ');
                        })()}
                      />
                    </svg>
                  </div>
                  <span className="text-[10px] font-mono-code text-[var(--on-surface-variant)]">
                    Phase orientation verified against SciPy CSD convention
                  </span>
                </div>
              </div>

              {/* Coherence Curve & Excited Band Mask */}
              <div
                className="rounded-xl border p-4 flex flex-col gap-2 shadow-xs"
                style={{ backgroundColor: 'var(--surface-card)', borderColor: 'var(--border-subtle)' }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono-code text-xs font-bold text-[var(--on-surface)]">
                    Ordinary Magnitude-Squared Coherence (γ_xy²) & Excited-Frequency Energy Mask
                  </span>
                  <button onClick={() => toggleExplanation('coherence')} className="text-[var(--accent-oxblood)]">
                    <HelpCircle size={13} />
                  </button>
                </div>

                <div className="w-full h-44 bg-[var(--surface-muted)] rounded-lg p-2 relative overflow-hidden border border-[var(--border-subtle)]">
                  <svg className="w-full h-full" viewBox="0 0 600 120" preserveAspectRatio="none">
                    {/* 0.8 Coherence Threshold line */}
                    <line x1="0" y1="24" x2="600" y2="24" stroke="#059669" strokeWidth="0.8" strokeDasharray="3,3" strokeOpacity="0.7" />
                    <text x="5" y="20" fill="#059669" fontSize="9" fontFamily="monospace">
                      γ² = 0.8
                    </text>

                    {/* Coherence Curve */}
                    <polyline
                      fill="none"
                      stroke="#059669"
                      strokeWidth="2"
                      points={(() => {
                        const freqs = systemIdResult.display.frequency_hz;
                        const coh = systemIdResult.display.coherence;
                        const maxF = Math.max(1000, freqs[freqs.length - 1]);
                        return freqs.map((f, i) => {
                          const x = (f / maxF) * 600;
                          const y = 120 - Math.max(0, Math.min(1.0, coh[i])) * 115;
                          return `${x.toFixed(1)},${y.toFixed(1)}`;
                        }).join(' ');
                      })()}
                    />
                  </svg>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono-code text-[var(--on-surface-variant)]">
                  <span>Coherence bounded in [0.0, 1.0]. Evaluated over excited frequencies.</span>
                  <span className="text-[var(--accent-oxblood)] font-bold">
                    Ordinary coherence measures linear association; it does NOT establish physical causality.
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
