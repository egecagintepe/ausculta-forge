# AuscultaForge — Real USB Integration Gap Matrix
**Module C Integration Architecture — Operation Real USB Integration Bridge**
**Date:** 2026-10-22
**Author:** Ege Çağın Tepe (Module C)
**Reviewer:** Ozan (Module B)
**Repository Branch:** `main`

---

## 1. Executive Summary

A comprehensive source-level audit of the AuscultaForge repository was performed to identify the exact technical gap between the existing host desktop application (`pcg_app`, `pcg_core`, React/Tauri frontend) and the canonical Module B/C USB CDC-ACM communication pipeline.

Prior work established:
1. Canonical wire contract v0.1 (`tools/protocol_lab/python/protocol_codec.py` and `protocol_session.py`).
2. Protocol verification lab and cross-language tests (`tools/protocol_lab/c/` and `tools/protocol_lab/python/`).
3. USB Discovery Doctor and Diagnostic Intelligence Flight Recorder (`software/pcg_app/diagnostics/`).
4. Decoupled Display Pipeline and Streaming DSP Pipeline (`software/pcg_app/state.py` and `display_pipeline.py`).

However, the desktop application backend and UI still had disjoint paths:
- `device_runtime.py` retained references to obsolete CRC-16 framing and a placeholder `PendingHardwareTransportFactory`.
- The canonical protocol was located only in `tools/protocol_lab/` rather than a shared production library.
- There was no single-owner bidirectional session engine running in `pcg_app`.
- FastAPI had no endpoints to connect to selected USB ports, execute HELLO handshakes, start acquisition sessions, or stop acquisition sessions.
- The UI had no port selection or acquisition mode selection for deterministic G1 vs real acoustic streaming.

---

## 2. Integration Gap Matrix

| Component / Subsystem | Current State on `main` | Production Requirement | Action Required |
| :--- | :--- | :--- | :--- |
| **Canonical Protocol Packaging** | Resides in `tools/protocol_lab/python/`. Import requires `sys.path` hacks. | Authoritative production package inside `software/pcg_app/canonical/`. `tools/` re-exports for reference. | Create `software/pcg_app/canonical/` containing `codec.py`, `session.py`, `transport.py`, `simulator.py`. Update `tools/` to import from it. |
| **CRC-16 Framing** | Legacy `ReferenceFramedPacketDecoder` with CRC-16 in `device_runtime.py`. | Quarantine obsolete CRC-16 framing to avoid decoding real devices with wrong codec. Authoritative decoder must be Profile B (CRC-32/IEEE). | Quarantine CRC-16 decoder as `LegacyObsoleteCrc16Decoder`. Make `CanonicalProfileBDecoder` primary. |
| **USB CDC-ACM Transport** | `UsbCdcAcmAdapter` in `tools/` only. `PendingHardwareTransportFactory` raises `NotImplementedError` in `device_runtime.py`. | Production CDC-ACM transport with bounded reads/writes, timeouts, privacy-safe enumeration, and safe resource cleanup. | Promote `UsbCdcAcmTransport` into `pcg_app/canonical/transport.py` and integrate with `DeviceRuntime`. |
| **Session Engine & Threading** | Disjoint state machines: `DeviceRuntime` has simple enum; `protocol_session.py` has canonical FSM; no worker thread. | Single-owner worker thread managing bidirectional communication. No competing reader threads. Nonzero session ID enforcement. | Implement `CanonicalSessionEngine` with dedicated worker thread, request-response futures, and bounded audio dispatch. |
| **Sample Ingestion Adapter** | `StreamManager.ingest_device_packet` converts `DeviceSamplePacket` to float32 `SampleBlock`. | Seamless link between canonical `AUDIO_DATA` packets and `StreamManager.ingest_device_packet`. | Map canonical 256-sample S32_LE frames directly to `DeviceSamplePacket` and route to `StreamManager`. |
| **Hardware Acquisition Modes** | No mode selection in host application. | Explicit support for Mode 1 (Deterministic G1: 480k samples verified) and Mode 0 (Real Acoustic Capture). | Expose mode parameter in session start and track deterministic verification vs live acoustic acquisition. |
| **FastAPI Device Control Endpoints** | Only `/api/device/poll` and `/api/device/state` exist. No port connect, handshake, start, stop. | Endpoints: `/api/device/usb/ports`, `/api/device/usb/connect`, `/api/device/usb/start`, `/api/device/usb/stop`, `/api/device/usb/disconnect`, `/api/device/usb/session`, `/api/device/usb/g1-evidence`. | Add complete REST device control suite to `software/pcg_app/app.py`. |
| **Desktop UI Device Center** | UI shows port scanning from USB Doctor, but no "Connect", "Start Acquisition", or Mode selector buttons. | Interactive hardware control: port selection, connection state badges, capability display, mode selector, live sample counter, stop summary. | Update `DeviceView.tsx` and `bridgeClient.ts` with complete interactive controls and truthful status badges. |
| **Simulated Desktop Loopback** | Standalone benchmark `canonical_g1_bench.py`. | Full end-to-end desktop loopback: UI -> FastAPI -> SessionEngine -> SimulatedTransport -> StreamManager -> DSP -> UI. | Add loopback mode supporting `port="SIMULATED_ESP32_S3"` across API and UI. |
| **Documentation & Bring-Up Guide** | Protocol spec exists in docs, but no first physical hardware bring-up manual for Ege & Ozan. | First Physical USB Bring-Up Guide with connector details, COM port identification, JTAG vs CDC, and evidence collection. | Author `docs/engineering/hardware/FIRST_PHYSICAL_USB_BRINGUP_GUIDE.md`. |

---

## 3. Preserved Systems (No Unnecessary Rewrites)

The following components are already validated and will NOT be rewritten:
1. `pcg_core/recording.py` — Session recording, metadata sidecars, and SHA-256 integrity hashing.
2. `pcg_core/streaming.py` — Stateful DSP bandpass filtering and streaming quality monitor.
3. `software/pcg_app/display_pipeline.py` — Display frame decimation and aggregation.
4. `software/pcg_app/diagnostics/` — Diagnostic event models, flight recorder, correlation engine, and fault catalog.
5. `tools/protocol_lab/c/` — C11 canonical protocol framing and cross-language tests.
