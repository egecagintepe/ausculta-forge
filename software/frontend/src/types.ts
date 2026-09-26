export type NavigationDestination = 'home' | 'live' | 'samples' | 'device' | 'settings';

export type AudioSourceType = 'none' | 'file' | 'device' | 'sample';

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
  state: 'Not connected' | 'Detected' | 'Connecting' | 'Connected' | 'Streaming' | 'Connection interrupted' | 'Reconnecting' | 'Connection failed';
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
