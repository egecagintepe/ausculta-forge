# AuscultaForge — B-to-C Protocol Wire Specification (Proposal)
## Version 1.0.0-PROVISIONAL — 40-Byte Header Framing Profile (Profile B)

- **Document Version:** `1.0.0-PROVISIONAL`
- **Owner:** Ege (Module C) & Ozan (Module B)
- **Status:** **PROPOSED ARCHITECTURAL SPECIFICATION FOR REVIEW**
- **Associated Decisions:** DW03-08, DW03-09, DW03-10, DW03-12

---

## 1. Frame Architecture Overview

The proposed Profile B frame consists of three contiguous byte sections:
1. **Header (40 bytes):** Fixed-length, naturally aligned metadata describing frame sequence, MCU timestamps, sample count, and error telemetry.
2. **Payload (1,024 bytes):** 256 samples × 4 bytes (32-bit signed integers carrying 24-bit meaningful sensor PCM, little-endian).
3. **Trailer (4 bytes):** 32-bit CRC (IEEE 802.3 standard) computed across the entire Header + Payload.

**Total Frame Size:** `40 + 1024 + 4 = 1,068 bytes`.

```
+-------------------------------------------------------------------------------+
| HEADER (40 Bytes)                                                             |
| Magic (4B) | Ver (1B) | Type (1B) | Flags (2B) | Seq (4B) | Rate (4B) ...    |
+-------------------------------------------------------------------------------+
| PAYLOAD (1,024 Bytes)                                                         |
| Sample 0 (4B) | Sample 1 (4B) | ... | Sample 255 (4B) (Signed 32-bit LE)      |
+-------------------------------------------------------------------------------+
| TRAILER (4 Bytes)                                                             |
| CRC-32 Checksum (4B Little-Endian, IEEE 802.3 over Header + Payload)          |
+-------------------------------------------------------------------------------+
```

---

## 2. Byte-Level Header Layout Table

All multi-byte numeric fields are encoded in **standard Little-Endian (`<`) format**. Multi-byte integers are positioned on their natural alignment boundaries to ensure identical packing on x86_64, ARM Cortex, and ESP32-S3 (Xtensa LX7):

| Byte Offset | Field Name | Data Type | Alignment | Example / Value | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `0x00 .. 0x03` | `magic` | `uint32_t` | 4 bytes | `0xAF534331` | Synchronization Word (`[0x31, 0x43, 0x53, 0xAF]`, ASCII `"1CSA"`). |
| `0x04` | `version` | `uint8_t` | 1 byte | `0x01` | Protocol Major Version (`1`). |
| `0x05` | `msg_type` | `uint8_t` | 1 byte | `0x01` | Message Type: `0x01` = Audio PCM Data, `0x02` = Heartbeat/Status. |
| `0x06 .. 0x07` | `flags` | `uint16_t` | 2 bytes | `0x0001` | Frame status flags bitmask (see Section 3). |
| `0x08 .. 0x0B` | `sequence_id` | `uint32_t` | 4 bytes | `0x0000002A` | Monotonic frame sequence counter (`0` to `2^32 - 1`). Wraps cleanly. |
| `0x0C .. 0x0F` | `sample_rate_hz` | `uint32_t` | 4 bytes | `48000` | Declared hardware acquisition rate in Hertz. |
| `0x10 .. 0x17` | `timestamp_us` | `uint64_t` | 8 bytes | `1000000` | Monotonic acquisition timestamp in microseconds (`esp_timer_get_time()`). |
| `0x18 .. 0x1F` | `sample_index_start` | `uint64_t` | 8 bytes | `10752` | Cumulative 64-bit absolute sample index of the first sample in this frame. |
| `0x20 .. 0x21` | `sample_count` | `uint16_t` | 2 bytes | `256` | Number of sample words in the payload (nominally 256). |
| `0x22` | `meaningful_bits` | `uint8_t` | 1 byte | `24` | Sensor ADC/I2S meaningful resolution bits (nominally 24). |
| `0x23` | `container_bits` | `uint8_t` | 1 byte | `32` | Container slot bit width (nominally 32). |
| `0x24` | `channels` | `uint8_t` | 1 byte | `1` | Number of channels (nominally 1 for mono PCG). |
| `0x25` | `encoding` | `uint8_t` | 1 byte | `0x01` | Encoding format: `0x01` = Signed PCM LSB-aligned, `0x02` = MSB-aligned. |
| `0x26 .. 0x27` | `mcu_buffer_drops` | `uint16_t` | 2 bytes | `0` | Cumulative sample drop counter maintained by MCU DMA/USB buffer supervisor. |

**Total Header Size:** Exactly `40 bytes` (`0x28`).

---

## 3. Flag Bitmask Definitions (`flags`)

The 16-bit `flags` field provides real-time operational status without requiring separate control packets:

| Bit | Identifier | Description |
| :---: | :--- | :--- |
| `Bit 0` (`0x0001`) | `FRAME_FLAG_TIMESTAMP_VALID` | Set when MCU hardware timer is initialized and synchronized. |
| `Bit 1` (`0x0002`) | `FRAME_FLAG_SAMPLE_DISCONTINUITY` | Set by MCU if internal DMA slip or buffer gap occurred immediately before this frame. |
| `Bit 2` (`0x0004`) | `FRAME_FLAG_DMA_BUFFER_OVERFLOW` | Set if I2S DMA receive FIFO experienced hardware overflow. |
| `Bit 3` (`0x0008`) | `FRAME_FLAG_USB_QUEUE_OVERFLOW` | Set if USB CDC-ACM / Bulk transmit queue filled and dropped data. |
| `Bit 4` (`0x0010`) | `FRAME_FLAG_CLIPPING_DETECTED` | Set if any sample in this frame touched `INT24_MAX` or `INT24_MIN`. |
| `Bit 5` (`0x0020`) | `FRAME_FLAG_SIMULATED_SOURCE` | Set when generating synthetic bench signals (prevents fake hardware claims). |
| `Bit 6` (`0x0040`) | `FRAME_FLAG_DIAGNOSTIC_TONE` | Set when transmitting calibration tones. |
| `Bits 7..15` | *Reserved* | Must be set to `0`. |

---

## 4. Payload Specification (Sample Representation — DW03-10)

- **Container:** 32-bit signed integer (`int32_t`) per sample.
- **Byte Order:** Little-Endian (`[LSB, Mid-Low, Mid-High, MSB]`).
- **Meaningful Bits:** 24 bits (`[-8,388,608, +8,388,607]`).
- **Alignment (Proposed Default):** LSB-aligned with sign-extension across bits 24..31:
  - Minimum negative (-FS): `0xFF800000` (-8,388,608)
  - Zero: `0x00000000` (0)
  - Maximum positive (+FS): `0x007FFFFF` (+8,388,607)
  - Negative one: `0xFFFFFFFF` (-1)

---

## 5. Trailer Specification (Application Integrity — DW03-09)

- **Algorithm:** CRC-32 (IEEE 802.3 standard, Ethernet / PNG / ZIP).
- **Polynomial:** `0xEDB88320` (reversed representation) / `0x04C11DB7`.
- **Initial Value:** `0xFFFFFFFF`.
- **Final XOR:** `0xFFFFFFFF`.
- **Coverage:** Computed across all 40 bytes of the Header followed immediately by all 1,024 bytes of the Payload (total 1,064 bytes).
- **Trailer Byte Order:** 4 bytes little-endian (`crc & 0xFF`, `(crc >> 8) & 0xFF`, etc.).

---

## 6. Bandwidth, Throughput & Timing Calculations

At the nominal baseline of **48,000 Hz mono 24-in-32 PCM**:
- **Samples per second:** 48,000 samples/s.
- **Raw Audio Payload Rate:** `48,000 × 4 bytes = 192,000 bytes/s` (**1.536 Mbps**).
- **Frame Rate (256 samples/frame):** `48,000 / 256 = 187.5 frames/s`.
- **Frame Interval:** `256 / 48,000 = 5.333 milliseconds`.
- **Header Overhead:** `187.5 × 40 bytes = 7,500 bytes/s` (**60.0 kbps**).
- **Trailer Overhead:** `187.5 × 4 bytes = 750 bytes/s` (**6.0 kbps**).
- **Total Wire Data Rate:** `187.5 × 1,068 bytes = 200,250 bytes/s` (**1.602 Mbps**).
- **Framing Overhead Ratio:** `(200,250 - 192,000) / 192,000 = 4.30%`.

### USB Transfer Comparison:
- **USB Full-Speed (12 Mbps):** Practical bulk throughput is ~1.0 MB/s (~8.0 Mbps). 200.25 kB/s consumes ~20% of bus capacity.
- **USB High-Speed (480 Mbps):** Practical throughput is ~40 MB/s. 200.25 kB/s consumes <0.5% of bus capacity.
