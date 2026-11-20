# AuscultaForge — REV04 Physical Evidence Integration & Audit Report

**Document ID:** `AF-REP-REV04-20261120`  
**Date:** 20 November 2026  
**Auditors & Contributors:** Ege Çağın Tepe (Module C), Ozan (Module B), Kaan (Module A)  
**Baseline Git Commit:** `8445eea` (`origin/main`)  
**Integration Branch:** `feature/rev04-evidence-integration`  
**Target Milestone:** Week 09 Physical Evidence Integration & Academic Closeout

---

## 1. Executive Summary

This report provides the formal engineering and academic audit for the **REV04 deliverables update** and the **second physical laboratory return package** (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`).

All incoming files provided in staging have been independently audited, mathematically verified, and integrated into the repository without overwriting historical REV03 baselines and without claiming unverified physical achievements.

---

## 2. Independent Laboratory ZIP & Audio Manifest Audit

### 2.1 Package Integrity & Checksum
- **Archive File:** `AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`
- **File Size:** 6,317,009 bytes
- **Computed SHA-256 Digest:** `b1fa9a90c2b4165115d60447bab2406cfddfc08d05780e1f42778d5c720e8f4d`
- **Internal Checksum Audit (`SHA256SUMS.txt`):** **148 / 148 member files verified bit-for-bit (100% PASS)**.

### 2.2 Ingested Physical Audio Recordings & Discrepancy Correction
The laboratory package contains four 10.0-second physical recordings ($48\,000\text{ Hz}$, signed 24-bit PCM in 32-bit slot, mono float32, $480\,000\text{ samples}$ each, total $1\,920\,000\text{ samples}$):

| Session ID | Role / Scenario | Duration & Samples | True Physical `raw.wav` SHA-256 | Former Repo Summary Hash | Audit Decision |
|---|---|---:|---|---|---|
| `session_20261118_091909_9e6baa63` | Quiet Ambient Baseline | 10.0 s (480,000) | `eb4f218c3a22158430993b2180cc28618b5e426d7588b1d3da1ca59fcdf3d903` | `eb4f218c3a22...` | **MATCHED (VERIFIED)** |
| `session_20261118_093225_19cde788` | Acoustic Stimulus (Run 1) | 10.0 s (480,000) | `76698e92fea31bed8ec27836e8f04e66d20639c79dbcf665df90f4ea09b7c5d9` | `76698e92fea3...` | **MATCHED (VERIFIED)** |
| `session_20261118_094939_4888e670` | Acoustic Stimulus (Run 2) | 10.0 s (480,000) | `733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857` | `6662e737c3da...` | **DISCREPANCY RESOLVED (CORRECTED)** |
| `session_20261118_100102_4e58ac08` | Acoustic Stimulus (Run 3) | 10.0 s (480,000) | `26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33` | `1381dcce8a1f...` | **DISCREPANCY RESOLVED (CORRECTED)** |

> [!IMPORTANT]
> **Resolution of Hash Discrepancies & Manifest Provenance:**  
> The former hashes (`6662e737...` and `1381dcce...`) in `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json` were clerical errors introduced during initial report drafting.  
> Crucially, `RETURN_PACKAGE_MANIFEST.json` in the laboratory package only enumerates the first two baseline sessions (`session_20261118_091807_e7aa7c19` and `session_20261118_093225_19cde788`). It does not list the later two stimulus runs.  
> The physical provenance and true digests of the final two WAV recordings (`session_20261118_094939_4888e670` → `733de8fd...` and `session_20261118_100102_4e58ac08` → `26c78582...`) are established directly by:
> 1. The root archive checksum file `SHA256SUMS.txt` (148/148 verified member files in `AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`),
> 2. The individual session sidecar metadata files (`session_stimulus_4888e670.json` and `session_stimulus_4e58ac08.json`), and
> 3. The laboratory test run orchestrator state file (`wednesday_20261118_state.json`).  
> `RETURN_EVIDENCE_SUMMARY.json` and `PHYSICAL_G2_ACCEPTANCE_REPORT.md` have now been updated with the verified true values.

---

## 3. Acoustic Separation: 23.2 dB vs. 8.0 dB Evidence

A key finding of the REV04 audit is the explicit separation of the two comparison metrics generated during testing:

1. **Stimulus Run 1 (09:32:25 UTC — 23.2 dB):**
   - Evaluated in `experiments/hardware/team_2026-11-18/wednesday_g2_comparison.json` / `.md`.
   - Result: **23.2 dB** in-band (20–500 Hz) power ratio against Quiet Baseline.
   - Acoustic Observation: Loud playback near microphone drove the transducer close to full scale (peak $0.999982\text{ FS}$), causing $0.2775\%$ near-clipping ($>0.98\text{ FS}$).
2. **Stimulus Run 3 (10:01:02 UTC — 8.0 dB):**
   - Evaluated in `experiments/hardware/team_2026-11-18/wednesday_g2_comparison_run3_8db.json` / `.md` (from package `100114Z.zip`).
   - Result: **8.0 dB** in-band (20–500 Hz) power ratio against Quiet Baseline.
   - Acoustic Observation & Near-Clipping Audit: With lower speaker drive level and repositioned source, near-clipping was substantially reduced from $0.2775\%$ ($1\,332$ samples) down to **$0.0575\%$** ($276$ samples), with `clipping_detected = true` and full 10-second capture peak reaching **$0.999967\text{ FS}$** ($1$ sample at saturation $\ge 0.9999\text{ FS}$).
   - Non-Linearity Caveat: Because $0.0575\%$ slightly exceeds the project's $< 0.05\%$ near-clipping target, this run **cannot** be characterized as "linear capture" or "clipping-free". Furthermore, while steady-state analysis windows (e.g. 1–5 s) exhibit attenuated peak values ($0.1667\text{ FS}$ / steady RMS $0.0209\text{ FS}$), full-session peaks approach full scale. Standardized acoustic drive attenuation remains mandatory for upcoming phantom experiments.

**Conclusion:** Both runs are preserved as separate, non-overlapping empirical records. The variation demonstrates that the INMP441 responds dynamically to changing sound pressure levels, and standardizing acoustic drive level is mandated for upcoming phantom experiments.

---

## 4. Integration of REV04 Office Deliverables

The REV04 deliverables authored by Ozan have been incorporated into Week 09 Module B:

- **Technical Specification:** `docs/sdp/week-09/submissions/module-b-ozan/W09_B_system-design-technical-specification_REV04_2026-11-20.docx` (38 pages, DSS-SYS-001 REV04-QA). Includes Section 13/17 alignment, Appendix F detailing physical G2 evidence, port assignments (ROM COM4 vs CDC COM3), safe 5V power rules, B-01a/B-01b separation, and 4,246.21 TL provisional spend.
- **BOM & Test Matrix Workbook:** `docs/sdp/week-09/submissions/module-b-ozan/W09_B_procurement-bom-test_REV04_2026-11-20.xlsx` (17 sheets, formula-verified totals of 4,246.21 TL / 4,156.21 TL, B-01a 35.35 TL + B-01b 90.00 TL = 3 boards, aligned Test_Matrisi!I14 and W09_Durum!D14).
- **QA & Reconciliation Note:** `docs/sdp/week-09/submissions/module-b-ozan/AuscultaForge_W09_REV04_QA_2026-11-20.md`.
- **Historical Preservation:** Historical REV03 files in `docs/sdp/week-04/submissions/module-b-ozan/` remain completely untouched.

---

## 5. Procurement Reconciliation & Double-Counting Safeguard

| Component | Model & SKU | Quantity | Unit Price (TL) | Sourcing Status in REV04 | Accounting Action |
|---|---|---:|---:|---|---|
| **Stethoscope Chestpiece** | Galena Çift Taraflı Profesyonel Yetişkin (A-01) | 1 | 283.00 TL | Ordered (User-Reported via Trendyol) | Replaces historical candidate (Medikaltec 679.99 TL). Delivery & invoice pending. |
| **Acoustic Phantom Medium** | AnkaHobiMarket RTV-2 Kalıp Silikonu 500g + Katalizör (A-09) | 1 | 350.00 TL | Ordered (User-Reported via Trendyol) | Replaces historical candidate (3 mm silicone sheet 1,173.00 TL). Chemical curing test pending. |
| **New Items Subtotal** | | | **633.00 TL** | | Documented without double-counting old candidates. |

- **Provisional Spend Total:** $3\,613.21\text{ TL (Rev03 base)} + 633.00\text{ TL} = \mathbf{4\,246.21\text{ TL}}$ (or $\mathbf{4\,156.21\text{ TL}}$ if the 90.00 TL unconfirmed perfboard estimate is omitted).
- **Material Status:** RTV-2 is a two-part liquid condensation-cure silicone requiring catalyst mixing and curing; it is **NOT ultrasound gel** and **NOT a ready-made sheet**. Standard ultrasound gel remains to be procured (~50 TL).

---

## 6. Strict Status of Academic Milestones

In full adherence to academic rigor, the following tasks are explicitly maintained as **OPEN / PENDING / NOT EXECUTED**:
1. **Week 9 Acoustic Phantom S1/S2 Feasibility Gate:** `PENDING PHYSICAL BENCH ASSEMBLY`.
2. **Acoustic Frequency Response (20–500 Hz):** `NOT MEASURED ON PHANTOM`.
3. **Absolute dB SPL Calibration:** `NOT PERFORMED`.
4. **Electret Condenser Microphone (ECM) / Analog AFE Comparison:** `NOT EXECUTED`.
5. **30-Minute Continuous USB Streaming:** `NOT EXECUTED` (blocked by firmware `G1_TARGET_SAMPLES = 480k` $\approx 10\text{ s}$ session limit).
