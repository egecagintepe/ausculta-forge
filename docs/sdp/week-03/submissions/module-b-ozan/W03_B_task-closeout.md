# W03 Module B Task Closeout and Acceptance Map

**Owner:** Ozan — Module B, Embedded Acquisition & Data Path  
**Status:** Documentation deliverables updated for review; several requirements intentionally remain open for Week 4 or physical bench validation.  
**Scope:** Evidence/status mapping based on the submitted REV02 procurement workbook and system-design specification. No firmware changes or physical measurement results are implied by this Markdown record.

## 1. Assigned work and acceptance status

| Assignment / requirement | Status | Evidence and honest completion boundary |
|---|---|---|
| **B-W2-01 — Embedded acquisition data-path architecture** | **DOCUMENTED** | The frame draft specifies sensor/input → I²S or ADC → ESP32-S3 → DMA-backed buffering → continuity/time metadata → wired Native USB → host PC. Nominal 48 kHz mono is recorded. The exact production ADC/profile has not been selected or measured. |
| **B-W2-02 — Streaming/DMA research and B→C framing inputs** | **PARTIAL; Week-4 freeze open** | The draft defines DMA/ping-pong direction, monotonic continuity, device-side timestamping, status/error concepts, estimated payload rate for the 24-in-32 proposal, and CDC-ACM versus Vendor Bulk as open choices. Exact buffer sizes, interrupt/cache behavior, final transport class, byte layout, CRC policy and measured throughput remain open or unmeasured; the document does not claim those are validated. |
| **B-W2-03 — Turkish sourcing table / BOM v0.1 → v1.0 review** | **REVIEWED; not wholly purchase-ready** | The REV02 workbook contains main sourcing, electronic pre-BOM, alternatives, decision/action tracking, order-readiness gates and pricing cross-check. Current plan includes 2 MCU boards, 4 ECMs, 3 PUI EB-R boards (2 + 1 spare), 5 MCP6022-I/P op-amps and 2 PAM8403 modules (1 + 1 spare). The entire BOM must not be labelled ready: exact chestpiece SKU, passive-kit selection, exciter/amplifier compatibility, silicone/frame geometry, several cable/connector details, and live price/stock/delivery checks remain open. |
| **B-W2-04 — Department laboratory equipment audit** | **AVAILABILITY STATUS RECORDED** | Ozan reports scope, function generator, DMM, soldering station and reusable breadboards/dev-boards available. The department USB audio interface C-05 is reported unavailable. This is an availability report only, not calibration or performance certification; the personal 3.5 mm→USB adapter remains unverified. |
| **W3 — Device-to-host frame draft** | **CONCEPTUAL DRAFT COMPLETE** | The linked frame draft defines protocol/version, type, sequence/index, timestamp, sample count/payload length, sample/profile metadata, status/error telemetry and an integrity-policy decision point. It deliberately avoids premature byte offsets and frame size. |
| **DW03-03 — MCU candidate** | **CLOSED FOR CANDIDATE IDENTITY ONLY** | ESP32-S3-DevKitC-1-N8R8. Live stock, physical board revision and connectors remain purchase checks. |
| **DW03-08 — USB medium** | **CLOSED FOR PHYSICAL MEDIUM ONLY** | Wired Native USB is the baseline. CDC-ACM versus vendor-specific Bulk remains open under DW03-12. |
| **DW03-09 — CRC/checksum** | **OPEN — DO NOT CLOSE UNILATERALLY** | Joint Module B + Module C decision. If selected, coverage, algorithm, byte order and failure/resynchronization behavior must be specified. |
| **DW03-10 — sample representation** | **OPEN — JOINT B/C AGREEMENT REQUIRED** | 48 kHz mono is nominal; signed 24-bit meaningful samples in a 32-bit little-endian container is only a proposal for the digital-I²S baseline. ECM ADC results may affect the common representation. |
| **DW03-13 — ECM ADC path** | **OPEN — ADVISOR / SCHEMATIC GATE** | ESP32-S3 SAR ADC1 is a bench candidate, not assumed audio-grade. PCM1808 is an external I²S ADC candidate only. Only purchase of the PCM1808 module is held specifically pending advisor approval and the exact module schematic/clock/power/interface review; unrelated Group-A items can progress after their own checks. |

## 2. Procurement safeguards from the submitted REV02 files

- **PUI EB-R:** 3 boards are planned (2 bench-use + 1 spare), with first-order priority due to a 2026-10-12 Farnell snapshot of 14 stock and 22-week standard manufacturer lead time. This is not a regional delivery promise. Public EUR listing and existing TRY snapshot are not reconciled. Obtain actual pad/power mapping and written confirmation of allowed VCC before wiring.
- **MEMS power:** USB 5 V is for the DevKit/MCU input only. PUI product data lists 1.8 V standard VCC and 3.6 V maximum. DevKit 3V3 → series R + C/decoupling is permitted as a test candidate only if PUI confirms 3.3 V at the real EB-R power pad; otherwise design a regulated 1.8 V rail and check I²S logic thresholds/translation. RC is not a regulator.
- **USB cables:** verify the existing stock now. Plan two data-capable Standard-A→Micro-B USB 2.0 cables for Native USB and separate USB-UART/log; purchase only any shortfall before first flash. Do not use charge-only cables.
- **PAM8403:** 2 modules are planned (1 use + 1 spare), but this is a short-term bench candidate, not a long-life component. Supplier UI observations on 2026-10-13 conflict (21.65 TL incl. VAT + out-of-stock versus 19.72 TL + Add to Cart). Live stock/price remains unverified; NRND/EOL status and compatibility with the proposed 12 Ω exciter require consideration.
- **PUI/ECM comparison:** measure the ADC/AFE-only noise floor in a documented safe test configuration as part of T-AUD-06 so electronics noise does not masquerade as a transducer difference.
- **Farnell pricing:** the separate workbook Fiyat_Kontrol page exposes EUR list price, FX/KDV assumptions and deviation from the local TRY snapshot. It is an estimate only; the live Turkish basket, VAT, shipping, import/bank effects and delivery must be confirmed.

## 3. Week-4 / course-gate handoff

Before the Week-4 requirements freeze, agree with Module C and the advisor on:
1. the acquisition path/profile and 48 kHz mono baseline details;
2. sample representation, alignment, endian convention, channel/rate declaration and payload packetization;
3. DMA buffer size/ping-pong policy, continuity counter width/rollover and timestamp clock/units;
4. Native USB class (CDC-ACM vs vendor Bulk), host resynchronization and error/status reporting;
5. CRC/checksum policy — keep DW03-09 open until both Module B and Module C owners agree;
6. order-ready status by item, with live MPN/stock/price/delivery and mechanical compatibility checks.

**G1 / Week 5:** synthetic/known signal must be captured end-to-end from Module B to Module C. This is planned, not yet completed.  
**G2 / Week 9:** independently known PCG stimulus through the acoustic phantom must be compared quantitatively. This is planned, not yet completed.

## 4. No false completion claims

This closeout records design and procurement work only. It does **not** claim firmware implementation, a successful physical ESP32-S3 stream, EB-R electrical connection, verified ADC performance, measured 20–500 Hz response/SNR, continuity/drop-rate results, or completion of G1/G2. Those require later implementation and evidence.