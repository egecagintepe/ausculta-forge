# AuscultaForge — ESP32-S3 Experimental Bring-Up Bench Example

**Course:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Module:** C (Computer Application & Quality Assessment)  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Interface Reviewer:** Ozan (Module B Owner)  
**Location:** `tools/esp32_bench_example/`  
**Target Hardware:** ESP32-S3-DevKitC-1 (N16R8: 16 MB Octal Flash, 8 MB Octal PSRAM)  
**Execution Status:** **UNVERIFIED / NOT EXECUTED ON HARDWARE** (Local ESP-IDF SDK not installed on host; physical hardware pending delivery)

---

## 1. Ownership & Architectural Boundary Notice

> [!IMPORTANT]
> **CROSS-MODULE COLLABORATION & HARDWARE READINESS NOTICE:**
> 1. This directory contains an isolated, non-production reference example prepared by Module C to explore synthetic bring-up patterns.
> 2. It is **NOT** a replacement for Module B's production firmware under `firmware/`. Ozan (Module B) retains sole ownership and decision authority over the production embedded firmware codebase.
> 3. No final USB wire framing (magic words, sequence headers, CRC-16) or integer bit alignment (LSB vs MSB) is finalized or advertised here. That remains **UNAPPROVED** and subject to joint approval under **DW03-09** and **DW03-12**.
> 4. Cross-compilation and physical flashing were **NOT EXECUTED** on this workstation because ESP-IDF is not locally installed and the physical MCU board is in transit.
> 5. **DirencNet Board Verification Required:** The purchased DirencNet N16R8 module must be physically verified upon arrival (checking whether it is a true dual-USB DevKitC-1 with native OTG USB port wired out or a single-port / CH340 variant) before assuming dual-USB enumeration.
> 6. **48 kHz Sampling Timing Limitation:** `512 samples + vTaskDelay(11 ms)` in software task loop is an approximation and DOES NOT guarantee a strict 48.000 kHz sampling rate due to FreeRTOS tick jitter. Production hardware sampling MUST be governed by I2S DMA interrupts.
> 7. **Backpressure & Queue Writes:** USB CDC-ACM writes must handle short writes, backpressure, and track dropped bytes.

---

## 2. Features Demonstrated

- **Deterministic 100 Hz Integer Sine Table:** Uses a 480-point fixed-point integer sine lookup table ($48,000 \text{ Hz} / 100 \text{ Hz} = 480 \text{ samples/period}$) scaled to 24-bit half-scale ($+4,194,304$).
- **FreeRTOS Real-Time Task:** Delivers 512-sample blocks every $\approx 10.67 \text{ ms}$ ($\approx 93.75 \text{ blocks/s}$).
- **TinyUSB CDC-ACM Integration:** Connects to the ESP32-S3 internal USB-OTG full-speed PHY. Host sees a standard virtual serial COM port without requiring custom driver installation.
- **DTR Line State Gating:** Streams only when the host PC application asserts Data Terminal Ready (DTR) by opening the port.

---

## 3. Hardware Configuration & Known Pinouts

| Function | Pin Name | Default ESP32-S3 GPIO | Notes |
|---|---|---|---|
| **USB D- (Data Negative)** | `USB_DM` | `GPIO 19` | Dedicated Native USB OTG PHY pin |
| **USB D+ (Data Positive)** | `USB_DP` | `GPIO 20` | Dedicated Native USB OTG PHY pin |
| **I2S BCLK (Bit Clock)** | `INMP441_SCK` | *Pending Module B declaration* | E.g. `GPIO 4` |
| **I2S WS (Word Select)** | `INMP441_WS` | *Pending Module B declaration* | E.g. `GPIO 5` |
| **I2S DIN (Data Input)** | `INMP441_SD` | *Pending Module B declaration* | E.g. `GPIO 6` |
| **I2S L/R (Channel Select)** | `INMP441_LR` | `GND` | Grounded for Left Channel data |
| **Power Supply** | `VDD` | `3.3V` | Direct 3.3V rail from DevKit regulator |

---

## 4. How to Build & Flash with ESP-IDF v5.x (When Hardware Arrives)

When Ozan / Module B integrates this reference into the development bench:

```bash
# 1. Set target to ESP32-S3
idf.py set-target esp32s3

# 2. Build project
idf.py build

# 3. Flash to ESP32-S3 (Connect to UART/COM port for flashing)
idf.py -p COMx flash monitor

# 4. Connect second USB cable to the Native "USB" port for PC host streaming
```
