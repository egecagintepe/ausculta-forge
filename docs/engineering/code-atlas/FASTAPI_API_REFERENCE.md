# AuscultaForge — FastAPI REST & WebSocket API Reference
**Document ID:** `AF-CODE-FASTAPI-REF-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference File:** `software/pcg_app/app.py`  
**Registered Route Count:** **57 Routes** (Programmatically Verified)

---

## 1. Application Creation & Architectural Boundaries

The AuscultaForge backend utilizes the **Application Factory Pattern** (`create_app()` inside `software/pcg_app/app.py`). There is **no module-level global `app` object**. This prevents race conditions during testing, ensures each test receives a clean database and sessions directory, and enables configurable runtime overrides.

### 1.1 Executable Launch Syntax
To launch the backend server with standard settings:
```powershell
# Option A: Recommended CLI server entrypoint
python -m pcg_app.server --host 127.0.0.1 --port 8000

# Option B: Direct Uvicorn launch using application factory
python -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

---

## 2. Registered Routes vs. Test-Exercised Subset

The FastAPI application registers **57 distinct routes** spanning core telemetry, device control, streaming, session persistence, virtual bench simulation, metrology automation, and PCG research labs.

* **Registered Routes (57):** Declared via `@app.get`, `@app.post`, `@app.delete`, and `@app.websocket` in `app.py`.
* **Directly Exercised Test Subset:** Core endpoints (health, status, device polling, stream start/stop, session queries, virtual bench scenarios, segmentation validation) are exercised directly through HTTP test client calls (`software/tests/test_app.py`, `test_virtual_bench.py`, `test_validation_api.py`, `test_springer_api.py`). Remaining analytical endpoints are validated through their underlying Python unit test modules.

---

## 3. Comprehensive Route Directory by Functional Category

### 3.1 System Status & Telemetry Endpoints

| HTTP Method | Route Path | Description | Request Body | Response Model / Status |
|---|---|---|---|---|
| `GET` | `/api/status` | Current system health, runtime state, and device capabilities | None | `SystemStatusResponse` (200 OK) |
| `GET` | `/api/health` | Lightweight service liveness check | None | `{"status": "ok"}` (200 OK) |
| `GET` | `/api/capabilities` | Authoritative sampling rate, channel count, and bit depth | None | `DeviceCapabilities` (200 OK) |

#### Example Response: `GET /api/status`
```json
{
  "state": "READY",
  "connected": true,
  "device": {
    "port": "COM3",
    "vid": "0x303A",
    "pid": "0x4001",
    "description": "ESP32-S3 USB CDC"
  },
  "capabilities": {
    "sample_rate": 48000,
    "channels": 1,
    "container": "S32_LE",
    "bit_depth": 24
  },
  "metrics": {
    "rms": 0.042,
    "peak": 0.185,
    "crest_factor": 4.40,
    "clipping_count": 0
  }
}
```

---

### 3.2 Device Lifecycle & Stream Control Endpoints

| HTTP Method | Route Path | Description | Request Body | Response Model / Status |
|---|---|---|---|---|
| `POST` | `/api/device/poll` | Trigger physical USB bus scan for ESP32-S3 devices | None | `{"detected": bool, "port": str}` |
| `POST` | `/api/device/open` | Open serial communication handle to designated port | `{"port": "COM3"}` | `{"success": bool, "state": str}` |
| `POST` | `/api/device/close` | Gracefully close serial communication handle | None | `{"success": bool, "state": str}` |
| `POST` | `/api/stream/start` | Begin continuous audio acquisition and streaming | `{"record": bool}` | `{"streaming": true, "session_id": str}` |
| `POST` | `/api/stream/stop` | Stop streaming and finalize active recording | None | `{"streaming": false}` |
| `GET` | `/api/stream/metrics` | Real-time audio stream metrics (RMS, Peak, Drop rate) | None | `StreamMetricsResponse` |

---

### 3.3 Session Persistence & Replay Endpoints

| HTTP Method | Route Path | Description | Query / Path Parameters | Response Status |
|---|---|---|---|---|
| `GET` | `/api/sessions` | List all recorded scientific sessions on disk | None | 200 OK (JSON list) |
| `GET` | `/api/sessions/{session_id}` | Retrieve JSON metadata sidecar and integrity hash | `session_id: str` | 200 OK / 404 Not Found |
| `GET` | `/api/sessions/{session_id}/audio` | Download uncompressed raw WAV audio file | `session_id: str` | 200 OK (`audio/wav`) |
| `DELETE` | `/api/sessions/{session_id}` | Safely delete a session WAV and its JSON metadata | `session_id: str` | 200 OK / 404 Not Found |
| `POST` | `/api/sessions/{session_id}/verify` | Recompute and verify SHA-256 payload integrity | `session_id: str` | `{"valid": bool, "hash": str}` |

---

### 3.4 Scientific Analysis & Metrology Endpoints

| HTTP Method | Route Path | Description | Request Body | Response Status |
|---|---|---|---|---|
| `POST` | `/api/analysis/spectral` | Compute Welch PSD, band powers, and mains pickup | `{"session_id": str}` | 200 OK (Spectral JSON) |
| `POST` | `/api/analysis/envelopes` | Compute Hilbert, Moving RMS, and TKEO envelopes | `{"session_id": str}` | 200 OK (Envelope JSON) |
| `POST` | `/api/analysis/system_id` | Compute SISO transfer function $H_1(f)$ and coherence | `{"ref_id": str, "cap_id": str}` | 200 OK (System ID JSON) |
| `POST` | `/api/metrology/run_all` | Execute automated 6-measurement laboratory campaign | `{"config": dict}` | 200 OK (Metrology Report) |
| `GET` | `/api/metrology/reports` | Retrieve list of completed laboratory characterization reports | None | 200 OK (Report List) |

---

### 3.5 Virtual Bench & Research Lab Endpoints

| HTTP Method | Route Path | Description | Request Body | Response Status |
|---|---|---|---|---|
| `GET` | `/api/bench/scenarios` | List 8 available deterministic test scenarios | None | 200 OK (List of names) |
| `POST` | `/api/bench/load` | Load a specific virtual bench scenario into runtime | `{"scenario": str}` | 200 OK / 400 Bad Request |
| `POST` | `/api/bench/run_all` | Execute automated test pass across all 8 scenarios | None | 200 OK (Test matrix) |
| `POST` | `/api/research/segment` | Run Springer LR-HSMM segmentation on audio file | `{"session_id": str}` | 200 OK (State boundaries) |
| `POST` | `/api/research/validate` | Run benchmark validation against CirCor pediatric dataset | `{"dataset_path": str}` | 200 OK (Benchmark stats) |

---

### 3.6 WebSocket Streaming Contract

* **Endpoint:** `ws://127.0.0.1:8000/api/ws/stream`
* **Transport:** Asynchronous JSON WebSocket frames pushed at $30\text{--}60\text{ Hz}$.
* **Frame Schema:**
```json
{
  "type": "signal_frame",
  "sequence": 1420,
  "timestamp": 1729440120.452,
  "sample_rate": 48000,
  "points": [-0.012, 0.015, -0.018, 0.022, ...],
  "metrics": {
    "rms": 0.041,
    "peak": 0.180,
    "crest_factor": 4.39,
    "clipping": false
  },
  "stream_health": {
    "mcu_drops": 0,
    "display_drops": 0,
    "continuity_ok": true
  }
}
```
* **Strict Telemetry Separation:** `mcu_drops` tracks genuine hardware packet drops over the physical USB bus; `display_drops` tracks browser frame skips caused by client UI lag.
