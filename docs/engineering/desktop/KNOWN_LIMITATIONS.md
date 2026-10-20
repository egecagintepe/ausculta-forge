# AuscultaForge Desktop Known Limitations & Academic Boundaries

- **Document Version:** 1.0.0
- **Scope:** Technical Boundaries, Hardware Status, Platform Constraints & Scope Limits
- **Target Platform:** Windows 10/11 x64
- **Academic Context:** EEE495 Senior Design Project (Academic Week 5)

---

## 1. Physical Hardware Boundary (Module B ESP32-S3)

### Current Physical Status
As of Academic Week 5, physical ESP32-S3 USB streaming has **not** been verified on physical hardware:
- The firmware bring-up checklist is prepared (`docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`), but physical board integration awaits Ozan's verified USB CDC-ACM implementation.
- The desktop application truthfully reflects this reality:
  - When no device is connected, the UI displays `ABSENT (NO HARDWARE)`.
  - The application **never** invents a fabricated COM port, serial number, firmware version, or battery percentage.
  - The Virtual Bench is prominently labeled: `SOFTWARE SIMULATION — NO PHYSICAL ESP32 ATTACHED`.
- Once Module B firmware is physically verified, the desktop application connects via the existing `DeviceRuntime` polling seam (`POST /api/device/poll`) without architectural changes.

---

## 2. Windows Code Signing & SmartScreen

- **Unsigned Binaries:** The Alpha 0.1.0-alpha.1 Windows installer and executable are built for academic evaluation without an Extended Validation (EV) commercial certificate.
- **SmartScreen Prompt:** On first launch, Windows SmartScreen will display an *"Unrecognized app"* notification. Users must select *More info* followed by *Run anyway*.
- **Integrity Alternative:** SHA-256 hashes of all release artifacts are published in the release notes to enable independent cryptographic verification.

---

## 3. Platform & Target Architectures

- **Primary Target:** Windows 10 / Windows 11 (64-bit x86_64).
- **ARM64 Windows:** Not natively compiled in Alpha 1; runs via Windows on ARM x64 emulation.
- **Linux & macOS:** While the core Python DSP backend and Tauri Rust shell are cross-platform, packaging scripts and Job Object process management in this sprint target Windows Win32 APIs specifically.

---

## 4. Signal Processing & Diagnostic Scope

- **Scientific Segmentation:** Springer DBN/HMM acoustic boundary segmentation executes on the CPU via NumPy/SciPy. Processing a 30-second heart sound recording requires approximately 2–3 seconds on a modern quad-core CPU.
- **No Clinical Diagnostics (Semester II Seam):** AuscultaForge Desktop provides signal acquisition, acoustic filtering, spectral analysis, and S1/S2 cycle segmentation. It **does not** output automated diagnostic murmur classifications, valvular disease predictions, or clinical diagnoses. Diagnostic ML models are intentionally scheduled for Semester II (EEE496) following clinical data validation.
