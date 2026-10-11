# EEE495 -- Week 03 Decisions

This file records all decisions that must be made at or before the Week-03 meeting.
A decision is CLOSED only when the team has a concrete, documented resolution.
Leave all genuinely open items as OPEN.

---

## Decision Table

| ID | Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW03-01 | ECM comparison candidate | CLOSED | Kaan (Module A) | **Kingstate KECG2740PBJ** selected as the Week-03 ECM comparison candidate. A previously evaluated alternative was rejected because procurement was impractical and its reviewed schematic/datasheet did not satisfy the documented project requirements. **Note:** Kingstate KECG2740PBJ is NOT declared the final system transducer. Final transducer selection remains measurement-based and will be determined after identical phantom comparison tests. Closure is retained for candidate identity only; lower -3 dB evidence and purchase readiness remain OPEN. See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). **NOT YET MEASURED.** |
| DW03-02 | MEMS comparison candidate | CLOSED | Kaan (Module A) | **PUI DMM-4026-B-I2S-R**, with **DMM-4026-B-I2S-EB-R** for bench use, records the candidate selected in Kaan's Week-3 report. I2S provides the digital comparison chain. CLOSED for candidate identity only, not final sensor choice or purchase approval. Datasheet lower -3 dB evidence, sensitivity-reference/clock clarification and B-interface confirmation remain OPEN. DigiKey/EKOM is a previously identified sourcing route; current stock and delivery require Ozan's recheck. See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). **NOT YET MEASURED.** |
| DW03-03 | MCU development board | OPEN | Ozan (Module B) | Board not yet selected. Must satisfy sample rate, USB throughput, and firmware toolchain requirements. |
| DW03-04 | Phantom exciter | OPEN | Kaan (Module A) | REV01 proposal: Motorobit 30 mm, 12 ohm vibration/resonance speaker. Exact power specifications, amplifier compatibility, mounting and usable LF excitation remain unresolved. **NOT YET MEASURED.** See the [Module A closeout](submissions/module-a-kaan/W03_A_transducer-candidate-selection.md). |
| DW03-05 | Phantom amplifier | OPEN | Kaan (Module A) | REV01 proposal: PAM8403 mini amplifier module. Exact module schematic, supply/load compatibility, input-coupling response and headroom need confirmation; advertised power is not guaranteed into the proposed 12 ohm load. **NOT YET MEASURED.** |
| DW03-06 | Coupling material | OPEN | Kaan (Module A) | REV01 proposal: transparent silicone sheet, nominal 3 mm starting thickness. Hardness, contact area, compression and required quantity are not fixed. **NOT YET MEASURED.** |
| DW03-07 | Rigid frame concept | OPEN | Kaan (Module A) | REV01 proposal: nominal 3 mm acrylic, 20 x 30 cm starting stock, with repeatable chestpiece clamping and cable restraint. Geometry, stiffness and clamp pressure remain to be specified. **NOT YET MEASURED.** |
| DW03-08 | B-to-C transport option | OPEN | Ozan (Module B) / Ege (Module C) | USB vs. other interface for device-to-host data path not yet decided. Depends on MCU board selection (DW03-03). |
| DW03-09 | Application-level integrity / CRC policy | OPEN | Ege (Module C) | Whether the application layer enforces CRC or integrity checks on incoming frames not yet decided. |
| DW03-10 | Sample representation | OPEN | Ozan (Module B) / Ege (Module C) | PCM bit depth and sample rate contract between Module B and Module C not yet agreed. |
| DW03-11 | Week-04 order readiness | OPEN | Team / Kaan | All Group-A components must be ordered before the Week-04 gate. Readiness depends on DW03-01 through DW03-07 being resolved. |

---

## Notes

- Add new rows as further decisions arise during the week.
- Change Status to CLOSED once a decision is made; record the rationale concisely.
- Cross-reference with the relevant task placeholder files in `submissions/`.
- All OPEN items in this table are inputs required for the Week-04 Requirements Freeze (see [week-04/decisions.md](../week-04/decisions.md)).
