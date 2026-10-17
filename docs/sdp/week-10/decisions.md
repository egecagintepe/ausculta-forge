# EEE495 -- Week 10 Decisions

| ID | Decision Topic | Status | Owner | Resolution / Notes |
|---|---|---|---|---|
| DW10-01 | Embedded Interoperability Reference Framework | CLOSED | Ege & Ozan | Standalone C golden-vector generator (`tools/c_golden_vectors`) and experimental ESP32-S3 bench example (`tools/esp32_bench_example`) established outside production firmware tree. Cross-compilation marked NOT EXECUTED pending physical hardware delivery. |
| DW10-02 | Physical Hardware Bring-Up Protocol | CLOSED | Ege & Ozan | 8-gate integration checklist established in `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md` covering dual USB port enumeration, INMP441 3.072 MHz clock verification, synthetic 100 Hz known sample test, and Gate G1 evidence package. |
| DW10-03 | B→C Byte-Level Wire Contract & CRC Policy | OPEN | Ozan & Ege | Wire framing (16B header, magic word `0xAA55`, CRC-16) and bit alignment (LSB vs MSB) remain PROPOSED / NOT APPROVED pending physical bench measurements with physical ESP32-S3. |

## Notes

- Cross-referenced with `docs/sdp/week-10/submissions/module-c-ege/W10_C_embedded-interoperability-audit_v01.md`.
- No wire format is prematurely frozen without physical bench verification by Module B.
