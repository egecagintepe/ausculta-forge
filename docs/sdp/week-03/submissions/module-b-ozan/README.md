# Module B -- Embedded Acquisition and Data Path
## Submission Folder -- Week 3

| Field | Value |
|---|---|
| **Owner** | Ozan |
| **Module** | B -- Embedded Acquisition and Data Path |
| **Week** | 3 |
| **Purpose** | Collect all Week-3 deliverables for Module B |

## Naming Convention

All files in this folder must follow the canonical naming pattern:

`W03_B_<short-description>_vNN.<ext>`

**Examples:**
- `W03_B_example-task_v01.pdf`
- `W03_B_example-task_v01.md`

## Week-3 Source Deliverables (Rev02)

- [Procurement, BOM and test matrix (XLSX)](W03_B_procurement-bom-test_v02.xlsx)
- [System design and technical specification (DOCX)](W03_B_system-design-technical-specification_v02.docx)
- [Device-to-host frame draft (Markdown)](W03_B_device-to-host-frame-draft.md)
- [Module B task closeout and acceptance map (Markdown)](W03_B_task-closeout.md)
- [Week-3 decision log](../../decisions.md)

The XLSX and DOCX are the source Office deliverables reviewed for this closeout. They document proposed architecture, procurement research, open technical decisions and planned tests; they do not certify that hardware has been built or that physical measurements have passed.

## Instructions

- Original PDF, DOCX, and XLSX deliverables may be placed in this folder alongside Markdown summaries.
- **Do not fabricate measurements, results, or component decisions.** Record only what has actually been performed.
- **Preserve original source files** when uploading (do not replace earlier versions; increment the version suffix instead).
- Where possible, commit evidence files from your own GitHub account so the contribution history reflects your individual work.

## Week-3 Submission Status

**Documentation closeout:** drafted and ready for team review. This does not mean the hardware has been built or the required physical tests have passed.

| Deliverable / requirement | Status | Evidence / remaining work |
|---|---|---|
| W03 Module B device-to-host frame draft | **DRAFT COMPLETE** | [W03_B_device-to-host-frame-draft.md](W03_B_device-to-host-frame-draft.md). Contains MCU candidate, MEMS and ECM acquisition paths, conceptual B→C frame fields, 48 kHz mono baseline, buffering/continuity/timebase direction and Week-4 handoff. |
| Acquisition / DMA research | **PARTIAL — Week 4 freeze remains** | Peripheral-driven DMA/ping-pong architecture and continuity/timestamp requirements documented. Exact DMA allocation/buffer sizes, interrupt/cache behavior and measured stream performance are not claimed as validated. |
| BOM / local sourcing | **REVIEWED — NOT FULLY ORDER-READY** | [REV02 workbook](W03_B_procurement-bom-test_v02.xlsx) identifies candidates and line-item gates. Exact chestpiece SKU, passive-kit selection, phantom geometry, several cable/connectors and live stock/price checks remain open. |
| System design / technical specification | **REV02 REVIEWED — OPEN ITEMS RETAINED** | [REV02 system design](W03_B_system-design-technical-specification_v02.docx) records architecture, ICD/power safety, requirements, procurement gates and verification plan. Physical tests remain pending. |
| Laboratory equipment audit | **AVAILABILITY RECORDED** | Ozan reports scope, function generator, DMM, solder station and reusable breadboards/dev-boards available; department USB audio interface C-05 unavailable. Availability does not confirm calibration/performance. |
| MCU / transport decision record | **PARTIALLY CLOSED BY SCOPE** | ESP32-S3-DevKitC-1-N8R8 candidate identity and wired Native USB physical medium are recorded. Actual board stock/revision and two data cables need confirmation; USB class stays open. |
| Sample representation / integrity | **OPEN — joint B/C decision** | Signed 24-bit meaningful samples in a 32-bit container is a proposal, not a frozen contract. DW03-09 CRC/checksum cannot be closed without Module B + Module C agreement; DW03-10 remains open. |
| ECM ADC architecture | **OPEN** | ESP32-S3 ADC1 is bench-only candidate; PCM1808 is advisor-approved external-ADC candidate only. Only the PCM1808 module purchase is held specifically for this approval/schematic check; unrelated Group-A items may progress when their own checks pass. |
| Physical tests / performance measurements | **NOT YET MEASURED** | No real hardware capture, SNR, frequency response, noise-floor, throughput, continuity or latency result is claimed by this document-only closeout. |

## Next handoff

- **Before W4 freeze:** agree with Module C on sample representation, declared sample rate/channel count, packetization, timestamp/continuity semantics, status/error reporting and CRC policy.
- **Before first MCU flash:** check for two data-capable Standard-A→Micro-B USB 2.0 cables (Native USB plus USB-UART/log); buy only what is missing.
- **Before EB-R wiring:** obtain PUI's actual board pad/power map and confirmation of allowed VCC. USB 5 V goes only to the DevKit/MCU input. Do not connect a MEMS rail from an assumed pinout.
- **W5 G1:** planned end-to-end synthetic/known signal capture; not yet performed.
- **W9 G2:** planned independent known PCG signal through acoustic phantom; not yet performed.

The Week-3 decision source of truth is [Week-3 decisions](../../decisions.md).
