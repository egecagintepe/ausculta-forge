export type NavigationDestination = 'home' | 'live' | 'samples' | 'device' | 'settings' | 'analysis' | 'research';

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

export interface DeviceCandidate {
  device_id: string;
  descriptor: string;
  detected_at_utc: string;
  transport_hint?: string;
  port?: string;
  vid?: number;
  pid?: number;
  serial_number?: string | null;
  description?: string | null;
  manufacturer?: string | null;
  is_auscultaforge_candidate?: boolean;
}

export interface DeviceRuntimeState {
  state: DeviceLifecycleState;
  device_state?: DeviceLifecycleState;
  connected: boolean;
  is_connected?: boolean;
  device_id: string | null;
  firmware_version: string | null;
  port?: string | null;
  candidate?: DeviceCandidate | null;
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

export interface SpectralFrameData {
  frequencies_hz: number[];
  power_db: number[];
  peak_frequency_hz: number;
  dominant_band: string;
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
  quality_dimensions?: Record<string, any>;
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
  filter_metadata?: Record<string, unknown>;
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
  status: 'COMPLETE_DATASET' | 'PARTIAL_DATASET' | 'REAL_DATA_PILOT' | 'DATASET_NOT_AVAILABLE' | 'FAILED';
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

// =============================================================================
// Virtual Integration Bench (Software-Only Known-Answer Testing)
// =============================================================================

export interface VirtualBenchMetric {
  name: string;
  expected: unknown;
  observed: unknown;
  tolerance?: number | null;
  passed: boolean;
  unit: string;
  notes: string;
}

export interface VirtualBenchScenarioSummary {
  id: string;
  title: string;
  category: string;
  description: string;
}

export interface VirtualBenchScenarioResult {
  scenario_id: string;
  title: string;
  category: string;
  passed: boolean;
  status_label: string; // "SOFTWARE_KNOWN_ANSWER"
  duration_ms: number;
  metrics: VirtualBenchMetric[];
  artifacts: Record<string, string>;
  telemetry_observed: Record<string, unknown>;
  error_message?: string | null;
  parameters: Record<string, unknown>;
}

export interface VirtualBenchReport {
  bench_version: string;
  timestamp_utc: string;
  status_tag: string; // "SOFTWARE_KNOWN_ANSWER"
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  all_passed: boolean;
  scenarios: VirtualBenchScenarioResult[];
  environment_summary: Record<string, string>;
}

// =============================================================================
// Phantom Reference Playback & System Identification (Sprint 07)
// =============================================================================

export interface PhantomTemplateItem {
  template_id: string;
  name: string;
  description: string;
  stimulus_type: string;
  target_frequency_band_hz: [number, number];
  default_output_gain_dbfs: number;
  recommended_duration_s: number;
  checklist: string[];
  expected_excitation_bandwidth_hz: [number, number];
}

export interface LatencyDecompositionData {
  estimated_acoustic_lag_ms: number;
  playback_pipeline_buffer_delay_ms: number;
  total_end_to_end_latency_estimate_ms: number;
  delay_samples: number;
  effective_sample_rate_hz: number;
  is_hardware_synchronized: boolean;
  notes: string;
}

export interface PhantomAlignmentData {
  sync_status: 'SYNCHRONIZED' | 'MARGINAL_SYNC' | 'SYNC_FAILED';
  normalized_cross_correlation: number;
  estimated_delay_samples: number;
  estimated_delay_ms: number;
  overlap_samples: number;
  overlap_duration_s: number;
  least_squares_gain: number;
  rms_gain_ratio: number;
  peak_gain_ratio: number;
  rmse: number;
  normalized_rmse: number;
  signal_to_error_ratio_db: number;
  reference_clipping: Record<string, any>;
  capture_clipping: Record<string, any>;
  excitation_coverage: {
    status: 'FULL_COVERAGE' | 'PARTIAL_COVERAGE' | 'INSUFFICIENT_EXCITATION';
    coverage_fraction: number;
    target_band_hz: [number, number];
  };
}

export interface PhantomExperimentRecord {
  schema_version: string;
  trial_id: string;
  template_id: string;
  created_at_utc: string;
  intended_device: string;
  intended_chain: string;
  hardware_status: 'PENDING_PHYSICAL_MEASUREMENT' | 'SIMULATED_BENCH_TEST' | 'PHYSICAL_VERIFIED';
  output_gain_dbfs: number;
  operator_notes: string;
  stimulus: Record<string, any>;
  capture: Record<string, any>;
  latency: LatencyDecompositionData;
  alignment: PhantomAlignmentData;
  system_id: SystemIdentificationCoreData;
  display: {
    time_ms: number[];
    aligned_reference: number[];
    aligned_capture: number[];
    aligned_error: number[];
    frequency_hz: number[];
    h1_magnitude_db: number[];
    h1_phase_deg: number[];
    coherence: number[];
  };
  metrological_disclaimer: string;
  provenance: Record<string, any>;
}

export interface PhantomExperimentSummary {
  trial_id: string;
  template_id: string;
  created_at_utc: string;
  hardware_status: string;
  stimulus_id?: string;
  stimulus_type?: string;
  session_id?: string;
  sync_status?: string;
  normalized_cross_correlation?: number;
  estimated_acoustic_lag_ms?: number;
  total_end_to_end_latency_estimate_ms?: number;
  mean_coherence_over_excited_band?: number | null;
  clipping_detected?: boolean;
}

export interface DiagnosticFaultDefinition {
  code: string;
  name: string;
  subsystem: string;
  severity: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  detection_condition: string;
  evidence_needed: string;
  description_en: string;
  description_tr: string;
  possible_causes: string[];
  suggested_actions: string[];
  auto_recovery_permitted: boolean;
  affects_g1_acceptance: boolean;
  observable_without_hardware: boolean;
  emitting_component: string;
  primary_owner: string;
}

export interface DiagnosticEventRecord {
  event_id: string;
  timestamp_utc: string;
  host_monotonic_ns: number;
  severity: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  subsystem: string;
  fault_code: string;
  message: string;
  source_type: string;
  evidence_origin: 'OBSERVED_HOST' | 'REPORTED_BY_FIRMWARE' | 'DERIVED_FROM_SAMPLES' | 'INFERRED_HYPOTHESIS' | 'INJECTED_SIMULATION' | 'NOT_MEASURED';
  device_state: string;
  session_id?: string | null;
  connection_attempt_id?: string | null;
  device_port?: string | null;
  protocol_version?: string | null;
  frame_sequence?: number | null;
  first_sample_index?: number | null;
  observed_value?: any;
  expected_value?: any;
  relevant_counter_snapshot?: Record<string, any>;
  possible_causes: string[];
  suggested_actions: string[];
  event_status: 'active' | 'resolved' | 'transient';
  correlation_id?: string | null;
  occurrence_count: number;
  last_occurred_utc?: string | null;
}

export interface DiagnosticHypothesisItem {
  title: string;
  subsystem: string;
  probability: 'HIGH' | 'MEDIUM' | 'LOW' | 'INVESTIGATIVE';
  reasoning: string;
  recommended_actions: string[];
}

export interface DiagnosticCorrelationReport {
  case_id: string;
  summary: string;
  active_incident_count: number;
  ranked_hypotheses: DiagnosticHypothesisItem[];
  evidence_demarcation: Record<string, string>;
}

export interface UsbPortDescriptorItem {
  port_name: string;
  description: string;
  hwid: string;
  vid?: number | null;
  pid?: number | null;
  vid_hex?: string | null;
  pid_hex?: string | null;
  serial_number?: string | null;
  manufacturer?: string | null;
  product?: string | null;
  interface?: string | null;
  is_espressif_candidate: boolean;
  candidate_reason: string;
}

export interface UsbSessionCounters {
  host_samples_accepted: number;
  host_frames_accepted: number;
  host_sample_value_errors: number;
  host_index_discontinuities: number;
  expected_next_sample_index: number;
  last_audio_sequence: number | null;
}

export interface UsbSessionSummary {
  session_state: string;
  port: string | null;
  is_simulated: boolean;
  active_session_id: string | null;
  device_capabilities: {
    protocol_version: string;
    firmware_version: string;
    hardware_sample_rate_hz: number;
    supported_profiles_mask: number;
    max_frame_samples: number;
    device_uid_low: string;
  } | null;
  active_config: {
    sample_rate_hz: number;
    target_samples: number;
    source_mode: number;
    encoding: number;
    channels: number;
    profile_id: number;
  } | null;
  counters: UsbSessionCounters;
  latest_telemetry: Record<string, any> | null;
  final_telemetry: Record<string, any> | null;
  has_g1_evidence: boolean;
}

export interface G1EvidenceData {
  session_id: string;
  mode: string;
  target_samples: number;
  host_samples_accepted: number;
  host_frames_accepted: number;
  host_sample_value_errors: number;
  host_index_discontinuities: number;
  firmware_samples_generated: number;
  firmware_samples_dropped: number;
  verification_result: 'PASS' | 'FAIL';
  verified_at_utc: string;
  is_simulated: boolean;
}

export interface ResearchModelMetricsSummary {
  test_auroc?: number;
  test_average_precision?: number;
  test_f1?: number;
  test_balanced_accuracy?: number;
  best_epoch?: number;
  threshold?: number;
  dataset?: string;
  [key: string]: unknown;
}

export interface ResearchModelInfo {
  model_id: string;
  name: string;
  version: string;
  task: string;
  status: 'AVAILABLE' | 'MISSING_ARTIFACT' | 'DEPENDENCY_MISSING' | 'PLANNED_FUTURE' | 'RULE_BASED_FOUNDATION';
  is_research_only: boolean;
  description: string;
  author: string;
  dataset_provenance: string;
  supported_inputs: string;
  threshold: number | null;
  metrics_summary: ResearchModelMetricsSummary | null;
  manifest: Record<string, unknown> | null;
  artifact_path: string | null;
  nonclinical_disclaimer: string;
}

export interface RecordingEvaluationItem {
  file_path: string;
  file_name: string;
  channels: number;
  sample_rate_hz: number;
  duration_sec: number;
  sample_width_bytes: number;
}

export interface ResearchPredictionResponse {
  research_only: boolean;
  strictly_nonclinical: boolean;
  model_id: string;
  model_version: string;
  task: string;
  patient_identifier: string;
  positive_probability: number;
  validation_selected_threshold: number;
  predicted_label: string;
  recordings_evaluated: RecordingEvaluationItem[];
  recording_count: number;
  dataset_provenance: string;
  disclaimer: string;
  warning: string;
}

