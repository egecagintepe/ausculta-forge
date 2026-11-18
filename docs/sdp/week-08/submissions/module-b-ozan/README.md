# Module B -- Embedded Acquisition and Data Path
## Submission Folder -- Week 8

| Field | Value |
|---|---|
| **Owner** | Ozan |
| **Module** | B -- Embedded Acquisition and Data Path |
| **Week** | 8 (9–15 November 2026) |
| **Task** | End-to-End Latency and 30-Minute Continuous Acquisition |
| **Status** | **NOT EXECUTED (FIRMWARE SESSION BOUNDED / BENCH RUN PENDING)** |

## Submissions

- [W08_B_latency-continuous-run.md](W08_B_latency-continuous-run.md) — Architectural analysis of firmware session bounds, software latency workflows, and documented status of 30-minute endurance run.

## Status Summary

- Week 8 coincided with the university midterm examination recess.
- Architectural analysis identified that firmware `G1_TARGET_SAMPLES` (10.0 s @ 48 kHz) and 40 s watchdog timeout cap prevent a 30-minute run without an intentional firmware update.
- On 18 November 2026 (Week 9), Ozan executed two 10-second physical streaming sessions (1,920,000 samples, 0 dropped frames) on COM3 (`W09_B_continuity-clipping-verification.md`). Continuous 30-minute endurance testing remains pending.
