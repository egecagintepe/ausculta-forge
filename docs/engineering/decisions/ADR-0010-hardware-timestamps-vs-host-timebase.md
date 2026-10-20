# ADR-0010: Timestamp Timebases — Hardware Ticks vs. Host Arrival Time
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module C (Ege), Module B (Ozan)  
**Technical Area:** System Architecture & Clock Synchronization

## Context & Problem Statement
Every audio block ingested by the system requires a timebase reference. Two timebases exist in the architecture:
1. **Hardware Timebase:** Microcontroller hardware timer ticks (microseconds or FreeRTOS ticks) driven by the on-chip crystal oscillator.
2. **Host Timebase:** Host computer system time (`time.time()` / `time.monotonic()`) synchronized to PC wall clock.

The team needed to decide which timebase governs persistent recording metadata and live waveform synchronization.

## Decision Drivers
* Cross-system reproducibility: Recording files must contain human-readable, calendar-aligned UTC timestamps (ISO-8601).
* Jitter detection: The system must be able to detect microcontroller clock drift relative to host time.
* Session independence: The MCU timer resets to zero upon every power cycle or reboot, whereas host timestamps remain monotonic.

## Considered Alternatives
1. **Sole Reliance on MCU Hardware Ticks:** Requires host to reconstruct real-world calendar time by querying MCU uptime, which fails if the MCU resets mid-session.
2. **Sole Reliance on Host OS Time:** Incurs host USB polling jitter; timestamp differences between consecutive blocks vary by $\pm 2 \text{ ms}$ even when hardware sampling is perfectly periodic.
3. **Dual-Timebase Governance:** Use host monotonic time for session recording and file metadata; use MCU hardware timestamps for low-level transmission jitter telemetry.

## Decision
Adopted **Dual-Timebase Governance**:
* **Host Monotonic Epoch (`time.time()`):** Assigned to `SampleBlock.timestamp` at the Layer 1 ingestion boundary. Governs WAV file headers, session sidecar timestamps, and frontend canvas rulers.
* **MCU Hardware Ticks:** Stored in wire packet headers and logged in `StreamQualityMonitor` to measure packet arrival jitter and evaluate crystal oscillator drift.

## Consequences & Trade-Offs
* **Positive:** Session files have unambiguous, human-readable real-world timestamps; hardware timer resets do not corrupt file timebases.
* **Negative:** Host arrival timestamp includes minor USB transport jitter ($\pm 1 \text{ ms}$).
