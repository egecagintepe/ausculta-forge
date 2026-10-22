# AuscultaForge — Module B-to-C Protocol Wire Specification
## Version 0.1.0-CANONICAL — 40-Byte Header Framing Profile (Profile B) & Control Handshake

- **Document Version:** `0.1.0-CANONICAL`
- **Owner:** Ege Çağın Tepe (Module C) & Ozan (Module B)
- **Status:** **JOINT CANONICAL SPECIFICATION — BASELINE v0.1**
- **Associated Decisions:** DW03-08, DW03-09, DW03-10, DW03-12, ADR-0003, ADR-0007, ADR-0008, ADR-0010, ADR-0011
- **Normative Full Specification:** `docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md`

---

## 1. Frame Architecture Overview

The canonical Profile B frame consists of three contiguous byte sections:
1. **Header (40 bytes):** Fixed-length, naturally aligned metadata describing sequence, timestamps, sample counts, and telemetry.
2. **Payload (Variable):**
   - **AUDIO (Opcode `0x01`):** `sample_count × 4 bytes` (nominally 256 samples × 4 = 1,024 bytes of 24-in-32 signed PCM, little-endian).
   - **Control Messages (`msg_type != 0x01`):** Fixed byte sizes per opcode. **Header's `sample_count` MUST BE 0**.
3. **Trailer (4 bytes):** 32-bit CRC (IEEE 802.3 standard) computed across the entire Header + Payload.

**Standard Audio Frame Total Size:** `40 + 1024 + 4 = 1,068 bytes`.

```
+-------------------------------------------------------------------------------+
| HEADER (40 Bytes)                                                             |
| Magic (4B) | Ver (1B) | Type (1B) | Flags (2B) | Seq (4B) | Rate (4B) ...    |
+-------------------------------------------------------------------------------+
| PAYLOAD (1,024 Bytes for Audio, or Control Payload)                           |
| Audio: Sample 0 (4B) | Sample 1 (4B) | ... | Sample 255 (4B) (Signed 32-bit)  |
| Control: Structured fields (0 to 72 bytes) with sample_count == 0             |
+-------------------------------------------------------------------------------+
| TRAILER (4 Bytes)                                                             |
| CRC-32 Checksum (4B Little-Endian, IEEE 802.3 over Header + Payload)          |
+-------------------------------------------------------------------------------+
```

---

## 2. Byte-Level Header Layout Table

All multi-byte numeric fields are encoded in **standard Little-Endian (`<`) format**:

| Byte Offset | Field Name | Data Type | Alignment | Example / Value | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `0x00 .. 0x03` | `magic` | `uint32_t` | 4 bytes | `0xAF534331` | Synchronization Word (`[0x31, 0x43, 0x53, 0xAF]`, ASCII `"1CSA"`). |
| `0x04` | `version` | `uint8_t` | 1 byte | `0x01` | Protocol Major Version (`1`). |
| `0x05` | `msg_type` | `uint8_t` | 1 byte | `0x01` | Message Type opcode (see Section 4). |
| `0x06 .. 0x07` | `flags` | `uint16_t` | 2 bytes | `0x0001` | 16-bit Frame status flags bitmask (see Section 3). |
| `0x08 .. 0x0B` | `sequence_id` | `uint32_t` | 4 bytes | `0x00000001` | Monotonic frame sequence counter (`0` to `2^32 - 1`). Wraps cleanly. |
| `0x0C .. 0x0F` | `sample_rate_hz` | `uint32_t` | 4 bytes | `48000` | Declared hardware acquisition rate in Hertz. |
| `0x10 .. 0x17` | `timestamp_us` | `uint64_t` | 8 bytes | `1000000` | Monotonic acquisition timestamp in microseconds (`esp_timer_get_time()`). |
| `0x18 .. 0x1F` | `sample_index_start` | `uint64_t` | 8 bytes | `0` | Cumulative 64-bit absolute sample index of first sample. (0 for control). |
| `0x20 .. 0x21` | `sample_count` | `uint16_t` | 2 bytes | `256` / `0` | Audio samples count in payload. **MUST BE 0 for all control frames**. |
| `0x22` | `meaningful_bits` | `uint8_t` | 1 byte | `24` | Sensor ADC/I2S meaningful resolution bits (nominally 24). |
| `0x23` | `container_bits` | `uint8_t` | 1 byte | `32` | Container slot bit width (nominally 32). |
| `0x24` | `channels` | `uint8_t` | 1 byte | `1` | Number of channels (nominally 1 for mono PCG). |
| `0x25` | `encoding` | `uint8_t` | 1 byte | `0x01` | Encoding format: `0x01` = Signed PCM LSB-aligned, `0x02` = MSB-aligned. |
| `0x26 .. 0x27` | `mcu_buffer_drops` | `uint16_t` | 2 bytes | `0` | Saturating sample drop indicator = `min(total_dropped_samples, 65535)`. |

**Total Header Size:** Exactly `40 bytes` (`0x28`).

---

## 3. Flag Bitmask Definitions (`flags`, 16-Bit)

| Bit | Identifier | Description |
| :---: | :--- | :--- |
| `Bit 0` (`0x0001`) | `FRAME_FLAG_TIMESTAMP_VALID` | Set when MCU hardware timer is initialized and synchronized. |
| `Bit 1` (`0x0002`) | `FRAME_FLAG_SAMPLE_DISCONTINUITY` | Set by MCU if internal DMA slip or buffer gap occurred. |
| `Bit 2` (`0x0004`) | `FRAME_FLAG_DMA_BUFFER_OVERFLOW` | Set if I2S DMA receive FIFO experienced hardware overflow. |
| `Bit 3` (`0x0008`) | `FRAME_FLAG_USB_QUEUE_OVERFLOW` | Set if USB CDC-ACM transmit ring buffer dropped data. |
| `Bit 4` (`0x0010`) | `FRAME_FLAG_CLIPPING_DETECTED` | Set if any sample in frame touched `INT24_MAX` or `INT24_MIN`. |
| `Bit 5` (`0x0020`) | `FRAME_FLAG_SIMULATED_SOURCE` | Set when generating synthetic bench signals (prevents fake hardware claims). |
| `Bit 6` (`0x0040`) | `FRAME_FLAG_DIAGNOSTIC_TONE` | Set when transmitting calibration tones. |
| `Bit 7` (`0x0080`) | `FRAME_FLAG_SESSION_ACTIVE` | Set when an authorized acquisition session is currently active. |
| `Bits 8..15` | *Reserved* | Reserved for future physical expansion; must be set to `0`. |

---

## 4. Message Types & Framing Table

| Message | Opcode | `sample_count` | Payload Size | Total Frame Size | Direction |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `AUDIO` | `0x01` | `N` (256) | `N × 4` (1024) | 1,068 bytes | ESP32 → Host |
| `STATUS` | `0x02` | `0` | 72 bytes | 116 bytes | ESP32 → Host |
| `START_REQ` | `0x03` | `0` | 16 bytes | 60 bytes | Host → ESP32 |
| `START_ACK` | `0x04` | `0` | 32 bytes | 76 bytes | ESP32 → Host |
| `STOP_REQ` | `0x05` | `0` | 8 bytes | 52 bytes | Host → ESP32 |
| `STOP_ACK` | `0x06` | `0` | 72 bytes | 116 bytes | ESP32 → Host |
| `ERROR` | `0x0F` | `0` | 8 bytes | 52 bytes | Bidirectional |
| `HELLO_REQ` | `0x10` | `0` | 4 bytes | 48 bytes | Host → ESP32 |
| `HELLO_ACK` | `0x11` | `0` | 24 bytes | 68 bytes | ESP32 → Host |

---

## 5. 72-Byte Telemetry Payload Schema (`STATUS` and `STOP_ACK`)

- Offset 0..7: `session_id` (`uint64_t` LE)
- Offset 8..15: `generated_samples` (`uint64_t` LE)
- Offset 16..23: `fully_queued_samples` (`uint64_t` LE)
- Offset 24..31: `dropped_samples` (`uint64_t` LE)
- Offset 32..35: `audio_frames_queued` (`uint32_t` LE)
- Offset 36..39: `dma_overflow_events` (`uint32_t` LE)
- Offset 40..43: `ring_overflow_events` (`uint32_t` LE)
- Offset 44..47: `usb_partial_write_events` (`uint32_t` LE)
- Offset 48..51: `usb_timeout_events` (`uint32_t` LE)
- Offset 52..55: `usb_disconnect_events` (`uint32_t` LE)
- Offset 56..63: `audio_bytes_queued` (`uint64_t` LE)
- Offset 64..67: `stop_reason` (`uint32_t` LE)
- Offset 68..71: `error_code` (`uint32_t` LE)

---

## 6. Trailer Specification

- **Algorithm:** Standard IEEE 802.3 CRC-32 (polynomial `0xEDB88320`, init `0xFFFFFFFF`, final XOR `0xFFFFFFFF`).
- **Coverage:** Computed across the entire 40-byte Header + Payload.
- **Trailer Bytes:** 4 bytes Little-Endian.
