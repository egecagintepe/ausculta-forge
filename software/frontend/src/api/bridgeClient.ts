/**
 * AuscultaForge — Local Python Bridge WebSocket & REST API Client.
 *
 * Connects the React application to the local Python FastAPI backend.
 * Supports:
 * - Dynamic desktop endpoint & ephemeral port discovery via Tauri IPC
 * - Per-process authentication token header (X-AuscultaForge-Auth) and query parameter
 * - Automatic startup polling and reconnect lifecycle
 * - Fallback to fixed port 8000 for standard web development mode
 */

import { isTauri, invoke } from '@tauri-apps/api/core';
import {
  FilterPreset,
  DeviceRuntimeState,
  DeviceEventItem,
  DeviceIntegrityStats,
  ReferenceAssetItem,
  SessionAnalysisSummary,
  AnalysisComparisonResult,
  ScientificSessionAnalysisResult,
  SystemIdReport,
  SpringerSegmentationModelSummary,
  SpringerSegmentationReport,
  ValidationBenchmarkSummary,
  ValidationBenchmarkReport,
  VirtualBenchScenarioSummary,
  VirtualBenchReport,
  SpectralFrameData,
  PhantomTemplateItem,
  PhantomExperimentRecord,
  PhantomExperimentSummary,
  DiagnosticFaultDefinition,
  DiagnosticEventRecord,
  DiagnosticCorrelationReport,
  UsbPortDescriptorItem,
  UsbSessionSummary,
  G1EvidenceData,
  ResearchModelInfo,
  ResearchPredictionResponse,
} from '../types';


export interface SignalFrameData {
  sequence: number;
  timestamp_s: number;
  sample_rate_hz: number;
  raw_samples: number[];
  filtered_samples: number[];
  metrics: {
    rms: number;
    peak: number;
    crest_factor: number;
  };
  stream_quality: {
    total_blocks: number;
    dropped_blocks: number;
    repeated_sequences: number;
    sequence_discontinuities: number;
    is_healthy: boolean;
  };
  recording_active: boolean;
}

export interface DisplayFrameData {
  stream_id?: string;
  type: 'display_frame';
  version: string;
  source_seq_start: number;
  source_seq_end: number;
  window_start_ts: number;
  window_end_ts: number;
  sample_rate_hz: number;
  source_sample_count: number;
  raw_points: number[];
  filtered_points: number[];
  metrics: {
    rms: number;
    peak: number;
    crest_factor: number;
  };
  stream_quality: {
    total_blocks: number;
    dropped_blocks: number;
    repeated_sequences: number;
    sequence_discontinuities: number;
    is_healthy: boolean;
  };
  recording_active: boolean;
  dropped_display_frames: number;
  spectral_frame?: SpectralFrameData;
}

export interface StreamStateData {
  is_streaming: boolean;
  is_paused: boolean;
  source_type: string;
  active_source_name: string;
  sample_rate_hz: number;
  filter_preset: FilterPreset;
  filter_low_hz: number;
  filter_high_hz: number;
}

export interface RecordingStateData {
  is_recording: boolean;
  session_id: string | null;
  elapsed_seconds: number;
  samples_recorded: number;
  blocks_recorded: number;
  source: string;
  sample_rate_hz: number;
}

export interface SessionIntegrityCheck {
  session_id: string;
  is_valid: boolean;
  status: string;
  sha256_match: boolean;
  expected_sha256: string;
  actual_sha256: string;
  sample_count_match: boolean;
  metadata_samples: number;
  wav_samples: number;
  sample_rate_match: boolean;
  metadata_sample_rate: number;
  wav_sample_rate: number;
  termination_reason: string;
  details: string;
}

export interface SessionItem {
  session_id: string;
  started_at_utc: string;
  ended_at_utc: string;
  source: string;
  sample_rate_hz: number;
  total_blocks: number;
  total_samples: number;
  duration_s: number;
  raw_wav_relpath: string;
  raw_wav_sha256: string;
  stream_quality: {
    total_blocks: number;
    dropped_blocks: number;
    repeated_sequences: number;
    sequence_discontinuities: number;
    is_healthy: boolean;
  };
  session_dir?: string;
  acquisition_mode?: string;
  termination_reason?: string;
  device_info?: Record<string, unknown>;
  schema_version?: string;
  storage_format?: string;
  wire_format?: string;
  storage_disclaimer?: string;
  processing_profile?: Record<string, unknown>;
  status?: string;
}

export interface BackendDesktopConfig {
  schema_version?: string;
  app?: string;
  version?: string;
  host?: string;
  port: number;
  auth_token?: string | null;
  pid: number;
  storage_dir: string;
  status: string;
  http_base_url: string;
  ws_url: string;
  health_url?: string;
}

type FrameCallback = (frame: SignalFrameData) => void;
type DisplayFrameCallback = (frame: DisplayFrameData) => void;
type StreamStateCallback = (state: StreamStateData) => void;
type RecordingStateCallback = (state: RecordingStateData) => void;
type DeviceStateCallback = (state: DeviceRuntimeState) => void;
type DeviceEventCallback = (event: DeviceEventItem) => void;
type DeviceStatsCallback = (stats: DeviceIntegrityStats) => void;
type ConnectionCallback = (connected: boolean) => void;

class BridgeClient {
  private ws: WebSocket | null = null;
  private url: string = 'ws://127.0.0.1:8000/ws';
  private apiUrl: string = 'http://127.0.0.1:8000/api';
  private authToken: string = '';
  private storageDir: string = '';
  private isDesktopMode: boolean = false;
  private activeEndpoint: string = '127.0.0.1:8000';
  private shouldReconnect: boolean = true;
  private reconnectTimer: number | null = null;
  private initPromise: Promise<boolean> | null = null;

  private frameListeners: Set<FrameCallback> = new Set();
  private displayFrameListeners: Set<DisplayFrameCallback> = new Set();
  private stateListeners: Set<StreamStateCallback> = new Set();
  private recordingListeners: Set<RecordingStateCallback> = new Set();
  private deviceStateListeners: Set<DeviceStateCallback> = new Set();
  private deviceEventListeners: Set<DeviceEventCallback> = new Set();
  private deviceStatsListeners: Set<DeviceStatsCallback> = new Set();
  private connectionListeners: Set<ConnectionCallback> = new Set();

  public isConnected: boolean = false;

  /**
   * Initializes desktop backend endpoint and authentication token via Tauri IPC.
   * If running in a standard web browser, gracefully falls back to default localhost:8000.
   */
  public async initDesktopBridge(): Promise<boolean> {
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      if (!isTauri()) {
        this.isDesktopMode = false;
        this.activeEndpoint = '127.0.0.1:8000';
        return true;
      }

      this.isDesktopMode = true;
      const maxAttempts = 60; // 60 * 250ms = 15 seconds
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          const cfg = await invoke<BackendDesktopConfig>('get_backend_config');
          if (cfg && cfg.port) {
            this.apiUrl = `${cfg.http_base_url}/api`;
            this.url = cfg.ws_url;
            this.authToken = cfg.auth_token || '';
            this.storageDir = cfg.storage_dir;
            this.activeEndpoint = `127.0.0.1:${cfg.port}`;
            return true;
          }
        } catch {
          // Backend might still be starting up, retry
        }
        await new Promise((r) => setTimeout(r, 250));
      }

      console.warn('[BridgeClient] Failed to resolve backend config from Tauri within timeout');
      return false;
    })();

    return this.initPromise;
  }

  public getEndpoint(): string {
    return this.activeEndpoint;
  }

  public getWsUrl(): string {
    return this.url;
  }

  public getSanitizedWsUrl(): string {
    return this.url.replace(/([?&]token=)[^&]+/, '$1***');
  }

  public getApiUrl(): string {
    return this.apiUrl;
  }

  public getAuthToken(): string {
    return this.authToken;
  }

  public getStorageDir(): string {
    return this.storageDir;
  }

  public isDesktop(): boolean {
    return this.isDesktopMode;
  }

  public async openStorageDir(): Promise<void> {
    if (isTauri()) {
      try {
        await invoke('open_storage_directory');
      } catch (e) {
        console.error('[BridgeClient] Failed to open storage dir:', e);
      }
    }
  }

  public async restartBackend(): Promise<boolean> {
    if (isTauri()) {
      try {
        this.disconnect();
        const cfg = await invoke<BackendDesktopConfig>('restart_backend');
        if (cfg && cfg.port) {
          this.apiUrl = `${cfg.http_base_url}/api`;
          this.url = cfg.ws_url;
          this.authToken = cfg.auth_token;
          this.storageDir = cfg.storage_dir;
          this.activeEndpoint = `127.0.0.1:${cfg.port}`;
          this.connect();
          return true;
        }
      } catch (e) {
        console.error('[BridgeClient] Backend restart failed:', e);
      }
    }
    return false;
  }

  private async request(path: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers || {});
    if (this.authToken) {
      headers.set('X-AuscultaForge-Auth', this.authToken);
    }
    return fetch(`${this.apiUrl}${path}`, {
      ...options,
      headers,
    });
  }

  public connect(url?: string) {
    if (url) this.url = url;
    this.shouldReconnect = true;

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.notifyConnection(true);
        // Refresh authoritative device state, stats, and events upon connection/reconnect
        this.fetchDeviceState().then(dev => {
          if (dev) this.deviceStateListeners.forEach(cb => cb(dev));
        });
        this.fetchDeviceStats().then(stats => {
          if (stats) this.deviceStatsListeners.forEach(cb => cb(stats));
        });
        this.fetchDeviceEvents().then(evts => {
          if (evts && evts.length > 0) {
            evts.forEach(evt => this.deviceEventListeners.forEach(cb => cb(evt)));
          }
        });
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.notifyConnection(false);
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.isConnected = false;
        this.notifyConnection(false);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch {
          // ignore malformed message
        }
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this.notifyConnection(false);
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) {
        this.connect();
      }
    }, 2000);
  }

  private handleMessage(msg: Record<string, unknown>) {
    const type = msg.type;
    if (type === 'display_frame') {
      const frame = msg as unknown as DisplayFrameData;
      this.displayFrameListeners.forEach(cb => cb(frame));
    } else if (type === 'signal_frame') {
      const frame = msg as unknown as SignalFrameData;
      this.frameListeners.forEach(cb => cb(frame));
    } else if (type === 'stream_state') {
      const state = (msg.state || msg) as unknown as StreamStateData;
      this.stateListeners.forEach(cb => cb(state));
    } else if (type === 'hello') {
      if (msg.state) {
        this.stateListeners.forEach(cb => cb(msg.state as unknown as StreamStateData));
      }
      if (msg.device_state) {
        this.deviceStateListeners.forEach(cb => cb(msg.device_state as unknown as DeviceRuntimeState));
      }
    } else if (type === 'device_state') {
      const dev = (typeof msg.state === 'object' && msg.state !== null ? msg.state : msg) as unknown as DeviceRuntimeState;
      this.deviceStateListeners.forEach(cb => cb(dev));
    } else if (type === 'device_event') {
      const evt = (msg.event || msg) as unknown as DeviceEventItem;
      this.deviceEventListeners.forEach(cb => cb(evt));
    } else if (type === 'device_stats') {
      const stats = (msg.stats || msg) as unknown as DeviceIntegrityStats;
      this.deviceStatsListeners.forEach(cb => cb(stats));
    } else if (type === 'recording_state') {
      const rec = msg as unknown as RecordingStateData;
      this.recordingListeners.forEach(cb => cb(rec));
    }
  }

  private notifyConnection(connected: boolean) {
    this.connectionListeners.forEach(cb => cb(connected));
  }

  public sendCommand(cmd: Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(cmd));
    }
  }

  public onDisplayFrame(cb: DisplayFrameCallback) {
    this.displayFrameListeners.add(cb);
    return () => this.displayFrameListeners.delete(cb);
  }

  public onSignalFrame(cb: FrameCallback) {
    this.frameListeners.add(cb);
    return () => this.frameListeners.delete(cb);
  }

  public onStreamState(cb: StreamStateCallback) {
    this.stateListeners.add(cb);
    return () => this.stateListeners.delete(cb);
  }

  public onDeviceState(cb: DeviceStateCallback) {
    this.deviceStateListeners.add(cb);
    return () => this.deviceStateListeners.delete(cb);
  }

  public onDeviceEvent(cb: DeviceEventCallback) {
    this.deviceEventListeners.add(cb);
    return () => this.deviceEventListeners.delete(cb);
  }

  public onDeviceStats(cb: DeviceStatsCallback) {
    this.deviceStatsListeners.add(cb);
    return () => this.deviceStatsListeners.delete(cb);
  }

  public onRecordingState(cb: RecordingStateCallback) {
    this.recordingListeners.add(cb);
    return () => this.recordingListeners.delete(cb);
  }

  public onConnectionChange(cb: ConnectionCallback) {
    this.connectionListeners.add(cb);
    cb(this.isConnected);
    return () => this.connectionListeners.delete(cb);
  }

  // High level actions
  public setFilter(preset: FilterPreset, low_hz?: number, high_hz?: number) {
    this.sendCommand({ action: 'set_filter', preset, low_hz, high_hz });
  }

  public startStream() {
    this.sendCommand({ action: 'start_stream' });
  }

  public pauseStream() {
    this.sendCommand({ action: 'pause_stream' });
  }

  public resumeStream() {
    this.sendCommand({ action: 'resume_stream' });
  }

  public stopStream() {
    this.sendCommand({ action: 'stop_stream' });
  }

  public selectSource(sourceType: string, path?: string, sessionId?: string) {
    this.sendCommand({ action: 'select_source', source_type: sourceType, path, session_id: sessionId });
  }

  public startRecording(source?: string) {
    this.sendCommand({ action: 'start_recording', source });
  }

  public stopRecording() {
    this.sendCommand({ action: 'stop_recording' });
  }

  // REST API Helpers
  public async fetchSessions(): Promise<SessionItem[]> {
    try {
      const resp = await this.request('/sessions');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchSession(sessionId: string): Promise<SessionItem | null> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async replaySession(sessionId: string): Promise<boolean> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}/replay`, { method: 'POST' });
      return resp.ok;
    } catch {
      return false;
    }
  }

  public async verifySession(sessionId: string): Promise<SessionIntegrityCheck | null> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}/verify`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async deleteSession(sessionId: string): Promise<boolean> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
      });
      return resp.ok;
    } catch {
      return false;
    }
  }

  public async getSessionManifest(sessionId: string): Promise<Record<string, unknown> | null> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}/manifest`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async fetchDeviceState(): Promise<DeviceRuntimeState | null> {
    try {
      const resp = await this.request('/device/state');
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async fetchDeviceEvents(): Promise<DeviceEventItem[]> {
    try {
      const resp = await this.request('/device/events');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchDeviceStats(): Promise<DeviceIntegrityStats | null> {
    try {
      const resp = await this.request('/device/stats');
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async pollDevice(): Promise<{ candidates: unknown[]; state: DeviceRuntimeState } | null> {
    try {
      const resp = await this.request('/device/poll', { method: 'POST' });
      if (!resp.ok) return null;
      const data = await resp.json();
      if (data.state) {
        this.deviceStateListeners.forEach(cb => cb(data.state));
      }
      return data;
    } catch {
      return null;
    }
  }

  public async disconnectDevice(): Promise<DeviceRuntimeState | null> {
    try {
      const resp = await this.request('/device/disconnect', { method: 'POST' });
      if (!resp.ok) return null;
      const data = await resp.json();
      this.deviceStateListeners.forEach(cb => cb(data));
      return data;
    } catch {
      return null;
    }
  }

  // =========================================================================
  // Analysis & Validation Workbench APIs
  // =========================================================================

  public async listReferenceAssets(): Promise<ReferenceAssetItem[]> {
    try {
      const resp = await this.request('/analysis/assets');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async uploadReferenceAsset(file: File): Promise<ReferenceAssetItem> {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await this.request('/analysis/assets', {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || `Upload failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async deleteReferenceAsset(assetId: string): Promise<boolean> {
    try {
      const resp = await this.request(`/analysis/assets/${encodeURIComponent(assetId)}`, {
        method: 'DELETE',
      });
      return resp.ok;
    } catch {
      return false;
    }
  }

  public async getSessionAnalysisSummary(sessionId: string, maxPoints: number = 600): Promise<SessionAnalysisSummary | null> {
    try {
      const resp = await this.request(`/sessions/${encodeURIComponent(sessionId)}/analysis-summary?max_points=${maxPoints}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async compareReferenceAndCapture(
    assetId: string,
    sessionId: string,
    maxPoints: number = 600
  ): Promise<AnalysisComparisonResult> {
    const resp = await this.request('/analysis/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset_id: assetId, session_id: sessionId, max_points: maxPoints }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Comparison failed' }));
      throw new Error(err.detail || `Comparison failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async getComparisonReport(analysisId: string): Promise<AnalysisComparisonResult | null> {
    try {
      const resp = await this.request(`/analysis/${encodeURIComponent(analysisId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public getExportReportUrl(analysisId: string): string {
    const base = `${this.apiUrl}/analysis/${encodeURIComponent(analysisId)}/export`;
    return this.authToken ? `${base}?token=${encodeURIComponent(this.authToken)}` : base;
  }

  // =========================================================================
  // Scientific Signal Quality, Spectral & System Identification APIs
  // =========================================================================

  public async getScientificProfiles(): Promise<any[]> {
    try {
      const resp = await this.request('/scientific/profiles');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async analyzeSessionScientific(
    sessionId: string,
    profileId: string = 'GENERAL_PCG_V1',
    welchNperseg: number = 2048,
    maxPoints: number = 600
  ): Promise<ScientificSessionAnalysisResult> {
    const resp = await this.request(`/scientific/session/${encodeURIComponent(sessionId)}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profileId,
        welch_nperseg: welchNperseg,
        max_display_points: maxPoints,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Scientific analysis failed' }));
      throw new Error(err.detail || `Analysis failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async runSystemIdentification(
    assetId: string,
    sessionId: string,
    params?: {
      nperseg?: number;
      noverlap?: number;
      excited_band_min_hz?: number;
      excited_band_max_hz?: number;
      energy_threshold_db_rel_max?: number;
      max_display_points?: number;
    }
  ): Promise<SystemIdReport> {
    const resp = await this.request('/scientific/system-id', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asset_id: assetId,
        session_id: sessionId,
        nperseg: params?.nperseg ?? 1024,
        noverlap: params?.noverlap ?? 512,
        excited_band_min_hz: params?.excited_band_min_hz ?? 20.0,
        excited_band_max_hz: params?.excited_band_max_hz ?? 1000.0,
        energy_threshold_db_rel_max: params?.energy_threshold_db_rel_max ?? -30.0,
        max_display_points: params?.max_display_points ?? 300,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'System identification failed' }));
      throw new Error(err.detail || `System ID failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async listSystemIdReports(): Promise<any[]> {
    try {
      const resp = await this.request('/scientific/system-id/reports');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async getSystemIdReport(analysisId: string): Promise<SystemIdReport | null> {
    try {
      const resp = await this.request(`/scientific/system-id/${encodeURIComponent(analysisId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  // =========================================================================
  // Phantom Reference Playback & System Identification
  // =========================================================================

  public async listPhantomTemplates(): Promise<PhantomTemplateItem[]> {
    try {
      const resp = await this.request('/scientific/phantom/templates');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async generatePhantomStimulus(payload: {
    stimulus_type: string;
    duration_s?: number;
    sample_rate_hz?: number;
    amplitude_fs?: number;
    save_as_asset?: boolean;
    custom_params?: Record<string, any>;
  }): Promise<any> {
    const resp = await this.request('/scientific/phantom/stimulus/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to generate phantom stimulus' }));
      throw new Error(err.detail || `Stimulus generation failed (${resp.status})`);
    }
    return await resp.json();
  }

  public async characterizePhantom(payload: {
    asset_id: string;
    session_id: string;
    template_id?: string;
    trial_id?: string;
    output_gain_dbfs?: number;
    operator_notes?: string;
    hardware_status?: string;
    pipeline_buffer_delay_ms?: number;
    max_display_points?: number;
  }): Promise<PhantomExperimentRecord> {
    const resp = await this.request('/scientific/phantom/characterize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Phantom characterization failed' }));
      throw new Error(err.detail || `Phantom characterization failed (${resp.status})`);
    }
    return await resp.json();
  }

  public async listPhantomExperiments(): Promise<PhantomExperimentSummary[]> {
    try {
      const resp = await this.request('/scientific/phantom/experiments');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async getPhantomExperiment(trialId: string): Promise<PhantomExperimentRecord | null> {
    try {
      const resp = await this.request(`/scientific/phantom/experiments/${encodeURIComponent(trialId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async listSegmentationModels(): Promise<SpringerSegmentationModelSummary[]> {
    try {
      const resp = await this.request('/scientific/segmentation/models');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async runSegmentation(
    sessionId: string,
    modelId?: string | null,
    profileId: string = 'SPRINGER_PHYSIONET_REFERENCE_V1',
    maxPoints: number = 600
  ): Promise<SpringerSegmentationReport> {
    const resp = await this.request('/scientific/segmentation/segment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        model_id: modelId || null,
        profile_id: profileId,
        max_display_points: maxPoints,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Segmentation failed' }));
      throw new Error(err.detail || `Segmentation failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async listSegmentationReports(): Promise<any[]> {
    try {
      const resp = await this.request('/scientific/segmentation/reports');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async getSegmentationReport(analysisId: string): Promise<SpringerSegmentationReport | null> {
    try {
      const resp = await this.request(`/scientific/segmentation/${encodeURIComponent(analysisId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async listValidationBenchmarks(): Promise<ValidationBenchmarkSummary[]> {
    try {
      const resp = await this.request('/scientific/validation/benchmarks');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async getValidationBenchmark(benchmarkId: string): Promise<ValidationBenchmarkReport | null> {
    try {
      const resp = await this.request(`/scientific/validation/benchmarks/${encodeURIComponent(benchmarkId)}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async listBenchScenarios(): Promise<VirtualBenchScenarioSummary[]> {
    try {
      const resp = await this.request('/bench/scenarios');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async runBenchScenario(scenarioId: string = 'all', seed: number = 42): Promise<VirtualBenchReport> {
    const resp = await this.request('/bench/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId, seed }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Virtual bench run failed' }));
      throw new Error(err.detail || `Virtual bench run failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  // =========================================================================
  // Diagnostic Intelligence & Flight Recorder API Methods
  // =========================================================================

  public async listFaultCatalog(): Promise<DiagnosticFaultDefinition[]> {
    try {
      const resp = await this.request('/diagnostics/catalog');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchDiagnosticEvents(params?: {
    limit?: number;
    subsystem?: string;
    severity?: string;
    fault_code?: string;
  }): Promise<DiagnosticEventRecord[]> {
    try {
      const query = new URLSearchParams();
      if (params?.limit) query.set('limit', String(params.limit));
      if (params?.subsystem) query.set('subsystem', params.subsystem);
      if (params?.severity) query.set('severity', params.severity);
      if (params?.fault_code) query.set('fault_code', params.fault_code);

      const qs = query.toString();
      const path = qs ? `/diagnostics/events?${qs}` : '/diagnostics/events';
      const resp = await this.request(path);
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchActiveFaults(): Promise<DiagnosticEventRecord[]> {
    try {
      const resp = await this.request('/diagnostics/active-faults');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchCorrelationReport(): Promise<DiagnosticCorrelationReport | null> {
    try {
      const resp = await this.request('/diagnostics/correlation');
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async scanUsbPorts(): Promise<UsbPortDescriptorItem[]> {
    try {
      const resp = await this.request('/diagnostics/usb/scan');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async injectFaultScenario(scenarioId: string): Promise<any> {
    const resp = await this.request('/diagnostics/fault/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to inject fault' }));
      throw new Error(err.detail || `Fault injection failed (${resp.status})`);
    }
    return await resp.json();
  }

  public async resolveFault(faultCode: string, resolutionMessage?: string): Promise<any> {
    const resp = await this.request('/diagnostics/fault/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fault_code: faultCode, resolution_message: resolutionMessage }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to resolve fault' }));
      throw new Error(err.detail || `Fault resolution failed (${resp.status})`);
    }
    return await resp.json();
  }

  public async exportDiagnosticsBundle(): Promise<Blob> {
    const resp = await this.request('/diagnostics/export', {
      method: 'POST',
    });
    if (!resp.ok) {
      throw new Error(`Export diagnostics bundle failed with status ${resp.status}`);
    }
    return await resp.blob();
  }

  // =========================================================================
  // Production USB CDC-ACM Device Control & Acquisition Methods
  // =========================================================================

  public async getUsbPorts(): Promise<UsbPortDescriptorItem[]> {
    try {
      const resp = await this.request('/device/usb/ports');
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async connectUsbDevice(port: string, baudrate: number = 115200, timeoutS: number = 3.0): Promise<any> {
    const resp = await this.request('/device/usb/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port, baudrate, timeout_s: timeoutS }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to connect to device' }));
      throw new Error(err.detail || `Connect failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async startUsbAcquisition(params?: {
    sourceMode?: number;
    targetSamples?: number;
    sampleRateHz?: number;
    timeoutS?: number;
  }): Promise<any> {
    const resp = await this.request('/device/usb/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_mode: params?.sourceMode ?? 1,
        target_samples: params?.targetSamples ?? 480000,
        sample_rate_hz: params?.sampleRateHz ?? 48000,
        timeout_s: params?.timeoutS ?? 3.0,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to start acquisition' }));
      throw new Error(err.detail || `Start acquisition failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async stopUsbAcquisition(): Promise<any> {
    const resp = await this.request('/device/usb/stop', {
      method: 'POST',
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to stop acquisition' }));
      throw new Error(err.detail || `Stop acquisition failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async disconnectUsbDevice(): Promise<any> {
    const resp = await this.request('/device/usb/disconnect', {
      method: 'POST',
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to disconnect device' }));
      throw new Error(err.detail || `Disconnect failed with status ${resp.status}`);
    }
    return await resp.json();
  }

  public async getUsbSession(): Promise<UsbSessionSummary | null> {
    try {
      const resp = await this.request('/device/usb/session');
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async getG1Evidence(): Promise<G1EvidenceData | null> {
    try {
      const resp = await this.request('/device/usb/g1-evidence');
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async exportG1Evidence(): Promise<void> {
    const response = await this.request('/device/usb/g1-export', { method: 'POST' });
    if (!response.ok) throw new Error('No completed G1 evidence to export');
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = 'auscultaforge-g1-evidence.zip';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  public async getResearchModels(): Promise<ResearchModelInfo[]> {
    const resp = await this.request('/research/ml/models');
    if (!resp.ok) {
      throw new Error(`Failed to load research models: ${resp.status}`);
    }
    return await resp.json();
  }

  public async getResearchModel(modelId: string): Promise<ResearchModelInfo> {
    const resp = await this.request(`/research/ml/models/${encodeURIComponent(modelId)}`);
    if (!resp.ok) {
      throw new Error(`Failed to load research model ${modelId}: ${resp.status}`);
    }
    return await resp.json();
  }

  public async predictResearch(
    filePaths: string[],
    modelId: string = 'af_murmur_mil_1.0',
    patientIdentifier?: string,
    sameSubjectAttestation: boolean = false
  ): Promise<ResearchPredictionResponse> {
    const resp = await this.request('/research/ml/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_paths: filePaths,
        model_id: modelId,
        patient_identifier: patientIdentifier,
        same_subject_attestation: sameSubjectAttestation,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
      throw new Error(err.detail || `Research inference failed (${resp.status})`);
    }
    return await resp.json();
  }
}


export const bridgeClient = new BridgeClient();
