# W05 Module C — Joint B→C Protocol Readiness Review (v01)

**Course:** EEE495 — Senior Design Project I  
**Week:** 05 Preflight — Sprint 1  
**Module:** C — Computer Application & Quality Assessment  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Review Target:** Ozan (Module B Owner) & Team Review  
**Status:** PROPOSED B→C INTERFACE CONTRACT / HOST PREFLIGHT REVIEW COMPLETE  
**Scope:** Host integration readiness and protocol proposal. No byte-level wire format is unilaterally frozen without Module B approval. No physical MCU measurements are claimed.

---

## 1. Executive Summary & Objective

This document prepares the joint embedded-to-host interface for the arrival of the real ESP32-S3 hardware in Week 05. The device-to-host physical transport was closed in **DW03-08** as **wired ESP32-S3 Native USB**. However, the byte-level wire layout, USB device class, packet framing, integer bit alignment, application CRC, and acquisition profile reconciliation remain open decisions under **DW03-09, DW03-10, and DW03-12**.

The objective of this review is to:
1. Provide Module C's concrete, defensible recommendations for all open B→C interface decisions.
2. Ensure the host application's packet ingestion engine is prepared for deterministic physical streaming.
3. Explicitly resolve the sensor profile discrepancy between the theoretical PUI DMM-4026 baseline and the purchased INMP441 MEMS breakout module.

---

## 2. Protocol Readiness Analysis

### 2.1 Transport Class: CDC-ACM vs. Vendor Bulk (DW03-12)

| Criterion | USB CDC-ACM (Virtual COM) | Vendor Bulk (Custom Endpoints via WinUSB / libusb) | Module C Assessment |
|---|---|---|---|
| **Host Driver Requirements** | Built-in OS support (Windows usbser.sys, Linux cdc_acm, macOS). Zero driver installation or INF signing needed. | Requires WinUSB installation via Zadig or custom INF on Windows. Potential driver conflicts during lab grading. | **CDC-ACM is strongly preferred for reliability across academic evaluator machines.** |
| **Python Ecosystem Support** | Supported natively via `pyserial` / `serial_asyncio`. Robust, mature, zero native C-extension compilation required. | Requires `pyusb` / `libusb-1.0.dll` bundled binaries and user-space access permissions. | **CDC-ACM minimizes host dependencies and runtime fragility.** |
| **Throughput Capability** | Native USB Full-Speed (12 Mbps) yields effective throughput > 800 kB/s. 48 kHz mono 24-in-32 requires 192 kB/s (~24% of bus limit). CDC virtual baud rate is ignored by Native USB stack. | Bulk endpoints can utilize available bus bandwidth with slightly lower packet framing overhead (~1–2%). | **Both classes easily satisfy the 192 kB/s payload requirement with >3× headroom.** |
| **Framing & Packetization** | Byte-stream transport. Requires explicit application-level sync framing / delimiters to recover frame boundaries. | USB transfer blocks provide packet boundary hints, but application framing is still required for multi-packet transfers. | **Application framing is required in either class; CDC-ACM has no inherent disadvantage.** |
| **Resynchronization on Loss** | Sync-word search in ring buffer recovers alignment immediately after dropped or corrupt bytes. | Bulk packet boundaries can desynchronize if transfer sizes do not match application frame sizes. | **CDC-ACM stream parser with sync word is simple, robust, and verifiable.** |

**Module C Recommendation:** Adopt **CDC-ACM** as the Hardware Rev-A physical baseline. It provides frictionless cross-platform connectivity without custom driver installation while easily providing the required 192 kB/s bandwidth.

---

### 2.2 Protocol Versioning & Message Types

To prevent silent misinterpretation of wire bytes, all communications must begin with an explicit message type header.

#### Proposed Message Types:
- `0x01` — `DATA_FRAME`: Streaming acoustic sample payload from MCU to PC.
- `0x02` — `HANDSHAKE_ANNOUNCE`: MCU advertises device ID, firmware SHA, and hardware capabilities.
- `0x03` — `HANDSHAKE_ACCEPT`: Host validates compatibility and confirms active profile & negotiated block size.
- `0x04` — `CMD_STREAM_START`: Host instructs MCU to commence DMA acquisition and USB packet transmission.
- `0x05` — `CMD_STREAM_STOP`: Host instructs MCU to halt DMA/USB streaming cleanly.
- `0x06` — `TELEMETRY_STATUS`: MCU reports internal health (DMA overruns, buffer depth, rail status).
- `0xFF` — `ERROR_REPORT`: Fatal error or invalid state notification.

The protocol version field must be a 1-byte integer (`0x01` for Version 1.0). If the host receives an unknown protocol version, it rejects the handshake and enters `DeviceState.INCOMPATIBLE`.

---

### 2.3 Frame Boundaries, Header Length, and Payload Layout

To achieve deterministic byte synchronization over CDC-ACM, frames must use a fixed-width header preceded by a magic sync pattern:

```
+-----------------------------------------------------------------------------------+
| Magic (2B) | Ver (1B) | Type (1B) | Seq (4B) | Timestamp (4B) | Samples (2B) | Flags (2B) | Payload (N bytes) | CRC-16 (2B) |
+-----------------------------------------------------------------------------------+
```

- **Magic Word:** `0xAA, 0x55` (2 bytes) — High-entropy preamble for rapid frame boundary detection.
- **Protocol Version:** `0x01` (1 byte).
- **Message Type:** `0x01` (`DATA_FRAME`, 1 byte).
- **Sequence Number:** 32-bit unsigned integer (4 bytes, little-endian).
- **Device Timestamp:** 32-bit microsecond counter (`esp_timer_get_time() & 0xFFFFFFFF`, 4 bytes, little-endian).
- **Sample Count ($N_{samples}$):** 16-bit unsigned integer (2 bytes, little-endian, e.g. `512`).
- **Hardware Status Flags:** 16-bit bitmask (2 bytes, little-endian).
  - Bit 0: DMA buffer overrun detected.
  - Bit 1: I2S FIFO overrun / clock synchronization fault.
  - Bit 2: Reserved / clipping indicator.
- **Sample Payload:** $N_{samples} \times 4$ bytes (for 32-bit container) or $N_{samples} \times 3$ bytes (for packed 24-bit). For 512 samples in 32-bit container: 2048 bytes.
- **Trailing CRC:** 16-bit CRC-CCITT (2 bytes, little-endian) computed over Header + Payload.

Total frame overhead: 16 bytes header + 2 bytes CRC = 18 bytes.  
At 512 samples per frame (93.75 frames/second), protocol overhead is $93.75 \times 18 \approx 1,688 \text{ bytes/s}$ (< 0.9% overhead).

---

### 2.4 Signed Integer Encoding, Container Width, and Endianness (DW03-10)

- **Numeric Representation:** Two's-complement signed integer (`signed_pcm`).
- **Endianness:** Strictly **Little-Endian** (`<i4` for 32-bit containers), matching both the ESP32-S3 architecture and x86/ARM host architectures.
- **Meaningful Bits:** 24 bits.
- **Container Width:** 32-bit slot width ($4 \text{ bytes/sample}$).
- **Bit Alignment within Container:**
  - **Proposed Standard:** Meaningful 24-bit data word is **LSB-aligned with sign extension** into bits [31:24], representing a legal signed integer in $[-8,388,608, +8,388,607]$.
  - **Alternative (MSB-aligned / Left-justified):** Meaningful data in bits [31:8], lower 8 bits zeroed. If Module B's I2S DMA produces MSB-aligned words, this must be declared in capabilities so the host normalizes by $2^{31}$ rather than $2^{23}$.
  - **Requirement:** Module B must specify whether DMA output is LSB-aligned with sign-extension or MSB-aligned with trailing zero-fill before byte parsing is implemented.

---

### 2.5 Sequence Tracking vs. First-Sample Index

- Host telemetry requires monotonic sample accounting to detect packet drops and buffer slips.
- Module C accepts either a **frame sequence counter** (incrementing by 1 per frame) or a **cumulative sample index** (incrementing by $N_{samples}$ per frame).
- **Module C Proposal:** Transmit **Frame Sequence Number** (`uint32`) in the primary header. Because $N_{samples}$ is fixed (512) or declared in each frame header, the cumulative sample index is computable deterministically:
  $$\text{Sample Index} = \text{Sequence} \times N_{samples}$$
- Rollover occurs at $2^{32}-1$ (approx. 530 days of continuous streaming at 93.75 fps), which is practically infinite for single-session PCG acquisitions.

---

### 2.6 Device Timestamp and Timebase

- The timestamp must originate from the **ESP32-S3 hardware monotonic clock** (`esp_timer_get_time()`, microsecond resolution).
- It must represent the acquisition start of the first sample in the payload block.
- The host records both the hardware timestamp and host arrival time, but never substitutes host wall-clock time for hardware timestamps.
- Telemetry monitors timestamp monotonicity; negative jumps indicate MCU timer rollover or firmware scheduling jitter.

---

### 2.7 Application CRC Policy (DW03-09)

- While USB physical packets contain hardware-level CRC (CRC5 for tokens, CRC16 for data packets), USB hardware CRC only protects data across the physical bus wires.
- **Risks not covered by USB hardware CRC:**
  1. ESP32-S3 DMA memory corruption or FIFO ring buffer contention.
  2. USB CDC driver partial packet read / fragmentation across OS buffer boundaries.
  3. Firmware buffer overwrite prior to USB endpoint staging.
- **Module C Recommendation:** Implement **CRC-16-CCITT** (`0x1021`, initial `0xFFFF`) over the 16-byte header and payload.
- On modern ESP32-S3 hardware (240 MHz dual-core), computing CRC-16 over a 2048-byte buffer takes < 15 microseconds, representing < 0.15% CPU load.
- Corrupt CRC packets are dropped immediately: no corrupted samples reach the DSP pipeline or recorded WAV file, and `crc_failures` counter increments truthfully.

---

### 2.8 Handshake and Streaming Lifecycle

1. **Host Opening:** Host detects CDC-ACM COM port and opens connection. State: `OPENING`.
2. **Capabilities Discovery:** Host issues `0x02` or MCU announces `DeviceCapabilities` upon port DTR assertion. State: `HANDSHAKING`.
3. **Compatibility Validation:** Host verifies protocol version, sample rate (48000 Hz), channels (1), and container format. State transitions to `READY`.
4. **Streaming Command:** Host transmits `0x04` (`CMD_STREAM_START`). MCU acknowledges and begins streaming frames. State: `STREAMING`.
5. **Clean Termination:** Host transmits `0x05` (`CMD_STREAM_STOP`). MCU halts transmission. State: `READY`.
6. **Physical Disconnect:** If USB cable is dislodged, host transitions immediately to `INTERRUPTED`. Any active recording is cleanly finalized with `termination_reason='device_disconnected'`.

---

### 2.9 Disconnect, Buffer Overflow, and Parser Recovery

- **Parser Recovery State Machine:**
  1. `SEARCH_SYNC`: Scan byte stream for magic pattern `[0xAA, 0x55]`.
  2. `READ_HEADER`: Accumulate fixed 16-byte header. Check protocol version and payload length ($N \le 2048$). If invalid, increment `malformed_frames` and return to `SEARCH_SYNC`.
  3. `READ_PAYLOAD`: Accumulate $N_{bytes} + 2$ (payload + CRC).
  4. `VERIFY_CRC`: Compute CRC-16. If mismatch, increment `crc_failures`, drop frame, and return to `SEARCH_SYNC`.
  5. `DISPATCH`: Construct `DeviceSamplePacket` and emit to push ingestion pipeline.
- **Buffer Overflow Visibility:** If MCU encounters DMA starvation or USB endpoint backpressure, it asserts Bit 0 in `Flags`. Host logs this in `DeviceIntegrityStats` rather than silently dropping samples.

---

## 3. Sensor Profile Reconciliation: PUI DMM-4026 vs. INMP441

### 3.1 The Procurement Discrepancy

- The current software baseline acquisition profile in `device_runtime.py` is configured as:
  ```python
  profile_id = "rev_a_pui_dmm4026"
  preferred_sample_rate_hz = 48000
  channels = 1
  sample_container_bits = 32
  meaningful_data_bits = 24
  sample_encoding = "signed_pcm"
  description = "Hardware Rev-A baseline (PUI DMM-4026-B-I2S-R: 48 kHz mono 24-in-32 signed PCM)"
  ```
- However, as documented in Week 03/04 sourcing reviews, the PUI DMM-4026-B-I2S-EB-R evaluation board exhibited standard manufacturer lead times of 22 weeks and stock risks at European distributors. An **INMP441 breakout module** was procured for early bench experimentation.

### 3.2 Key Differences Requiring Verification

| Parameter | PUI DMM-4026-B-I2S-R | INMP441 Breakout Module | Engineering Impact |
|---|---|---|---|
| **Acoustic Dynamic Range / SNR** | 64 dBA SNR; -26 dB sensitivity | 61 dBA SNR; -26 dBFS sensitivity | Acoustic precision differs by ~3 dB; sensor physics dictate usable PCG dynamic range. |
| **Low-Frequency Cutoff (-3 dB)** | Listed 20 Hz – 20 kHz; typical curve extends to 20 Hz. | Flat response begins at 60 Hz; high-pass corner typically 60 Hz. | Sub-50 Hz heart sound components (S1/S2 fundamentals) may suffer attenuation on INMP441. |
| **I2S Bit Alignment** | 24 bits in 32-bit slot, MSB first, standard I2S. | 24 bits in 32-bit slot, MSB first, standard I2S. Lower 8 bits zeroed. | **Identical bus framing**, but bit positioning inside the 32-bit DMA word depends on ESP32-S3 I2S driver configuration. |
| **Supply Voltage & Logic Levels** | 1.8 V nominal (3.6 V max); 3.3 V operation required vendor confirmation. | 3.3 V tolerant on VDD and I2S IO lines. | INMP441 breakout is simpler to wire directly to DevKit 3.3 V rail. |

### 3.3 Engineering Policy on Profile Updates

> **CRITICAL RULE:** Do NOT silently alter or overwrite `REV_A_BASELINE_PROFILE` in `device_runtime.py`.

Before any profile modifications are made:
1. **Manufacturer / Module B Evidence Required:**
   - Module B must inspect the received INMP441 breakout board and supply the exact I2S driver configuration (e.g. `i2s_channel_fmt_t`, slot width, bit order).
   - Module B must confirm whether DMA buffer integers are MSB-aligned or LSB-aligned with sign-extension.
2. **Explicit Profile Addition:**
   - If differences exist, define an explicit secondary profile:
     ```python
     INMP441_BENCH_PROFILE = AcquisitionProfile(
         profile_id="bench_inmp441_breakout",
         preferred_sample_rate_hz=48000,
         channels=1,
         sample_container_bits=32,
         meaningful_data_bits=24,
         sample_encoding="signed_pcm",
         description="Bench validation profile: INMP441 MEMS breakout (48 kHz mono 24-in-32 signed PCM)",
     )
     ```
   - Retain `REV_A_BASELINE_PROFILE` as the reference architectural standard until team review approves a formal profile migration.

---

## 4. Summary of Action Items for Week 05 Handshake

1. **Module B (Ozan):**
   - Confirm adoption of CDC-ACM transport class.
   - Confirm frame header structure (16 bytes) and sync magic word (`0xAA, 0x55`).
   - Confirm sample bit alignment in DMA buffers (LSB-aligned vs MSB-aligned).
   - Implement CRC-16-CCITT or propose alternative checksum.
   - Flash synthetic 100 Hz sine / counter generator for initial bench bringup.

2. **Module C (Ege):**
   - Implement byte-level CDC-ACM serial decoder matching agreed framing upon Module B sign-off.
   - Execute C-W05-01 through C-W05-08 live on bench when ESP32-S3 arrives.
   - Retain all WAV and JSON artifacts under `experiments/sessions/` with Git SHA provenance.
