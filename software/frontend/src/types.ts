export type NavigationDestination = 'home' | 'live' | 'samples' | 'device' | 'settings';

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
