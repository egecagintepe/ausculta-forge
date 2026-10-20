# EEE495 — Software Sprint 10 Decisions (Embedded Interoperability)

> [!NOTE]
> **TIMELINE CLARIFICATION:**
> "Sprint 10" designates the internal agile software iteration cycle for Module C, NOT the academic semester Week 10 (the academic calendar is currently at Week 04/05). This document preserves sprint decision provenance while aligning with semester gates.

| ID | Decision Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW10-01 | Embedded Interoperability Reference Framework | CLOSED | Ege & Ozan | Standalone C golden-vector generator (`tools/c_golden_vectors`) and experimental ESP32-S3 bench example (`tools/esp32_bench_example`) established outside production firmware tree (`firmware/` remains under Ozan's ownership). Cross-compilation marked UNVERIFIED / NOT EXECUTED pending physical hardware delivery. |
| DW10-02 | Physical Hardware Bring-Up Protocol | CLOSED | Ege & Ozan | 8-gate integration checklist established in `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`. DirencNet N16R8 board must be physically verified for true dual-USB routing upon arrival before Gate 2. |
| DW10-03 | B→C Byte-Level Wire Contract & CRC Policy | OPEN | Ozan & Ege | Wire framing (16B header, magic word `0xAA55`, CRC-16 polynomial) and bit alignment (LSB vs MSB) remain PROPOSED / NOT APPROVED pending physical bench measurements with physical ESP32-S3 and joint B/C sign-off. |

## Notes

- Cross-referenced with `docs/sdp/week-10/submissions/module-c-ege/W10_C_embedded-interoperability-audit_v01.md`.
- No wire format is prematurely frozen without physical bench verification by Module B.
- Virtual bench results reflect software verification, not physical G1 evidence.
