# Architecture Decision Record: Desktop Workstation Shell Technology

- **Document ID:** ADR-DESKTOP-001
- **Status:** APPROVED & IMPLEMENTED
- **Date:** Academic Week 5 (October 2026)
- **Author:** Ege Çağın Tepe (Module C Lead)
- **Scope:** AuscultaForge Desktop Workstation (Windows 10/11 x64)

---

## 1. Context & Problem Statement

AuscultaForge integrates high-throughput PCG acquisition (48 kHz logical 32-bit floating-point streaming), scientific digital signal processing (Welch periodograms, H1 frequency response estimation, Springer DBN/HMM segmentation), deterministic virtual bench testing, and an interactive React-based telemetry workspace.

Previously, running the system required a developer environment:
1. Manually activating a Python virtual environment and starting Uvicorn (`python -m pcg_app.server`).
2. Starting the Vite development server (`npm run dev`).
3. Opening a standard web browser (Chrome/Edge) to `http://localhost:3000`.

For an engineering workstation and senior design defense (EEE495/EEE496), AuscultaForge must be distributed as a self-contained, professional Windows application that launches from the Start Menu without terminal intervention, leaves zero orphan background processes upon exit, binds to dynamic non-conflicting loopback ports, and protects local endpoints with per-process authentication.

---

## 2. Evaluated Candidates

### Candidate A: Tauri 2 (Rust Shell + Microsoft WebView2)
- **Architecture:** Rust native binary hosting Windows WebView2 (evergreen runtime pre-installed on Windows 10/11), controlling the React UI bundle and supervising a packaged Python backend sidecar.
- **IPC Mechanism:** Type-safe native IPC (`#[tauri::command]`), asynchronous event bus, and loopback WebSocket/REST.
- **Process Supervision:** Win32 Job Objects (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) ensuring child process hierarchy is terminated unconditionally if the parent process exits or crashes.
- **Installer Capabilities:** Native NSIS and WiX/MSI installers with Start Menu shortcuts and standard uninstallers.
- **Resource Footprint:** ~35–50 MB RAM for the shell; sub-second window startup time.

### Candidate B: pywebview (Python-Driven Native Window)
- **Architecture:** Python process creating a native WinForms/WPF WebView2 window, serving React static assets directly from Python or a local thread.
- **IPC Mechanism:** JS-to-Python HTTP bridge or window-evaluated JavaScript.
- **Process Supervision:** Single Python process running both backend and UI window.
- **Installer Capabilities:** Requires wrapping Python + pywebview via PyInstaller/cx_Freeze as a single giant monolithic executable.
- **Resource Footprint:** ~120–180 MB RAM; Python interpreter startup overhead before window appears; prone to GUI thread locking when DSP algorithms run heavy GIL operations.

---

## 3. Technology Decision & Comparison Matrix

| Evaluation Dimension | Candidate A: Tauri 2 (Selected) | Candidate B: pywebview (Rejected) |
| :--- | :--- | :--- |
| **Toolchain Feasibility on Target Machine** | **PASSED:** MSVC C++ VS 2026, Rust 1.97.1, Cargo 1.97.1 verified operational. | **PASSED:** Python 3.12 present. |
| **GUI Thread Decoupling** | **EXCELLENT:** Rust UI shell completely decoupled from Python scientific computing GIL. High-rate 60 FPS waveform decimation never stutters during heavy SciPy/NumPy execution. | **POOR:** Python GIL contention between GUI event pump and heavy signal processing (Welch/H1/Springer). |
| **Process Lifecycle & Cleanup** | **KERNEL-LEVEL GUARANTEE:** Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) guarantees zero orphan processes even on hard crash. | **RISK:** Thread deadlocks on shutdown frequently leave orphan Uvicorn threads or background sockets open. |
| **Packaging & Distribution** | **PROFESSIONAL:** Independent frontend bundle + PyInstaller one-dir backend packaged into standard NSIS/MSI installer. | **COMPLEX:** Monolithic bundle often fails with dynamic imports in FastAPI and SciPy native DLLs. |
| **Startup Latency** | **FAST:** Native Rust window appears in <400ms, showing workstation loading state while Python backend initializes in parallel. | **SLOW:** 3–6 second black screen or delay while Python runtime and heavy scientific modules unpickle. |
| **Memory Footprint** | Low idle memory (~40 MB native shell + dynamic backend). | Monolithic process overhead (>150 MB baseline). |
| **Academic Defense Quality** | High: Industrial-grade multi-tier architecture demonstrating systems programming (Rust) and scientific computing (Python). | Medium: Monolithic script wrapper. |

---

## 4. Decision Outcome

**Decision:** Adopt **Candidate A: Tauri 2** as the native desktop workstation shell for AuscultaForge Desktop 1.0.

### Key Implementation Principles
1. **Dynamic Ephemeral Port:** The backend never binds to a fixed port (e.g., 8000). It binds to OS port 0 and hands the assigned port to Tauri via stdout IPC.
2. **Per-Process Authentication:** A high-entropy cryptographic token is generated per instance. The React client injects this token in `X-AuscultaForge-Auth` headers and WebSocket query parameters.
3. **Dual Lifecycle Supervision:**
   - Layer 1 (OS Kernel): Windows Job Object automatically reaps all child processes when the parent job handle closes.
   - Layer 2 (Application Watchdog): Python backend monitors the parent PID via Win32 `OpenProcess` and exits gracefully if the parent terminates.
4. **Isolated Storage:** User data is stored strictly in `%APPDATA%\AuscultaForge`, decoupled from application installation files.
