# EEE495 — Week 4 Decisions

| ID | Decision Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW04-01 | Purchased MCU board identity / pinout | OPEN — physical confirmation required | B (Ozan) | Direnc.net listing identifies ESP32-S3-WROOM-1-N16R8, seller code DSTK22852, quantity 2. This supersedes the N8R8 / DevKitC-1 candidate. Actual PCB revision, header map and USB-C connector routing must be confirmed from the delivered board / matching schematic. |
| DW04-02 | MEMS hardware candidate | PROVISIONAL — bench check open | A/B | INMP441 I²S breakout, quantity 3, is the purchased candidate; PUI DMM-4026-B-I2S-EB-R was not purchased. Datasheet specifies 24-bit two's-complement I²S and a typical 60 Hz low-frequency −3 dB point; physical slot alignment and 20–60 Hz performance remain to be measured. |
| DW04-03 | Nominal acquisition profile | BASELINE — measured clock open | B | Keep 48 kHz mono nominal. The actual WS/BCLK waveform and sample rate must be measured during bring-up before claiming verified acquisition. |
| DW04-04 | I²S DMA depth / block size | PROPOSAL — bench validation open | B | Initial proposal is 256 WS frames per block × 4 buffers (5.333 ms/block, 21.333 ms pool at 48 kHz). Actual DMA slot count, byte allocation, scheduling behaviour and overrun response must be validated on the physical board. |
| DW04-05 | USB device class / controller | OPEN — joint B/C review | B/C | Wired USB is the physical-medium baseline. CDC-ACM is the rapid-prototyping candidate; Vendor Bulk remains an alternative. Identify the physical connector/controller on the purchased board before selecting the implementation path. |
| DW04-06 | B→C frame / sample encoding | PROPOSAL — joint B/C review | B/C | Week-4 proposal documents 40-byte draft header, S32_LE host payload, frame sequence, first sample index, device timestamp and status flags. It is not the final contract until Ege and Ozan agree. |
| DW04-07 | CRC / application integrity | OPEN — joint B/C review | B/C | No CRC algorithm, coverage or trailer is frozen. Initial G1 can compare expected synthetic samples and continuity; that does not close the long-term integrity policy. |
| DW04-08 | ECM ADC architecture | OPEN — Module A / B / advisor | A/B + advisor | ESP32-S3 ADC1 continuous/DMA is bench-only; audio-grade noise/linearity is not assumed. PCM1808-class external I²S ADC remains a candidate gated by advisor approval and exact module schematic, MCLK, supply, input and cost review. G1 is not blocked by this decision. |
| DW04-09 | Procurement closeout / final gross total | DOCUMENTED WITH RECONCILIATION OPEN | B (Ozan) | Reported supplier totals sum to 3,523.21 TL, but the Motorobit total does not prove whether the two later-added 7×9 cm perfboards are included. Keep final paid total provisional until order confirmation / invoice is reconciled. |
| DW04-10 | Week-5 G1 status | PLANNED — NOT RUN | B/C | Plan: real physical ESP32-S3 generates 10 s of 48 kHz synthetic data; host checks 480,000 samples, 1,875 frames at 256 samples/frame, exact deterministic sequence, zero gaps/duplicates and zero unexpected device error counters. No G1 pass is currently claimed. |

## References

- [Week-4 Module B embedded requirements](submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md)
- [Procurement closeout](procurement-closeout.md)
- [B→C protocol proposal](submissions/module-b-ozan/W04_B_to_C_protocol-proposal_v01.md)
- [Week-5 G1 plan](../week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md)

## Notes

- A requirement being documented is not the same as a decision being closed.
- Physical evidence and explicit B/C/advisor agreement are required before closure.
- Do not mark a planned test as passed.
