# AuscultaForge Desktop Academic Code Defense & Engineering Viva Guide

- **Document Version:** 1.0.0
- **Scope:** Oral Defense Questions, Architectural Rationale, Systems Explanations & Viva Preparation
- **Academic Context:** EEE495 / EEE496 Senior Design Project (Bilkent University)
- **Primary Author:** Ege Çağın Tepe (Module C Lead)

---

## 1. Core Architectural Questions & Model Answers

### Q1: Why transform AuscultaForge into a native Windows desktop workstation instead of remaining a web browser application?
**Model Defense Answer:**
> *"AuscultaForge is a medical-grade engineering workstation acquiring high-bandwidth phonocardiogram signals at 48 kHz (48,000 32-bit floating-point samples per second). Browser-based deployment exhibits three fundamental flaws for an engineering instrument:*
> 1. *It requires non-technical clinical users to manually open terminal windows, activate Python environments, and start Uvicorn and Vite servers.*
> 2. *Web browsers impose strict security sandboxes that prohibit native process management, leading to orphaned background processes that keep audio devices and local ports occupied after the tab is closed.*
> 3. *Standard browser origins on localhost expose local signal recording endpoints to cross-origin drive-by attacks from external websites.*
>
> *By building a native desktop shell, we achieve single-click Start Menu execution, kernel-level process supervision, isolated `%APPDATA%` medical session storage, dynamic port allocation, and per-process authentication."*

---

### Q2: Why choose Tauri 2 (Rust + WebView2) instead of Electron or pywebview?
**Model Defense Answer:**
> *"We conducted an evidence-based Technology Decision Spike (ADR-DESKTOP-001) comparing Tauri 2, Electron, and pywebview:*
> - *Electron bundles a redundant ~150 MB Chromium runtime with high memory overhead (>300 MB idle RAM).*
> - *pywebview couples GUI event loops to Python's Global Interpreter Lock (GIL), resulting in UI stutter when heavy DSP algorithms (Welch periodograms or Springer segmentation) execute.*
> - *Tauri 2 provides an ultra-lightweight (~13 MB executable, ~40 MB RAM) Rust native shell utilizing Windows WebView2, which is pre-installed on Windows 10/11. Furthermore, Rust enables direct Win32 API calls to create Windows Job Objects, guaranteeing zero orphaned backend processes upon exit."*

---

### Q3: How do you guarantee that closing the desktop application never leaves a zombie Python process?
**Model Defense Answer:**
> *"We implemented a dual-layer defense mechanism:*
> 1. *OS Kernel Guarantee (Windows Job Object): When Tauri spawns `auscultaforge-backend.exe`, the child process handle is immediately enrolled into a Win32 Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Even if the Tauri host is forcefully killed in Task Manager or encounters an unhandled crash, the Windows kernel automatically terminates all processes in that job.*
> 2. *Application Watchdog Thread: The Python backend runs a daemon thread continuously monitoring the parent PID via Win32 `OpenProcess` and `GetExitCodeProcess`. If the parent terminates, the backend initiates an immediate graceful Uvicorn shutdown."*

---

### Q4: How does the application avoid port conflicts if port 8000 is occupied?
**Model Defense Answer:**
> *"In production desktop mode, AuscultaForge does not use port 8000. It binds to socket port 0, instructing the Windows TCP stack to allocate an open ephemeral port (e.g. 58903). Once bound, the backend outputs an atomic handshake line on stdout (`AUSCULTAFORGE_BACKEND_READY:{...}`). The Rust shell captures this line, parses the assigned port and a 256-bit cryptographic auth token, and injects them into the React frontend via Tauri IPC. The frontend then connects directly to its own dedicated backend instance without port collisions."*

---

### Q5: Is the physical ESP32-S3 stethoscope hardware verified?
**Model Defense Answer (Honest Academic Standard):**
> *"No. We maintain strict academic integrity: physical USB streaming from the custom ESP32-S3 hardware has not yet been verified. The firmware brings up USB CDC-ACM protocols in Module B, but until physical testing occurs, the desktop application truthfully displays `ABSENT (NO HARDWARE)`. We do not fabricate fake telemetry, battery levels, or serial numbers. Instead, we developed the Deterministic Virtual Bench with 8 known-answer test scenarios to rigorously verify the entire host acquisition seam, DSP filtering, display decimation, and session recording independently of physical hardware."*

---

### Q6: Where is user recording data stored, and how is integrity guaranteed?
**Model Defense Answer:**
> *"Recordings are stored in `%APPDATA%\AuscultaForge\sessions\<session_id>\`, completely decoupled from application installation directories. Each session contains a normalized Float32 `raw.wav`, acquisition metadata `session.json`, and a cryptographic `manifest.json`. Upon recording completion, a SHA-256 hash is computed and sealed in the manifest. The verification endpoint re-computes the hash on demand to detect file tampering or corruption."*
