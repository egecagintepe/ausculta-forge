# W05 Module C — Joint B→C Protocol Readiness Review (v01)

**Course:** EEE495 — Senior Design Project I  
**Week:** 05 Preflight — Sprint 1  
**Module:** C — Computer Application & Quality Assessment  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Review Target:** Ozan (Module B Owner) & Team Review  
**Status:** PROPOSED / NOT APPROVED (Awaiting joint review and sign-off by Ozan / Module B and Ege / Module C)  
**Scope:** Host integration readiness and protocol recommendations. No byte-level wire format is finalized or frozen without joint approval. No physical MCU measurements are claimed.

> [!WARNING]
> **CRITICAL DECISION BOUNDARY:**  
> All transport options, frame headers, sync magic words (`0xAA55`), sequence widths, timestamp units, and CRC algorithms described in this document are **PROPOSED / NOT APPROVED**. None of these are final B→C decisions until Ozan (Module B) and Ege (Module C) jointly approve them.  
> **Do not implement a production decoder against this unapproved layout.**

---

## 1. Executive Summary & Objective

This document prepares the joint embedded-to-host interface review for Week 05. The device-to-host physical transport medium was closed in **DW03-08** as **wired ESP32-S3 Native USB**. However, the byte-level wire layout, USB device class, packet framing, integer bit alignment, application CRC, and acquisition profile reconciliation remain open decisions under **DW03-09, DW03-10, and DW03-12**.

The objective of this review is to:
1. Provide Module C's concrete, defensible recommendations for all open B→C interface decisions.
2. Outline an illustrative packet framing concept to guide firmware development without prematurely freezing byte-level offsets.
3. Explicitly resolve the sensor profile discrepancy between the theoretical PUI DMM-4026 baseline and the purchased INMP441 MEMS breakout module.

---

## 2. Protocol Readiness Analysis

### 2.1 Transport Class: CDC-ACM vs. Vendor Bulk (DW03-12 — PROPOSED / NOT APPROVED)

| Criterion | USB CDC-ACM (Virtual COM) — *Proposed* | Vendor Bulk (Custom Endpoints via WinUSB / libusb) | Module C Assessment |
|---|---|---|---|
| **Host Driver Requirements** | Built-in OS support (Windows usbser.sys, Linux cdc_acm, macOS). Zero driver installation or INF signing needed. | Requires WinUSB installation via Zadig or custom INF on Windows. Potential driver conflicts during lab grading. | **CDC-ACM is strongly preferred for reliability across academic evaluator machines.** |
| **Python Ecosystem Support** | Supported natively via `pyserial` / `serial_asyncio`. Robust, mature, zero native C-extension compilation required. | Requires `pyusb` / `libusb-1.0.dll` bundled binaries and user-space access permissions. | **CDC-ACM minimizes host dependencies and runtime fragility.** |
| **Throughput Capability** | Native USB Full-Speed (12 Mbps) yields effective throughput > 800 kB/s. 48 kHz mono 24-in-32 requires 192 kB/s (~24% of bus limit). CDC virtual baud rate is ignored by Native USB stack. | Bulk endpoints can utilize available bus bandwidth with slightly lower packet framing overhead (~1–2%). | **Both classes easily satisfy the 192 kB/s payload requirement with >3× headroom.** |
| **Framing & Packetization** | Byte-stream transport. Requires explicit application-level sync framing / delimiters to recover frame boundaries. | USB transfer blocks provide packet boundary hints, but application framing is still required for multi-packet transfers. | **Application framing is required in either class; CDC-ACM has no inherent disadvantage.** |
| **Resynchronization on Loss** | Sync-word search in ring buffer recovers alignment immediately after dropped or corrupt bytes. | Bulk packet boundaries can desynchronize if transfer sizes do not match application frame sizes. | **CDC-ACM stream parser with sync word is simple, robust, and verifiable.** |

**Module C Position (Proposed / Not Approved):** Recommend **CDC-ACM** as the Hardware Rev-A physical baseline. It provides frictionless cross-platform connectivity without custom driver installation while easily providing the required 192 kB/s bandwidth. This recommendation remains subject to Module B evaluation.

---

### 2.2 Protocol Versioning & Message Types (PROPOSED / NOT APPROVED)

To prevent silent misinterpretation of wire bytes, all communications must begin with an explicit message type header.

#### Proposed Conceptual Message Types:
- `0x01` — `DATA_FRAME`: Streaming acoustic sample payload from MCU to PC.
- `0x02` — `HANDSHAKE_ANNOUNCE`: MCU advertises device ID, firmware SHA, and hardware capabilities.
- `0x03` — `HANDSHAKE_ACCEPT`: Host validates compatibility and confirms active profile & negotiated block size.
- `0x04` — `CMD_STREAM_START`: Host instructs MCU to commence DMA acquisition and USB packet transmission.
- `0x05` — `CMD_STREAM_STOP`: Host instructs MCU to halt DMA/USB streaming cleanly.
- `0x06` — `TELEMETRY_STATUS`: MCU reports internal health (DMA overruns, buffer depth, rail status).
- `0xFF` — `ERROR_REPORT`: Fatal error or invalid state notification.

The protocol version field is proposed as a 1-byte integer (`0x01` for Version 1.0). If the host receives an unknown protocol version, it rejects the handshake and enters `DeviceState.INCOMPATIBLE`.

---

### 2.3 Illustrative Frame Concept & Header Layout (ILLUSTRATIVE ONLY / NOT APPROVED)

> [!NOTE]
> The layout below is an **illustrative concept** to verify field requirements and length math. It is **NOT** a frozen byte-level wire contract. Offsets, packing pragmas (`#pragma pack(1)`), alignment, and delimiter choices must be jointly agreed with Module B.

```
+-----------------------------------------------------------------------------------+
| Magic (2B) | Ver (1B) | Type (1B) | Seq (4B) | Timestamp (4B) | Samples (2B) | Flags (2B) | Payload (N bytes) | CRC-16 (2B) |
+-----------------------------------------------------------------------------------+
```

#### Illustrative Header Field Breakdown:
- **Magic Word:** `0xAA, 0x55` (2 bytes, offset 0) — Proposed synchronization preamble for frame boundary recovery.
- **Protocol Version:** `0x01` (1 byte, offset 2) — Proposed protocol version identifier.
- **Message Type:** `0x01` (`DATA_FRAME`, 1 byte, offset 3) — Proposed message discriminator.
- **Sequence Number:** 32-bit unsigned integer (4 bytes, offset 4, little-endian) — Proposed frame counter.
- **Device Timestamp:** 32-bit microsecond counter (4 bytes, offset 8, little-endian) — Proposed hardware acquisition time.
- **Sample Count ($N_{samples}$):** 16-bit unsigned integer (2 bytes, offset 12, little-endian, e.g. `512`).
- **Hardware Status Flags:** 16-bit bitmask (2 bytes, offset 14, little-endian).
  - Bit 0: DMA buffer overrun detected.
  - Bit 1: I2S FIFO overrun / clock synchronization fault.
  - Bit 2: Reserved / clipping indicator.
- **Sample Payload:** $N_{samples} \times 4$ bytes (for 32-bit container) or $N_{samples} \times 3$ bytes (for packed 24-bit). For 512 samples in 32-bit container: 2048 bytes.
- **Trailing CRC:** Proposed 16-bit CRC (2 bytes, little-endian) placed at frame end.

**Internal Consistency Check:**  
$2 \text{ (Magic)} + 1 \text{ (Ver)} + 1 \text{ (Type)} + 4 \text{ (Seq)} + 4 \text{ (Timestamp)} + 2 \text{ (Samples)} + 2 \text{ (Flags)} = 16 \text{ bytes header}$.  
While the arithmetic sums cleanly to 16 bytes, compiler structure padding on 32-bit architectures may insert alignment bytes unless packed explicitly. This confirms it is an **illustrative concept only** and requires exact C-struct alignment validation with Module B before freezing.

---

### 2.4 Signed Integer Encoding, Container Width, and Endianness (DW03-10 — PROPOSED / NOT APPROVED)

- **Numeric Representation:** Two's-complement signed integer (`signed_pcm`).
- **Endianness:** Strictly **Little-Endian** (`<i4` for 32-bit containers), matching both the ESP32-S3 architecture and x86/ARM host architectures.
- **Meaningful Bits:** 24 bits.
- **Container Width:** 32-bit slot width ($4 \text{ bytes/sample}$).
- **Bit Alignment within Container (OPEN):**
  - **Option 1 (LSB-aligned with sign extension):** Meaningful 24-bit data word in bits [23:0], sign-extended into bits [31:24], representing a legal signed integer in $[-8,388,608, +8,388,607]$. Host normalizes by $2^{23}$.
  - **Option 2 (MSB-aligned / Left-justified):** Meaningful data in bits [31:8], lower 8 bits zeroed. If Module B's I2S DMA produces MSB-aligned words, host normalizes by $2^{31}$.
  - **Requirement:** Module B must specify whether DMA output is LSB-aligned or MSB-aligned before wire decoding is implemented.

---

### 2.5 Sequence Tracking vs. First-Sample Index (PROPOSED / NOT APPROVED)

- Host telemetry requires monotonic sample accounting to detect packet drops and buffer slips.
- **Module C Proposal:** Transmit **Frame Sequence Number** (`uint32`) in the primary header. Because $N_{samples}$ is fixed (512) or declared in each frame header, the cumulative sample index is computable deterministically:
  $$\text{Sample Index} = \text{Sequence} \times N_{samples}$$
- Rollover occurs at $2^{32}-1$ (approx. 530 days of continuous streaming at 93.75 fps), which is practically infinite for single-session PCG acquisitions.

---

### 2.6 Device Timestamp and Timebase (PROPOSED / NOT APPROVED)

- The timestamp must originate from the **ESP32-S3 hardware monotonic clock** (`esp_timer_get_time()`, microsecond resolution).
- It must represent the acquisition start of the first sample in the payload block.
- The host records both the hardware timestamp and host arrival time, but never substitutes host wall-clock time for hardware timestamps.
- Telemetry monitors timestamp monotonicity; negative jumps indicate MCU timer rollover or firmware scheduling jitter.

---

### 2.7 Application CRC Policy (DW03-09 — PROPOSED / NOT APPROVED)

- While USB physical packets contain hardware-level CRC (CRC5 for tokens, CRC16 for data packets), USB hardware CRC only protects data across the physical bus wires.
- **Risks not covered by USB hardware CRC:**
  1. ESP32-S3 DMA memory corruption or FIFO ring buffer contention.
  2. USB CDC driver partial packet read / fragmentation across OS buffer boundaries.
  3. Firmware buffer overwrite prior to USB endpoint staging.
- **Module C Position:** We propose evaluating **CRC-16-CCITT**.
- **Crucial Unfinalized Parameters:**
  - Polynomial (e.g. `0x1021` vs `0x8005`) — **NOT FINALIZED**.
  - Initialization value (e.g. `0xFFFF` vs `0x0000`) — **NOT FINALIZED**.
  - Input bit reflection (`RefIn`) and output bit reflection (`RefOut`) — **NOT FINALIZED**.
  - Final XOR value — **NOT FINALIZED**.
  - Coverage (Header + Payload vs Payload only) — **NOT FINALIZED**.
  - Byte order on wire (little-endian vs big-endian) — **NOT FINALIZED**.
  - Hardware failure behavior (immediate drop vs error packet) — **NOT FINALIZED**.
- This policy is completely open under DW03-09 and requires joint sign-off.

---

### 2.8 Handshake and Streaming Lifecycle (PROPOSED / NOT APPROVED)

1. **Host Opening:** Host detects CDC-ACM COM port and opens connection. State: `OPENING`.
2. **Capabilities Discovery:** Host issues `0x02` or MCU announces `DeviceCapabilities` upon port DTR assertion. State: `HANDSHAKING`.
3. **Compatibility Validation:** Host verifies protocol version, sample rate (48000 Hz), channels (1), and container format. State transitions to `READY`.
4. **Streaming Command:** Host transmits `0x04` (`CMD_STREAM_START`). MCU acknowledges and begins streaming frames. State: `STREAMING`.
5. **Clean Termination:** Host transmits `0x05` (`CMD_STREAM_STOP`). MCU halts transmission. State: `READY`.
6. **Physical Disconnect:** If USB cable is dislodged, host transitions immediately to `INTERRUPTED`. Any active recording is cleanly finalized with `termination_reason='device_disconnected'`.

---

### 2.9 Disconnect, Buffer Overflow, and Parser Recovery (PROPOSED / NOT APPROVED)

- **Conceptual Parser Recovery:**
  1. `SEARCH_SYNC`: Scan byte stream for magic pattern `[0xAA, 0x55]`.
  2. `READ_HEADER`: Accumulate 16-byte header. Check protocol version and payload length ($N \le 2048$). If invalid, increment `malformed_frames` and return to `SEARCH_SYNC`.
  3. `READ_PAYLOAD`: Accumulate $N_{bytes} + 2$ (payload + CRC).
  4. `VERIFY_CRC`: Compute CRC-16. If mismatch, increment `crc_failures`, drop frame, and return to `SEARCH_SYNC`.
  5. `DISPATCH`: Construct `DeviceSamplePacket` and emit to push ingestion pipeline.
- **Buffer Overflow Visibility:** If MCU encounters DMA starvation or USB endpoint backpressure, it asserts Bit 0 in `Flags`. Host logs this in `DeviceIntegrityStats` rather than silently dropping samples.

---

## 3. Hardware Profile Accuracy: PUI DMM-4026 vs. Purchased INMP441

### 3.1 Sourcing Background

- The purchased MEMS microphone module is the **INMP441 breakout module**, selected because the original PUI evaluation board (`PUI DMM-4026-B-I2S-EB-R`) could not be sourced within the required project schedule (exhibiting 22-week manufacturer lead times and distributor stock deficits).
- **CRITICAL DIRECTIVE:** Do NOT assume that the INMP441 module uses the identical meaningful-bit interpretation, slot alignment, or USB sample representation as the PUI sensor.
- **PROFILE PRESERVATION:** The existing PUI Rev-A baseline profile (`rev_a_pui_dmm4026`) and legacy 4 kHz development profile (`dev_4khz_legacy`) in `software/pcg_app/device_runtime.py` remain **STRICTLY PRESERVED** and unchanged until a separately reviewed and approved hardware profile change is formally available.

### 3.2 Transducer Discrepancy Matrix

| Parameter | PUI DMM-4026-B-I2S-R (Theoretical Rev-A Baseline) | INMP441 Breakout Module (Purchased Hardware) | Engineering Impact |
|---|---|---|---|
| **Acoustic Dynamic Range / SNR** | 64 dBA SNR; -26 dB sensitivity | 61 dBA SNR; -26 dBFS sensitivity | Acoustic precision differs by ~3 dB; sensor physics dictate usable PCG dynamic range. |
| **Low-Frequency Cutoff (-3 dB)** | Listed 20 Hz – 20 kHz; typical curve extends to 20 Hz. | Flat response begins at 60 Hz; high-pass corner typically 60 Hz. | Sub-50 Hz heart sound components (S1/S2 fundamentals) may suffer attenuation on INMP441. |
| **I2S Bus Timing & Alignment** | 24 bits in 32-bit slot, MSB first, standard I2S. | 24 bits in 32-bit slot, MSB first, standard I2S. Lower 8 bits zeroed. | **Identical bus framing**, but bit positioning inside the 32-bit DMA word depends on ESP32-S3 I2S driver configuration. |
| **Supply Voltage & Logic Levels** | 1.8 V nominal (3.6 V max); 3.3 V operation required vendor confirmation. | 3.3 V tolerant on VDD and I2S IO lines. | INMP441 breakout is simpler to wire directly to DevKit 3.3 V rail. |

### 3.3 Prerequisites for Any Future Profile Migration

Before any new acquisition profile is introduced into `device_runtime.py`:
1. **Manufacturer & Module B Evidence Required:**
   - Module B must inspect the received INMP441 breakout board and supply the exact I2S driver configuration (e.g. `i2s_channel_fmt_t`, slot width, bit order).
   - Module B must confirm whether DMA buffer integers are MSB-aligned or LSB-aligned with sign-extension.
2. **Explicit Profile Definition:**
   - When approved, define a distinct profile ID (e.g. `bench_inmp441_breakout`) without silently modifying `REV_A_BASELINE_PROFILE`.
   - Both profiles will coexist in the centralized configuration model.

---

## 4. Summary of Action Items for Week 05 Handshake

1. **Joint Review (Ozan & Ege):**
   - Review and evaluate CDC-ACM as the transport class.
   - Evaluate the 16-byte illustrative header concept and decide on packing pragmas.
   - Agree on CRC policy (DW03-09): decide whether to use CRC-16 or USB hardware CRC.
   - Confirm I2S DMA sample alignment (LSB vs MSB).

2. **Module B (Ozan):**
   - Flash synthetic 100 Hz sine / counter generator for initial bench bringup.

3. **Module C (Ege):**
   - Implement byte-level serial decoder matching agreed framing **ONLY AFTER** joint sign-off.
   - Execute C-W05-01 through C-W05-08 live on bench when ESP32-S3 arrives.
   - Retain all WAV and JSON artifacts under `experiments/sessions/` with Git SHA provenance.
