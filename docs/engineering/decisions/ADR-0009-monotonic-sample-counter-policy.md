# ADR-0009: Sample Continuity — Monotonic Counter Policy
**Status:** `ACCEPTED`  
**Date:** 2026-10-18  
**Deciders:** Module B (Ozan), Module C (Ege)  
**Technical Area:** Stream Telemetry & Metrological Continuity

## Context & Problem Statement
A primary engineering criterion in senior design is verifying continuous, unbroken streaming during prolonged acquisition (including the advisor-mandated $\ge 30$-minute stress test). The team needed a reliable mechanism to detect packet drops, buffer overruns, and timeline gaps.

## Decision Drivers
* Must track packet loss unambiguously across integer counter wraparounds.
* Must allow exact accounting of how many discrete samples were dropped during an interruption.
* Must not rely on host PC timestamps, which are subject to operating system scheduling jitter.

## Considered Alternatives
1. **Host Wall-Clock Comparison:** Checking delta timestamps on the host. Inaccurate because USB host polling jitter causes arrival time to fluctuate by several milliseconds even when zero hardware samples are dropped.
2. **16-bit Packet Index Only:** Rolls over every $\approx 10.92$ seconds (at 6000 packets/s), requiring unwrapping logic on the host.
3. **Cumulative Monotonic Sample Index (64-bit Equivalent):** Firmware transmits a monotonic packet counter; host `StreamQualityMonitor` maintains an un-wrapped 64-bit cumulative sample index ($S_{\text{cumulative}}$).

## Decision
Adopted the **Monotonic Cumulative Sample Index Policy**:
* Every packet carries a sequence counter incremented monotonically by the MCU.
* The host `StreamQualityMonitor` (`software/pcg_core/streaming.py`) verifies that:
  $$\Delta S = S_{\text{received}} - S_{\text{expected}} = 1$$
* If $\Delta S > 1$, exactly $\Delta S - 1$ missing blocks are recorded in session metadata.
* If $\Delta S \le 0$ (repeated or out-of-order packet), a sequence regression fault is logged.

## Consequences & Trade-Offs
* **Positive:** Mathematically rigorous verification of $100\%$ sample continuity; proves zero dropped samples to the course advisor.
* **Negative:** Requires stateful continuity monitoring in host memory.
