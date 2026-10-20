# AuscultaForge — FastAPI REST & WebSocket API Reference
**Document ID:** `AF-CODE-FASTAPI-REF-V02`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference File:** `software/pcg_app/app.py`  
**Automated Audit Tool:** `tools/audit_fastapi_routes.py`  
**Registered Route Count:** **57 Routes** (52 Application HTTP + 1 WebSocket + 4 Built-in OpenAPI)

---

## 1. Application Creation & Architectural Boundaries

The AuscultaForge backend utilizes the **Application Factory Pattern** (`create_app()` in `software/pcg_app/app.py`). There is **no module-level global `app` object**. This prevents cross-test state leakage, ensures isolated database sessions and temporary directories, and allows programmatic injection of runtime configurations.

### 1.1 Verified Launch Commands
Every documented command has been validated for execution in the repository root:
```powershell
# Option A: Recommended CLI server entrypoint
python -m pcg_app.server --host 127.0.0.1 --port 8000

# Option B: Direct Uvicorn launch using application factory syntax
python -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

---

## 2. Programmatic Route Verification & Testing Coverage

An automated inspection tool (`tools/audit_fastapi_routes.py`) programmatically instantiates the application, queries `app.openapi()` and `app.routes`, and compares registered routes against test calls executed in `software/tests/`:

* **Total Registered Routes:** **57 Route Objects**
  - **52 Application REST Endpoints**
  - **1 Real-Time WebSocket Endpoint (`/ws`)**
  - **4 OpenAPI / Documentation Endpoints** (`/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect`)
* **Test Verification Taxonomy:**
  - `[TESTED]`: Directly called by an automated test in `software/tests/` via `fastapi.testclient.TestClient`.
  - `[REGISTERED]`: Present and validated in the application routing table, but not directly invoked via HTTP in the test suite (logic validated via core unit tests).

---

## 3. Comprehensive Authoritative Route Directory

### 3.1 Device Lifecycle & Telemetry Endpoints (6 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/status` | `get_status` | None | General system health, current streaming source, and active filter preset. |
| `[TESTED]` | `GET` | `/api/device/state` | `get_device_state` | None | Current `DeviceState` enum (e.g. `absent`, `ready`, `streaming`). |
| `[TESTED]` | `GET` | `/api/device/stats` | `get_device_stats` | None | Runtime packet counts, dropped sample totals, and CRC integrity metrics. |
| `[TESTED]` | `GET` | `/api/device/events` | `get_device_events` | None | Chronological log of recent device lifecycle state transitions. |
| `[TESTED]` | `POST` | `/api/device/poll` | `api_poll_device` | None | Trigger serial scan for connected ESP32-S3 hardware. |
| `[TESTED]` | `POST` | `/api/device/disconnect` | `api_disconnect_device` | None | Gracefully disconnect physical serial transport handle. |

---

### 3.2 Real-Time Streaming & Filter Control (6 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `POST` | `/api/stream/start` | `api_start_stream` | None | Start pushing audio blocks to the rolling buffer. |
| `[TESTED]` | `POST` | `/api/stream/pause` | `api_pause_stream` | None | Pause real-time stream ingestion without dropping device connection. |
| `[REGISTERED]` | `POST` | `/api/stream/stop` | `api_stop_stream` | None | Completely stop stream ingestion and reset buffer state. |
| `[TESTED]` | `POST` | `/api/stream/source` | `api_set_source` | `SourceRequest` | Switch input between `"mock"`, `"file"`, and `"device"`. |
| `[TESTED]` | `POST` | `/api/stream/filter` | `api_set_filter` | `FilterRequest` | Change filter preset (`"bell"`, `"diaphragm"`, `"extended"`). |
| `[REGISTERED]` | `WS` | `/ws` | `websocket_endpoint` | WebSocket Frames | Bidirectional streaming: client handshake, live decimated display frames. |

---

### 3.3 Session Persistence, Replay & Integrity (9 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `POST` | `/api/recording/start` | `api_start_recording` | `RecordingStartRequest` | Start recording session to `experiments/sessions/<id>/`. |
| `[TESTED]` | `POST` | `/api/recording/stop` | `api_stop_recording` | None | Finalize recording, serialize `raw.wav`, and generate `session.json`. |
| `[TESTED]` | `GET` | `/api/sessions` | `api_list_sessions` | None | List all session metadata sidecars on disk. |
| `[TESTED]` | `GET` | `/api/sessions/{session_id}` | `api_get_session` | Path: `session_id` | Retrieve metadata sidecar and stream quality summary. |
| `[REGISTERED]` | `DELETE`| `/api/sessions/{session_id}` | `api_delete_session` | Path: `session_id` | Delete session folder, `raw.wav`, and metadata. |
| `[TESTED]` | `GET` | `/api/sessions/{session_id}/manifest` | `api_get_session_manifest` | Path: `session_id` | Retrieve machine-readable laboratory manifest. |
| `[TESTED]` | `GET` | `/api/sessions/{session_id}/verify` | `api_verify_session` | Path: `session_id` | Recompute whole-file SHA-256 and verify sample accounting. |
| `[TESTED]` | `GET` | `/api/sessions/{session_id}/analysis-summary` | `api_get_session_analysis_summary` | Path: `session_id` | Retrieve quick spectral/RMS overview of session audio. |
| `[REGISTERED]` | `POST` | `/api/sessions/{session_id}/replay` | `api_replay_session` | Path: `session_id` | Replay historical session through real-time rolling buffer. |

---

### 3.4 Virtual Bench Simulation (2 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/bench/scenarios` | `api_list_bench_scenarios` | None | List available deterministic scenarios (`normal_s1_s2`, `murmur`, etc.). |
| `[TESTED]` | `POST` | `/api/bench/run` | `api_run_bench` | `BenchRunRequest` | Execute automated test scenario and assert pipeline output metrics. |

---

### 3.5 Metrology Automation & Reports (6 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/scientific/metrology/template` | `api_get_metrology_template` | None | Return standard configuration template for 6-test metrology suite. |
| `[TESTED]` | `POST` | `/api/scientific/metrology/run` | `api_run_metrology_experiment` | `MetrologyRunRequest` | Execute automated metrology campaign (frequency response, SNR, etc.). |
| `[TESTED]` | `GET` | `/api/scientific/metrology/reports` | `api_list_metrology_reports` | None | List all completed metrology run reports. |
| `[TESTED]` | `GET` | `/api/scientific/metrology/reports/{report_id}` | `api_get_metrology_report` | Path: `report_id` | Retrieve full JSON report for a metrology run. |
| `[TESTED]` | `GET` | `/api/scientific/metrology/reports/{report_id}/csv` | `api_get_metrology_csv` | Path: `report_id` | Download tabular CSV export of metrology metrics. |
| `[TESTED]` | `GET` | `/api/scientific/metrology/reports/{report_id}/markdown` | `api_get_metrology_markdown` | Path: `report_id` | Download formatted Markdown report suitable for report inclusion. |

---

### 3.6 Scientific Phantom & Stimulus (5 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/scientific/phantom/templates` | `api_list_phantom_templates` | None | List standard excitation templates (log sweeps, multitone, cardiac pulse). |
| `[TESTED]` | `POST` | `/api/scientific/phantom/stimulus/generate` | `api_generate_phantom_stimulus` | `PhantomStimulusRequest` | Generate synthetic stimulus audio file for phantom excitation. |
| `[TESTED]` | `POST` | `/api/scientific/phantom/characterize` | `api_characterize_phantom` | `PhantomCharacterizeRequest` | Run dual-channel transfer function $H_1(f)$ characterization. |
| `[TESTED]` | `GET` | `/api/scientific/phantom/experiments` | `api_list_phantom_experiments` | None | List completed phantom characterization trial runs. |
| `[TESTED]` | `GET` | `/api/scientific/phantom/experiments/{trial_id}` | `api_get_phantom_experiment` | Path: `trial_id` | Retrieve detailed transfer function and coherence results. |

---

### 3.7 Profiles & Session Analysis (2 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/scientific/profiles` | `api_list_scientific_profiles` | None | List configured signal processing and filter profiles. |
| `[REGISTERED]` | `POST` | `/api/scientific/session/{session_id}/analyze` | `api_analyze_session_scientific` | Path: `session_id`, Body: `ScientificAnalyzeRequest` | Execute deep spectral and quality assessment on recorded session. |

---

### 3.8 Scientific System Identification (3 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[REGISTERED]` | `POST` | `/api/scientific/system-id` | `api_run_system_id` | `SystemIdRequest` | Compute SISO transfer function $H_1(f)$, delay, and coherence. |
| `[TESTED]` | `GET` | `/api/scientific/system-id/reports` | `api_list_system_id_reports` | None | List historical system identification analysis reports. |
| `[TESTED]` | `GET` | `/api/scientific/system-id/{analysis_id}` | `api_get_system_id_report` | Path: `analysis_id` | Retrieve comprehensive transfer function and coherence curves. |

---

### 3.9 Scientific Segmentation Models (4 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/scientific/segmentation/models` | `api_list_segmentation_models` | None | List available segmentation models (Springer HSMM 4-state). |
| `[TESTED]` | `POST` | `/api/scientific/segmentation/segment` | `api_segment_session` | `SegmentationSegmentRequest` | Execute Viterbi state segmentation ($S_1, \text{systole}, S_2, \text{diastole}$). |
| `[TESTED]` | `GET` | `/api/scientific/segmentation/reports` | `api_list_segmentation_reports` | None | List completed segmentation reports. |
| `[TESTED]` | `GET` | `/api/scientific/segmentation/{analysis_id}` | `api_get_segmentation_report` | Path: `analysis_id` | Retrieve state boundary timecodes and confidence metrics. |

---

### 3.10 Scientific Validation Benchmarks (2 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/scientific/validation/benchmarks` | `api_list_validation_benchmarks` | None | List benchmark datasets (CirCor DigiScope, PhysioNet CinC 2016). |
| `[TESTED]` | `GET` | `/api/scientific/validation/benchmarks/{benchmark_id}` | `api_get_validation_benchmark` | Path: `benchmark_id` | Retrieve benchmark performance metrics (F1 score, timing error). |

---

### 3.11 Reference Asset Comparison (8 Endpoints)

| Status | Method | Route Path | Operation ID / Handler | Request Body / Params | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[TESTED]` | `GET` | `/api/analysis/assets` | `api_list_reference_assets` | None | List uploaded reference WAV assets. |
| `[REGISTERED]` | `POST` | `/api/analysis/assets` | `api_upload_reference_asset` | Multipart Form | Upload new reference audio asset. |
| `[TESTED]` | `GET` | `/api/analysis/assets/{asset_id}` | `api_get_reference_asset` | Path: `asset_id` | Retrieve metadata of specific reference asset. |
| `[TESTED]` | `DELETE`| `/api/analysis/assets/{asset_id}` | `api_delete_reference_asset` | Path: `asset_id` | Delete uploaded reference asset. |
| `[REGISTERED]` | `POST` | `/api/analysis/compare` | `api_compare_reference_and_capture` | `ComparisonRequest` | Run comparative spectral and correlation analysis against reference. |
| `[TESTED]` | `GET` | `/api/analysis/reports` | `api_list_comparison_reports` | None | List comparison reports. |
| `[TESTED]` | `GET` | `/api/analysis/{analysis_id}` | `api_get_comparison_report` | Path: `analysis_id` | Retrieve comparison results. |
| `[TESTED]` | `GET` | `/api/analysis/{analysis_id}/export` | `api_export_comparison_report` | Path: `analysis_id` | Export comparison report data. |

---

### 3.12 Built-in OpenAPI Endpoints (4 Endpoints)

| Status | Method | Route Path | Description |
| :--- | :--- | :--- | :--- |
| `[BUILT-IN]` | `GET` | `/docs` | Interactive Swagger UI API documentation. |
| `[BUILT-IN]` | `GET` | `/redoc` | Interactive ReDoc API documentation. |
| `[BUILT-IN]` | `GET` | `/openapi.json` | Machine-readable OpenAPI v3.1 schema specification. |
| `[BUILT-IN]` | `GET` | `/docs/oauth2-redirect` | OAuth2 redirect helper for Swagger UI. |
