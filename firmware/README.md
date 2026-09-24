# AuscultaForge — Firmware Directory

This directory contains the embedded software running on the microcontroller (MCU).

## Scope & Responsibility
- **Owner:** Kaan
- **Hardware Target:** Candidate: ESP32 family (provisional; final selection subject to evaluation)
- **Key Responsibilities:**
  - Sensor/transducer interface (e.g. I2S digital audio or ADC sampling depending on microphone selection)
  - DMA / ring buffer management and framing
  - Serial/USB communication driver for PC streaming
  - Status monitoring, packet sequence counters, and transmission health
