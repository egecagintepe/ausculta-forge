# EEE495 -- Week 03 Decisions

This file records all decisions that must be made at or before the Week-03 meeting.
A decision is CLOSED only when the team has a concrete, documented resolution.
Leave all genuinely open items as OPEN.

---

## Decision Table

| ID | Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW03-01 | ECM comparison candidate | CLOSED | Kaan (Module A) | **Kingstate KECG2740PBJ** selected as the Week-03 ECM comparison candidate. A previously evaluated alternative was rejected because procurement was impractical and its reviewed schematic/datasheet did not satisfy the documented project requirements. **Note:** Kingstate KECG2740PBJ is NOT declared the final system transducer. Final transducer selection remains measurement-based and will be determined after identical phantom comparison tests. |
| DW03-02 | MEMS comparison candidate | OPEN | Kaan (Module A) | Candidate not yet selected. Requires datasheet review and Turkish procurement check. |
| DW03-03 | MCU development board | OPEN | Ozan (Module B) | Board not yet selected. Must satisfy sample rate, USB throughput, and firmware toolchain requirements. |
| DW03-04 | Phantom exciter | OPEN | Kaan (Module A) | Exciter type and source not yet determined. |
| DW03-05 | Phantom amplifier | OPEN | Kaan (Module A) | Amplifier for phantom exciter not yet selected. |
| DW03-06 | Coupling material | OPEN | Kaan (Module A) | Coupling material between transducer and phantom surface not yet selected. |
| DW03-07 | Rigid frame concept | OPEN | Kaan (Module A) | Phantom rigid frame design not yet finalised. |
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
