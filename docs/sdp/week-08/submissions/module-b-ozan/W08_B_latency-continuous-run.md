# W08 Module B: Latency and Continuous Run

- **Week:** 8 (9–15 November 2026)
- **Module:** B (Embedded Acquisition and Data Path)
- **Owner:** Ozan
- **Official Module Role:** Microcontroller sampling, buffering and timestamping, device-to-computer protocol, device self-test and status reporting, and latency/stability measurement.
- **Status:** NOT EXECUTED (FIRMWARE SESSION BOUNDED / BENCH RUN PENDING)

---

## 1. Objective (Planned vs. Syllabus)

According to the official project plan (`SDP4_Digital_Stethoscope_Plan_EN.docx`):
> *"Week 8 Module B: Measure the end to end latency and run a continuous acquisition of at least thirty minutes."*

The goals were:
1. Measure end-to-end latency from acoustic physical excitation to host application display.
2. Execute a continuous, uninterrupted acquisition run of at least 30 minutes without dropping a single packet or sample.

---

## 2. Inputs & Dependencies

- ESP32-S3 firmware capable of unbounded continuous streaming.
- Host-side automated latency and packet drop logger.
- Reference audio excitation and loopback synchronization channel.

---

## 3. Work Performed During Week 8 (9–15 November 2026)

- **Calendar Context:** Week 8 coincided with the university midterm examination recess.
- **Substantiated Work & Architectural Findings:**
  - **Firmware Session Limitation Analysis (Authored by Ege Çağın Tepe):**
    - Audit of the firmware code revealed that `firmware/components/g1/include/g1.h` deliberately sets:
      $$\text{G1\_TARGET\_SAMPLES} = 480\,000\text{ samples}\quad (10.0\text{ seconds at }48\text{ kHz})$$
    - Furthermore, `firmware/components/g1/g1.c` enforces a 40.0-second session watchdog timeout cap (`g1_tick()`).
    - Consequently, a 30-minute continuous run cannot be performed on the current firmware without an intentional architectural change to support continuous endurance streaming.
  - **Software Metrology Preparation (Authored by Ege Çağın Tepe):**
    - Implemented `compute_latency_measurement` and `compute_continuity_drop_rate` in `software/pcg_core/metrology/workflows.py`.
    - Explicitly separated unsynchronized acoustic propagation lag from hardware-triggered loopback latency.
  - **Module B Field Execution (Ozan):**
    - Physical continuous bench runs of 30 minutes were **NOT EXECUTED** during Week 8.

---

## 4. Evidence & References

- Firmware constraints: `firmware/components/g1/include/g1.h:37`, `firmware/components/g1/g1.c:192`
- Software latency workflows: `software/pcg_core/metrology/workflows.py`
- Automated tests: `software/tests/test_metrology_automation.py`, `software/tests/test_streaming_performance.py`
- Architectural status report: [`docs/sdp/PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

---

## 5. Results & Compliance

- **30-Minute Continuous Endurance Run:** `NOT EXECUTED`.
- **End-to-End Latency Measurement:** `NOT MEASURED ON PHYSICAL BENCH` (Software model verified; hardware measurement pending).
- **Compliance Policy:** No fabricated 30-minute test logs or synthetic timestamps are reported as physical results.

---

## 6. Subsequent Dated Follow-Up (18 November 2026 — Week 9)

On Wednesday, 18 November 2026, Ozan and Kaan ran the physical hardware in the laboratory (`W09_B_continuity-clipping-verification.md`):
- Executed two discrete 10.0-second physical streaming sessions (quiet baseline and acoustic stimulus).
- Verified **0 dropped frames and 0 CRC failures across 1,920,000 physical I²S samples** (40 seconds total streaming duration across sessions).
- The 30-minute continuous endurance run remains an outstanding requirement scheduled for future characterization once dedicated endurance firmware is staged.

---

## 7. Open Decisions & Risks

1. **Continuous Acquisition Firmware Architecture:** Before a 30-minute run can succeed, the team must decide whether to remove `G1_TARGET_SAMPLES` entirely (unbounded streaming mode) or segment continuous capture into rollover blocks.
2. **Thermal & USB Buffer Stability:** Extended streaming on ESP32-S3 USB CDC requires verifying that thermal throttling and USB endpoint FIFO stalls do not occur over 1,800 seconds.

---

## 8. Next Lab Handoff

Prepare an endurance firmware configuration allowing continuous streaming, and run the 30-minute stability audit script.
