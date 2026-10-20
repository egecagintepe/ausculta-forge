# ADR-0006: Sampling Rate — Nominal 48.000 kHz Baseline
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module B (Ozan), Module C (Ege)  
**Technical Area:** Embedded Firmware & Digital Signal Processing

## Context & Problem Statement
The cardiac phonocardiogram contains dominant energy below 500 Hz. Standard biomedical literature often downsamples PCG to 1,000 Hz, 2,000 Hz, or 4,000 Hz. The team evaluated whether the microcontroller should sample at a low rate (e.g. 4 kHz) or operate at standard audio rates (44.1 kHz or 48.0 kHz).

## Decision Drivers
* Hardware I2S Master Clock Dividers: Hardware I2S PLLs on microcontrollers generate integer clock divisions easily for standard audio rates ($48\text{ kHz}, 44.1\text{ kHz}$). Generating odd rates like $4\text{ kHz}$ often introduces clock jitter.
* Sensor Compatibility: Many digital I2S MEMS microphones (including INMP441) specify an operational clock window ($f_{\text{SCK}} \in [1.024\text{ MHz}, 3.072\text{ MHz}]$), which requires $f_s \ge 16 \text{ kHz}$ or $f_s = 48 \text{ kHz}$ for standard 32-bit slot allocations.
* Oversampling benefits: Relaxing anti-aliasing constraints and lowering in-band quantization noise.

## Considered Alternatives
1. **Low-Rate Sampling (4,000 Hz):** Reduces USB bandwidth, but violates INMP441 hardware bit clock limits on standard DevKit configurations.
2. **44.1 kHz (CD Standard):** Valid, but requires fractional clock multipliers from standard 40 MHz ESP32 crystal oscillators, introducing minor phase jitter.
3. **48.000 kHz (Studio Standard):** Exact integer division of internal audio PLL; optimal for digital MEMS microphones.

## Decision
Established **48.000 kHz** as the authoritative continuous acquisition baseline across all modules:
* Bit clock: $f_{\text{SCK}} = 3.072 \text{ MHz}$.
* Word Select: $f_{\text{WS}} = 48 \text{ kHz}$.
* Downsampling to 1,000 Hz is executed in software exclusively inside research algorithms (Springer segmentation).

## Consequences & Trade-Offs
* **Positive:** Flawless I2S hardware compatibility; pristine 48x oversampling of cardiac frequencies.
* **Negative:** Host generates larger raw WAV files ($11.52 \text{ MB/hour}$ at 24-bit mono), which is easily absorbed by modern host PC storage.
