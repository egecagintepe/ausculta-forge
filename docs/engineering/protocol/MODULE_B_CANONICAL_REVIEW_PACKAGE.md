# AuscultaForge — Module B/C Joint Protocol Canonical Review Package
## Document Version: 1.0.0-REVIEW — Candidate Baseline v0.1

- **Project:** EEE495 / EEE496 Senior Design Project — AuscultaForge
- **Module C (Computer Application / Processing):** Ege Çağın Tepe
- **Module B (Transducer & Embedded Hardware):** Ozan
- **Target Microcontroller:** Espressif ESP32-S3 (Xtensa Dual-Core 32-bit LX7)
- **Target Transport:** USB CDC-ACM Full-Speed (12 Mbps) / High-Speed Virtual Serial
- **Target Branch:** `feature/ege-canonical-bc-protocol-v01`
- **Specification Baseline:** [`docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md`](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md)

---

## 1. Executive Summary & Review Intent

This document is the joint technical review package submitted by Module C (Ege) to Module B (Ozan) for final protocol sign-off prior to first physical USB bring-up.

> [!IMPORTANT]
> **Joint Alignment Notice:**
> Agreement on architectural principles (e.g. 40-byte framing, 72-byte telemetry, deterministic ramp verification) does **not** imply automatic final sign-off on every field-level definition. Field definitions marked with `[PENDING MODULE B APPROVAL]` are explicitly submitted for Ozan's review and adjustment to match ESP-IDF hardware primitives.

---

## 2. Byte-Exact Profile B Framing Header (40 Bytes)

Every protocol frame begins with a fixed 40-byte Profile B header. All multi-byte numeric fields are encoded in **Standard Little-Endian (`<`) byte order**.

### 2.1 Header Field Map & Wire Offsets

| Offset Range | Field Name | Wire Type | Example / Value | Description & Invariants |
| :---: | :--- | :---: | :---: | :--- |
| `0x00 .. 0x03` | `magic` | `uint32_t` | `0xAF534331` | Sync Word (`[0x31, 0x43, 0x53, 0xAF]`, ASCII `"1CSA"`). |
| `0x04` | `version` | `uint8_t` | `0x01` | Protocol Major Version (`1`). Non-matching versions rejected. |
| `0x05` | `msg_type` | `uint8_t` | Opcode | Opcode identifier (see Section 3). |
| `0x06 .. 0x07` | `flags` | `uint16_t` | `0x0001` | 16-bit status & error flag bitmask (Section 2.2). |
| `0x08 .. 0x0B` | `sequence_id` | `uint32_t` | Monotonic | Frame sequence counter (`0 .. 2^32 - 1`). Wraps cleanly. |
| `0x0C .. 0x0F` | `sample_rate_hz`| `uint32_t` | `48000` | Declared sampling rate in Hz (nominally 48000). |
| `0x10 .. 0x17` | `timestamp_us` | `uint64_t` | Microseconds | Monotonic timestamp from MCU timebase (`esp_timer_get_time()`). |
| `0x18 .. 0x1F` | `sample_index_start`| `uint64_t`| Cumulative | Cumulative 64-bit absolute sample index. **0 for all control frames**. |
| `0x20 .. 0x21` | `sample_count` | `uint16_t` | `256` or `0` | Number of 32-bit sample words in payload. **MUST BE ZERO for all control messages**. |
| `0x22` | `meaningful_bits` | `uint8_t` | `24` | Active ADC/I2S resolution bits (nominally 24). |
| `0x23` | `container_bits` | `uint8_t` | `32` | Container slot bit width (nominally 32). |
| `0x24` | `channels` | `uint8_t` | `1` | Channels count (nominally 1 for mono PCG). |
| `0x25` | `encoding` | `uint8_t` | `0x01` | Encoding format: `0x01` = Signed PCM LSB-aligned, `0x02` = MSB-aligned. |
| `0x26 .. 0x27` | `mcu_buffer_drops` | `uint16_t` | Counter | Saturating sample drop indicator = `min(total_dropped, 65535)`. |

**Total Header Size:** Exactly `40 bytes` (`0x28`).  
**Portability Rule:** While fields follow natural alignment boundaries (1, 2, 4, 8 bytes), in-memory struct layouts are not assumed identical across Xtensa and x86_64 compilers. **Field-by-field little-endian wire serialization is the actual cross-compiler guarantee.**

### 2.2 16-Bit Flag Bitmask

- Bit 0 (`0x0001`): `FRAME_FLAG_TIMESTAMP_VALID` — Timestamp derived from real timebase.
- Bit 1 (`0x0002`): `FRAME_FLAG_SAMPLE_DISCONTINUITY` — Sequence gap or index skip occurred.
- Bit 2 (`0x0004`): `FRAME_FLAG_DMA_BUFFER_OVERFLOW` — I2S DMA receive buffer overflowed.
- Bit 3 (`0x0008`): `FRAME_FLAG_USB_QUEUE_OVERFLOW` — USB CDC TX ring buffer overflowed.
- Bit 4 (`0x0010`): `FRAME_FLAG_CLIPPING_DETECTED` — Transducer acoustic saturation.
- Bit 7 (`0x0080`): `FRAME_FLAG_SIMULATED_SOURCE` — Synthetic test generator (source mode $\ne 0$).
- Bit 8 (`0x0100`): `FRAME_FLAG_SESSION_ACTIVE` — Frame belongs to an authorized session.

---

## 3. Control Opcodes and Payload Sizes

Every control frame carries `sample_count = 0` in the 40-byte header. The payload length is strictly determined by the opcode:

| Opcode | Mnemonic | Direction | Payload Size | Total Wire Size (Hdr + Pay + CRC) | Purpose |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `0x01` | `AUDIO_DATA` | ESP32 $\to$ Host | $N \times 4$ B (`1024B`) | `1068 bytes` (for $N=256$) | Normal streaming audio samples. |
| `0x02` | `HEARTBEAT_STATUS` | ESP32 $\to$ Host | `72 bytes` | `116 bytes` | Periodic status & hardware counters. |
| `0x03` | `ERROR_NOTIFICATION` | Bidirectional | `8 bytes` | `52 bytes` | Asynchronous protocol/hardware error. |
| `0x10` | `HELLO_REQ` | Host $\to$ ESP32 | `4 bytes` | `48 bytes` | Connection handshake probe with nonce. |
| `0x11` | `HELLO_ACK` | ESP32 $\to$ Host | `24 bytes` | `68 bytes` | Nonce echo and hardware capabilities. |
| `0x20` | `STREAM_START_REQ` | Host $\to$ ESP32 | `16 bytes` | `60 bytes` | Request stream commencement. |
| `0x21` | `STREAM_START_ACK` | ESP32 $\to$ Host | `32 bytes` | `76 bytes` | Confirm stream and issue session ID. |
| `0x22` | `STREAM_STOP_REQ` | Host $\to$ ESP32 | `8 bytes` | `52 bytes` | Command stream termination. |
| `0x23` | `STREAM_STOP_ACK` | ESP32 $\to$ Host | `72 bytes` | `116 bytes` | Final telemetry reconciliation. |

---

## 4. Control Message Payloads

### 4.1 `HELLO_REQ` (4 Bytes) — Host $\to$ ESP32
- `0x00 .. 0x03`: `host_nonce` (`uint32_t`) — Cryptographically random 32-bit challenge.

### 4.2 `HELLO_ACK` (24 Bytes) — ESP32 $\to$ Host `[PENDING MODULE B APPROVAL]`

| Offset | Field Name | Type | Description | Status |
| :---: | :--- | :---: | :--- | :--- |
| `0x00 .. 0x03` | `nonce_echo` | `uint32_t` | Exact echo of `host_nonce`. | Agreed |
| `0x04` | `protocol_version_major` | `uint8_t` | Must be `1`. | Agreed |
| `0x05` | `protocol_version_minor` | `uint8_t` | Must be `0`. | Agreed |
| `0x06` | `supported_profiles_mask` | `uint8_t` | Bit 1 = Profile B (`0x02`). | Agreed |
| `0x07` | `supported_encodings_mask`| `uint8_t` | Bit 0 = LSB (`0x01`). | Agreed |
| `0x08 .. 0x0B` | `hardware_sample_rate_hz`| `uint32_t` | Nominally `48000`. | Agreed |
| `0x0C` | `firmware_version_major` | `uint8_t` | ESP-IDF firmware major. | Agreed |
| `0x0D` | `firmware_version_minor` | `uint8_t` | ESP-IDF firmware minor. | Agreed |
| `0x0E` | `firmware_version_patch` | `uint8_t` | ESP-IDF firmware patch. | Agreed |
| `0x0F` | `reserved` | `uint8_t` | Pad to 32-bit boundary (`0x00`). | Agreed |
| `0x10 .. 0x11` | `max_frame_samples` | `uint16_t` | Max samples per frame (`256`). | Agreed |
| `0x12 .. 0x13` | `capability_flags` | `uint16_t` | Bitmask: USB_CDC, SYNTH, 72B_TELEM. | Agreed |
| `0x14 .. 0x17` | `device_uid_low` | `uint32_t` | Lower 32 bits of ESP32 chip MAC ID. | **PENDING REVIEW** |

> [!NOTE]
> `device_uid_low`: Proposed to carry the lower 32 bits of `esp_efuse_mac_get_default()`. If Ozan prefers a different hardware identifier or a 64-bit UID, Module C can expand the payload accordingly.

### 4.3 `START_REQ` (16 Bytes) — Host $\to$ ESP32
- `0x00 .. 0x03`: `sample_rate_hz` (`uint32_t`, `48000`).
- `0x04 .. 0x0B`: `target_samples` (`uint64_t`, `480000` for 10s G1; `0` = continuous).
- `0x0C`: `source_mode` (`uint8_t`, `0` = Live MEMS, `1` = Deterministic Ramp, `2` = 100 Hz Sine).
- `0x0D`: `encoding` (`uint8_t`, `1` = LSB-aligned signed PCM).
- `0x0E`: `channels` (`uint8_t`, `1` = mono).
- `0x0F`: `profile_id` (`uint8_t`, `2` = Profile B).

### 4.4 `START_ACK` (32 Bytes) — ESP32 $\to$ Host (Repaired Specification)

| Offset | Field Name | Type | Description |
| :---: | :--- | :---: | :--- |
| `0x00 .. 0x07` | `session_id` | `uint64_t` | Non-zero unique 64-bit session ID generated by ESP32. |
| `0x08 .. 0x0F` | `session_reference_time_us` | `uint64_t` | Monotonic timestamp $t_0$ when session commenced. |
| `0x10 .. 0x13` | `accepted_sample_rate_hz` | `uint32_t` | Confirmed sample rate (`48000`). |
| `0x14 .. 0x1B` | `accepted_target_samples` | `uint64_t` | Confirmed target samples. |
| `0x1C` | `accepted_source_mode` | `uint8_t` | Confirmed source mode (`1` for G1). |
| `0x1D` | `encoding` | `uint8_t` | Confirmed sample encoding (`1`). |
| `0x1E` | `channels` | `uint8_t` | Confirmed channel count (`1`). |
| `0x1F` | `profile_id` | `uint8_t` | Confirmed framing profile (`2`). |

**Total Payload Size:** Exactly `32 bytes`. Contradictory reserved padding bytes (`0x20..0x27`) were removed to match current C and Python codecs.

### 4.5 `STOP_REQ` (8 Bytes) — Host $\to$ ESP32
- `0x00 .. 0x07`: `session_id` (`uint64_t`) — Must match active `session_id`.

### 4.6 `STATUS` and `STOP_ACK` Telemetry (72 Bytes) — ESP32 $\to$ Host

| Offset | Field Name | Type | Description |
| :---: | :--- | :---: | :--- |
| `0x00 .. 0x07` | `session_id` | `uint64_t` | Active or finalized session ID. |
| `0x08 .. 0x0F` | `generated_samples` | `uint64_t` | Total samples produced by I2S DMA or synthetic generator. |
| `0x10 .. 0x17` | `fully_queued_samples`| `uint64_t` | Total samples placed into outgoing transport FIFO. |
| `0x18 .. 0x1F` | `dropped_samples` | `uint64_t` | Total samples dropped due to buffer/queue overflow. |
| `0x20 .. 0x23` | `audio_frames_queued` | `uint32_t` | Total Profile B AUDIO frames submitted to USB CDC-ACM. |
| `0x24 .. 0x27` | `dma_overflow_events` | `uint32_t` | Count of I2S DMA receive FIFO overflow events. |
| `0x28 .. 0x2B` | `ring_overflow_events`| `uint32_t` | Count of MCU intermediate ring buffer overflows. |
| `0x2C .. 0x2F` | `usb_partial_write_events`| `uint32_t`| Count of non-blocking USB partial write returns. |
| `0x30 .. 0x33` | `usb_timeout_events` | `uint32_t` | Count of USB endpoint write timeout events. |
| `0x34 .. 0x37` | `usb_disconnect_events` | `uint32_t` | Count of USB bus suspend/disconnect events. |
| `0x38 .. 0x3F` | `audio_bytes_queued` | `uint64_t` | Cumulative wire bytes queued (`audio_frames_queued × 1068`). |
| `0x40 .. 0x43` | `stop_reason` | `uint32_t` | `0` = TARGET_REACHED, `1` = HOST_REQUEST, `2` = DMA_OVERFLOW, `3` = USB_ERR, `4` = USER_ABORT, `5` = TIMEOUT. |
| `0x44 .. 0x47` | `error_code` | `uint32_t` | `0` = OK; otherwise non-zero error identifier. |

### 4.7 `ERROR` (8 Bytes) — Bidirectional `[PENDING MODULE B APPROVAL]`
- `0x00 .. 0x03`: `error_code` (`uint32_t`, `1` = INVALID_MAGIC, `2` = CRC_FAIL, `3` = SESSION_MISMATCH, `4` = INVALID_PARAM, `5` = OVERFLOW).
- `0x04 .. 0x07`: `error_context` (`uint32_t`, opcode or sequence ID causing error).

---

## 5. Trailer & CRC-32 Specification

- **Algorithm:** IEEE 802.3 Ethernet Standard CRC-32.
- **Polynomial:** `0xEDB88320` (reversed representation) / `0x04C11DB7`.
- **Initial Value:** `0xFFFFFFFF`.
- **Final XOR:** `0xFFFFFFFF`.
- **Coverage:** Computed across the entire 40-byte header followed immediately by all payload bytes ($40 + \text{payload\_len}$ bytes).
- **Known-Answer Vector:**
  - Input ASCII `"123456789"` (`0x31..0x39`, 9 bytes) $\implies$ CRC-32 = `0xCBF43926`.
  - Little-endian wire trailer: `[0x26, 0x39, 0xF4, 0xCB]`.

---

## 6. Normative Deterministic Integer Sequence (Source Mode 1)

For hardware bring-up and G1 verification, `source_mode = 1` commands the ESP32 to generate an exact pseudo-random sequence:

1. **Origin:** Cumulative 0-indexed sample counter $n \in \{0, 1, 2, \dots, 479999\}$.
2. **24-bit Unsigned Arithmetic:**
   $$U_n = (n \times 16807 + 7) \bmod 2^{24}$$
3. **Sign Extension to 32-bit Container (`int32_t`):**
   $$S_n = \begin{cases} U_n - 2^{24}, & \text{if } U_n \ge 2^{23} \\ U_n, & \text{if } U_n < 2^{23} \end{cases}$$
4. **Known-Answer Regression Standards:**
   - $n = 0 \implies S_0 = 7$ (`0x00000007`)
   - $n = 1 \implies S_1 = 16814$ (`0x000041AE`)
   - $n = 500 \implies S_{500} = -8373709$ (`0xFF803A33`)
   - $n = 1000 \implies S_{1000} = 29791$ (`0x0000745F`)
   - $n = 479999 \implies S_{479999} = -2497696$ (`0xFFD9E360`)

---

## 7. Concrete Byte-Level Exchange Example

### 7.1 HELLO Handshake
```
Host -> ESP32: [48 Bytes]
  Header: [0x31, 0x43, 0x53, 0xAF] (Magic)
          [0x01] (Ver 1), [0x10] (Opcode HELLO_REQ), [0x00, 0x00] (Flags)
          [0x00, 0x00, 0x00, 0x00] (Seq 0), [0x80, 0xBB, 0x00, 0x00] (48 kHz)
          [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] (Timestamp 0)
          [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] (Sample Index 0)
          [0x00, 0x00] (Sample Count = 0), [24, 32, 1, 1], [0x00, 0x00] (Drops 0)
  Payload: [0x43, 0x55, 0x53, 0x41] (Host Nonce: 0x41535543)
  Trailer: [0x.. 4-byte CRC-32]

ESP32 -> Host: [68 Bytes]
  Header: Magic, Ver 1, Opcode 0x11 (HELLO_ACK), Sample Count = 0
  Payload: [0x43, 0x55, 0x53, 0x41] (Nonce Echo)
           [0x01, 0x00] (Proto 1.0), [0x02] (Profile B), [0x01] (LSB)
           [0x80, 0xBB, 0x00, 0x00] (48000 Hz)
           [0x01, 0x00, 0x00, 0x00] (FW 1.0.0, reserved 0)
           [0x00, 0x01] (256 samples/frame), [0x07, 0x00] (Capabilities)
           [0x32, 0x33, 0x43, 0x53] (Device UID low)
  Trailer: [0x.. 4-byte CRC-32]
```

### 7.2 START Handshake
```
Host -> ESP32: [60 Bytes]
  Header: Opcode 0x20 (START_REQ), Sample Count = 0
  Payload: [0x80, 0xBB, 0x00, 0x00] (48000 Hz)
           [0x00, 0x53, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00] (480,000 target samples)
           [0x01] (Source Mode = 1: Deterministic Ramp)
           [0x01] (Encoding = 1: LSB), [0x01] (Channels = 1), [0x02] (Profile B)
  Trailer: [0x.. 4-byte CRC-32]

ESP32 -> Host: [76 Bytes]
  Header: Opcode 0x21 (START_ACK), Sample Count = 0
  Payload: [0x01, 0x00, 0x00, 0x00, 0xED, 0xFE, 0xFE, 0xCA] (Session ID: 0xCAFEFEED00000001)
           [0x40, 0x42, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00] (t0 = 1,000,000 us)
           [0x80, 0xBB, 0x00, 0x00] (48000 Hz)
           [0x00, 0x53, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00] (480000 samples)
           [0x01] (Source Mode 1), [0x01] (Encoding 1), [0x01] (1 Ch), [0x02] (Profile B)
  Trailer: [0x.. 4-byte CRC-32]
```

### 7.3 Streaming Audio Frames (1,875 Frames)
```
ESP32 -> Host: [1,068 Bytes per Frame]
  Header (40B):
    Opcode 0x01 (AUDIO_DATA), Flags = 0x0181 (TIMESTAMP_VALID | SIMULATED | SESSION_ACTIVE)
    Sequence ID = k (0 .. 1874)
    Timestamp us = t0 + floor(k * 256 * 1e6 / 48000)
    Sample Index Start = k * 256
    Sample Count = 256
    Encoding = 1, Channels = 1, Meaningful Bits = 24
  Payload (1,024B):
    256 x 32-bit little-endian samples: S_{k*256 + 0} ... S_{k*256 + 255}
  Trailer (4B): CRC-32 over (Header + Payload)
```

### 7.4 STOP Handshake and Final Telemetry
```
Host -> ESP32: [52 Bytes]
  Header: Opcode 0x22 (STOP_REQ), Sample Count = 0
  Payload: [0x01, 0x00, 0x00, 0x00, 0xED, 0xFE, 0xFE, 0xCA] (Active Session ID)
  Trailer: [0x.. 4-byte CRC-32]

ESP32 -> Host: [116 Bytes]
  Header: Opcode 0x23 (STOP_ACK), Sample Count = 0
  Payload (72B):
    Session ID: 0xCAFEFEED00000001
    Generated Samples: 480000
    Fully Queued Samples: 480000
    Dropped Samples: 0
    Audio Frames Queued: 1875
    DMA Overflows: 0, Ring Overflows: 0, Partial Writes: 0, Timeouts: 0, Disconnects: 0
    Audio Bytes Queued: 2,002,500 (1875 * 1068)
    Stop Reason: 1 (HOST_REQUEST) or 0 (TARGET_REACHED)
    Error Code: 0 (OK)
  Trailer: [0x.. 4-byte CRC-32]
```

---

## 8. Session Failure and Recovery Matrix

| Trigger / Fault Condition | Host State Transition | Immediate Action Taken |
| :--- | :--- | :--- |
| **Nonce mismatch in HELLO_ACK** | `HELLO_PENDING` $\to$ `ERROR` | Abort handshake, do not send `START_REQ`. |
| **HELLO_ACK timeout (>2.0s)** | `HELLO_PENDING` $\to$ `ERROR` | Close port, emit `PHYSICAL_G1_FAIL`. |
| **START_ACK rejected (`ERROR` frame)** | `START_PENDING` $\to$ `ERROR` | Log error code & context, abort session. |
| **Negotiated config mismatch** | `START_PENDING` $\to$ `ERROR` | Abort; refuse to stream unsupported mode. |
| **Zero session ID (`session_id == 0`)**| `START_PENDING` $\to$ `ERROR` | Invalidate session; zero ID is forbidden. |
| **CRC-32 failure on any frame** | Any state $\to$ `ERROR` | Reject frame, log sequence ID, fail G1. |
| **Missing frame (Sequence gap)** | `STREAMING` $\to$ `ERROR` | Log sequence gap, fail zero-tolerance gate. |
| **Duplicate frame** | `STREAMING` $\to$ `ERROR` | Log duplicate sequence ID, fail gate. |
| **Sample value mismatch ($val \ne S_n$)**| `STREAMING` $\to$ `ERROR` | Increment error count, fail G1 gate. |
| **Stream stall (>2.0s inactivity)** | `STREAMING` $\to$ `ERROR` | Timeout triggered, fail G1 gate. |
| **USB cable disconnect** | Any state $\to$ `DISCONNECTED` | Invalidate active session ID, reset decoder. |
| **STOP_ACK timeout (>2.0s)** | `STOPPING` $\to$ `ERROR` | Fail G1 gate; final telemetry unconfirmed. |
| **Mismatched STOP_ACK session ID** | `STOPPING` $\to$ `ERROR` | Invalidate acceptance; wrong session finalized. |

---

## 9. First Physical Bring-Up Command

When Module B's board is flashed and connected to the host PC via USB CDC-ACM:

```bash
python tools/protocol_lab/module_b_package/verify_g1_bringup.py --port COM3 --seconds 10
```

### Strict Output Semantics:
- If all 480,000 samples, 1,875 frames, and all 72 bytes of telemetry reconcile:
  ```
  >>> STATUS: PHYSICAL_G1_PASS <<<
  ```
  Process exit code: `0`.
- If any frame is dropped, CRC corrupted, sample mismatched, or telemetry reports drops:
  ```
  >>> STATUS: PHYSICAL_G1_FAIL <<<
  ```
  Process exit code: `1`.

---

## 10. Physical Timing Truth & Hardware Clock Verification Proposal

> [!CAUTION]
> **Separation of Sample Integrity from Physical Clock Truth:**
> Software loopback simulation transfers 480,000 samples in ~0.35 seconds at host CPU memory bandwidth. While this establishes 100% mathematical sample integrity, it does **NOT** prove that the physical ESP32-S3 hardware sampling clock runs at 48,000 Hz.

Module C proposes the following explicit timing criteria to Module B:

### Proposed Hardware Timing Acceptance Gate:
1. **Host Wall-Clock Elapsed Time Verification:**
   - Nominally: $T_{\text{target}} = \frac{480\,000}{48\,000} = 10.000\text{ seconds}$.
   - Allowed Physical Tolerance: $\pm 2.0\%$ ($\pm 200\text{ ms}$, range $[9.800\text{s}, 10.200\text{s}]$).
   - This accommodates ESP32 crystal frequency tolerance ($\pm 50\text{ ppm}$) and USB CDC-ACM packet scheduling jitter.
   - If 480,000 samples arrive in $<9.8\text{s}$ or $>10.2\text{s}$, `PHYSICAL_SAMPLE_TIMING_VERIFIED` fails.
2. **Firmware Timestamp Delta Verification:**
   - The final telemetry timestamp delta $\Delta t = t_{\text{final}} - t_0$ must satisfy:
     $$\Delta t \in [9\,990\,000\mu\text{s}, 10\,010\,000\mu\text{s}] \quad (\pm 0.1\%)$$
3. **Formal Evidence Separation in Verification Reports:**
   - `SAMPLE_INTEGRITY_VERIFIED`: True/False.
   - `NOMINAL_TIMESTAMP_CONSISTENCY_VERIFIED`: True/False.
   - `PHYSICAL_SAMPLE_TIMING_VERIFIED`: True / NOT VERIFIED (requires physical hardware pacing).
   - `PHYSICAL_USB_TRANSFER_VERIFIED`: True / NOT VERIFIED (requires physical CDC-ACM).

---

## 11. Checklist of Pending Hardware Decisions for Ozan

- [ ] **1. `HELLO_ACK` Device UID:** Confirm whether lower 32 bits of ESP32 eFuse MAC address (`esp_efuse_mac_get_default()`) is the preferred unique device ID.
- [ ] **2. `ERROR` Context Field:** Confirm whether sequence ID or failing opcode is the preferred diagnostic context in the 8-byte `ERROR` payload.
- [ ] **3. Hardware Timing Tolerance:** Approve the $\pm 2.0\%$ wall-clock delivery window ($10.0\text{s} \pm 200\text{ms}$) for physical G1 acceptance.
- [ ] **4. STOP Handshake Flushing:** Confirm that upon receiving `STOP_REQ`, the ESP32 firmware stops I2S DMA queuing, transmits any residual packets remaining in the USB FIFO, and then emits `STOP_ACK`.
