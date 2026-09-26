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
       "sources": ["mock", "realtime_wav", "session"],
       "filter_presets": ["recommended", "bell", "diaphragm", "extended"]
     },
     "state": { ... }
   }
   ```
2. **`signal_frame`:** Periodic chunk transmission containing both raw and filtered audio arrays:
   ```json
   {
     "type": "signal_frame",
     "sequence": 142,
     "timestamp_s": 4.544,
     "sample_rate_hz": 4000,
     "raw_samples": [-0.012, 0.045, ...],
     "filtered_samples": [-0.008, 0.038, ...],
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
     "recording_active": false
   }
   ```
3. **`stream_state`:** Broadcast whenever active source, filter passband, or run state changes.
4. **`recording_state`:** Broadcast whenever a session recording is started, progressing, or stopped.
5. **`device_state`:** Real-time hardware lifecycle and capability status (`absent`, `detected`, `opening`, `handshaking`, `ready`, `streaming`, `interrupted`, `error`, `incompatible`).
6. **`device_event`:** Structured audit log event emission (`timestamp_utc`, `code`, `severity`, `message`).
7. **`device_stats`:** Real-time physical stream integrity counters (packets received, sequence gaps, CRC failures, disconnect/reconnect counts).

### Client $\rightarrow$ Server Commands

- `{"action": "start_stream"}` / `{"action": "pause_stream"}`
- `{"action": "set_filter", "preset": "recommended" | "bell" | "diaphragm" | "extended"}`
- `{"action": "start_recording", "source": "..."}`
- `{"action": "stop_recording"}`
- `{"action": "select_source", "source_type": "none" | "hardware" | "session" | "realtime_wav" | "synthetic_dev", "session_id": "...", "path": "..."}`

---

## 5. Device Runtime Foundation & Configurable Acquisition Profiles

A dedicated subsystem (`software/pcg_app/device_runtime.py`) manages physical transducer hardware readiness without hardcoded sample-rate assumptions:

1. **Truthful Startup State:**
   The application starts in a truthful inactive state:
   - `source_type`: `"none"`
   - `active_source`: `"None"`
   - `device_state`: `"absent"`
   - `is_streaming`: `false`
   No synthetic waveforms are emitted until an offline replay source or explicitly labeled synthetic test signal is selected.
2. **Centralized Acquisition Profile (`AcquisitionProfile`):**
   - **Rev-A Baseline Profile:** 48,000 Hz, mono, 32-bit I2S container, 24-bit meaningful sensor data, signed PCM.
   - **Hardware Distinctions:** Distinguishes container width (32-bit DMA slot), meaningful data bits (24-bit sensor word), and sensor acoustic precision (microphone transducer SNR / noise floor).
   - **Decoupled Architecture:** Core DSP pipeline and file recording operate on sample-rate-aware `SampleBlock` instances, preventing lock-in to fixed sample rates.
3. **Explicit 9-State Lifecycle Machine:**
   Deterministic state transitions: `ABSENT -> DETECTED -> OPENING -> HANDSHAKING -> READY -> STREAMING`.
   When disconnected while streaming: `STREAMING -> INTERRUPTED`.
   Reconnect path: `INTERRUPTED -> DETECTED -> OPENING -> HANDSHAKING -> READY`. (No separate phantom reconnecting state).
4. **Disconnection Handling:**
   - Link drop while streaming: Transitions to `INTERRUPTED` and notifies UI.
   - Link drop while recording: Safely stops and seals recording with `termination_reason: "device_disconnected"`.
5. **Decoupled High-Rate Stream Ingestion:**
   ```text
   48 kHz Hardware USB Acquisition
              │
              ▼
   Full-Rate Storage & Analysis (SampleBlock, 48 kHz WAV, session.json)
              │
              ▼
   Rolling Buffers & Decimated UI Display Frames (~30-60 fps)
   ```
   Recording preserves the full uncompressed acquisition stream with zero downsampling.
6. **Dürüst Bütünlük Telemetrisi (10 Sayaç):**
   Exposes strictly real counters: `packets_received`, `samples_received`, `sequence_gaps`, `repeated_packets`, `out_of_order_packets`, `crc_failures`, `malformed_frames`, `timestamp_regressions`, `disconnect_count`, `reconnect_count`.
7. **Transport & Packet Abstraction:**
   - Physical transport technology is ESP32-S3 Native USB (final decision).
   - CDC-ACM is the current Rev-A proposal under team review; no fake COM ports or fake VID/PID are injected until descriptors are finalized.
   - `DeviceSamplePacket` carries raw container integer samples until the `packet_to_sample_block` normalization adapter.

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
