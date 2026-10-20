# ADR-0015: Display Decoupling — Bounded Peak-Preserving Decimation
**Status:** `ACCEPTED`  
**Date:** 2026-09-26 (Hardened in Sprint 05, PR #21)  
**Deciders:** Module C (Ege)  
**Technical Area:** UI Performance & Real-Time Visualization

## Context & Problem Statement
Transmitting full-rate 48,000 samples/s over WebSockets to a web browser causes browser heap exhaustion, intensive garbage collection pauses, and tab crashes. The host must decimate the audio stream for display without attenuating or hiding narrow transient acoustic spikes (such as sharp valve clicks or clicks from $S_1/S_2$).

## Decision Drivers
* Client-side CPU and memory bounding: Browser frame rate must remain steady at 60 FPS.
* Visual transient fidelity: Narrow 1-sample or 2-sample acoustic spikes must not be missed.
* True decoupling: Dropping display frames during browser lag must never drop audio samples from the background WAV recording.

## Considered Alternatives
1. **Full-Rate WebSocket Stream (48 kHz):** Overwhelms browser JSON parsing and canvas rendering.
2. **Subsampling (Decimation by Stride $K$):** Takes every $K$-th sample ($x[0], x[K], x[2K], \dots$).
   * *Critical Flaw:* High-frequency clicks and transient peaks that fall between sampled indices are completely lost (aliasing artifact).
3. **Boxcar / Moving Average:** Smooths out sharp peaks, artificially reducing visible signal dynamic range.
4. **Min/Max Peak-Preserving Decimation:** Partitions blocks into small buckets and extracts both the minimum and maximum sample in each bucket.

## Decision
Implemented **Peak-Preserving Min/Max Decimation** (`software/pcg_app/display_pipeline.py`):
* Incoming 512-sample blocks are compressed to $\le 600$ interleaved min/max points per frame.
* Pushed over WebSockets at $30\text{--}60\text{ Hz}$.
* Full-rate audio continues uninterrupted into the WAV recorder.

## Consequences & Trade-Offs
* **Positive:** 100% of transient acoustic peaks remain visible on screen; browser CPU utilization drops below 5%.
* **Negative:** Decimated vectors cannot be used directly for spectral Fourier math (spectral analysis is performed on the raw buffer in `pcg_core`).
