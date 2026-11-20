# AuscultaForge — REV04 Evidence Integration & Audit Directive

**Document ID:** `AF-REV04-AGENT-20261120`  
**Date:** 20 November 2026  
**Scope:** Integration of REV04 Office deliverables (Word & Excel), QA findings, and 18 November secondary lab return package (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`).  
**Authoritative Baseline:** GitHub `main` (commit `8445eea`).  
**Target Branch:** `feature/rev04-evidence-integration`

---

## 1. Executive Context & Incoming Artifacts

On 20 November 2026, the team completed the REV04 update to Module B documentation and evaluated the second field laboratory ZIP package (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`, SHA-256: `b1fa9a90c2b4165115d60447bab2406cfddfc08d05780e1f42778d5c720e8f4d`).

### Incoming Files in Staging (`_incoming/rev04-2026-11-20/`):
1. `AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`: 148 internal files, total uncompressed data ~6.3 MB, verified with 148/148 internal SHA-256 match in `SHA256SUMS.txt`.
2. `AuscultaForge_REV04_W09_QA_2026-11-20.md`: Comprehensive QA audit, pricing reconciliation, and evidence check.
3. `W09_B_procurement-bom-test_REV04_W09_2026-11-20.xlsx`: 17 worksheets with updated BOM, provisional spending reconciliations, and test matrix.
4. `W09_B_system-design-technical-specification_REV04_W09_2026-11-20.docx`: Technical specification updated for REV04 (36 pages) with Appendix F detailing 18 November physical evidence boundaries.

---

## 2. Core Integration Requirements & Action Items

### Item 1: Independent ZIP & SHA-256 Integrity Verification
- Compute bit-for-bit SHA-256 of all 4 physical `raw.wav` recordings in the laboratory return package.
- **Critical Discrepancy Correction:** In `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json`, lines 137 and 154 previously recorded inaccurate hashes (`6662e737...` and `1381dcce...`). Correct them to the verified physical hashes:
  - Session 1 (`091909_9e6baa63`, quiet): `eb4f218c3a22158430993b2180cc28618b5e426d7588b1d3da1ca59fcdf3d903`
  - Session 2 (`093225_19cde788`, stimulus 1): `76698e92fea31bed8ec27836e8f04e66d20639c79dbcf665df90f4ea09b7c5d9`
  - Session 3 (`094939_4888e670`, stimulus 2): `733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857`
  - Session 4 (`100102_4e58ac08`, stimulus 3): `26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33`
- Update corresponding records in `PHYSICAL_G2_ACCEPTANCE_REPORT.md` and release notes.

### Item 2: Separation of 23.2 dB vs. 8.0 dB Acoustic Evidence
- Clearly document that 23.2 dB and 8.0 dB originate from different physical sessions:
  - **Run 1 (09:32:25):** 23.2 dB in-band (20–500 Hz) SNR against quiet, with high loudspeaker level (%0.2775 near-clipping at >0.98 FS).
  - **Run 3 (10:01:02):** 8.0 dB in-band (20–500 Hz) SNR against quiet, with reduced acoustic level (%0.0575 near-clipping at >0.98 FS).
- Preserve both comparisons: Keep Run 1 in `wednesday_g2_comparison.json`/`.md` and extract Run 3 as `wednesday_g2_comparison_run3_8db.json`/`.md`. Do not overwrite or conflate them.

### Item 3: Week 09 Module B Integration & Historical Preservation
- Preserve historical REV03 documents in `docs/sdp/week-04/submissions/module-b-ozan/` untouched.
- Place REV04 Word (`.docx`), Excel (`.xlsx`), and QA note (`.md`) into `docs/sdp/week-09/submissions/module-b-ozan/`.
- Update `docs/sdp/week-09/submissions/module-b-ozan/README.md` and `docs/sdp/week-09/README.md` with proper cross-links and descriptions.

### Item 4: BOM & Procurement Reconciliation (Stethoscope & RTV-2 Silicone)
- Integrate Galena Dual-Head Stethoscope (283.00 TL) and AnkaHobiMarket RTV-2 Casting Silicone (350.00 TL) into inventory tracking.
- Do NOT label them as delivered or verified by invoice; classify them as `ORDERED / USER-REPORTED (PROOF PENDING)`.
- Reconcile spending base:
  - Historical Rev03: 3,613.21 TL (includes 90.00 TL unconfirmed estimate for perfboard).
  - Current provisional total: 4,246.21 TL (or 4,156.21 TL without the 90.00 TL perfboard estimate).
- Prevent double-counting: New items supersede exploratory candidates (Medikaltec 679.99 TL, 3mm silicone sheet 1,173.00 TL).
- Note that RTV-2 liquid silicone requires chemical curing with catalyst; it is NOT ultrasound gel and NOT a ready-made sheet.

### Item 5: Strict Gating Integrity
- Maintain official SDP4 Week 9 Feasibility Gate as `PENDING / NOT EXECUTED`.
- Acoustic calibration (dB SPL): `PENDING / NOT EXECUTED`.
- Analog front-end (AFE) / ECM vs. MEMS comparison: `NOT EXECUTED`.
- 30-minute continuous streaming: `PENDING / NOT EXECUTED` (architecturally blocked by 10s/40s firmware limits).

### Item 6: Git Hygiene, Test Execution & PR
- Execute on branch `feature/rev04-evidence-integration`.
- Verify software test suite passes.
- Push branch to `origin/feature/rev04-evidence-integration` and open/provide Pull Request link.
- Never force-push or auto-merge into `main`.
