# ADR-0005: Procurement Substitution — INMP441 Selected Over PUI Audio
**Status:** `ACCEPTED`  
**Date:** 2026-10-16  
**Deciders:** Module B (Ozan), Module A (Kaan)  
**Technical Area:** Procurement, BOM & Hardware Sourcing

## Context & Problem Statement
During initial design planning (Weeks 02–03), the team specified high-grade PUI Audio MEMS microphones (e.g. DMM-4026) based on published biomedical acoustic research. However, upon placing the official component purchase order in Week 04 (PR #28), procurement constraints required an immediate engineering pivot.

## Decision Drivers
* Local distributor stock: Components had to be available for immediate purchase from Turkish distributors (DirencNet, Robotistan, Özdisan) to meet Academic Week 05 bench bring-up deadlines.
* Avoidance of customs importation delays: Ordering from international distributors (DigiKey, Mouser) carried high shipping costs, import duties, and unpredictable 3–5 week delivery windows.
* Breadboard prototyping: SMT bare-die components require custom PCB breakout manufacturing, which was unnecessary for the initial bench gate.

## Considered Alternatives
1. **PUI Audio DMM-4026 (Original Choice):** High performance, but completely out-of-stock in Turkey.
2. **Analog ECM Capsules (In-Stock):** Readily available, but required extensive analog pre-amp circuitry.
3. **INMP441 I2S MEMS Breakout Module:** Readily available in stock at DirencNet; comes mounted on a 6-pin 0.1" header breakout board.

## Decision
Formally substituted PUI Audio with the **INMP441 I2S MEMS breakout board** purchased from DirencNet:
* Verified that the INMP441 pinout, 24-bit resolution, and standard I2S protocol fulfill all functional acoustic requirements for phantom phonocardiography ($20\text{--}500\text{ Hz}$).

## Consequences & Trade-Offs
* **Positive:** Components delivered immediately; pre-soldered 0.1" header allows rapid breadboard wiring.
* **Negative:** Acoustic SNR is 61 dBA (slightly lower than the 68 dBA offered by high-end PUI industrial sensors, but entirely adequate for bench testing).
