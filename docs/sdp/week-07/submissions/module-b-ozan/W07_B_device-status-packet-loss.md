# W07 Module B: Device Status and Packet Loss

- **Week:** 7 (2–8 November 2026)
- **Module:** B (Embedded Acquisition and Data Path)
- **Owner:** Ozan
- **Official Module Role:** Microcontroller sampling, buffering and timestamping, device-to-computer protocol, device self-test and status reporting, and latency/stability measurement.
- **Status:** PARTIAL (Firmware & Host Telemetry Implemented in Code by Ege / Physical Bench Loss Audit Pending)

---

## 1. Objective (Planned vs. Syllabus)

According to the official project plan (`SDP4_Digital_Stethoscope_Plan_EN.docx`):
> *"Week 7 Module B: Implement device status reporting and packet loss detection."*

The goal was to implement embedded telemetry reporting (tracking dropped samples, DMA overflows, ring buffer overflows, and USB transmission stalls) and provide host-side packet loss detection to ensure zero-loss audio stream continuity.

---

## 2. Inputs & Dependencies

- ESP-IDF v5.5.1 TinyUSB CDC and I²S audio driver architecture.
- Binary packet protocol framing (`AF01` magic, 32-bit sequence counter, CRC-16-CCITT).
- Host-side USB acquisition bridge (`software/pcg_app/hardware_workflow.py`).

---

## 3. Work Performed During Week 7 (2–8 November 2026)

- **Calendar Context:** Week 7 coincided with the university midterm examination recess (2–15 November 2026).
- **Substantiated Work & Contribution Breakdown:**
  - **Firmware Implementation (Authored by Ege Çağın Tepe):**
    - Designed and implemented embedded telemetry counters inside the ESP32-S3 firmware: `dropped_samples`, `dma_overflow_events`, `ring_overflow_events`, and `usb_partial_write_events`.
    - Integrated sequence counter continuity verification into `firmware/components/g1/g1.c` and protocol header structures.
  - **Host Acquisition Software (Authored by Ege Çağın Tepe):**
    - Implemented host-side packet continuity validation in `software/pcg_app/canonical/session.py` and `software/pcg_app/hardware_workflow.py`.
    - Added host FSM disconnect/reconnect recovery: `(ABSENT | INTERRUPTED | ERROR) -> DETECTED -> OPENING`.
  - **Module B Field Execution (Ozan):**
    - Physical hardware bench execution and packet loss logging under Ozan's operation were **NOT EXECUTED** during Week 7 due to the midterm recess.

---

## 4. Evidence & Code References

- Firmware telemetry structures: `firmware/components/g1/include/g1.h`, `firmware/components/g1/g1.c`
- Host-side loss detection: `software/pcg_app/canonical/session.py`, `software/pcg_app/hardware_workflow.py`
- Automated tests: `software/tests/test_stream_filter_contract.py`, `software/tests/test_replay_eof_health.py`
- Architectural documentation: [`docs/sdp/PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

---

## 5. Results & Compliance

- **Software / Firmware Implementation:** **COMPLETE** — Firmware and host-side telemetry pipelines were verified with synthetic and loopback unit tests.
- **Physical Bench Verification:** `PENDING BENCH EXECUTION` during Week 7.

---

## 6. Subsequent Dated Follow-Up (18 November 2026 — Week 9)

On Wednesday, 18 November 2026, Ozan executed the first physical hardware bringup in the laboratory (`W09_B_continuity-clipping-verification.md`):
- Measured the ESP32-S3 3.3V rail at **3.28 V** using a calibrated Agilent U1232A digital multimeter (safe operating range: 1.62 V – 3.63 V).
- Flashed candidate firmware onto the ESP32-S3 over USB CDC on port `COM3`.
- Executed two 10-second G1/G2 physical streaming sessions:
  - Total samples streamed: **1,920,000 samples** (40.0 s total across G1 and G2).
  - Telemetry verification: **0 dropped frames, 0 CRC failures, and 0 in-stream dropped samples**.
  - Normal post-target FIFO drain of 256 samples observed at acquisition boundary without in-stream data loss.

---

## 7. Open Decisions & Risks

1. **Extended Stress Testing:** The 18 November test verified 10-second acquisitions. A multi-minute or 30-minute stress test has not yet been executed on physical hardware.
2. **Buffer Margin Under Load:** Telemetry must be monitored under heavy host CPU load to confirm FreeRTOS ring buffer depth adequacy.

---

## 8. Next Lab Handoff

In the next lab session, monitor telemetry during the physical acoustic phantom experiment using `tools/hardware/run_phantom_pcg_experiment.py` to ensure 0 in-stream packet drops.
