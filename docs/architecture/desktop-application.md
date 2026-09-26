# AuscultaForge — Desktop Application & Local Bridge Architecture

## 1. Architectural Overview & System Boundary

The AuscultaForge desktop software architecture is structured into strictly isolated tiers:

```text
+-------------------------------------------------------------+
| Physical Hardware (Future ESP32-S3) / Simulation Sources   |
| (I2S MEMS -> DMA -> Wired Native USB / RealtimeWavSource)   |
+-------------------------------------------------------------+
                              │
                              ▼ (SampleBlock Interface)
+-------------------------------------------------------------+
| pcg_core (DSP & Processing Pipeline)                        |
| - SampleBlock Uniform Data Container                        |
| - Stateful Butterworth Bandpass Filtering                   |
| - LiveStreamingPipeline & StreamQualityMonitor              |
| - SessionRecorder (raw.wav + session.json sidecar)         |
+-------------------------------------------------------------+
                              │
                              ▼ (Direct Python Calls)
+-------------------------------------------------------------+
| pcg_app (Local Desktop Bridge Layer)                        |
| - FastAPI REST Endpoints (/api/status, /api/sessions, etc.) |
| - StreamManager Background Async Task                       |
| - WebSocket Protocol v1.0 Broadcaster & Command Ingestion   |
+-------------------------------------------------------------+
                              │
                              ▼ (Local WebSocket: ws://127.0.0.1:8000/ws)
+-------------------------------------------------------------+
| React / Vite Frontend (Local Desktop Client)                |
| - Dual-Channel Canvas Oscilloscope (Raw vs Filtered)        |
| - Real-time Signal Metrics & Health Display                 |
| - Passband Filter Selection Controls                        |
| - Session Recording Controls & Session Replay Browser       |
| - Strict Consumer of State (No DSP Reimplemented in UI)     |
+-------------------------------------------------------------+
```

---

## 2. Fundamental Architectural Rule: No DSP in the Frontend

1. **Strict Consumer Model:**
   The React frontend is strictly a visualization and presentation consumer. All filtering, decimation, RMS calculation, peak detection, crest factor computation, and stream quality inspection are executed exclusively within `pcg_core`.
2. **Deterministic Processing:**
   Running DSP in Python guarantees that the exact same filtering algorithms run during automated batch testing, interactive replay, and live bench testing.
3. **Decoupled Render Cadence:**
   Waveform frames arrive in chunks of 128 samples ($\approx 32\text{ ms}$ at $4\text{ kHz}$, yielding $\approx 31\text{ fps}$). The HTML5 Canvas batches min/max bins across its pixel width, rendering smooth physiological waveforms without overloading the browser's main thread.

---

## 3. Strict Separation of Protocols

AuscultaForge maintains an explicit architectural distinction between two fundamentally different communication boundaries:

| Dimension | 1. MCU-to-PC Transport Protocol | 2. Python-to-UI Application Protocol |
|---|---|---|
| **Specification Document** | [`docs/protocol/PROTOCOL_DRAFT.md`](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/protocol/PROTOCOL_DRAFT.md) | [`software/pcg_app/protocol.py`](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/software/pcg_app/protocol.py) |
| **Physical Boundary** | Physical USB cable between ESP32-S3 and Host PC | Local loopback network interface (`127.0.0.1`) |
| **Transport Layer** | Wired Native USB (Bulk endpoint or CDC-ACM) | HTTP / WebSocket (`ws://127.0.0.1:8000/ws`) |
| **Data Encoding** | Packed binary frames (Sync word, Sequence, Timestamp, PCM payload, CRC) | JSON message envelopes (`signal_frame`, `stream_state`, `recording_state`) |
| **Purpose** | Low-level embedded packet integrity, CRC error detection, DMA packet ingestion | Application state synchronization, telemetry display, and UI command dispatch |
| **Status** | Conceptual draft (byte details reserved for bench validation) | **Operational Protocol v1.0** |

---

## 4. Local WebSocket Message Contracts (Protocol v1.0)

### Server $\rightarrow$ Client Envelopes

1. **`hello`:** Sent immediately upon WebSocket connection handshake:
   ```json
   {
     "type": "hello",
     "version": "1.0",
     "app": "AuscultaForge Bridge",
     "capabilities": {
       "sample_rate_hz": 4000,
       "sources": ["none", "hardware", "session", "realtime_wav", "synthetic_dev"],
       "filter_presets": ["recommended", "bell", "diaphragm", "extended"],
       "display_pipeline": {
         "target_display_hz": 25.0,
         "points_per_frame": 128,
         "spectral_update_hz": 5.0
       }
     },
     "state": { ... }
   }
   ```
2. **`display_frame`:** Primary display-oriented snapshot emitted at UI cadence (~25 Hz):
   ```json
   {
     "type": "display_frame",
     "version": "1.0",
     "source_seq_start": 140,
     "source_seq_end": 143,
     "window_start_ts": 4.544,
     "window_end_ts": 4.584,
     "sample_rate_hz": 48000,
     "source_sample_count": 1920,
     "raw_points": [-0.012, 0.045, ...],
     "filtered_points": [-0.008, 0.038, ...],
     "metrics": {
       "rms": 0.08412,
       "peak": 0.34120,
       "crest_factor": 4.056
     },
     "stream_quality": {
       "total_blocks": 143,
       "dropped_blocks": 0,
       "repeated_sequences": 0,
       "sequence_discontinuities": 0,
       "is_healthy": true
     },
     "recording_active": false,
     "dropped_display_frames": 0,
     "spectral_frame": { ... }
   }
   ```
3. **`signal_frame`:** Backward-compatible per-block signal transmission (optional, for legacy tooling).
4. **`stream_state`:** Broadcast whenever active source, filter passband, or run state changes.
5. **`recording_state`:** Broadcast whenever a session recording is started, progressing, or stopped.
6. **`device_state`:** Real-time hardware lifecycle and capability status (`absent`, `detected`, `opening`, `handshaking`, `ready`, `streaming`, `interrupted`, `error`, `incompatible`).
7. **`device_event`:** Structured audit log event emission (`timestamp_utc`, `code`, `severity`, `message`).
8. **`device_stats`:** Real-time physical stream integrity counters (packets received, sequence gaps, CRC failures, disconnect/reconnect counts).

### Client $\rightarrow$ Server Commands

- `{"action": "start_stream"}` / `{"action": "pause_stream"}`
- `{"action": "set_filter", "preset": "recommended" | "bell" | "diaphragm" | "extended"}`
- `{"action": "start_recording", "source": "..."}`
- `{"action": "stop_recording"}`
- `{"action": "select_source", "source_type": "none" | "hardware" | "session" | "realtime_wav" | "synthetic_dev", "session_id": "...", "path": "..."}`

---

## 5. Decoupled Display Pipeline & Backpressure Isolation

A dedicated subsystem (`software/pcg_app/display_pipeline.py`) isolates high-rate hardware acquisition from UI visualization:

```text
48 kHz Physical Acquisition (Hardware Rev-A)
         │
         ▼
DeviceSamplePacket (~512 samples / 10.67 ms)
         │
         ▼
StreamManager.ingest_device_packet()
         │
         ▼
Integrity Validation + SampleBlock Conversion
         │
         ├─────────────────────────────────────────┐
         │                                         │
         ▼                                         ▼
FULL-RATE DSP (48 kHz Bandpass)           FULL-RATE SessionRecorder (48 kHz WAV)
         │                                         │
         └───────────────────┬─────────────────────┘
                             │
                             ▼
                     Display Aggregator (DisplayPipeline)
                             │ (Peak-Preserving Decimation: decimate_min_max)
                             │ (Decoupled Spectral Computation: ~5 Hz)
                             ▼
                     Bounded Drop-Oldest Queue (ClientSession, maxsize=2)
                             │ (Display frame drops DO NOT affect recording)
                             │ (Hardware sequence_gaps NEVER increment on UI drop)
                             ▼
                     Lower-Rate WebSocket UI (display_frame @ 25 Hz)
                             │
                             ▼
                     React Desktop Client (LiveWorkspace / Canvas)
```

### Key Principles

1. **Full-Rate Recording Preservation:**
   Every single valid hardware sample passes through DSP and reaches `SessionRecorder`. A slow or frozen WebSocket consumer can never cause sample drops in recording.
2. **Peak-Preserving Decimation (`decimate_min_max`):**
   Instead of naive decimation (`samples[::N]`) which can skip narrow transients (S1/S2 clicks, murmurs), min/max bucket aggregation preserves both the minimum and maximum extrema in chronological order within each bin.
3. **Backpressure Isolation:**
   Each client possesses an independent bounded queue (`maxsize=2`). Slow clients drop obsolete display frames without stalling fast clients or ingestion. Dropped frames increment `dropped_display_frames` in display telemetry only, strictly isolated from hardware `sequence_gaps`.
4. **Decoupled Spectrogram Computation:**
   Welch power spectral density is computed at a sensible periodic cadence (5 Hz) over recent audio buffers, avoiding executing spectral algorithms 94 times per second.
5. **Throughput vs Latency:**
   Host processing capacity exceeds real-time by >4.5x (processing runtime <2.5 ms per 10.67 ms block). End-to-end device latency remains explicitly unmeasured until physical Rev-A hardware is physically connected.

---

## 6. REST Endpoints

- `GET /api/status`: System state, capabilities, active sources, and device summary.
- `GET /api/device/state`: Structured hardware state, capability parameters, and discovery status.
- `GET /api/device/events`: Bounded circular audit trail of recent hardware events.
- `GET /api/device/stats`: Real-time packet, sample, sequence gap, and CRC failure telemetry counters.
- `GET /api/sessions`: List all recorded sessions in `experiments/sessions/`.
- `GET /api/sessions/{session_id}`: Load specific `session.json` metadata.
- `POST /api/sessions/{session_id}/replay`: Replay a saved session through the live DSP streaming pipeline.
- `POST /api/recording/start` & `POST /api/recording/stop`: Start and finalize acquisition sessions.
