# W09 Module A: Feasibility Test — INMP441 Breadboard Integration & Transducer Feasibility

- **Week:** 9 (16–22 Kasım 2026)
- **Date of Lab Execution:** 18 Kasım 2026
- **Module:** A (Acquisition Hardware and Characterisation)
- **Owner:** Kaan
- **Status:** COMPLETED (Physical Wiring & Functional Sound Test) / ACOUSTIC CALIBRATION PENDING

## Objective

Assemble the INMP441 omnidirectional I²S MEMS microphone with the ESP32-S3 microcontroller on the laboratory breadboard, route the digital I²S audio lines (SCK, WS, SD), provide a clean 3.3V power connection, and evaluate mechanical transducer feasibility under controlled acoustic excitation.

## Inputs / Dependencies

- ESP32-S3-WROOM-1 N16R8 development board (provided by Ege).
- INMP441 MEMS microphone breakout board (circular PCB format).
- Breadboard and male-to-male jumper wires.
- Preliminary pin plan: `SCK -> GPIO4`, `WS -> GPIO5`, `SD -> GPIO6`, `L/R -> GND` (Left channel).
- Hand-off lab guide: `docs/handoff/START_HERE_2026-11-18.md`.

## Work Performed

1. **Breadboard Physical Wiring:**
   - Mounted the ESP32-S3 development board on the primary breadboard socket.
   - Positioned the circular INMP441 breakout module with its pin header securely seated.
   - Connected signal lines:
     - `SCK` (Bit Clock) connected to `GPIO4`.
     - `WS` (Word Select / LRCLK) connected to `GPIO5`.
     - `SD` (Serial Data) connected to `GPIO6`.
     - `L/R` (Channel select) tied to `GND` rail (Left channel data selection).
     - `VDD` tied to the ESP32-S3 3.3V rail.
     - `GND` tied to the common ground rail.
2. **Acoustic Transducer Functional Feasibility:**
   - Observed that the microphone picked up acoustic excitation (test tones played into the room).
   - A distinct spectral response difference of 23.2 dB (20–500 Hz) was captured between ambient quiet room noise and active stimulus.
   - Identified that high acoustic volume levels placed near the microphone drove the transducer close to full scale (peak 0.999982 FS), indicating high transducer sensitivity.

## Evidence

- **Laboratory Setup Photographs (Local Archive):**
  - `ilkentegrasyonolcumleri/images/lab_photo_esp32_top.jpg` (SHA256: `BD5E0C4AEB4090D257C5D31FC2AF18B79D10FE38F2C64D2A8FA6D5D13D0E0C58`) — ESP32-S3 top view on breadboard with USB-C connected and active power indicator.
  - `ilkentegrasyonolcumleri/images/lab_photo_inmp441_esp32_wiring_top.jpg` (SHA256: `408B16B6C5A11D3ECEE5B23DB0B47D43E4FA964B28F4A454E64C6E2F4679DE83`) — Top-down detail of INMP441 breakout pinout and jumper routing to ESP32-S3.
  - `ilkentegrasyonolcumleri/images/lab_photo_breadboard_angle.jpg` (SHA256: `AEBE1C8B00C7976634E4C54F766D936CD0343FB78624A3D6014798BADB27C2A7`) — Perspective view showing full breadboard integration.
- **Hardware Integration Manifests:**
  - `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json`
  - `experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md`

## Results

- **Wiring Feasibility:** **PASSED** — All I²S lines established reliable electrical contact with no loose jumper disconnections during the 40+ seconds of recording.
- **Acoustic Responsiveness:** **PASSED** — INMP441 successfully converted acoustic pressure waves into digital I²S samples.
- **Transducer Dynamic Range:** High volume acoustic stimulus caused ~0.2775% near-clipping (>0.98 FS). Subsequent measurements must calibrate sound source distance and volume.

## Open Decisions / Risks

1. **Acoustic Port Macro Photo:** The INMP441 is a bottom-port MEMS microphone. An underside macro photo showing the sound port opening and solder joint clearance is missing and remains an open documentation action item.
2. **Acoustic Phantom & Chamber Coupling:** Mechanical housing, acoustic chamber bell/diaphragm coupling, and acoustic phantom S1/S2 frequency response are not yet tested and remain PENDING for Week 10.
3. **dB SPL Calibration:** Absolute sensitivity calibration against a reference SPL meter has not been performed.

## Next Week Handoff

Hand off physical breadboard wiring configuration to Week 10 for acoustic phantom integration, silicone diaphragm coupling tests, and controlled SPL frequency response measurement.
