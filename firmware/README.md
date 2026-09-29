# Firmware Directory
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Senior Design Project — Module B
Software / Platform Codename: `AuscultaForge`

This directory contains the embedded software running on the microcontroller unit (MCU).

---

## Scope & Responsibility
- **Primary Module Owner:** Ozan (Module B — Embedded Acquisition & Data Path)
- **Hardware Target:** ESP32-S3 development board (Native USB exposed)
- **Key Responsibilities:**
  - Transducer acquisition interface (ADC / I2S with DMA double-buffering) at nominal 48 kHz continuous baseline
  - Hardware transport: Wired Native USB (ESP32-S3 USB OTG / TinyUSB)
  - Monotonic sample continuity counter, timestamping, status flags, and CRC integrity generation
  - Hardware overflow detection (DMA FIFO overrun flags) and stream lifecycle management
