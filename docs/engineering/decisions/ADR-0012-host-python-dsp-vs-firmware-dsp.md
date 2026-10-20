# ADR-0012: DSP Allocation — Host Python DSP vs. Embedded Firmware DSP
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module C (Ege), Module B (Ozan)  
**Technical Area:** System Architecture & Processing Allocation

## Context & Problem Statement
In digital stethoscope design, signal processing (bandpass filtering, envelope extraction, spectral analysis) can theoretically be executed either on the embedded microcontroller (ESP32-S3) or on the host computer (Python). The team needed to decide where the primary DSP pipeline should reside.

## Decision Drivers
* Preservation of raw data: Scientific analysis requires access to pristine, unadulterated sensor output. Filtering audio in firmware permanently discards spectral components outside the passband, preventing retrospective analysis.
* Numerical precision: Double-precision floating point (64-bit IEEE-754) is trivial on a host CPU, but taxes an embedded microcontroller.
* Research iteration speed: Developing and tuning filters, envelopes, and ML models is vastly faster in Python than flashing firmware binaries over UART.

## Considered Alternatives
1. **Full Firmware DSP:** Execute bandpass filtering and envelope extraction on the ESP32-S3 using the Xtensa DSP instruction set.
   * *Critical Flaw:* Destroys raw acoustic information before reaching the PC; makes it impossible to compare different digital filter topologies retrospectively on the same acoustic recording.
2. **Hybrid DSP:** Basic low-pass filtering in firmware, secondary analysis in Python.
   * Introduces duplicate filtering pipelines and documentation ambiguity.
3. **Pure Host DSP with Pristine Firmware Streaming:** Firmware acts strictly as a transparent acquisition conduit, streaming raw digitized I2S samples over USB. All digital filtering, decimation, and spectral analysis run on the host PC.

## Decision
Selected **Pure Host Python DSP**:
* The ESP32-S3 firmware is dedicated entirely to hardware acquisition, DMA double-buffering, continuity sequencing, and USB transport.
* The host PC executes all DSP algorithms (`StreamingBandpass`, `scipy.signal.welch`, `pcg_core.scientific`).

## Consequences & Trade-Offs
* **Positive:** 100% of raw sensor data is preserved on disk; algorithms can be updated and re-run on historical recordings without touching firmware.
* **Negative:** Host CPU must process 48,000 samples/s in real-time, but modern host CPUs consume $< 5\%$ of a single core for this task.
