# AuscultaForge — Week 10 Pre-Lab Readiness & Catch-Up Matrix

**Preparation Date:** 2026-11-24 (Tuesday)  
**Scheduled Physical Lab:** 2026-11-25 (Wednesday Morning)  
**Target Repository:** `egecagintepe/ausculta-forge`  
**Course:** EEE 495 / SDP4 — Smart Digital Stethoscope  
**Authors:** Ünal Kaan Öztürk (A), Özgür Ozan Yıldız (B), Ege Çağın Tepe (C)

---

## 1. Overall Readiness Verdict for 25 November 2026

### **VERDICT: GO (CONDITIONAL ON PHYSICAL BENCH PREREQUISITES)**

| Area | Readiness Status | Condition / Blocker to Resolve on Arrival |
|---|---|---|
| **Software & Test Pipeline** | **GO (`VERIFIED SOFTWARE`)** | Phantom anti-false-pass tests & frontend `lint`/`test`/`build` passing. |
| **Firmware Integrity** | **GO (`VERIFIED PHYSICAL`)** | Working G2 candidate (`g2_candidate_20261117`) preserved untouched on ESP32-S3. |
| **Git & Document Provenance** | **GO (`VERIFIED`)** | PR #36 cleanly reconciled with `origin/main`; Ozan's REV04 DOCX/XLSX preserved. |
| **5V / 3.3V Supply & BTL Safety** | **CONDITIONAL (`PENDING`)** | Independent regulated 5V for PAM8403 (BTL isolated, never grounded) and 3.3V rail check ($3.14\text{--}3.46\text{ V}$) via multimeter. |
| **Acoustic Phantom & Chestpiece** | **CONDITIONAL (`PENDING`)** | RTV-2 cure check; if tacky, do **not** use (even with pad on top)—substitute a separate, fully cured compliant material. Couple via `chestpiece -> sealed cavity -> INMP441`. |

---

## 2. Weeks 05–10 Official Catch-Up Matrix (`SDP4_Digital_Stethoscope_Plan_EN.docx`)

| Week | Official Plan Requirement | Software Status | Physical Evidence | Overall Status |
|---|---|---|---|---|
| **W05** | A: Breadboard front end, shorted-input noise floor.<br>B: Board bring-up, synthetic stream, 0 drops.<br>C: Live display & recording verified with synthetic stream. | `VERIFIED SOFTWARE` | G1 synthetic ramp (480k samples, 0 drops) & INMP441 quiet baseline (18 Nov). | **PARTIAL** (digital MEMS used instead of analog AFE breadboard) |
| **W06** | A: Connect transducer, measure gain & bandwidth.<br>B: Real converter input, timestamp continuity.<br>C: Spectrogram view & recording library with metadata. | `VERIFIED SOFTWARE` | G2 live INMP441 (`source_mode=0`, 4 $\times$ 10s, 1.92M samples, 18 Nov). | **PARTIAL** (bandwidth sweep on phantom scheduled 25 Nov) |
| **W07** | A: Build acoustic phantom (exciter + compliant layer + chestpiece).<br>B: Device status reporting & packet loss detection.<br>C: Playback path for dataset recordings. | `VERIFIED SOFTWARE` | RTV-2 poured 23 Nov (cure check 25 Nov); Profile B telemetry proven 18 Nov. | **PENDING** (cure gate & chestpiece assembly) |
| **W08** | A: Swept-sine frequency response on phantom.<br>B: End-to-end latency & $\ge 30\text{ min}$ continuous run.<br>C: Automated test script & results table. | `VERIFIED SOFTWARE` | Host endurance tool ready; physical 30-min run deferred post-P0 (`NOT EXECUTED`). | **NOT EXECUTED** (scheduled post-P0) |
| **W09 (P0)** | Feasibility gate: known PCG played through phantom captured with recognisable S1/S2 structure, continuous & clipping-free. | `VERIFIED SOFTWARE` | Scheduled as primary P0 objective for 25 Nov morning lab. | **PENDING** (Primary P0 Gate) |
| **W10** | A: Compare two transducer candidates.<br>B: Adjustable gain / filter modes.<br>C: Quality check & threshold calibration on phantom. | `VERIFIED SOFTWARE` | Scheduled 25 Nov post-P0 (if comparator transducer available). | **NOT EXECUTED** |

---

## 3. Tomorrow's First 3 Actions & Single Launch Command

1. **Supply & BTL Safety Check (Ozan):** Verify independent 5 V for PAM8403 (no speaker terminal to GND) and 3.3 V ($3.14\text{--}3.46\text{ V}$) on INMP441.
2. **Cure Gate & Mechanical Chain (Kaan):** Inspect RTV-2; if tacky, set aside and use a separate fully cured compliant material. Assemble `exciter -> transfer plate -> cured phantom -> chestpiece -> sealed cavity -> INMP441`.
3. **Single Launch Command (Ege):**
   ```powershell
   cd c:\Dev\Antigravity\bitirme\ausculta-forge
   .\tools\hardware\run_lab_phantom_workflow.ps1
   ```
   *(Handles port discovery, 10s quiet baseline, -18 dBFS calibration tone, explicit operator confirmation, synchronized PCG phantom run with `--quiet-session`, and evidence ZIP packaging.)*
