# ADR-0004: Acoustic Transducer Selection — Digital I2S MEMS vs. Analogue ECM
**Status:** `ACCEPTED`  
**Date:** 2026-10-06  
**Deciders:** Module A (Kaan), Module B (Ozan)  
**Technical Area:** Acoustic Transducers & Front-End Electronics

## Context & Problem Statement
Module A evaluated acoustic transducer candidates to capture faint heart sounds ($20\text{--}500\text{ Hz}$) from the chestpiece cavity. The two leading candidates were traditional Electret Condenser Microphones (ECM) and Digital MEMS Microphones.

## Decision Drivers
* Immunity to 50 Hz power mains electromagnetic pickup on prototype breadboards.
* Minimization of discrete analog component count (op-amps, precision resistors, capacitors).
* Transducer dynamic range and low-frequency sensitivity down to $20\text{ Hz}$.

## Considered Alternatives
1. **Electret Condenser Microphone (ECM) + Analogue Front-End:**
   * Requires JFET biasing resistor, DC-blocking capacitors, and multi-stage active operational amplifier filtering (e.g. Sallen-Key low-pass and high-pass filters).
   * High-impedance analog traces on solderless breadboards act as antennae, picking up massive 50 Hz mains hum and RF hash from the microcontroller switching regulators.
2. **Digital I2S MEMS Microphone (INMP441):**
   * Integrates acoustic diaphragm, low-noise pre-amp, and 24-bit $\Sigma\Delta$ ADC directly inside a shielded silicon package.
   * Outputs digitized PCM words over standard 3-wire digital I2S (`SCK`, `WS`, `SD`), completely eliminating breadboard analog noise.

## Decision
Selected **Digital I2S MEMS Microphone** as the primary system baseline:
* The ECM path is preserved as a secondary comparative study in `hardware/` to fulfill the course requirement of evaluating $\ge 2$ transducer technologies.

## Consequences & Trade-Offs
* **Positive:** Superior SNR ($61\text{ dBA}$); zero analog noise pickup on breadboard.
* **Negative:** Bottom-port MEMS requires careful mechanical acoustic coupling into the chestpiece chamber to prevent air acoustic leaks.
