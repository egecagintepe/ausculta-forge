# Engineering Release Report: Week 9 — Physical G2 I²S Hardware Integration

- **Release Date:** 2026-11-18
- **Milestone:** Physical G2 I²S Acquisition (ESP32-S3 + INMP441 over native USB CDC)
- **Verdict:** **CONDITIONAL PASS**
  - Physical I²S Data Transport: **PASS** (Zero in-stream packet or sample drop across 1.92M samples)
  - Firmware Dual-Mode G1 Rollback: **PASS** (Bit-exact synthetic ramp verified pre- and post-flash)
  - Acoustic Feasibility: **PASS** (23.2 dB power difference in 20–500 Hz band)
  - Acoustic Calibration & Clinical Acceptance: **PENDING** (Absolute dB SPL sensitivity and clinical PCG validation open for Weeks 10–12)

---

## 1. Executive Summary

On 18 November 2026, team members Kaan (transducer and breadboard assembly) and Ozan (electrical rail verification, flashing, and execution) completed the first physical hardware bring-up of the INMP441 MEMS microphone with the ESP32-S3 microcontroller. Ege performed software/firmware design, protocol validation, and independent evidence acceptance review.

The physical I²S peripheral was successfully brought up in 48 kHz, 24-bit (in 32-bit slot) Philips mode, streaming digitized audio frames across native USB CDC to the host computer with zero lost samples. G1 synthetic verification was maintained pre- and post-flash, proving complete backward compatibility.

---

## 2. Hardware and Wiring Specification

- **SoC:** ESP32-S3 (QFN56 v0.2, 8 MB PSRAM, MAC: `7c:e8:b1:aa:7c:c4`, UID low: `0xb1aa7cc4`)
- **Microphone:** INMP441 omnidirectional bottom-port MEMS microphone
- **Pin Configuration:**
  - `SCK` (BCLK) -> `GPIO4`
  - `WS` (LRCLK) -> `GPIO5`
  - `SD` (Data Out) -> `GPIO6`
  - `L/R` (Channel) -> `GND` (Left channel selected)
  - `VDD` -> `3.3V` Rail (Measured: 3.28 V via Agilent U1232A, attested)
  - `GND` -> Common Ground Rail
- **Operating Ports:**
  - Native USB CDC: `COM3`
  - ROM Bootloader / UART Flash: `COM4`

---

## 3. Test Results Matrix

| Test Step | Target | Result | Evidence / Notes |
| :--- | :--- | :--- | :--- |
| **G1 Pre-Flash USB CDC** | 480,000 samples, 0 loss | **PASS** | Bundle `20261118T090212Z_5e7113d0`, bit-exact sequence. |
| **Firmware Flash** | SHA-256 verified | **PASS** | `esptool v5.6.0`, `bootloader` (`28e9a0...`), `app` (`22af47...`), `partitions` (`73c0b5...`). |
| **G1 Post-Flash Fallback** | 480,000 samples, 0 loss | **PASS** | Bundle `20261118T091801Z_750cfd3e`, confirms dual-mode runtime integrity. |
| **G2 Quiet Baseline (10 s)** | Steady RMS baseline, 0 loss | **PASS** | `session_20261118_091909_9e6baa63`. Steady RMS: 0.0156 (Initial 100ms startup transient: 0.4982). |
| **G2 Stimulus Run 1 (10 s)** | Acoustic response, 0 loss | **CONDITIONAL PASS** | `session_20261118_093225_19cde788`. Steady RMS: 0.2224. 23.2 dB SNR. Near-clipping on 0.2775% of samples (>0.98 FS) due to loud test sound. |
| **G2 Stimulus Run 2 (10 s)** | Controlled response, 0 loss | **PASS** | `session_20261118_094939_4888e670`. Steady RMS: 0.0219. Near-clipping reduced to 0.0006%. |
| **G2 Stimulus Run 3 (10 s)** | Repeatability, 0 loss | **PASS** | `session_20261118_100102_4e58ac08`. Steady RMS: 0.0209. Near-clipping 0.0575%. |

---

## 4. Engineering Findings and Root-Cause Analysis

1. **Firmware Telemetry (`dropped_samples = 256`):**
   - Telemetry reports `generated_samples = 480256`, `fully_queued_samples = 480000`, `dropped_samples = 256`.
   - The I²S DMA block size is 256 samples. Upon reaching exactly 480,000 target samples (1,875 blocks), host STOP was signaled, and one trailing DMA buffer in transit was drained.
   - **`in_stream_dropped_samples = 0`**: In-stream packet drop was strictly zero.
2. **Quiet Baseline Startup Transient:**
   - First 100 ms has RMS of 0.4982, rapidly settling to 0.0156.
   - Root cause: Initial FIFO flush of the I²S hardware ring buffer and settling of the on-chip DC-blocking filter.
   - Recommendation: Host ingestion should discard the first 100–150 ms to eliminate initial audio pop.
3. **Clipping vs. Hard Saturation Discrepancy:**
   - In stimulus session 1, `saturation_fraction` reported 0.0 while `clipping_detected` was True.
   - Root cause: `saturation_fraction` measures samples pinned at full scale (`|x| >= 0.9999`), which accounted for only 6 samples (0.0013%). `clipping_detected` fired on samples exceeding `|x| > 0.98` (1,332 samples / 0.2775%).
   - Recommendation: Standardize acoustic excitation distance and speaker volume in future lab runs.

---

## 5. Artifact and Evidence Index

- Complete Technical Review: [`experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md`](../../experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md)
- Return Evidence Summary: [`experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json`](../../experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json)
- Setup Photographs (Local Archive): `ilkentegrasyonolcumleri/images/`
- Academic Week 9 Submissions: [`docs/sdp/week-09/`](../sdp/week-09/README.md)
