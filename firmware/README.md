# AuscultaForge — Firmware Directory

This directory contains the embedded software running on the microcontroller (MCU).

## Scope & Responsibility
- **Owner:** Kaan
- **Hardware Target:** ESP32 / MCU platform
- **Key Responsibilities:**
  - Microphone interface (e.g. I2S digital audio or ADC sampling)
  - DMA buffer management and sample packaging
  - Serial/USB communication driver for PC streaming
  - Status monitoring, packet sequence counters, and transmission health
