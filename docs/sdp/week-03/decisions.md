# EEE495 -- Week 03 Decisions

This file records decisions that must be made at or before the Week-03 meeting.
A decision is CLOSED only for the scope explicitly stated in its resolution. A candidate identity closure does not imply final system validation, purchase approval, or measured performance.

---

## Decision Table

| ID | Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW03-01 | ECM comparison candidate | CLOSED | Kaan (Module A) | **Kingstate KECG2740PBJ** selected as the Week-03 ECM comparison candidate. A previously evaluated alternative was rejected because procurement was impractical and its reviewed schematic/datasheet did not satisfy the documented project requirements. **This closes candidate identity only:** Kingstate is NOT declared the final system transducer. Final transducer selection remains measurement-based after identical phantom comparison tests. Lower -3 dB evidence and purchase readiness remain OPEN. See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). **NOT YET MEASURED.** |
| DW03-02 | MEMS comparison candidate | CLOSED | Kaan (Module A) | **PUI DMM-4026-B-I2S-R** is the sensor under evaluation; **PUI DMM-4026-B-I2S-EB-R** is the proposed bench/evaluation carrier to purchase. This closes candidate identity only, not final sensor choice or purchase approval. EB-R solder-pad mapping/physical interface, stock/delivery, sensitivity-reference/clock clarification, and lower -3 dB evidence remain OPEN. See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). **NOT YET MEASURED.** |
| DW03-03 | MCU development board | CLOSED (candidate identity) | Ozan (Module B) | **ESP32-S3-DevKitC-1-N8R8** is the Module B baseline development-board candidate because it provides ESP32-S3 I²S-capable acquisition resources and a native USB physical path. This does not close purchase readiness: verify supplier stock, exact shipped board revision, and the actual connectors/cable types before ordering or at receipt. Sample-rate, buffering, and firmware settings are frozen in Week 4. |
| DW03-04 | Phantom exciter | OPEN | Kaan (Module A) | REV01 proposal: Motorobit 30 mm, 12 ohm vibration/resonance speaker. Exact power specifications, amplifier compatibility, mounting and usable low-frequency excitation remain unresolved. An alternate exciter may be evaluated if budget and sourcing permit. **NOT YET MEASURED.** See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). |
| DW03-05 | Phantom amplifier | OPEN | Kaan (Module A) | REV01 proposal: PAM8403 mini amplifier module. Confirm the exact module schematic, supply/load compatibility, input-coupling response and headroom; advertised power is not guaranteed into the proposed 12 ohm load. Keep amplifier power/cable routing separate from the microphone/AFE path. **NOT YET MEASURED.** |
| DW03-06 | Coupling material | OPEN | Kaan (Module A) | REV01 proposal: transparent silicone sheet, nominal 3 mm as a starting thickness. Hardness, contact area, compression, geometry and required quantity are not fixed. **NOT YET MEASURED.** |
| DW03-07 | Rigid frame concept | OPEN | Kaan (Module A) | REV01 proposal: nominal 3 mm acrylic starting stock, 20 x 30 cm, with repeatable chestpiece clamping and cable restraint. Geometry, stiffness and clamp pressure remain to be specified. **NOT YET MEASURED.** |
| DW03-08 | B-to-C physical transport medium | CLOSED (physical medium only) | Ozan (Module B) / Ege (Module C) | The device-to-host physical data path is **wired ESP32-S3 Native USB**. This closes the physical-medium choice only. USB device class (CDC-ACM vs vendor-specific Bulk), endpoint details, and final host integration remain OPEN under DW03-12. Do not interpret this as selecting CDC-ACM or Vendor Bulk. |
| DW03-09 | Application-level integrity / CRC policy | OPEN | Ege (Module C) / Ozan (Module B) | Joint decision. Decide whether the application layer adds CRC/checksum or relies on lower-layer USB integrity plus continuity/status checks. **Do not close without agreement from both Module B and Module C owners and the team decision review.** If CRC is selected, define coverage, algorithm, byte order and failure behavior. |
| DW03-10 | Sample representation | OPEN | Ozan (Module B) / Ege (Module C) | Week-2 B-to-C requirements contain a **proposal** of signed 24-bit meaningful PCM carried in a 32-bit container for the digital-I²S baseline, little-endian. This is not yet a jointly frozen wire-format contract and may be affected by the selected ECM ADC path. Agree sample encoding/alignment, endianness, declared sample rate/channel count, payload count and packetization with Module C before closing. The nominal baseline remains 48 kHz mono; final acquisition profile and implementation settings are frozen in Week 4. |
| DW03-11 | Week-04 order readiness | OPEN | Team / Ozan / Kaan | Purchase readiness requires the exact MCU board/revision and Native USB cable type; ECM quantity; PUI EB-R stock and its actual pad/interface mapping; approved ECM bias/AFE and ADC architecture; exciter/amplifier compatibility; silicone/coupling and rigid-frame geometry; breadboard/jumpers, headers/wire, shielded cable/connectors; current price/stock/delivery snapshot; and completion of the lab equipment audit. Items not physically checked at the department must be marked **PENDING LAB CONFIRMATION**. Do not mark the entire BOM purchase-ready until blocked choices are resolved. |
| DW03-12 | USB device class / B-to-C transport protocol | OPEN | Ozan (Module B) / Ege (Module C) | Compare USB CDC-ACM versus USB vendor-specific Bulk after the physical Native USB choice in DW03-08. Record host driver/support, stream robustness, throughput, parser/resynchronization behavior and implementation effort. No class or endpoint layout is frozen in Week 3. |
| DW03-13 | ECM external ADC path | OPEN | Ozan (Module B) with advisor/team review | Required architecture to assess: Kingstate KECG2740PBJ -> bias/AFE -> ADC -> ESP32-S3 -> Native USB -> PC. ESP32-S3 SAR ADC1 may be evaluated on the bench but is not assumed to provide audio-grade PCG characterization. **PCM1808 is an external I²S ADC candidate only**, not selected/final: confirm the actual breakout schematic, MCLK generation, analog/digital rails, input coupling/full-scale compatibility, availability, and advisor approval. The department USB audio interface (C-05) is a separate reference-instrument possibility, not automatically a substitute for the MCU-to-host path. |
| DW03-14 | Department lab equipment audit | OPEN | Ozan (Module B) | Physical availability is not yet evidenced in this decision record. Check and record the location/availability of: oscilloscope, function generator, multimeter, soldering station, USB audio interface, and any reusable breadboards/DevKit boards. Keep each unverified item as **PENDING LAB CONFIRMATION** until confirmed with department/lab staff. |

---

## Week-3 Module B Decision Summary

- Board candidate identity is closed as ESP32-S3-DevKitC-1-N8R8; physical revision and procurement confirmation remain pending.
- Wired Native USB is the selected physical transport. CDC-ACM versus Vendor Bulk remains open.
- 48 kHz mono is the nominal baseline, not yet a complete frozen acquisition profile.
- The B-to-C frame is conceptual only in Week 3. Byte offsets, exact frame size, buffer size, clock/timestamp units and sample packing are Week-4 freeze items.
- DW03-09 is a joint Module B / Module C integrity decision and remains OPEN until the owners agree.
- The ECM external ADC path is OPEN. PCM1808 is a candidate, not a final decision.
- No physical measurements or hardware tests are claimed by this document-only closeout.

## Notes

- Add rows as further decisions arise.
- Change a decision to CLOSED only when the stated scope has a concrete, documented resolution; record any remaining purchase/test conditions.
- Cross-reference the relevant submission files.
- All unresolved items are inputs to the Week-04 Requirements Freeze (see [week-04/decisions.md](../week-04/decisions.md)).
