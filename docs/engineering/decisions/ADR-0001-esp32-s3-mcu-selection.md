# ADR-0001: Microcontroller Selection — ESP32-S3
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module B (Ozan), Module C (Ege)  
**Technical Area:** Embedded Hardware & Firmware

## Context & Problem Statement
The digital stethoscope prototype requires an embedded microcontroller capable of capturing 24-bit audio at 48,000 samples/s over an I2S master bus, double-buffering data via Direct Memory Access (DMA), and streaming continuous PCM data to a host PC over USB with minimal latency and zero sample drops.

## Decision Drivers
* Native hardware I2S master peripheral with DMA support.
* Integrated Native USB 2.0 Full-Speed PHY (eliminating external USB-UART converter bottlenecks).
* High-performance processing core with FPU and sufficient SRAM.
* Low cost and immediate availability from Turkish local distributors.

## Considered Alternatives
1. **STM32F401 / STM32F411 (Black Pill):** Excellent industrial audio support, but board cost is higher and Turkish distributor stock was inconsistent.
2. **Standard ESP32 (ESP32-WROOM-32):** Lacks native USB OTG PHY. Requires external CP2102/CH340 USB-UART bridge, which chokes and drops bytes at continuous high-throughput streaming ($> 1.5\text{ Mbps}$).
3. **Raspberry Pi Pico (RP2040):** Excellent dual Cortex-M0+ and PIO, but lacks integrated hardware I2S and hardware floating-point acceleration.

## Decision
Selected the **ESP32-S3-DevKitC-1-N16R8**:
* Dual-core Xtensa LX7 @ 240 MHz with single-precision FPU.
* Hardware I2S controller with linked-list DMA ping-pong buffering.
* Integrated on-chip USB OTG Full-Speed PHY (`GPIO 19/20`).
* 512 KB internal SRAM and 8 MB Octal PSRAM.

## Consequences & Trade-Offs
* **Positive:** Zero external USB bridge chip required; standard TinyUSB CDC-ACM stacks supported out of the box.
* **Negative:** Commercial DevKit clones vary widely in PCB layout; physical bench verification of dual USB port routing is mandatory upon delivery.
