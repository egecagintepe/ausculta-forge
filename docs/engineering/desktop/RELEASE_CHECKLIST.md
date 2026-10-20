# AuscultaForge Desktop Release & Pre-Flight Verification Checklist

- **Release Designation:** AuscultaForge Desktop 1.0 (Alpha 0.1.0-alpha.1)
- **Target OS:** Windows 10/11 x64
- **Verification Date:** Academic Week 5 (October 2026)
- **Checklist Owner:** Ege Çağın Tepe (Module C Lead)

---

## 1. Codebase & Integrity Verification

- [x] **No Modified Production Firmware:** Module B firmware C code (`software/esp32_firmware/` and `src/c/`) unchanged.
- [x] **No Modified Hardware CAD:** Module A hardware design files unchanged.
- [x] **No Leaked Development Paths:** Absolute paths (e.g. `C:\Dev\...`) eliminated from production code.
- [x] **No Hardcoded Secrets or Credentials:** Auth tokens generated dynamically at runtime via `secrets.token_hex(32)`.
- [x] **PR #32 Isolation:** Branch `docs/ege-engineering-intelligence-system` (PR #32) untouched and unmerged.
- [x] **Git Cleanliness:** Large build artifacts (`dist_backend/`, `build_backend/`, `target/`) excluded via `.gitignore`.

---

## 2. Test & Build Automation Matrix

- [x] **Full Backend Pytest Suite:** All 402 unit and integration tests passing (`pytest software/tests/`).
- [x] **Desktop Security Tests:** 8/8 tests passing (`test_desktop_security.py`).
- [x] **Subprocess Lifecycle Test:** Standalone process execution and handshake passing (`test_desktop_server.py`).
- [x] **Frontend Mathematical Verification:** Live workspace buffer and scaling tests passing (`npm test`).
- [x] **TypeScript Static Analysis:** Strict typecheck passing without errors (`npm run lint` / `tsc --noEmit`).
- [x] **Production Frontend Build:** Vite production assets generated (`npm run build`).
- [x] **Self-Contained Backend Executable:** Standalone PyInstaller bundle built (`software/build_desktop_backend.py`).
- [x] **Tauri Desktop Shell Build:** Native Rust executable compiled (`cargo build` / `npm run tauri build`).

---

## 3. Runtime & User Experience Verification

- [x] **Single-Click Startup:** Application starts without manual command prompt or Python launch.
- [x] **Ephemeral Port Allocation:** Loopback binding dynamically assigns an open OS port without collision.
- [x] **Process Supervision:** Windows Job Object terminates backend tree when desktop window closes.
- [x] **Truthful Hardware Status:** UI reports `ABSENT (NO HARDWARE)` when physical board is not detected.
- [x] **Simulation Disclosure:** Virtual Bench displays `SOFTWARE SIMULATION — NO PHYSICAL ESP32 ATTACHED`.
- [x] **User Data Persistence:** Sessions and manifests stored in `%APPDATA%\AuscultaForge`, surviving app restart.
- [x] **Cryptographic Verification:** SHA-256 verification confirms recording validity on demand.
