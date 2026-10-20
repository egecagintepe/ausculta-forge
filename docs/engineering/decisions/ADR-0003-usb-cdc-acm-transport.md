# ADR-0003: USB Transport Class — CDC-ACM Device Selection
**Status:** `ACCEPTED`  
**Date:** 2026-10-17  
**Deciders:** Module B (Ozan), Module C (Ege)  
**Technical Area:** USB Device Architecture & Host Ingestion

## Context & Problem Statement
When implementing USB communication between the ESP32-S3 and the host PC, the firmware must expose a standard USB device class. The team evaluated USB Audio Class (UAC 1.0/2.0), Custom Vendor Bulk Transfer (WinUSB/libusb), and Communication Device Class (CDC-ACM).

## Decision Drivers
* Host driver compatibility: Must work seamlessly on modern Windows 10/11 machines without requiring custom INF files or driver signing overrides.
* Software accessibility: Must be readable via standard Python libraries (`pyserial`).
* Metadata flexibility: The stream requires interleaving binary PCM samples with packet sequence numbers, timestamps, and error flags.

## Considered Alternatives
1. **USB Audio Class (UAC 1.0 / 2.0):**
   * Recognizable as a native sound card input in Windows.
   * *Critical Flaw:* Windows audio stack imposes automatic resampling, dynamic range compression, and volume controls, corrupting raw scientific integer words. Furthermore, UAC cannot easily carry custom telemetry (packet drop counters and hardware flags).
2. **Custom Vendor Bulk Transfer (WinUSB / libusb):**
   * High performance, but requires users to install custom WinUSB driver overrides using Zadig, which is prohibited in many institutional lab environments.
3. **USB CDC-ACM (Virtual COM Port):**
   * Uses standard Microsoft in-box driver `usbser.sys`.
   * Appears as a standard serial port (`COMx`).
   * Provides direct access to raw bytes without OS audio filtering or sample rate conversion.

## Decision
Selected **USB CDC-ACM (Abstract Control Model)**:
* Firmware implements TinyUSB CDC-ACM stack.
* Host connects via standard `pyserial.Serial` in Python.

## Consequences & Trade-Offs
* **Positive:** Zero third-party driver dependencies; full control over binary packet framing and metadata.
* **Negative:** Host software must implement its own packet framing and synchronization layer.
