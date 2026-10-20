# W10 Module C — Embedded Interoperability, C Golden Vectors & Hardware Bring-Up Readiness (v01)

**Course:** EEE495 — Senior Design Project I  
**Week:** 10 — Sprint 10  
**Module:** C — Computer Application & Quality Assessment  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Review Target:** Ozan (Module B Owner — Embedded Acquisition & Hardware Integration)  
**Status:** IMPLEMENTED / READY FOR MODULE B REVIEW  
**Scope:** Cross-module interoperability tools, portable C golden vectors, hardware bring-up readiness, and interface decision audit. Does NOT replace or modify Module B's production firmware.

---

## 1. Executive Summary & Interface Decision Audit

This document constitutes Module C's deliverable for Sprint 10. The mission of this sprint is to deliver embedded-facing reference tools and verification frameworks to ensure rapid, zero-friction integration when the ESP32-S3 development board and INMP441 microphone arrive on the physical bench.

### Decision Audit Matrix: B→C Interface Decisions

| Decision ID | Interface Topic | Previous Status (Week 04/05) | Current Status (Sprint 10) | Module C Position & Rationale | Action for Physical Bring-Up |
|---|---|---|---|---|---|
| **DW03-08** | Physical Transport Medium | CLOSED (Wired ESP32-S3 Native USB) | **CLOSED** (Confirmed) | Wired Native USB eliminates wireless battery drain, Wi-Fi congestion, and BLE packet loss. | Plug into onboard Native "USB" Type-C port (`GPIO 19`/`20`). |
| **DW03-12** | USB Transport Class | PROPOSED (CDC-ACM virtual COM) | **OPEN / PENDING JOINT APPROVAL** | CDC-ACM provides zero-driver cross-platform portability on Windows (`usbser.sys`), Linux, and macOS. Avoids custom WinUSB INF signing. | Measure actual throughput on bench with Cable 2 connected. |
| **DW03-09** | Application Framing & CRC Policy | PROPOSED (16B Header + Trailing CRC-16) | **PROPOSED / NOT APPROVED** | Application framing is required to delineate sample blocks and detect buffer slip. However, byte offsets and CRC polynomial must not be frozen prematurely. | Benchmark CRC-16 vs. hardware USB CRC on physical MCU. |
| **DW03-10** | Integer Bit Alignment in 32-bit Container | OPEN (LSB-aligned vs. MSB-aligned) | **OPEN / PENDING BENCH DMA MEASUREMENT** | Standard 24-in-32 I²S DMA can stage words as LSB-aligned with sign extension ($2^{23}$ normalization) or MSB-aligned ($2^{31}$ normalization). | Inspect raw DMA buffer dump from physical INMP441 capture. |
| **DW03-11** | Sequence Counter vs. Sample Index | PROPOSED (32-bit Sequence Counter) | **PROPOSED / OPEN** | Fixed-size blocks allow exact first-sample index calculation ($\text{Seq} \times N$). Variable-length flushes require explicit first-sample accounting. | Agree on fixed vs. variable flush policy with Module B. |

> [!WARNING]
> **NO PREMATURE WIRE FREEZE:**  
> In strict accordance with the project charter, Module C has **NOT** silently finalized or frozen the wire packet format. The portable C golden-vector tools developed in this sprint test **representation-independent sample sequences and integer encodings**, preserving Module B's complete architectural ownership over production firmware.

---

## 2. Phase A: Portable C Golden-Vector Tools

To verify data representations, endianness, sign extension, and deterministic mathematical sequences independently of hardware, Module C developed a standalone C toolsuite in `tools/c_golden_vectors/`:

### 2.1 Architectural Verification
The tool verifies core architecture assumptions via `golden_generator.exe --verify-types`:
- **Word Widths:** Confirms `sizeof(int16_t) == 2`, `sizeof(int32_t) == 4`, `sizeof(uint32_t) == 4`, `sizeof(float) == 4`.
- **Endianness:** Confirms **Little-Endian** byte ordering on the host system (matching ESP32-S3 Xtensa/RISC-V native endianness).
- **Two's Complement Signedness:** Confirms negative integer representation (`-1 == 0xFFFFFFFF`).
- **24-bit to 32-bit Sign Extension:** Confirms that negative 24-bit words (e.g. `0x00800000`, representing $-8,388,608$) correctly sign-extend into 32-bit integers without sign inversion.

### 2.2 Deterministic Generated Golden Vectors
The tool generates 6 distinct golden fixtures in both binary (`.bin`) and CSV (`.csv`) formats:
1. `sine_100hz_48khz_512s_lsb`: Deterministic 100 Hz sine wave, 512 samples at 48 kHz, LSB-aligned with sign extension (normalized by $2^{23}$).
2. `sine_100hz_48khz_512s_msb`: Identical sine wave in MSB-aligned container format (lower 8 bits zeroed, normalized by $2^{31}$).
3. `counter_ramp_512s_lsb` & `counter_ramp_512s_msb`: Sequential ramp pattern (step = 1) spanning through zero crossing, used to verify DMA FIFO continuity and bit alignment.
4. `boundary_stress_lsb` & `boundary_stress_msb`: Extreme numerical boundaries including exact zero, $+1$, $-1$, $+8,388,607$ ($+2^{23}-1$), $-8,388,608$ ($-2^{23}$), and walking ones across all 24 bits.

---

## 3. Phase B: Isolated ESP-IDF Bench Reference

Module C prepared an isolated, non-production reference project in `tools/esp32_bench_example/`:
- **Target:** ESP32-S3-DevKitC-1 N16R8.
- **Components:**
  - `CMakeLists.txt` and `sdkconfig.defaults` configuring TinyUSB, CDC-ACM class, and Octal PSRAM/Flash.
  - `main/main.c`: Deterministic 480-point 100 Hz integer sine lookup table ($48,000 / 100 = 480$), double-buffered FreeRTOS streaming task, and DTR-gated CDC-ACM transmission.
- **Execution Evidence:**  
  **STATUS: NOT EXECUTED.**  
  Cross-compilation and flashing were not performed because the ESP-IDF toolchain is not installed on this workstation, and the physical development board is awaiting delivery. This reference code is ready for Ozan to inspect and compile on his ESP-IDF setup.

---

## 4. Phase C: Physical Hardware Bring-Up & Integration Checklist

A comprehensive 8-gate physical bring-up checklist was authored in `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`:
1. **Physical Inspection & Power Rails:** Multimeter verification of $3.3 \text{ V}$ rail and INMP441 wiring (`GPIO 4` SCK, `GPIO 5` WS, `GPIO 6` SD).
2. **Native USB Enumeration:** Verifying dual-port enumeration (UART COM port for logs vs. Native USB COM port for audio streaming under `usbser.sys`).
3. **I²S Clock Verification:** Oscilloscope check of continuous 3.072 MHz bit clock ($2 \times 32 \times 48,000$) and 48 kHz word select.
4. **Synthetic Sample Transmission:** Transmitting known 100 Hz tone from MCU to PC.
5. **Host Handshake & Ingestion:** Verifying `device_runtime` state transitions from `ABSENT` to `READY` to `STREAMING`.
6. **WAV Sample Count & Spectral Verification:** Confirming exactly 480,000 samples for a 10.0-second recording with a clean 100 Hz spectral peak.
7. **Disconnect/Reconnect Resilience:** Testing cable removal mid-stream, verifying safe recording finalization with `termination_reason='device_disconnected'`.
8. **Gate G1 Evidence Matrix:** Required screenshots, logic traces, and WAV files for advisor milestone sign-off.

---

## 5. Automated Python-C Equivalence Verification

An automated pytest test suite was added in `software/tests/test_c_golden_vectors.py`:
- Compares the C-generated golden fixtures against pure Python mathematical implementations.
- Asserts bit-for-bit exactness: sample difference $\equiv 0$ across all 512 samples.
- Validates that `packet_to_sample_block` normalizes C golden vectors to $[-1.0, +1.0]$ float32 with zero numerical distortion.
- Passes completely alongside all 283 existing Python unit and integration tests.
