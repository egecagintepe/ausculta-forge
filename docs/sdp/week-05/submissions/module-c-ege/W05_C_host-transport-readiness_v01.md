# AuscultaForge — Week 05 Module C Technical Report
## Host Transport Readiness & Plug-and-Play Integration Architecture

- **Document ID:** `W05_C_host-transport-readiness_v01`
- **Author:** Ege Çağın Tepe (Module C Lead — Software & Host Application)
- **Module:** Module C (Host Architecture, DSP, UI & System Integration)
- **Status:** **PROPOSED / HOST-READY — PENDING JOINT B→C PROTOCOL APPROVAL**
- **Target Hardware:** ESP32-S3 Native USB (Hardware Rev-A)
- **Reference Profile:** PUI DMM-4026 MEMS Baseline (`rev_a_pui_dmm4026`, 48 kHz, 24-bit in 32-bit container, 1 ch)

---

## 1. Executive Summary

During Sprint 03 (*Plug-and-Play Host Transport Readiness*), Module C implemented and verified the host-side acquisition supervisor, transport boundaries, and lifecycle management required to interface directly with the physical ESP32-S3 Native USB bridge.

To prevent premature coupling to unapproved hardware contracts, the architecture establishes strict, decoupled abstraction boundaries between:
1. **Raw byte streaming** (`DeviceTransport`),
2. **Wire frame decoding** (`DevicePacketDecoder`),
3. **Sample normalization & bounds validation** (`packet_to_sample_block`), and
4. **Scientific DSP, recording & visualization** (`StreamManager`).

When Module B (Ozan) and Module C (Ege) jointly approve the final B→C wire protocol (DW03-09, DW03-10, DW03-12), physical USB acquisition will be activated by dropping in a minimal, single-class concrete transport adapter without modifying the DSP engine, session recording pipeline, state machine, or React frontend.

---

## 2. Decoupled 4-Layer Architecture

```
[ ESP32-S3 Native USB Hardware ]
               │
               ▼  (Raw Wire Bytes: chunks, fragments, line noise)
┌───────────────────────────────────────────────────────────────┐
│ Layer 1: Physical Byte Transport & Supervisor                 │
│ - DeviceTransport (open, read, close, is_connected)           │
│ - TransportSupervisor (background thread, ownership lock)     │
│ - Guaranteed cancellation, join timeouts, zero orphan threads │
└──────────────────────────────┬────────────────────────────────┘
                               │ (Raw byte chunks)
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ Layer 2: Semantic Packet Framing & Decoding                   │
│ - DevicePacketDecoder (feed_bytes, reset)                     │
│ - Sync magic seeker (recovers from preamble line noise)       │
│ - Reassembly accumulator (buffers fragmented sub-frame reads) │
│ - Frame slicer (unpacks concatenated frames from single read) │
│ - CRC-16 integrity validation & error accounting              │
└──────────────────────────────┬────────────────────────────────┘
                               │ (DeviceSamplePacket: integer samples)
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ Layer 3: Sample Normalization & Legal Range Checking          │
│ - packet_to_sample_block()                                    │
│ - Verifies 24-bit signed bounds [-8388608, 8388607]           │
│ - Normalizes to [-1.0, 1.0] float32 SampleBlock               │
└──────────────────────────────┬────────────────────────────────┘
                               │ (SampleBlock: normalized float32)
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ Layer 4: Pipeline Processing, Session Recording & UI Display  │
│ - StreamManager (ingest_device_packet)                        │
│ - FullRateDspPipeline (Butterworth/Bessel, quality monitor)   │
│ - SessionRecorder (full-rate uncorrupted WAV + session.json)  │
│ - DisplayAggregator (decoupled 30-60 Hz UI websocket frames)  │
└───────────────────────────────────────────────────────────────┘
```

### Boundary Responsibilities

| Layer | Component | Input | Output | Invariants & Guarantees |
|---|---|---|---|---|
| **Layer 1** | `DeviceTransport`<br>`TransportSupervisor` | USB Endpoints / VCP | Raw byte chunks (`bytes`) | Single-reader ownership enforcement; graceful cancellation; join timeouts; bounded memory; no leaked OS handles. |
| **Layer 2** | `DevicePacketDecoder`<br>`ReferenceFramedPacketDecoder` | Arbitrary byte chunks | `list[DeviceSamplePacket]` | Partial frames are **never** emitted prematurely; preamble noise is skipped; corrupt CRC frames are flagged with `crc_ok=False`. |
| **Layer 3** | `packet_to_sample_block` | `DeviceSamplePacket` | `SampleBlock` | Hardware integer values are validated against bit-depth limits; converts to canonical `[-1.0, 1.0]` float32. |
| **Layer 4** | `StreamManager`<br>`FullRateDspPipeline` | `SampleBlock` | Processed audio & UI display | CRC-failed packets are dropped from DSP; every valid sample is recorded; display rate is decoupled from 48 kHz audio rate. |

---

## 3. Blocked Protocol Decisions (Joint B→C Status)

The following architectural decisions remain **PROPOSED / NOT APPROVED** pending formal joint review and hardware verification between Module B and Module C:

### 3.1. DW03-12: USB Class & Endpoint Configuration
- **Option A (Proposal):** USB CDC-ACM (Virtual COM Port). Simple driverless access on modern OSes; configured via `CdcAcmTransportConfig(port, baudrate, timeout_s)`.
- **Option B (Alternative):** USB Vendor Bulk (WinUSB / pyusb). Lower OS stack overhead; configured via `VendorBulkTransportConfig(vid, pid, read_endpoint, write_endpoint)`.
- **Status:** Concrete physical adapter is deliberately left in `PendingHardwareTransportFactory`. No unapproved COM port or VID/PID has been hardcoded.

### 3.2. DW03-09: Frame Synchronization Magic & CRC-16 Specification
- **Sync Magic:** Proposal is `0xAA55` (2 bytes, little-endian). Awaiting Module B confirmation.
- **CRC-16 Specification:** Proposal is CRC-16-CCITT (polynomial `0x1021`, initial `0xFFFF`). The following parameters are **not yet finalized**:
  - Exact polynomial & initialization vector.
  - Input bit reflection (`refin`) and output bit reflection (`refout`).
  - XOR output mask (`xorout`).
  - Byte endianness on the wire.
  - Exact coverage (header-only vs header + payload).

### 3.3. DW03-10: Sample Representation & Alignment
- **Acoustic Profile:** PUI Audio DMM-4026 MEMS reference microphone (`rev_a_pui_dmm4026`).
- **Sample Format:** 32-bit slot containing 24-bit meaningful signed PCM data, little-endian, mono, 48,000 Hz.
- **Constraint:** Must **not** be replaced with INMP441 assumptions or arbitrary 16-bit truncations without Module A/B joint specification.

---

## 4. Module B Integration Checklist (For Ozan)

This checklist provides the exact requirements for Module B firmware to achieve zero-friction integration with the Module C host runtime.

### Step 1: USB Transport Configuration
- [ ] Choose USB device class: CDC-ACM (VCP) or Vendor Bulk.
- [ ] If CDC-ACM:
  - Default baud rate (e.g., 115200 or 921600; note CDC-ACM operates at USB full-speed 12 Mbps regardless of baud rate).
  - Enable DTR/RTS flow control support.
- [ ] If Vendor Bulk:
  - Document USB VID and PID (e.g., Espressif VID `0x303A`).
  - Designate IN endpoint address (typically `0x81`) for streaming sample packets.
  - Designate OUT endpoint address (typically `0x01`) for control commands.

### Step 2: Binary Frame Structure
- [ ] Implement the proposed binary frame layout (or provide approved alternative):
  ```
  Offset   Size (B)   Type      Description
  0        2          uint16    Sync Magic (Proposal: 0xAA55)
  2        1          uint8     Protocol Version (Proposal: 1)
  3        1          uint8     Flags (0x01 = CRC Valid, 0x02 = Stream Active)
  4        4          uint32    Sequence Number (Monotonically ascending, 0 .. 2^32-1)
  8        8          uint64    ESP32 Timestamp (Microseconds since boot)
  16       N * 4      int32[]   Raw PCM Audio Samples (24-bit signed in 32-bit container)
  16+N*4   2          uint16    Frame CRC (Proposal: CRC-16-CCITT)
  ```
- [ ] Ensure frame payload size ($N$ samples) is fixed or bounded (e.g., 64, 128, or 256 samples per frame).
- [ ] Ensure byte order is explicitly little-endian (`<`) for all multi-byte fields.

### Step 3: CRC-16 Calculation
- [ ] Confirm polynomial and parameters:
  - Standard CCITT: `0x1021`, init `0xFFFF`.
- [ ] Compute CRC over bytes `[0 .. 16 + N*4 - 1]` (entire header + sample payload).
- [ ] Append 2-byte CRC at the end of the frame in little-endian order.

### Step 4: Disconnection & Error Behavior
- [ ] On USB unplug or host port close, ESP32-S3 must gracefully flush/discard pending DMA buffers.
- [ ] On USB cable re-insertion, ESP32-S3 must reset sequence counter to 0 (or continue monotonically) without hanging the I2S peripheral.

### Step 5: Host Adapter Drop-In
- [ ] Once Steps 1–4 are signed off, implement the single-class concrete transport adapter in `software/pcg_app/device_runtime.py`:
  ```python
  class SerialCdcTransport(DeviceTransport):
      def __init__(self, port: str, baudrate: int = 115200) -> None: ...
      def open(self) -> bool: ...
      def close(self) -> None: ...
      def is_connected(self) -> bool: ...
      def read(self, max_bytes: int = 4096, timeout_s: float = 0.05) -> bytes: ...
      def write_control(self, data: bytes) -> int: ...
  ```
- [ ] Register `SerialCdcTransport` in `TransportFactory`.
- [ ] Run full test suite: `.venv\Scripts\python.exe -m pytest software/tests/test_transport_readiness.py`.

---

## 5. Automated Verification Results

All 16 dedicated transport readiness tests pass cleanly with zero warnings:

```
software/tests/test_transport_readiness.py::test_layer1_byte_transport_boundary PASSED
software/tests/test_transport_readiness.py::test_layer2_packet_decoder_boundary PASSED
software/tests/test_transport_readiness.py::test_layer3_sample_normalization_boundary PASSED
software/tests/test_transport_readiness.py::test_fragmented_byte_reads_not_prematurely_emitted PASSED
software/tests/test_transport_readiness.py::test_combined_concatenated_frames_in_single_read PASSED
software/tests/test_transport_readiness.py::test_preamble_garbage_noise_recovery PASSED
software/tests/test_transport_readiness.py::test_corrupt_crc_frame_flagged PASSED
software/tests/test_transport_readiness.py::test_supervisor_single_reader_ownership PASSED
software/tests/test_transport_readiness.py::test_supervisor_clean_stop_and_join PASSED
software/tests/test_transport_readiness.py::test_supervisor_read_timeout_tolerance PASSED
software/tests/test_transport_readiness.py::test_supervisor_error_callback_propagation PASSED
software/tests/test_transport_readiness.py::test_abrupt_disconnect_finalizes_session_and_preserves_samples PASSED
software/tests/test_transport_readiness.py::test_reconnect_recovery_lifecycle PASSED
software/tests/test_transport_readiness.py::test_transport_configs_validation PASSED
software/tests/test_transport_readiness.py::test_pending_hardware_factory PASSED
software/tests/test_transport_readiness.py::test_pui_reference_profile_preservation PASSED
============================= 16 passed in 3.13s ==============================
```

Overall repository test suite: **299 passed, 1 warning (deprecation), 0 failed**.
Frontend check: **0 lint errors, production bundle built cleanly**.
