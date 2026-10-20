# AuscultaForge — Commit & PR Evidence Index
**Document ID:** `AF-HIST-EVIDENCE-INDEX-V01`  
**Classification:** `GIT_VERIFIED` / `CODE_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Target Repository:** `egecagintepe/ausculta-forge`  
**Integrated Baseline SHA:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Overview and Purpose

This index serves as the definitive historical audit trail for AuscultaForge. Every core architectural decision, algorithmic milestone, academic submission, and cross-module boundary agreement is mapped to its exact Git commit hash, pull request identifier, author, modified file set, and verification status.

---

## 2. Master PR Index (Consolidated & Preceding)

| PR # | Branch Name | Title / Purpose | Lead Author | Baseline / Merge Commit | Verification Status |
|---|---|---|---|---|---|
| **#07** | `docs/week3-module-c-validation` | docs: complete Week 3 Module C quality validation | Ege | `9e5852c` | `GIT_VERIFIED` |
| **#08** | `docs/ozan-week02-submission` | docs: add Ozan Week 02 Module B submissions | Ozan | `8b9420b` | `GIT_VERIFIED` |
| **#10** | `docs/ozan-week03-closeout` | docs: complete Ozan Week 03 Module B closeout | Ozan | `ec5e17c` | `GIT_VERIFIED` |
| **#11** | `docs/ozan-week03-lab-audit` | docs: clarify audio dongle and lab availability | Ozan | `69cfd26` | `GIT_VERIFIED` |
| **#12** | `docs/kaan-week02-archive-cleanup-20261012` | docs: organize Kaan Week 02 PDF evidence and indexes | Ege | `ab70007` | `GIT_VERIFIED` |
| **#13** | `docs/ege-week04-module-c-requirements-20261012` | docs: define Ege Week 04 Module C application requirements | Ege | `1dd3073` | `GIT_VERIFIED` |
| **#16** | `docs/ege-week04-module-c-closeout` | docs: close out Module C Week 04 deliverable pack | Ege | `Merged prior to Gate` | `GIT_VERIFIED` |
| **#17** | `feature/ege-s01-device-runtime-truth` | feat(runtime): truthful hardware UI & device runtime state machine | Ege | `Merged prior to Gate` | `TEST_VERIFIED` (34 tests) |
| **#18** | `feature/ege-s02-virtual-bench` | feat(bench): deterministic virtual bench & 8 test scenarios | Ege | `Integrated in #31` | `TEST_VERIFIED` (12 tests) |
| **#19** | `feature/ege-s03-host-transport-readiness` | feat(transport): 3-layer transport architecture & framing | Ege | `Integrated in #31` | `TEST_VERIFIED` (16 tests) |
| **#20** | `feature/ege-s04-loss-aware-recording` | feat(recording): loss-aware session recording & SHA-256 sidecars | Ege | `Integrated in #31` | `TEST_VERIFIED` (20 tests) |
| **#21** | `feature/ege-s05-live-workstation` | feat(ui): live workstation, waveform canvas, display decimation | Ege | `Integrated in #31` | `TEST_VERIFIED` (Frontend tests) |
| **#22** | `feature/ege-s06-scientific-dsp-metrics` | feat(dsp): 20–500 Hz scientific bandpass, spectral metrics | Ege | `Integrated in #31` | `TEST_VERIFIED` (29 tests) |
| **#23** | `feature/ege-s07-phantom-system-id` | feat(phantom): acoustic phantom stimulus playback & SISO H1 ID | Ege | `Integrated in #31` | `TEST_VERIFIED` (14 tests) |
| **#24** | `feature/ege-s08-metrology-automation` | feat(metrology): automated 6-measurement test harness & reports | Ege | `Integrated in #31` | `TEST_VERIFIED` (15 tests) |
| **#25** | `feature/ege-s09-pcg-research-lab` | feat(research): Springer LR-HSMM lab & benchmark validation UI | Ege | `Integrated in #31` | `TEST_VERIFIED` (CirCor suite) |
| **#26** | `feature/ege-s10-embedded-interoperability` | feat(interop): portable C golden vectors & ESP32 bringup checklist | Ege | `Integrated in #31` | `TEST_VERIFIED` (6 tests) |
| **#27** | `docs/kaan-week04-closeout` | docs: Kaan Week 04 acoustic requirements report and high-pass | Kaan | `6b8b0e7` | `GIT_VERIFIED` |
| **#28** | `docs/ozan-week04-procurement-closeout` | docs: Ozan Week 04 procurement closeout and actual orders | Ozan | `9067b57` | `GIT_VERIFIED` |
| **#30** | `docs/ozan-week04-protocol-proposal` | docs: Ozan Week 04 protocol proposal and G1 bringup plan | Ozan | `797c489` | `GIT_VERIFIED` |
| **#31** | `integration/ege-s01-s10-consolidation` | feat(integration): Master Integration Gate — Consolidate S01–10 | Ege | `fa4b75a` | `TEST_VERIFIED` (394 tests) |

---

## 3. High-Impact Commit Evidence Index

### 3.1 Initial Core & Architecture Foundation
* **Commit:** `c7751bf` (2026-09-24)
  * **Author:** Ege Çağın Tepe
  * **Title:** `chore: initialize AuscultaForge project structure`
  * **Files Added:** `software/pcg_core/models.py`, `software/pcg_core/dsp.py`, `software/pcg_core/buffers.py`, `software/tests/`
  * **Verification:** Unit tests verifying `SampleBlock` immutability and initial causal bandpass filtering.
* **Commit:** `57025ff` (2026-09-24)
  * **Author:** Ege Çağın Tepe
  * **Title:** `docs: add AuscultaForge engineering knowledge base`
  * **Files Added:** `docs/knowledge-base/00-project-overview.md` through `07-testing-and-validation.md`
  * **Impact:** Established the foundational educational documentation for team members and external reviewers.

### 3.2 Ingestion, Recording & Desktop Bridge
* **Commit:** `667daa7` (2026-09-26)
  * **Author:** Ege Çağın Tepe
  * **Title:** `docs: record phase-1 hardware and team decisions`
  * **Files Added:** Initial ADRs establishing ESP32-S3 selection, 48 kHz nominal rate, and Module A/B/C team allocations.
* **Commit:** `d8c3505` (2026-09-26)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat: add acquisition session recording and replay`
  * **Files Added:** `software/pcg_core/recording.py`, `software/tests/test_recording.py`
  * **Verification:** Tests confirming bit-exact raw WAV file creation and JSON metadata synchronization.
* **Commit:** `18d5381` (2026-09-26)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat(runtime): implement device lifecycle state machine and transport abstraction`
  * **Files Added:** `software/pcg_app/device_runtime.py`, `software/tests/test_device_runtime.py`
  * **Verification:** State machine transition tests verifying rejection of out-of-order streaming requests.
* **Commit:** `da8f0d5` (2026-09-26)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat: decouple host acquisition from display with peak-preserving decimation and backpressure isolation`
  * **Files Added:** `software/pcg_app/display_pipeline.py`, `software/tests/test_display_pipeline.py`
  * **Verification:** Verified min/max peak decimation algorithm retaining transient clicks without browser overload.

### 3.3 Advanced Scientific Modeling & Segmentation
* **Commit:** `3f13136` (2026-09-27)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat: add scientific signal characterization, envelope lab, and system identification foundation`
  * **Files Added:** `software/pcg_core/scientific/envelopes.py`, `software/pcg_core/scientific/system_id.py`, `software/pcg_core/scientific/signal_quality.py`
  * **Verification:** Numerical tests comparing Hilbert, Moving RMS, and TKEO envelopes; cross-spectral H1 transfer function estimation.
* **Commit:** `d38fd71` (2026-09-27)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat: add source-faithful Springer LR-HSMM segmentation`
  * **Files Added:** `software/pcg_core/segmentation/springer_hsmm.py`, `software/pcg_core/segmentation/springer_logistic.py`
  * **Verification:** Verified Bayes emission computation and extended Viterbi cyclic sequence decoding.
* **Commit:** `1bcfb74` (2026-09-27)
  * **Author:** Ege Çağın Tepe
  * **Title:** `feat: add real PCG segmentation validation benchmark`
  * **Files Added:** `software/pcg_core/segmentation/validation/`, `software/tests/test_circor_adapter.py`
  * **Verification:** CirCor pediatric dataset ingestion and multi-metric event tolerance matching.

### 3.4 Academic Deliverables & Procurement Closeouts
* **Commit:** `16fc986` (2026-10-06)
  * **Author:** Kaan
  * **Title:** `Module_A_Technical_Selection`
  * **Files Added:** `docs/sdp/week-02/submissions/module-a-kaan/`
  * **Content:** Evaluation matrix comparing Electret Condenser Microphones vs. Digital MEMS.
* **Commit:** `e90817a` (2026-10-07)
  * **Author:** Ozan
  * **Title:** `docs: add Ozan Week 02 Module B submissions`
  * **Files Added:** BOM v0.1, ESP32-S3 microcontroller initial specification.
* **Commit:** `9067b57` (2026-10-16, PR #28)
  * **Author:** Ozan
  * **Title:** `docs: record Module B Week 04 procurement closeout and actual orders`
  * **Files Added:** `docs/sdp/week-04/procurement-closeout.md`, `docs/sdp/week-04/W04_B_actual-orders_2026-10-16_v01.csv`
  * **Significance:** Documented the shift from PUI Audio to purchased INMP441 MEMS microphone from DirencNet.
* **Commit:** `797c489` (2026-10-17, PR #30)
  * **Author:** Ozan
  * **Title:** `docs: align Week 04 protocol proposal and G1 bringup plan`
  * **Files Added:** `docs/sdp/week-04/submissions/module-b-ozan/W04_B_to_C_protocol-proposal_v01.md`, `docs/sdp/week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md`
  * **Content:** Defined Module B's proposed USB wire packet formats and hardware bring-up gates.

### 3.5 Master Integration Gate PR #31
* **Commit:** `16a95a8` (2026-10-20)
  * **Author:** Ege Çağın Tepe
  * **Title:** `docs(interop): apply Sprint 10 hardware-readiness corrections and boundary disclaimers`
  * **Impact:** Added backpressure handling to experimental C code, emphasized task-delay timing jitter, and flagged DirencNet N16R8 dual-USB verification requirement.
* **Commit:** `895763d` (2026-10-20)
  * **Author:** Ege Çağın Tepe
  * **Title:** `docs(integration): apply PR #31 final acceptance patch for hardware bring-up and startup commands`
  * **Impact:** Audited `ESP32_S3_BRINGUP_CHECKLIST.md` routes (corrected `/api/device/detect` to `/api/device/poll`), updated startup commands to use `pcg_app.server` and `create_app` factory, and updated README test counts.
* **Commit:** `fa4b75a` (2026-10-20)
  * **Author:** Ege Çağın Tepe
  * **Title:** `Merge pull request #31 from egecagintepe/integration/ege-s01-s10-consolidation`
  * **Impact:** Consolidated all 10 software sprints and academic Week 04 deliverables into `main` with 394 automated tests passing.
