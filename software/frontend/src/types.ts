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
