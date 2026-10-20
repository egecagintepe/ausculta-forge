# ADR-0017: Verification Methodology — Virtual Bench & C Golden Vectors
**Status:** `ACCEPTED`  
**Date:** 2026-10-18 (Sprint 02 & Sprint 10)  
**Deciders:** Module C (Ege)  
**Technical Area:** Verification, Testing & Simulation

## Context & Problem Statement
During agile software development (Sprints 01–10), the physical ESP32-S3 microcontroller and INMP441 sensors were pending procurement and laboratory arrival. The host software team needed a way to verify the entire end-to-end software pipeline (ingestion, framing, DSP, display, metrology, and session storage) without physical hardware.

## Decision Drivers
* Deterministic reproducibility: Known mathematical signals with known-answer outputs.
* Edge case testing: Injecting electrical faults, dropped packets, and corrupt CRC frames that are difficult to reproduce consistently on physical breadboards.
* Cross-language bit-level parity: Ensuring C integer manipulation matches Python floating-point normalization.

## Considered Alternatives
1. **Ad-Hoc Mock Functions:** Simple random noise or uncalibrated mock generators.
   * Lacks mathematical rigor; does not verify bit-level alignment or frequency response estimators.
2. **Deterministic Virtual Bench + Portable C Golden Vectors:**
   * `VirtualBench` (`software/pcg_app/virtual_bench.py`): 8 mathematically specified scenarios.
   * `c_golden_vectors` (`tools/c_golden_vectors/`): Compilable C11 test suite generating binary reference fixtures.

## Decision
Implemented the **Deterministic Virtual Bench & C Golden Vector Suite**:
* The 8 Virtual Bench scenarios cover sine generation, monotonic ramp counters, boundary transitions, clipping, dropped blocks, timestamp jitter, CRC corruption, and mid-stream disconnects.
* Portable C vectors compile under standard GCC C11 and verify bit-for-bit parity against Python in automated CI.

## Consequences & Trade-Offs
* **Positive:** Allowed 100% of host software, metrology pipelines, and UI features to be completed, verified, and merged prior to physical silicon delivery.
* **Negative:** Software passing all virtual bench scenarios does not guarantee that physical solder joints or jumper wires will work without laboratory debugging.
