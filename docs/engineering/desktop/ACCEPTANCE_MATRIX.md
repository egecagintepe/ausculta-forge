# AuscultaForge Desktop Verification & Acceptance Matrix

- **Document Version:** 1.0.0
- **Release Designation:** Desktop Alpha 0.1.0-alpha.1
- **Target OS:** Windows 10/11 x64
- **Date:** Academic Week 5 (October 2026)
- **Primary Owner:** Ege Çağın Tepe (Module C Lead)

---

## 1. Acceptance Journey Matrix

| Journey ID | Journey Name | Acceptance Criteria | Verified Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **JOURNEY A** | First Launch & Auto-Start | 1. Application launches from Start Menu / executable.<br>2. Python backend starts automatically without manual terminal.<br>3. React UI displays `CONNECTED (127.0.0.1:<port>)`.<br>4. Sensor Hardware truthfully reports `ABSENT (NO HARDWARE)`. | Verified via standalone executable and subprocess integration tests (`test_desktop_server.py`). | **PASSED** |
| **JOURNEY B** | Deterministic Virtual Bench | 1. Virtual Bench runs 8 deterministic scenarios.<br>2. All 8 known-answer tests pass.<br>3. UI displays prominent banner: `SOFTWARE SIMULATION — NO PHYSICAL ESP32 ATTACHED`.<br>4. Seed 42 produces repeatable numerical outputs. | Verified via `/api/bench/run` and frontend `DeviceView.tsx`. | **PASSED** |
| **JOURNEY C** | Persistent Session Workflow | 1. 48 kHz recording session started and stopped.<br>2. Session saved to `%APPDATA%\AuscultaForge\sessions\<id>`.<br>3. Session contains `raw.wav`, `session.json`, `manifest.json`.<br>4. SHA-256 integrity verification endpoint returns valid match. | Verified via `SessionRecorder` and `test_session_recorder.py`. | **PASSED** |
| **JOURNEY D** | Scientific Laboratory | 1. Scientific views load and execute Welch periodogram, H1 frequency response, and Springer segmentation.<br>2. Reports generate without error.<br>3. Export downloads work with authenticated token query param. | Verified via `test_dsp_pipeline.py` and `bridgeClient.ts`. | **PASSED** |
| **JOURNEY E** | Failure Handling & Recovery | 1. Unauthenticated requests to loopback rejected with HTTP 401.<br>2. Unauthorized WebSocket rejected with code 1008.<br>3. Backend restart via IPC re-establishes connection cleanly.<br>4. Graceful UI error reporting without raw traceback dump. | Verified via `test_desktop_security.py` (8/8 unit tests passed). | **PASSED** |
| **JOURNEY F** | Process Supervision & Restart | 1. Application exit terminates child backend process cleanly.<br>2. Tasklist check confirms zero orphan Python/Uvicorn processes.<br>3. Relaunching application reads previous sessions and settings. | Verified via Windows Job Object and parent PID watchdog monitor. | **PASSED** |
| **JOURNEY G** | Windows NSIS Packaging | 1. NSIS installer generated.<br>2. Product identity: `AuscultaForge`, Version: `0.1.0-alpha.1`.<br>3. Installs without external Python or Node.js required on machine.<br>4. Uninstaller provided. | Release build pipeline execution verified. | **VERIFIED** |

---

## 2. Test Execution Summary

- **Backend Pytest Unit Tests:** 402 tests passed (including 8 new desktop security tests and server integration tests).
- **Frontend Unit Tests:** `tsx src/tests/live_workspace_math.test.ts` passed (4/4 tests passed).
- **TypeScript Typecheck:** `tsc --noEmit` passed with 0 errors.
- **Vite Production Bundler:** `vite build` completed in 11.43s, generating optimized production bundle.
- **Standalone Backend Executable:** `auscultaforge-backend.exe` passed dynamic port binding test in 2.27s.
- **Tauri Shell Compilation:** `cargo check` and `cargo build` passed with zero errors.
