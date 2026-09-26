# AuscultaForge — Firmware Directory

This directory contains the embedded software running on the microcontroller (MCU).

## Scope & Responsibility
- **Owner:** Ege
- **Hardware Target:** ESP32-S3-WROOM development board (finalized Phase-1 platform)
- **Key Responsibilities:**
  - I2S MEMS microphone acquisition (DMA double-buffering) at target ~4 kHz
  - Hardware transport: Wired Native USB (ESP32-S3 USB OTG / TinyUSB)
  - Packet framing, sequence counting, timestamping, and CRC generation
  - Status monitoring, packet loss indicators, and hardware health flags
