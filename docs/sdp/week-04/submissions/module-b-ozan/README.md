# Module B — Embedded Acquisition and Data Path
## Submission Folder — Week 4

| Field | Value |
|---|---|
| Owner | Ozan |
| Module | B — Embedded Acquisition and Data Path |
| Week | 4 |
| Purpose | Week-4 requirements, procurement and Week-5 handoff deliverables |

## Deliverables

- [W04 embedded requirements freeze](W04_B_embedded-requirements-freeze.md) — measurable requirements; board, USB and B/C closure gates explicitly retained.
- [Week-4 procurement closeout](../../procurement-closeout.md) — actual order summary and 12 Group-A category audit.
- [Date-stamped order ledger](../../W04_B_actual-orders_2026-10-16_v01.csv) — reported amounts/statuses with unresolved lines called out.
- [B→C protocol proposal](W04_B_to_C_protocol-proposal_v01.md) — for Ege's review; not final.
- [Week-5 G1 bring-up plan](../../../week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md) — planned test, not evidence of a pass.

## Status

**DOCUMENTATION READY FOR REVIEW; PHYSICAL INTEGRATION NOT STARTED / NOT VERIFIED.**

No firmware build, board enumeration, sensor capture, throughput, continuity, SNR, frequency-response or latency result is claimed by these planning documents.

## Hardware identity and safety notes

- Purchased board: Direnc.net ESP32-S3 N16R8 WiFi Bluetooth board, seller code DSTK22852, quantity 2. The exact PCB revision and connector routing remain to be checked physically.
- Purchased digital microphone: INMP441 I²S breakout ×3. PUI EB-R was not purchased.
- GPIO4/5/6 are provisional I²S candidates only; GPIO35–37 are not available for general use on the octal-PSRAM N16R8 module.
- SoC USB D−/D+ are GPIO19/GPIO20, but the USB-C port used for the selected device controller must be identified on the real board.
- Do not order / wire around assumed pinout. Keep CRC, USB class and final wire format open until B/C agreement.
## Rev03 Office deliverables — actual purchase baseline

- [Procurement, BOM and test matrix — Rev03 (XLSX)](W04_B_procurement-bom-test_REV03.xlsx)
- [System design and technical specification — Rev03 (DOCX)](W04_B_system-design-technical-specification_REV03.docx)

These Week-4 Rev03 source documents reflect the reported purchases (INMP441 instead of PUI EB-R, ESP32-S3 N16R8 instead of the N8R8 candidate, and the actual ordered quantities). They do not claim physical delivery, board pinout verification, firmware execution or G1 test success.
