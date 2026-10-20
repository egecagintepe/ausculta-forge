# AuscultaForge Desktop Packaging, Build Pipeline & Distribution Guide

- **Document Version:** 1.0.0
- **Scope:** Multi-Stage Build Pipeline, PyInstaller Bundling, Tauri NSIS Installer & Verification
- **Target Platform:** Windows 10 / Windows 11 (x64)
- **Primary Code References:**
  - `software/build_desktop_backend.py`
  - `software/frontend/src-tauri/tauri.conf.json`
  - `software/frontend/package.json`

---

## 1. Multi-Stage Build Pipeline Overview

AuscultaForge Desktop employs a reproducible, three-stage build pipeline:

```
[STAGE 1: Frontend]             [STAGE 2: Backend]               [STAGE 3: Desktop Shell]
 React / TSX Source              Python Scientific Modules        Rust Tauri 2 Host
        │                               │                                │
  vite build                      PyInstaller                      tauri build
        │                               │                                │
        v                               v                                v
 dist/ (HTML, CSS, JS)   dist_backend/auscultaforge-backend/   auscultaforge-desktop.exe
        │                               │                                │
        └───────────────────────┬───────┴────────────────────────────────┘
                                │
                                v
               [OUTPUT: NSIS Windows Installer]
               AuscultaForge_0.1.0-alpha.1_x64-setup.exe
```

---

## 2. Toolchain Prerequisites

The build pipeline requires the following tools verified on Windows 10/11 x64:
- **Node.js:** v24.18.0+ / npm 11.16.0+
- **Rust & Cargo:** 1.97.1+ (MSVC toolchain: `x86_64-pc-windows-msvc`)
- **Microsoft C++ Build Tools:** Visual Studio Community 2026 / Build Tools with Windows 10/11 SDK
- **Python:** 3.12.x (64-bit) with `PyInstaller >= 6.12.0`
- **Microsoft Edge WebView2:** Evergreen Runtime (pre-installed on Windows 10/11)

---

## 3. Step-by-Step Build Instructions

### Step 1: Install Dependencies
```powershell
# Frontend dependencies
cd software/frontend
npm install

# Backend dependencies (in Python virtual environment)
cd ../..
pip install -r software/requirements.txt
pip install pyinstaller
```

### Step 2: Build Self-Contained Python Backend
Run the backend build script from the repository root:
```powershell
python software/build_desktop_backend.py
```
This produces an auditable one-directory bundle at:
`software/dist_backend/auscultaforge-backend/` containing:
- `auscultaforge-backend.exe` (Entrypoint)
- Core Python 3.12 runtime and standard libraries
- Native NumPy, SciPy, and PyWavelets C-extensions and DLLs
- FastAPI, Starlette, Uvicorn, and WebSockets servers

### Step 3: Build Production React Assets
```powershell
cd software/frontend
npm run build
```
Generates production assets in `software/frontend/dist/`.

### Step 4: Build Native Tauri Desktop Shell & Installer
```powershell
cd software/frontend
npm run tauri build -- --bundles nsis --ci
```
Tauri bundles the compiled frontend and embeds the backend directory from `software/dist_backend/` into the application resources, producing a standalone Windows installer in:
`software/frontend/src-tauri/target/release/bundle/nsis/`.

---

## 4. Code Signing & Windows SmartScreen Disclosure

> [!IMPORTANT]
> **Academic Release Honest Disclosure:**
> Alpha release binaries produced by this pipeline are unsigned developer engineering builds. When launching the installer or executable on a clean Windows machine, Windows SmartScreen may present a warning stating: *"Windows protected your PC: Microsoft Defender SmartScreen prevented an unrecognized app from starting."*
>
> To proceed during academic defense testing:
> 1. Click **More info**.
> 2. Click **Run anyway**.
>
> Commercial production deployment requires purchasing an Extended Validation (EV) Code Signing Certificate from a Microsoft-approved Certificate Authority. No attempt has been made to fabricate or forge code signatures.
