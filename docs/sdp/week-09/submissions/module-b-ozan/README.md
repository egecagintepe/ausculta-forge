# Module B -- Embedded Acquisition and Data Path
## Submission Folder -- Week 9

| Field | Value |
|---|---|
| **Owner** | Ozan |
| **Module** | B -- Embedded Acquisition and Data Path |
| **Week** | 9 (16–22 Kasım 2026) |
| **Lab Date** | 18 Kasım 2026 |
| **Document Update** | 20 Kasım 2026 (REV04 Release) |
| **Status** | **COMPLETED (Electrical Continuity, Flashing & Zero-Loss Acquisition) / PHANTOM PENDING** |

---

## Deliverables in this Folder

1. **Physical Continuity & G2 Ingest Acceptance:**
   - [W09_B_continuity-clipping-verification.md](W09_B_continuity-clipping-verification.md) — 18 Nov lab report: 3.28V rail measurement (Agilent U1232A, operator-attested), ROM flash on COM4, USB CDC streaming on COM3, and 0 in-stream loss over 1,920,000 samples.
2. **REV04 System Design Technical Specification:**
   - [W09_B_system-design-technical-specification_REV04_2026-11-20.docx](W09_B_system-design-technical-specification_REV04_2026-11-20.docx) — Technical specification document (DSS-SYS-001 REV04-QA, 38 pages). Includes Section 13/17 alignment, Appendix B/D/E/F, B-01a/B-01b perfboard separation, physical G2 evidence, and updated provisional BOM.
3. **REV04 Procurement, BOM & Test Matrix Workbook:**
   - [W09_B_procurement-bom-test_REV04_2026-11-20.xlsx](W09_B_procurement-bom-test_REV04_2026-11-20.xlsx) — 17 worksheets with updated BOM, provisional spending reconciliations (4,246.21 TL / 4,156.21 TL), B-01a/B-01b separation (3 boards), aligned `Test_Matrisi!I14` and `W09_Durum!D14`, and 0 formula errors. Preserves historical REV03 sheets without modification.
4. **REV04 Quality Assurance & Reconciliation Note:**
   - [AuscultaForge_W09_REV04_QA_2026-11-20.md](AuscultaForge_W09_REV04_QA_2026-11-20.md) — Comprehensive QA audit of REV04 Office deliverables (04-QA revision), pricing reconciliation, 18 Nov evidence checks, and resolution of GitHub hash discrepancies.

---

## Summary of REV04 Updates (20 November 2026)

- **Preservation of Historical REV03 Baseline:** Historical REV03 files in `docs/sdp/week-04/submissions/module-b-ozan/` (`W04_B_procurement-bom-test_REV03.xlsx` and `W04_B_system-design-technical-specification_REV03.docx`) remain unchanged as baseline records.
- **BOM & Procurement Reconciliation:**
  - Added Galena Dual-Head Stethoscope (283.00 TL) and AnkaHobiMarket RTV-2 Casting Silicone 500g (350.00 TL) as user-reported orders (screenshot available, official invoice and physical delivery confirmation pending).
  - Provisional spending total reconciled: **4,246.21 TL** (or **4,156.21 TL** excluding the 90.00 TL unconfirmed Motorobit perfboard estimate).
  - Double-counting prevented: New items supersede earlier exploratory candidates (Medikaltec 679.99 TL, 3mm silicone sheet 1,173.00 TL) rather than accumulating on top.
  - RTV-2 liquid silicone requires chemical curing with catalyst; it is uncalibrated and not a ready-made sheet.
- **Physical G2 Evidence Reconciliation:**
  - 4 distinct 10-second sessions captured on 18 Nov totaling 1,920,000 samples with 0 in-stream drops and 0 CRC failures.
  - Clarified separation of acoustic ratios: **23.2 dB** in Stimulus Run 1 (`093225_19cde788`) vs. **8.0 dB** in Stimulus Run 3 (`100102_4e58ac08`).
  - Corrected raw WAV SHA-256 digests in `RETURN_EVIDENCE_SUMMARY.json` for Sessions 3 and 4 to match verified ZIP archives.
- **Unfinished Gates Kept Open:**
  - Acoustic phantom S1/S2 transmission: `PENDING`.
  - Absolute SPL calibration: `PENDING`.
  - ECM/analog AFE bench comparison: `NOT EXECUTED`.
  - 30-minute continuous run: `PENDING` (firmware session limit `G1_TARGET_SAMPLES = 480k` $\approx 10\text{ s}$).

---

## Key Evidence References
- Attestation: `experiments/hardware/team_2026-11-18/g2_physical_attestation.json`
- Flashing: `experiments/hardware/team_2026-11-18/first_flash_log.md`
- G1 Pre/Post Reports: `experiments/hardware/team_2026-11-18/g1_pre_acceptance_report.md`, `g1_post_acceptance_report.md`
- Comparisons: `experiments/hardware/team_2026-11-18/wednesday_g2_comparison.md` (23.2 dB) and `wednesday_g2_comparison_run3_8db.md` (8.0 dB)
- Summary Manifest: `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json`
