# W04 Module B → Module C — Protocol Proposal v0

**Owners:** Module B (Ozan) + Module C (Ege)  
**Date prepared:** 2026-10-18  
**Status:** FOR JOINT REVIEW — NOT CLOSED / NOT IMPLEMENTED

## 1. Goal

Select the smallest testable device-to-host contract for Week 5 G1: the ESP32-S3 generates known synthetic mono samples at a declared 48 kHz rate, and the Python host receives and checks them. This test is independent of INMP441 acquisition and the open ECM ADC path.

This is a proposal, not a unilateral freeze. USB class, final wire format and integrity policy require explicit B/C agreement.

## 2. Transport candidate

- Physical medium: wired USB; Wi-Fi/BLE are outside the core data path.
- CDC-ACM-style serial is the rapid-prototyping candidate, pending Ege's acceptance.
- Before coding against a connector, identify which physical USB-C port on the purchased N16R8 board is routed to the intended USB controller. The seller listing is not a board schematic.
- ESP32-S3 USB Serial/JTAG is fixed-function CDC serial/JTAG; USB-OTG/TinyUSB is a separate firmware-capable device path. Decide explicitly which controller/connector the host uses.
- USB Full-Speed theoretical line rate is not a measured stream rate. G1 records actual received throughput and sample continuity.

## 3. Proposed acquisition contract

| Item | Proposal | Status |
|---|---|---|
| Sample rate | 48,000 logical mono samples/s | Existing project baseline; clock measurement pending |
| Logical channels | 1 | Proposal for host API |
| INMP441 source format | I²S, 24-bit two's complement, MSB-first; MSB delayed by one SCK from half-frame start; 64 SCKs/WS frame | Datasheet-backed; real slot extraction pending |
| BCLK | 3.072 MHz nominal at 48 kHz × 64 SCK/frame | Derived; measure on board |
| Host payload | S32_LE signed 32-bit; decode 24-bit microphone word and sign-extend to int32 | Proposed; verify signedness / alignment on physical capture |
| Audio frame | 256 mono samples | Proposal; sample_count permits shorter final frame |
| Payload bytes | 256 × 4 = 1,024 bytes/frame | Derived |
| I²S DMA | 256 WS frames/block, 4 descriptors; 5.333 ms/block, 21.333 ms pool. Actual raw buffer bytes depend on one-slot versus two 32-bit slot allocation | Tuning proposal; validate |
| Frame sequence | uint32 increments per frame, modulo 2³² | Proposal |
| Sample index | uint64 first_sample_index; starts zero per session, increments by sample_count | Proposal |
| Timestamp | uint64 monotonic device timestamp in microseconds, anchored to first sample; later frame times derive from sample index / 48,000 | Proposal; drift/uncertainty measured later |
| Telemetry | Flags/counters for invalid config, I²S/DMA overrun, ring-buffer overflow, USB timeout/short write, stop reason and host-detected continuity failures | Minimum content proposed; exact bit fields open |
| CRC/checksum | OPEN. Initial G1 may use deterministic sample + continuity comparison; that does not freeze the long-term integrity policy | Joint decision required |

At 48 kHz with S32_LE, audio is 192,000 bytes/s. A 40-byte header on 187.5 frames/s adds 7,500 bytes/s, about 199,500 bytes/s before any optional trailer. This is capacity planning only, not measured throughput.

## 4. Proposed v0 header — for review

Proposed fixed header: 40 bytes; multi-byte numeric fields little-endian.

| Field | Size | Meaning |
|---|---:|---|
| Sync word “AUCF” | 4 bytes | Byte-stream resynchronization candidate |
| protocol_version | uint8 | Draft version; actual value assigned by B/C |
| frame_type | uint8 | HELLO, START, AUDIO, STATUS or STOP family |
| header_length | uint16 | Proposed 40 |
| frame_sequence | uint32 | Per-session frame counter |
| first_sample_index | uint64 | First logical mono sample in frame |
| timestamp_us | uint64 | Device monotonic timestamp anchor for first sample |
| sample_rate_hz | uint32 | 48,000 nominal |
| channel_count | uint8 | 1 logical channel |
| sample_encoding | uint8 | Proposed S32_LE |
| sample_count | uint16 | 256 full frame; final frame may be shorter |
| payload_length_bytes | uint16 | For S32_LE, sample_count × 4 |
| status_flags | uint16 | Versioned status bit field |

AUDIO frame proposal: 40-byte header then exactly payload_length_bytes. CRC/checksum trailer is not frozen here; agree integrity mode and resynchronization rules before closing the protocol. Host validates sync, header length, type, count/length consistency, sequence and sample index.

## 5. Proposed lifecycle / handshake

1. Host sends HELLO_REQ; device replies HELLO_ACK with protocol version, board/firmware descriptor, supported rates, channels, encoding and capabilities.
2. Host sends START_REQ with requested rate/channel/encoding. Device replies START_ACK with actual accepted settings and new session ID/epoch. Host must not stream/parse as an accepted configuration until the ACK matches.
3. Device sends AUDIO frames. USB writes occur in task context, not an I²S ISR. STATUS / stop summary carries device error counters.
4. Host sends STOP_REQ. Device stops at a frame boundary and returns STOP_ACK with final frame/sample counts and counters.
5. Disconnect/restart creates a new session ID, resets sample_index to zero inside the new session and causes host to discard incomplete frames from the previous session.

Exact opcodes, timeouts, session ID fields and CDC-ACM versus Vendor Bulk remain OPEN.

## 6. Week 5 G1 acceptance proposal

For a 10-second 48 kHz synthetic stream:
- Expected samples: 480,000.
- With 256 samples/frame: 1,875 audio frames.
- All headers and payload lengths parse successfully.
- Host receives exactly 480,000 logical samples; deterministic sample sequence matches numerically; zero missing, duplicate or reordered frames/samples.
- Zero unexpected device overflow / DMA / USB timeout counters.
- A 100 Hz synthetic sine is plotted; host spectral estimate has dominant frequency 100 Hz ±1 Hz.
- Log duration, actual throughput, device counters, host device/port identification, firmware commit SHA and environment versions.

This is a proposed acceptance test, not evidence that G1 has passed.

## 7. Explicit review request for Ege

Please review: (1) CDC-ACM vs Vendor Bulk; (2) sync/header/frame types; (3) S32_LE encoding; (4) I²S slot extraction, signedness and alignment; (5) frame sequence and cumulative sample-index semantics; (6) timestamp base/timebase; (7) error flags; (8) CRC/checksum or alternative integrity policy; (9) START/STOP and handshake semantics; (10) disconnect/reconnect behaviour.

Keep all undecided fields OPEN until joint review is recorded.
