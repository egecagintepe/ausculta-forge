# AuscultaForge — Module B (Embedded) Interface Review Package
## Portable C11 Acquisition Core, Wire Framing Proposal & Hardware Bring-Up Guidance

- **Package Author:** Ege Çağın Tepe (Module C / Software Integration)
- **Primary Recipient & Reviewer:** Ozan (Module B / Embedded Acquisition & Data Path)
- **Project Stage:** EEE495 / EEE496 Senior Design Project — Academic Week 05
- **Package Status:** **PROPOSED / EXPERIMENTAL FOR REVIEW (NON-BLOCKING)**
- **Authoritative Decisions:** DW03-08 (Wired Native USB), DW03-09 (Application CRC), DW03-10 (Sample Representation), DW03-12 (USB Class)

---

## 1. Executive Purpose & Collaboration Protocol

Welcome, Ozan! This package was engineered in Module C to provide a **production-ready, portable C11 and Python laboratory** in preparation for the arrival and bring-up of our ESP32-S3 physical hardware.

### Core Principles of This Package:
1. **Zero Pre-emption:** This is a **proposal and review package**, not an imposed frozen contract. Ozan retains full architectural authority and ownership over production firmware under `firmware/`.
2. **Hardware-Free Verification:** Everything in this package compiles with standard GCC/Clang on host operating systems and has been verified with 100% mathematical known-answer tests in Python before flashing a single MCU.
3. **Bring-Up Velocity:** When the ESP32-S3 hardware arrives, we should spend our lab time measuring real PUI MEMS acoustic noise, I2S DMA timing, and physical USB enumeration — **not** debugging basic byte endianness, integer sign-extension, or ring buffer math from scratch.

---

## 2. Package Directory Structure

```
tools/protocol_lab/module_b_package/
├── README.md                     <- This executive briefing & index
├── PROTOCOL_SPECIFICATION.md     <- Exact byte offsets, bitfields, and layout tables
├── TRADE_OFFS_ANALYSIS.md        <- CDC-ACM vs Bulk, CRC16 vs CRC32, timestamping trade-offs
├── ESP_IDF_INTEGRATION_GUIDE.md  <- ESP-IDF v5.x integration instructions & DMA code example
├── verify_g1_bringup.py          <- Standalone Python tool to test physical hardware on USB
└── include/                      <- Portable C11 interface headers (drop-in ready)
    ├── protocol_types.h          <- Profile A (16B) and Profile B (40B) struct definitions
    ├── packet_framing.h          <- Endian-safe packet builders & CRC routines
    ├── waveform_gen.h            <- Deterministic 100 Hz sine, ramp & boundary generators
    └── ring_buffer.h             <- Bounded SPSC circular buffer with exact 64-bit accounting
```

---

## 3. Quickstart: How to Evaluate This Package

### Step 1: Inspect the C Core & Run C11 Unit Tests
```bash
cd tools/protocol_lab/c
gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2 -Iinclude -o test_c_core.exe tests/test_c_protocol_core.c src/waveform_gen.c src/ring_buffer.c src/packet_framing.c -lm
./test_c_core.exe
```

### Step 2: Run the 10-Second G1 Simulation Suite
```bash
cd tools/protocol_lab/python
python ten_second_g1_bench.py
```
This runs the compiled C generator through a live streaming pipe into the Python decoder, verifying:
- Exactly 480,000 samples across 1,875 frames @ 256 samples/frame (48 kHz).
- 100.0 Hz pure sine spectral peak with SNR > 50 dB.
- Monotonic sample ramp counter continuity (zero gaps).
- Automated trapping of 5 simulated errors (dropped frame, CRC corruption, duplicate frame, line noise, timestamp regression).

### Step 3: Review Open Decisions with Ege
Please read `TRADE_OFFS_ANALYSIS.md` and review the open decisions in Section 4 below.

---

## 4. Open Joint Decisions Requiring Ozan's Sign-Off

| Decision ID | Topic | Current Module C Proposal | Alternatives to Evaluate |
| :--- | :--- | :--- | :--- |
| **DW03-09** | Application Integrity / CRC | **CRC-32 (IEEE 802.3)** appended as 4-byte trailer per 256-sample frame | CRC-16-CCITT (2 bytes), or rely on USB hardware CRC + sequence/status checks |
| **DW03-10** | Sample Representation | **Signed 24-bit PCM in 32-bit container (LSB-aligned, sign-extended)** | MSB-aligned (I2S left-justified), or 3-byte packed PCM (`int24_t`) |
| **DW03-12** | USB Device Class | **USB CDC-ACM (Virtual COM port)** for Day-1 bring-up | Vendor-Specific Bulk transfers (WinUSB / libusb) |
| **Frame Size** | Samples per Packet | **256 samples (1,024 bytes payload, 187.5 fps, 5.33 ms latency)** | 512 samples (2,048 bytes payload, 93.75 fps, 10.67 ms latency) |
| **Timestamp** | Device Timebase | **64-bit microsecond monotonic tick (`esp_timer_get_time()`)** | 32-bit millisecond counter or sample-index only |
