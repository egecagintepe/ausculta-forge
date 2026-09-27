export type NavigationDestination = 'home' | 'live' | 'samples' | 'device' | 'settings' | 'analysis';

export type AudioSourceType = 'none' | 'file' | 'device' | 'sample' | 'session' | 'synthetic';

export type DeviceLifecycleState =
  | 'absent'
  | 'detected'
  | 'opening'
  | 'handshaking'
  | 'ready'
  | 'streaming'
  | 'interrupted'
  | 'error'
  | 'incompatible';

export interface DeviceRuntimeState {
  state: DeviceLifecycleState;
  device_state?: DeviceLifecycleState;
  connected: boolean;
  is_connected?: boolean;
  device_id: string | null;
  firmware_version: string | null;
  sample_rate_hz: number | null;
  sample_format: string | null;
  channels?: number | null;
  sample_container_bits?: number | null;
  meaningful_data_bits?: number | null;
  transport_type: string | null;
  connected_at_utc: string | null;
  disconnected_at_utc: string | null;
  last_error: string | null;
  discovery_status: string;
  acquisition_profile?: Record<string, unknown> | null;
}

export interface DeviceEventItem {
  timestamp_utc: string;
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  metadata: Record<string, unknown>;
}

export interface DeviceIntegrityStats {
  packets_received: number;
  samples_received: number;
  sequence_gaps: number;
  repeated_packets: number;
  out_of_order_packets: number;
  crc_failures: number;
  malformed_frames: number;
  timestamp_regressions: number;
  disconnect_count: number;
  reconnect_count: number;
}

export type FilterPreset = 'recommended' | 'bell' | 'diaphragm' | 'extended';

export type FilterStrength = 'Off' | 'Normal' | 'Strong';

export type ListeningTrack = 'filtered' | 'raw';

export type SignalQualityRating = 'Good' | 'Fair' | 'Poor' | 'Unavailable';

export interface SignalQuality {
  rating: SignalQualityRating;
  score: number | null; // 0-100 or null if unavailable
  snrDb?: number;
  message?: string;
}

export interface StethoscopeDevice {
  connected: boolean;
  state: 'Not connected' | 'Detected' | 'Connecting' | 'Ready' | 'Connected' | 'Streaming' | 'Connection interrupted' | 'Incompatible' | 'Connection failed';
  deviceId: string;
  port: string;
  firmwareVersion: string;
  sampleRateHz: number;
  batteryPercent?: number;
  uptimeSeconds?: number;
}

export interface HeartSoundMetadata {
  id: string;
  title: string;
  filename: string;
  category: string;
  durationSeconds: number;
  sampleRateHz: number;
  channels: number;
  description: string;
  sourceAttribution: string;
  quality: SignalQuality;
  heartRateBpm?: number;
  spectralCentroidHz?: number;
  noiseFloorDb?: number;
}

export interface DiagnosticLogEvent {
  id: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error';
  message: string;
  component: string;
}

export interface AudioMetrics {
  currentPeakDb: number;
  currentRmsDb: number;
  clippingDetected: boolean;
  activeTrack: ListeningTrack;
  playbackVolume: number;
  isMuted: boolean;
}

export interface DiagnosticState {
  sourceType: AudioSourceType;
  fileName?: string;
  filePath?: string;
  inputFormat: string;
  inputSampleRate: string;
  channels: string;
  duration: string;
  decodeStatus: string;
  internalProcessingRate: string;
  resamplingStatus: string;
  filterPreset: string;
  filterStrength: FilterStrength;
  packetsReceived: number;
  droppedFrames: number;
  estimatedLatencyMs: number;
  bufferFillPercent: number;
  recordingActive: boolean;
  recordingFramesWritten: number;
  recordingElapsedSeconds: number;
  logs: DiagnosticLogEvent[];
}

export interface ReferenceAssetItem {
  asset_id: string;
  filename: string;
  sha256: string;
  sample_rate_hz: number;
  channels: number;
  total_samples: number;
  duration_s: number;
  created_at_utc: string;
}

export interface SessionAnalysisSummary {
  session_id: string;
  started_at_utc: string;
  ended_at_utc: string;
  duration_s: number;
  sample_rate_hz: number;
  total_samples: number;
  total_blocks: number;
  acquisition_mode: string;
  source: string;
  termination_reason: string;
  raw_wav_sha256: string;
  git_commit_sha?: string | null;
  device_info?: Record<string, unknown> | null;
  stream_quality: {
    total_blocks?: number;
    dropped_blocks?: number;
    repeated_sequences?: number;
    sequence_discontinuities?: number;
    is_healthy?: boolean;
  };
  metrics: {
    raw_rms: number;
    raw_peak: number;
    raw_crest_factor: number;
    filtered_rms: number;
    filtered_peak: number;
    filtered_crest_factor: number;
    dominant_frequency_hz: number;
    band_energy_ratios: Record<string, number>;
  };
  display: {
    time_points_s: number[];
    raw_points: number[];
    filtered_points: number[];
    spectrum_frequencies_hz: number[];
    spectrum_power_db: number[];
  };
}

export interface AnalysisComparisonResult {
  version: string;
  analysis_id: string;
  created_at_utc: string;
  reference: {
    asset_id: string;
    filename: string;
    sha256: string;
    sample_rate_hz: number;
    duration_s: number;
    total_samples: number;
  };
  capture: {
    session_id: string;
    wav_sha256: string;
    sample_rate_hz: number;
    duration_s: number;
    total_samples: number;
    acquisition_mode: string;
    source: string;
    termination_reason: string;
    device_info?: Record<string, unknown> | null;
  };
  alignment: {
    resampled: boolean;
    effective_sample_rate_hz: number;
    delay_samples: number;
    delay_ms: number;
    overlap_samples: number;
    overlap_duration_s: number;
  };
  metrics: {
    normalized_cross_correlation: number;
    rms_gain_ratio: number;
    gain_ratio_rms?: number;
    peak_gain_ratio: number;
    gain_ratio_peak?: number;
    least_squares_gain: number;
    rmse: number;
    normalized_rmse: number;
    nrmse?: number;
    signal_to_error_ratio_db: number;
    ser_db?: number;
    dominant_frequency_reference_hz: number;
    dominant_frequency_capture_hz: number;
    dominant_frequency_difference_hz: number;
    band_energy_ratio_diffs: Record<string, number>;
    mean_coherence_pcg_band: number;
  };
  display: {
    time_ms: number[];
    aligned_reference: number[];
    aligned_capture: number[];
    error: number[];
    spectrum_frequencies_hz: number[];
    spectrum_reference_db: number[];
    spectrum_capture_db: number[];
    coherence_frequencies_hz: number[];
    coherence_values: number[];
  };
  provenance: {
    app_version: string;
    git_commit_sha?: string | null;
    python_version: string;
    numpy_version: string;
    scipy_version: string;
  };
}

export interface ScientificSignalQuality {
  schema_version: string;
  sample_count: number;
  duration_s: number;
  sample_rate_hz: number;
  mean_dc: number;
  rms: number;
  peak_absolute: number;
  peak_to_peak: number;
  crest_factor: number;
  digital_full_scale_utilization: number;
  digital_saturation_count: number;
  digital_saturation_fraction: number;
  zero_crossing_rate: number | null;
  provenance: Record<string, unknown>;
}

export interface ScientificSpectralData {
  schema_version: string;
  sample_rate_hz: number;
  frequencies_hz: number[];
  psd: number[];
  psd_relative_db: number[];
  frequency_bin_spacing_hz: number;
  actual_segments: number;
  enbw_hz: number;
  config: Record<string, unknown>;
  provenance: Record<string, unknown>;
}

export interface ScientificEnvelopeSeries {
  algorithm: string;
  sample_rate_hz: number;
  time_s: number[];
  values: number[];
  parameters: Record<string, unknown>;
  input_sample_count: number;
  output_sample_count: number;
  provenance: Record<string, unknown>;
}

export interface ScientificEnvelopeLabData {
  schema_version: string;
  input_sample_rate_hz: number;
  input_duration_s: number;
  envelopes: Record<string, ScientificEnvelopeSeries>;
  provenance: Record<string, unknown>;
}

export interface ScientificDisplayData {
  time_points_s: number[];
  raw_signal: number[];
  analysis_signal: number[];
  envelopes: Record<string, { algorithm: string; time_s: number[]; values: number[] }>;
  psd: {
    frequencies_hz: number[];
    psd_db: number[];
    delta_f_hz: number;
    n_segments: number;
    db_reference: number;
  };
}

export interface ScientificSessionAnalysisResult {
  schema_version: string;
  session_id: string;
  sample_rate_hz: number;
  total_samples: number;
  duration_s: number;
  analysis_profile: string;
  signal_quality: ScientificSignalQuality;
  spectral: ScientificSpectralData;
  envelope_lab: ScientificEnvelopeLabData;
  display: ScientificDisplayData;
  provenance: {
    app_version: string;
    git_commit_sha?: string | null;
    python_version: string;
    numpy_version: string;
    scipy_version: string;
    metrology_notes?: string[];
  };
}

export interface SystemIdentificationCoreData {
  schema_version: string;
  sample_rate_hz: number;
  input_name: string;
  output_name: string;
  frequencies_hz: number[];
  gxx_autospectrum: number[];
  gyy_autospectrum: number[];
  coherence: number[];
  h1_magnitude: number[];
  h1_magnitude_db: number[];
  h1_phase_rad: number[];
  h1_phase_deg: number[];
  coherent_output_spectrum: number[];
  residual_output_spectrum: number[];
  excited_frequency_mask: boolean[];
  excited_bins_count: number;
  mean_coherence_over_excited_band: number | null;
  frequency_bin_spacing_hz: number;
  notes: string;
  provenance: Record<string, unknown>;
}

export interface SystemIdReport {
  schema_version: string;
  analysis_id: string;
  created_at_utc: string;
  reference: {
    asset_id: string;
    filename: string;
    sha256: string;
    sample_rate_hz: number;
    duration_s: number;
    total_samples: number;
  };
  capture: {
    session_id: string;
    wav_sha256: string;
    sample_rate_hz: number;
    resampled: boolean;
    duration_s: number;
    total_samples: number;
  };
  system_id: SystemIdentificationCoreData;
  display: {
    frequency_hz: number[];
    h1_magnitude_db: number[];
    h1_phase_rad: number[];
    h1_phase_deg: number[];
    coherence: number[];
    gxx: number[];
    gyy: number[];
    coherent_output_psd: number[];
    residual_output_psd: number[];
    excited_energy_mask: boolean[];
  };
  provenance: Record<string, unknown>;
}

export interface StateIntervalItem {
  state: number;
  state_name: string;
  start_s: number;
  end_s: number;
  duration_s: number;
  start_frame_50hz: number;
  end_frame_50hz: number;
}

export interface SpringerSegmentationModelSummary {
  model_id: string;
  algorithm_id: string;
  feature_profile_id: string;
  feature_names: string[];
  feature_count: number;
  feature_sample_rate_hz: number;
  created_at_utc: string;
  is_demo: boolean;
  label: string;
  notes: string;
}

export interface SpringerSegmentationCoreResult {
  schema_version: string;
  status: string;
  profile_id: string;
  model_id: string;
  heart_rate_estimate_bpm: number | null;
  cycle_duration_estimate_s: number | null;
  systolic_interval_estimate_s: number | null;
  feature_sample_rate_hz: number;
  total_frames_50hz: number;
  duration_s: number;
  state_sequence_50hz: number[];
  state_intervals: StateIntervalItem[];
  s1_intervals: StateIntervalItem[];
  s2_intervals: StateIntervalItem[];
  systole_intervals: StateIntervalItem[];
  diastole_intervals: StateIntervalItem[];
  cycle_count: number;
  technical_warnings: string[];
  feature_traces?: Record<string, unknown> | null;
  durations_summary: Record<string, unknown>;
  provenance: Record<string, unknown>;
}

export interface SpringerSegmentationReport {
  schema_version: string;
  analysis_id: string;
  created_at_utc: string;
  session: {
    session_id: string;
    sample_rate_hz: number;
    duration_s: number;
    total_samples: number;
  };
  segmentation: SpringerSegmentationCoreResult;
  display: {
    waveform: {
      time_s: number[];
      amplitude: number[];
    };
    state_intervals: StateIntervalItem[];
    feature_traces: Record<string, { time_s: number[]; values: number[] }>;
  };
  provenance: Record<string, unknown>;
}

export interface ValidationBenchmarkSummary {
  benchmark_id: string;
  status: string;
  dataset_id: string;
  dataset_version: string;
  profile_id: string;
  total_records: number;
  coverage_rate: number;
  created_at_utc: string;
}

export interface EventToleranceMetricItem {
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface EventEvaluationView {
  tolerance_ms: number;
  s1: EventToleranceMetricItem;
  s2: EventToleranceMetricItem;
  combined: EventToleranceMetricItem;
}

export interface TimingErrorStats {
  count: number;
  mean_error_ms: number;
  median_error_ms: number;
  mean_abs_error_ms: number;
  median_abs_error_ms: number;
  p25_abs_error_ms: number;
  p75_abs_error_ms: number;
  p95_abs_error_ms: number;
}

export interface StateMetricsData {
  confusion_matrix_4x4: number[][];
  per_state_precision: Record<string, number>;
  per_state_recall: Record<string, number>;
  per_state_f1: Record<string, number>;
  macro_f1: number;
  annotated_frame_agreement: number;
  total_annotated_frames: number;
  ignored_frames_state0: number;
}

export interface LocationBreakdownItem {
  location: string;
  record_count: number;
  subject_count: number;
  coverage_rate: number;
  s1_f1_100ms: number;
  s2_f1_100ms: number;
  combined_f1_100ms: number;
}

export interface FoldSummaryData {
  fold_idx: number;
  train_subjects_count: number;
  eval_subjects_count: number;
  train_records_count: number;
  eval_records_count: number;
  coverage_rate: number;
  end_to_end_combined_f1_100ms: number;
  conditional_combined_f1_100ms: number;
  macro_state_f1: number;
}

export interface ValidationBenchmarkReport {
  schema_version: string;
  benchmark_id: string;
  status: 'COMPLETE_DATASET' | 'PARTIAL_DATASET' | 'DATASET_NOT_AVAILABLE' | 'FAILED';
  config: {
    dataset_id: string;
    dataset_version: string;
    profile_id: string;
    fold_count: number;
    random_seed: number;
    tolerances_ms: number[];
    primary_event_anchor: string;
    max_subjects?: number | null;
    max_records?: number | null;
  };
  dataset_summary: Record<string, unknown>;
  fold_summaries: FoldSummaryData[];
  coverage: {
    total_eligible_records: number;
    successful_segmentations: number;
    failed_segmentations: number;
    coverage_rate: number;
    failure_status_counts: Record<string, number>;
  };
  end_to_end_event_metrics: Record<string, EventEvaluationView>;
  conditional_event_metrics: Record<string, EventEvaluationView>;
  timing_errors: {
    s1: TimingErrorStats;
    s2: TimingErrorStats;
    combined: TimingErrorStats;
  };
  state_metrics?: StateMetricsData | null;
  location_breakdown: LocationBreakdownItem[];
  failure_status_counts: Record<string, number>;
  macro_subject_metrics: Record<string, unknown>;
  training_summary: Record<string, unknown>;
  runtime_summary: Record<string, unknown>;
  provenance: Record<string, unknown>;
  warnings: string[];
  limitations: string[];
}
