# W05 Module C: Live Display and Recording Verification

**Week:** 5  
**Module:** C — Computer Application & Quality Assessment  
**Owner:** Ege Çağın Tepe  
**Status:** IN PROGRESS (Host Preflight Complete; Physical MCU Bench Execution Pending)  

## Objective

Verify the real-time PCG live display, signal-processing views, continuous recording, and session provenance sidecar generation upon the arrival of the physical ESP32-S3 synthetic stream.

## Inputs / Dependencies

- Module B: ESP32-S3 DevKitC-1 with flashed Native USB synthetic stream (100 Hz sine or counter pattern) under agreed CDC-ACM profile.
- Module C Preflight Deliverables:
  - Protocol Readiness Review: [`W05_C_protocol-readiness-review_v01.md`](W05_C_protocol-readiness-review_v01.md)
  - Host Integration Preflight Report: [`W05_C_host-integration-preflight_v01.md`](W05_C_host-integration-preflight_v01.md)
  - Automated Preflight Test Suite: `software/tests/test_device_runtime.py` (Class `TestHostPreflightVerification`, 7/7 tests passing)

## Work Performed

- Executed Sprint 1 host preflight audit and testing across 48 kHz mono synthetic preservation, normalization bounds, multi-block ordering, gap/duplicate telemetry, and WAV/JSON hash integrity.
- Prepared the proposed B→C interface contract review covering CDC-ACM transport, 16-byte frame headers, 24-in-32 signed PCM, timestamping, CRC-16, and INMP441 profile reconciliation.
- Mapped acceptance cases `C-W05-01` through `C-W05-09` against existing test coverage and bench requirements.

## Evidence

- Preflight test execution: 34/34 tests passing in `software/tests/test_device_runtime.py` (281/281 passing across complete repository test suite).
- All preflight results labeled strictly `SOFTWARE_KNOWN_ANSWER`.
- Physical bench runs and hardware logs remain pending physical board arrival.

## Results

- Host software ingestion engine is verified and ready for physical byte streaming.
- **NOT TESTED ON HARDWARE:** Physical USB enumeration, bench throughput, hardware latency, and real acoustic phantom signals remain pending.
- Gate G1 remains **OPEN / PENDING PHYSICAL HARDWARE BENCH RUN**.

## Open Decisions / Risks

- **DW03-09 (Application CRC):** CRC-16-CCITT proposed by Module C; pending Module B sign-off.
- **DW03-10 (Sample Packing & Alignment):** LSB-aligned signed PCM in 32-bit container proposed; pending Module B confirmation of I2S DMA bit alignment.
- **DW03-12 (USB Class):** CDC-ACM virtual serial port proposed; pending Module B sign-off.
- **Sensor Profile:** INMP441 breakout module procured instead of PUI EB-R; profile migration requires breakout verification.

## Next Week Handoff

- Attach physical ESP32-S3 Native USB port upon arrival.
- Execute live bench acceptance run `C-W05-01..09`.
- Retain session WAV, JSON sidecars, and terminal logs for Gate G1 sign-off.
