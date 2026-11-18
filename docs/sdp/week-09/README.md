# EEE495 -- Week 9 -- Feasibility and Continuity Verification

- **Theme:** Feasibility and Continuity Verification (`16–22 Nov 2026`)
- **Status as of 2026-11-18:** **PHYSICAL G2 ACQUISITION COMPLETED (CONDITIONAL PASS)**
  - G1 pre/post-flash dual-mode deterministic verification: **PASSED** (0 loss across 960,000 samples).
  - ESP32-S3 + INMP441 breadboard integration: **PASSED** (0 loss across 1,920,000 real I²S samples).
  - VDD rail voltage: **3.28 V** (Agilent U1232A, attested; safe operating range 1.62V–3.63V).
  - Acoustic transduction: **PASSED** (23.2 dB power ratio in 20–500 Hz cardiac band).
  - Acoustic calibration, phantom frequency response & clinical certification: **PENDING** (Scheduled for Weeks 10–12).

## Submission Structure

| Folder | Owner | Module | Current Status |
|---|---|---|---|
| `submissions/module-a-kaan/` | Kaan | A -- Acquisition Hardware and Characterisation | **COMPLETED / CALIBRATION PENDING** ([W09_A_feasibility-test.md](submissions/module-a-kaan/W09_A_feasibility-test.md) — Breadboard wiring, INMP441 placement, acoustic sound test) |
| `submissions/module-b-ozan/` | Ozan | B -- Embedded Acquisition and Data Path | **COMPLETED** ([W09_B_continuity-clipping-verification.md](submissions/module-b-ozan/W09_B_continuity-clipping-verification.md) — 3.28V rail measurement, firmware flash, G1 pre/post runs, zero-loss acquisition) |
| `submissions/module-c-ege/` | Ege | C -- Computer Application and Quality Assessment | **COMPLETED / PHANTOM PENDING** ([W09_C_source-capture-comparison.md](submissions/module-c-ege/W09_C_source-capture-comparison.md) — Physical acceptance report, Welch PSD analysis, startup transient & clipping root-cause analysis) |

## Tracked Evidence & Lab Links

- [Physical G2 Acceptance Report](../../../experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md)
- [Return Evidence Summary (JSON)](../../../experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json)
- [Wednesday G2 Quantitative Comparison](../../../experiments/hardware/team_2026-11-18/wednesday_g2_comparison.md)
- [ESP32-S3 First Flash Verification Log](../../../experiments/hardware/team_2026-11-18/first_flash_log.md)
- [Physical Attestation Record](../../../experiments/hardware/team_2026-11-18/g2_physical_attestation.json)
- [Historical Progress Report with 18 Nov Addendum](../SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md)
- See [decisions.md](decisions.md) for open and resolved decisions.

## Weeks 7–9 Feasibility Gate Preparation & Phantom Artifacts

- [Weeks 7–9 Academic Progress Brief](../../sdp/reports/EEE495_AuscultaForge_Weeks07-09_Progress_Brief_2026-11-18.md) — 18 Nov instructor meeting brief covering Weeks 7, 8, and 9 progress matrix.
- [Next Lab Inventory Confirmation & Experiment Backlog](../../engineering/hardware/NEXT_LAB_INVENTORY_CONFIRMATION.md) — Physical YES/NO checklist, approved alternatives, electrical safety, and prioritized backlog.
- [Weeks 7–9 Physical Feasibility Readiness Audit](../../engineering/hardware/W07_W09_READINESS_AUDIT.md) — Comprehensive component audit, safe PAM8403 BTL wiring rules, and firmware 10s/40s limit analysis.
- [Acoustic Phantom BOM & Wiring Checklist](../../engineering/hardware/PHANTOM_BOM_AND_WIRING_CHECKLIST.md) — Mechanical/electrical BOM, pin-by-pin connections, and BTL ground isolation checks.
- [Week 9 Physical PCG Feasibility Runbook](../../engineering/hardware/W09_PHYSICAL_PCG_FEASIBILITY_RUNBOOK.md) — Role-based lab protocol for Kaan, Ozan, and Ege with explicit STOP criteria.
- [Week 9 Experiment Automation Plan](../../engineering/hardware/W09_EXPERIMENT_AUTOMATION_PLAN.md) — Software workflow architecture, mathematical metrics (NCC, Welch coherence, Shannon envelope).
- [Automated Phantom Experiment Runner CLI](../../../tools/hardware/run_phantom_pcg_experiment.py) — Synchronized audio playback, USB CDC acquisition, and reporting runner.

## Open Notes & Limitations

- Multimeter photo and acoustic sound port underside macro photos are missing in the field handoff; noted as explicit documentation limitations.
- High stimulus loudness resulted in ~0.2775% near-clipping (>0.98 FS) during stimulus run 1; acoustic test volume must be standardised in Week 10.
- Raw WAV audio files and photographs are archived locally and excluded from Git tracking in accordance with repository privacy and artifact guidelines.
