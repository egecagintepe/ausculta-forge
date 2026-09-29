# Module B â†’ Module C Interface Requirements
## Week-02 Draft v0.1

- **Status:** DRAFT / WEEK-02
- **Last Updated:** 2026-09-29
- **Interface Owners:**
  - Ozan â€” Producer / Module B (Embedded Acquisition & Data Path)
  - Ege â€” Consumer / Module C (Computer Application & Quality Assessment)
- **Course Context:** EEE495 Senior Design Project I / Semester I â€” Week 2
- **Relevant GitHub Issues:**
  - [#2 ([EEE495][W2][B] Embedded acquisition architecture)](https://github.com/egecagintepe/ausculta-forge/issues/2)
  - [#4 ([EEE495][W2][C] Module-C status and B-to-C interface requirements)](https://github.com/egecagintepe/ausculta-forge/issues/4)
- **Purpose:** Define what the host computer application requires from the embedded acquisition data path without prematurely freezing the wire-level packet layout.

> [!IMPORTANT]
> **THIS IS A REQUIREMENTS DOCUMENT. THIS IS NOT THE FINAL PACKET SPECIFICATION.**
> The final binary frame layout, byte packing, and endpoint descriptors will be drafted jointly during Week 3 and frozen after hardware transport assumptions and bench tests are experimentally verified.

---

## 1. Proposed Acquisition Baseline

The following baseline parameters represent the current engineering consensus between Modules B and C as **PROPOSED** targets for Semester I:

- **Signal Modality:** Single-channel (mono) acoustic phonocardiogram (PCG).
- **Nominal Sampling Rate ($f_s$):** 48,000 Hz (48 kHz) continuous acquisition. While diagnostic heart sounds lie predominantly below 500 Hz, 48 kHz provides wide margin for anti-aliasing filter transitions, preserves high-frequency acoustic characteristics of mechanical murmurs and valve clicks, and avoids complex non-integer hardware resampling inside the microcontroller.
- **Streaming Mode:** Continuous synchronous streaming from MCU to PC host over wired transport.
- **Transport Medium:** ESP32-S3 Native USB (hardware physical layer established).
- **Sample Representation Convention:**
  - As formalized in `software/pcg_app/device_runtime.py` (`AcquisitionProfile`), the proposed hardware container is a 32-bit word carrying 24-bit meaningful signed integer sensor data (`signed_pcm`).
  - The host converts accepted valid integer frames into normalized $[-1.0, +1.0]$ float32 `SampleBlock` streams for downstream DSP and session recording.
- **Continuity Observability:** Sample continuity must be verifiable by the host through an explicit counter mechanism embedded in the stream, entirely decoupled from operating system scheduling or USB packet arrival timing.
- **Stream State Distinguishability:** The host must deterministically distinguish between:
  1. *No device present* on host bus (`ABSENT`).
  2. *Stream stalled / interrupted* mid-acquisition (`INTERRUPTED`).
  3. *Corrupted / malformed transmission* (`ERROR`).
  4. *Healthy continuous data flow* (`STREAMING`).

---

## 2. Required Information from Module B

To guarantee deterministic ingestion, scientific provenance, and real-time stream quality assessment, every message or frame transmitted by the embedded layer must convey the following conceptual information to Module C:

1. **Protocol / Schema Version:** Explicit version identifier (e.g., protocol major/minor) allowing the host to reject mismatched firmware protocols before parsing data.
2. **Packet / Message Type Identifier:** Field distinguishing between sample streaming frames, control/handshake responses, and diagnostic/error telemetry events.
3. **Monotonic Sample Counter / Continuity Mechanism:** A strictly incrementing counter (either sequential packet index or cumulative sample index) with well-defined rollover rules.
   *(Metrological Rule: Wall-clock timestamps do NOT replace the monotonic continuity counter. The host must NEVER infer stream continuity or sample loss purely from host-side packet arrival time).*
4. **Payload Sample Count:** Exact count of acoustic samples contained in the immediate payload block (supporting fixed or variable block sizes without framing ambiguity).
5. **Declared Sample Rate:** Nominal sampling frequency in Hertz (e.g., 48,000 Hz) confirmed by MCU hardware clock configuration.
6. **Channel Count:** Number of interleaved channels (nominally 1 for mono PCG).
7. **Sample Representation & Alignment Convention:** Explicit bit-depth convention (e.g., 24-bit meaningful sensor PCM left-aligned or sign-extended in 32-bit slot, little-endian byte order).
8. **Device & Stream Status Flags:** Bitfield indicating MCU operational state (e.g., ADC/I2S running, PLL locked, mute status).
9. **Hardware Overflow / Drop Indication:** Explicit error flags asserted if the MCU detects an internal DMA FIFO overrun, circular buffer wrap, or dropped sample event prior to USB transmission.
10. **Data Integrity Verification (CRC / Checksum):** An integrity check field (e.g., CRC-16 or CRC-32) spanning the packet header and sample payload to detect USB bus transmission corruption.
11. **Stream Start / Stop Semantics:** Clean boundary indicators signaling acquisition session commencement and graceful termination.
12. **Device Identification & Firmware Version:** Readily accessible hardware identifier (VID/PID, serial number string) and firmware build string reported during initial connection handshake.

---

## 3. Host Behaviors & Architectural Guarantees

Module C guarantees the following behaviors upon ingesting the data stream from Module B:

- **Discontinuity Detection:** The host ingestion pipeline tracks the monotonic sample counter. Any skipped sequence index is immediately flagged as a sample drop event, cataloged in real-time telemetry, and recorded in the session metadata.
- **State Transition Enforcement:** The host state machine (`DeviceState` in `software/pcg_app/device_runtime.py`) enforces strict lifecycle transitions. A stalled stream transitions from `STREAMING` to `INTERRUPTED`; transport disconnect transitions to `ABSENT`.
- **Incompatible Profile Rejection:** If the device reports a protocol version, channel count, or container format inconsistent with the active acquisition profile, the host transitions to `INCOMPATIBLE` and halts ingestion, preventing data corruption.
- **Scientific Metadata Provenance:** Every recorded session captures full acquisition provenance (sample rate, bit container, dropped packet count, total sample count, Git commit SHA, and device ID) in a structured JSON sidecar (`session.json`).
- **Truthful Telemetry (No Fabricated Indicators):** The user interface displays only verified hardware states. Indicators such as "Connected", "Signal Quality", and "Dropped Packets" strictly reflect verified telemetry. Synthetic or estimated connection health is prohibited.
- **Uncompromised DSP & Storage Coupling:** Accepted sample frames are converted directly into `SampleBlock` instances and routed identically to:
  1. Full-rate raw session storage (unaltered PCM/WAV).
  2. Stateful streaming bandpass filters (`pcg_core.dsp`).
  3. Bounded display decimation pipeline (`pcg_app.display_pipeline`).

---

## 4. Week-3 Open Decisions Matrix

The following engineering decisions must be jointly evaluated and frozen during the Week-3 integration sprint:

| Decision Item | Primary Owner | Needed By | Current Status | Description & Alternatives Under Review |
|---|---|---|---|---|
| **USB Transport Class** | Ozan (Mod B) / Ege (Mod C) | Week 3 | **OPEN â€” WEEK 3** | USB CDC-ACM (virtual COM port) vs USB Vendor Bulk endpoint. CDC-ACM offers simple cross-platform drivers; Vendor Bulk offers lower driver overhead. |
| **Final Wire Frame Layout** | Ege (Mod C) / Ozan (Mod B) | Week 3 | **OPEN â€” WEEK 3** | Binary byte structure: header field order, byte offsets, sync words, and endianness (little-endian proposed). |
| **Sample Payload Encoding** | Ozan (Mod B) / Ege (Mod C) | Week 3 | **OPEN â€” WEEK 3** | 24-bit packed integer (3 bytes/sample) vs 24-bit in 32-bit slot (4 bytes/sample). 32-bit simplifies DMA alignment; 24-bit packed saves 25% USB bandwidth. |
| **Packet Size (Samples/Frame)** | Ozan (Mod B) / Ege (Mod C) | Week 3 | **OPEN â€” WEEK 3** | Block size trade-off: 128, 256, or 512 samples per frame (at 48 kHz: 2.67 ms, 5.33 ms, or 10.67 ms latency per packet). |
| **Continuity Counter Width** | Ege (Mod C) | Week 3 | **OPEN â€” WEEK 3** | 16-bit vs 32-bit sequence counter. 16-bit at 100 packets/sec rolls over in ~11 minutes; 32-bit avoids rollover ambiguity for multi-hour runs. |
| **Status / Error Bitmask** | Ozan (Mod B) | Week 3 | **OPEN â€” WEEK 3** | Exact bit definitions for DMA overflow, I2S sync loss, and clipping flags. |
| **CRC / Integrity Polynomial** | Ege (Mod C) / Ozan (Mod B) | Week 3 | **OPEN â€” WEEK 3** | CRC-16-CCITT vs CRC-32-IEEE. Computational cost on ESP32-S3 vs error detection capability. |
| **Device Identification Handshake** | Ege (Mod C) | Week 3 | **OPEN â€” WEEK 3** | USB descriptor strings vs dedicated ASCII/JSON handshake command on control endpoint. |

---

## 5. Acceptance Test Criteria for Future Interface

The following verification suite defines the future acceptance criteria required before the Module B $\to$ Module C interface can be formally certified:

1. **Synthetic Waveform Stream Test:** Firmware transmits a known mathematical sequence (e.g., continuous 100 Hz full-scale sine or sawtooth wave). Host verifies sample-for-sample waveform fidelity.
2. **Sample Count Exactness:** Host records continuous acquisition over a timed interval. Verified sample count must equal $f_s \times t_{\text{elapsed}}$ within hardware crystal tolerance ($\pm 50\text{ ppm}$).
3. **Zero Undetected Discontinuity:** In a healthy continuous stream, every sequential packet index $N, N+1, N+2, \dots$ must be received monotonically with zero missing sequence numbers.
4. **Intentional Discontinuity Injection:** Firmware intentionally drops 5 packets. Host must flag exactly 5 missing packets and record the gap in telemetry.
5. **Corrupted Frame Rejection:** Frames with intentionally flipped bits or invalid CRC must be rejected by host ingestion and increment the CRC error counter without crashing the stream.
6. **Incompatible Version Handshake Rejection:** Device reporting unsupported protocol version (e.g. "9.9") must be rejected gracefully with `INCOMPATIBLE` state.
7. **Clean Disconnect & Reconnect Handling:** Abrupt physical cable disconnect must transition state cleanly to `INTERRUPTED` / `ABSENT` without hanging threads or leaving locked files. Subsequent reconnection must restore `READY` state.
8. **Sustained 48 kHz Throughput:** Stream must run continuously without buffer overrun or host backpressure stalls.
9. **WAV/Session Integrity Verification:** Raw session recordings must match the ingested stream byte-for-byte upon offline replay.

> [!NOTE]
> None of the above hardware acceptance tests have been run yet. These tests will be executed starting in Week 5 upon operational bench setup.
