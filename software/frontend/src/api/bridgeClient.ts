/**
 * AuscultaForge — Local Python Bridge WebSocket & REST API Client.
 *
 * Connects the React application to the local Python FastAPI backend (http://127.0.0.1:8000).
 * Decouples waveform ingestion from hardware protocols.
 */

import { FilterPreset } from '../types';

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
}

type FrameCallback = (frame: SignalFrameData) => void;
type StreamStateCallback = (state: StreamStateData) => void;
type RecordingStateCallback = (state: RecordingStateData) => void;
type ConnectionCallback = (connected: boolean) => void;

class BridgeClient {
  private ws: WebSocket | null = null;
  private url: string = 'ws://127.0.0.1:8000/ws';
  private apiUrl: string = 'http://127.0.0.1:8000/api';
  private shouldReconnect: boolean = true;
  private reconnectTimer: number | null = null;

  private frameListeners: Set<FrameCallback> = new Set();
  private stateListeners: Set<StreamStateCallback> = new Set();
  private recordingListeners: Set<RecordingStateCallback> = new Set();
  private connectionListeners: Set<ConnectionCallback> = new Set();

  public isConnected: boolean = false;

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
    if (type === 'signal_frame') {
      const frame = msg as unknown as SignalFrameData;
      this.frameListeners.forEach(cb => cb(frame));
    } else if (type === 'stream_state' || type === 'hello') {
      const state = (msg.state || msg) as unknown as StreamStateData;
      this.stateListeners.forEach(cb => cb(state));
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

  public onSignalFrame(cb: FrameCallback) {
    this.frameListeners.add(cb);
    return () => this.frameListeners.delete(cb);
  }

  public onStreamState(cb: StreamStateCallback) {
    this.stateListeners.add(cb);
    return () => this.stateListeners.delete(cb);
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
      const resp = await fetch(`${this.apiUrl}/sessions`);
      if (!resp.ok) return [];
      return await resp.json();
    } catch {
      return [];
    }
  }

  public async fetchSession(sessionId: string): Promise<SessionItem | null> {
    try {
      const resp = await fetch(`${this.apiUrl}/sessions/${sessionId}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  public async replaySession(sessionId: string): Promise<boolean> {
    try {
      const resp = await fetch(`${this.apiUrl}/sessions/${sessionId}/replay`, { method: 'POST' });
      return resp.ok;
    } catch {
      return false;
    }
  }
}

export const bridgeClient = new BridgeClient();
