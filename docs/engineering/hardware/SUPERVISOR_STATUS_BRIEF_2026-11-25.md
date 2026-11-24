# AuscultaForge (SDP4) — Project Status Summary for Supervisor

**Date:** 25 November 2026 | **Course:** EEE 495 Senior Design Project I | **Team:** Ünal Kaan Öztürk (A), Özgür Ozan Yıldız (B), Ege Çağın Tepe (C)

---

## 1. Verified 18 November 2026 Hardware Evidence
- **G1 Deterministic Stream (`VERIFIED PHYSICAL`):** ESP32-S3 streamed 480,000 synthetic ramp samples @ 48 kHz mono over USB CDC (`source_mode=1`) with **0 dropped frames** and **0 CRC-32 errors**.
- **G2 Live INMP441 Acquisition (`VERIFIED PHYSICAL`):** Four separate 10-second physical captures (1 quiet baseline + 3 acoustic stimuli, totaling 1,920,000 samples @ 48 kHz mono, `source_mode=0`) were acquired over USB CDC (`COM3`) after ROM flashing (`COM4`), with operator-reported 3.28 V supply rail.
- **Measured Active/Quiet Separation:** Run 1 achieved a **23.2 dB** active-to-quiet band power ratio (with 0.2775% near-clipping); Run 4 achieved **8.0 dB** (with 0.0575% near-clipping, peak 0.999967 FS). These are distinct uncalibrated active/quiet ratios, demonstrating live acoustic responsiveness while highlighting gain/clipping sensitivity.

## 2. Current Progress (As of 24 November 2026)
- **Software & Metrology (`VERIFIED SOFTWARE`):**
  - Unified phantom experiment pipeline (`run_phantom_pcg_experiment.py` & `run_lab_phantom_workflow.ps1`) with strict anti-false-pass guards: real `raw_wav_path` extraction, SHA-256 content-copy rejection, mandatory fresh quiet baseline (`INCONCLUSIVE_NO_QUIET_BASELINE` if omitted), zero-defaulting telemetry checks, playback timeout/abort gating, and one-to-one envelope burst matching.
  - Desktop/Web application (FastAPI backend + React/Vite frontend) with live waveform, Welch PSD, spectrogram, Butterworth Bell/Diaphragm filters, and offline-capable session export/ZIP packaging.
  - All automated regression suites verified (Python phantom/orchestrator tests + 9 TypeScript frontend test suites + production build).
- **Phantom Preparation (`PENDING` Cure Gate):** A nominal $12\text{ cm} \times 10\text{ mm}$ RTV-2 silicone specimen was poured on 23 Nov using volumetric kitchen dosing (~105 mL base, ~3.75 mL catalyst); on 24 Nov 07:20 it remained tacky (`CURE_NOT_VERIFIED`). A separate fully cured compliant material is prepared as an exploratory substitute if the RTV-2 fails the 25 Nov cure gate.
- **30-Minute Endurance (`NOT EXECUTED` Physically):** An isolated $O(1)$-memory host streaming tool (`run_endurance_session.py`) was prepared and tested in simulation, but the working G2 firmware release (`g2_candidate_20261117`, 10s target / 40s watchdog) is preserved untouched to protect tomorrow's P0 experiment.

## 3. Objectives for Today's Laboratory Session (25 November 2026)
1. **P0 — Week 9 Feasibility Gate:** Play CirCor clinical PCG (`40058_AV.wav`) through `PC -> PAM8403 -> 30 mm / 12 Ω exciter -> transfer plate -> cured phantom -> chestpiece -> sealed cavity -> INMP441 -> ESP32-S3 -> USB CDC` and achieve $\ge 12\text{ dB}$ in-band SNR, `NCC >= 0.35`, coherence $\ge 0.40$, $< 0.05\%$ near-clipping, and $\ge 70\%$ envelope burst correspondence.
2. **P1 — Sweep & Filter Evaluation (Post-P0):** Execute 20–500 Hz swept-sine response ($H_1(f)$) and compare Bell vs. Diaphragm digital filter modes.

## 4. Key Limitations & Safety Boundaries
- **Academic Prototype Only:** No human recordings, no medical diagnostic claims, and no mains power connections (battery/USB only).
- **Sensor & Metrology Limits:** INMP441 has a nominal $-3\text{ dB}$ roll-off near $60\text{ Hz}$; cross-correlation lag (`estimated_recording_lag_ms`) is not hardware-synchronized end-to-end latency.
