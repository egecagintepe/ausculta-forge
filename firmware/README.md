# Firmware Directory
## Smart Digital Stethoscope — Module B
## EEE495 / EEE496 — AuscultaForge

This directory is the target for firmware running on the purchased ESP32-S3 N16R8 development board. As of Week 4, firmware implementation and physical G1 bring-up have not yet been recorded.

## Current purchased hardware baseline

- Seller / model: Direnc.net “ESP32 S3 N16R8 WiFi Bluetooth Board”, code DSTK22852, quantity 2.
- Module designation in seller listing: ESP32-S3-WROOM-1-N16R8.
- Digital mic candidate ordered: INMP441 I²S breakout ×3.
- PUI DMM-4026-B-I2S-EB-R was not purchased.
- The exact board PCB revision, physical header map and USB-C connector-to-controller routing still require inspection / matching schematic.

## Planned responsibilities

- Nominal 48 kHz mono acquisition profile.
- INMP441 standard I²S capture, 24-bit two's-complement words, correct slot/bit alignment and sign extension.
- DMA-driven acquisition and bounded buffering; no blocking USB write in an I²S ISR callback.
- Device-side frame sequence, cumulative sample index, monotonic timestamp, status/error counters.
- Wired USB device-to-host synthetic stream for G1, independent of the microphone and ECM ADC path.

## Decisions kept open

- USB interface: CDC-ACM is the rapid-prototyping candidate; Vendor Bulk remains open for joint Module B / C decision. First identify the actual board connector/controller.
- B→C header/sample wire format and status flags remain a proposal until jointly approved.
- CRC/checksum / application integrity policy is OPEN.
- ECM ADC1 versus advisor-approved external I²S ADC remains OPEN and does not block synthetic G1.
- GPIO4/5/6 are proposed I²S assignments only; verify actual header mapping. GPIO35–GPIO37 are reserved by octal PSRAM on the N16R8 module. SoC USB D−/D+ map to GPIO19/GPIO20, but this alone does not establish the physical USB connector route.

See [Week-4 embedded requirements](../docs/sdp/week-04/submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md), [B→C protocol proposal](../docs/sdp/week-04/submissions/module-b-ozan/W04_B_to_C_protocol-proposal_v01.md) and [Week-5 G1 plan](../docs/sdp/week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md).

No firmware build, physical USB enumeration, microphone capture, throughput result or G1 pass is claimed in this README.
