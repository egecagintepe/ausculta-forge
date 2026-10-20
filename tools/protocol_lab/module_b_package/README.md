# AuscultaForge — Module B (Embedded) Interface Review Package
## Portable C11 Acquisition Core, Wire Framing Proposal & Hardware Bring-Up Guidance

- **Package Author:** Ege Çağın Tepe (Module C / Software Integration)
- **Primary Recipient & Reviewer:** Ozan (Module B / Embedded Acquisition & Data Path)
- **Project Stage:** EEE495 / EEE496 Senior Design Project — Academic Week 05
- **Package Status:** **PROPOSED / EXPERIMENTAL FOR REVIEW (NON-BLOCKING)**
- **Formal Review Status:** **PENDING MODULE B JOINT REVIEW & SIGN-OFF** (Ozan has NOT yet formally reviewed or approved this implementation).

---

## 1. Executive Purpose & Collaboration Protocol

Welcome, Ozan! This package was engineered in Module C to provide a **production-ready, portable C11 and Python laboratory** in preparation for the arrival and physical bring-up of our ESP32-S3 hardware.

### Core Principles of This Package:
1. **Zero Pre-emption:** This is an **engineering proposal and review package**, not an imposed frozen contract. Ozan retains full architectural authority and ownership over production firmware under `firmware/`.
2. **Hardware-Free Verification:** Everything in this package compiles with standard GCC/Clang on host operating systems and has been verified with 100% mathematical known-answer tests in Python before flashing a single MCU.
3. **Bring-Up Velocity:** When the ESP32-S3 hardware arrives, we should spend our laboratory time measuring real PUI MEMS acoustic noise, I2S DMA timing, and physical USB enumeration — **not** debugging basic byte endianness, integer sign-extension, or ring buffer concurrency from scratch.

---

## 2. Package Directory Structure

```
tools/protocol_lab/module_b_package/
├── README.md                     <- This executive briefing & review checklist
├── PROTOCOL_SPECIFICATION.md     <- Exact byte offsets, bitfields, and wire layout tables
├── TRADE_OFFS_ANALYSIS.md        <- CDC-ACM vs Bulk, CRC16 vs CRC32, timestamping trade-offs
├── ESP_IDF_INTEGRATION_GUIDE.md  <- ESP-IDF v5.x integration instructions & DMA code example
├── verify_g1_bringup.py          <- Standalone Python tool to test physical hardware on USB
└── include/                      <- Portable C11 interface headers (drop-in ready)
    ├── protocol_types.h          <- Profile A (16B) and Profile B (40B) struct definitions
    ├── packet_framing.h          <- Endian-safe packet builders & CRC routines
    ├── waveform_gen.h            <- Deterministic 100 Hz sine, ramp & boundary generators
    └── ring_buffer.h             <- Lock-free SPSC circular buffer with C11 atomics
```

---

## 3. Quickstart: How to Evaluate This Package

### Step 1: Run C11 Unit Tests (Including Multi-Threaded SPSC Concurrency Test)
```powershell
gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2 -Itools/protocol_lab/c/include -o test_c_core.exe tools/protocol_lab/c/tests/test_c_protocol_core.c tools/protocol_lab/c/src/waveform_gen.c tools/protocol_lab/c/src/ring_buffer.c tools/protocol_lab/c/src/packet_framing.c -lm -lpthread
.\test_c_core.exe
Remove-Item test_c_core.exe
```

### Step 2: Run the 10-Second G1 Simulation Suite
```powershell
python tools/protocol_lab/python/ten_second_g1_bench.py
```
This runs the compiled C generator through a live streaming pipe into the Python decoder, verifying:
- Exactly 480,000 samples across 1,875 frames @ 256 samples/frame (48 kHz).
- 100.0 Hz pure sine spectral peak with SNR = 57.45 dB.
- Monotonic sample ramp counter continuity (zero gaps).
- Automated trapping of 5 simulated errors (dropped frame, CRC corruption, duplicate frame, line noise, timestamp regression).

---

## 4. Comprehensive Decisions Requiring Joint Module B / C Agreement

The following 10 architectural decisions remain proposed and require joint approval between Ozan (Module B) and Ege (Module C):

| # | Engineering Decision | Module C Proposal | Alternatives / Considerations | Sign-Off Status |
| :-: | :--- | :--- | :--- | :-: |
| **1** | **Physical USB Hardware** | **ESP32-S3 Native USB OTG (GPIO 19/20)** | External CP2102 USB-UART Bridge (limits throughput to 2-3 Mbps with higher CPU load) | OPEN |
| **2** | **USB Device Class** | **USB CDC-ACM (Virtual COM Port)** | USB Vendor Bulk (WinUSB / libusb; requires custom INF driver) | OPEN |
| **3** | **Framing Profile** | **Profile B (40-byte header, 256 samples/frame)** | Profile A (16-byte header, 512 samples/frame) | OPEN |
| **4** | **40-Byte Header Layout** | **Naturally aligned 40-byte field layout** (uint64 on 8B, uint32 on 4B, uint16 on 2B) | Compact unaligned packed header with pragma pack | OPEN |
| **5** | **PCM Word Representation** | **Signed 24-bit in 32-bit container (LSB-aligned, sign-extended)** | MSB-aligned (I2S left-justified) or 3-byte packed PCM (`int24_t`) | OPEN |
| **6** | **Integrity Check (CRC)** | **CRC-32 (IEEE 802.3, 4-byte trailer)** | CRC-16-CCITT (2 bytes) or hardware USB CRC only | OPEN |
| **7** | **Sequence & Sample Counter** | **32-bit sequence ID with RFC 3550 signed wrapping + 64-bit sample index start** | 32-bit sequence only, or non-wrapping 64-bit sequence | OPEN |
| **8** | **Hardware Timestamping** | **64-bit microsecond timestamp (`esp_timer_get_time()`)** | 32-bit millisecond tick or host-assigned timestamp | OPEN |
| **9** | **Overflow Counter Semantics** | **Cumulative dropped sample counter in header (`mcu_buffer_drops`)** | Delta dropped samples per frame, or status bitmask flag | OPEN |
| **10**| **Streaming Lifecycle** | **Auto-start on USB DTR assertion, auto-stop on disconnect** | Explicit bidirectional start/stop command opcodes (`0x03` / `0x05`) | OPEN |

---

## 5. Concise Review Checklist for Ozan

You can copy and paste this checklist into our team discussions or GitHub review comments:

```markdown
### Module B Review Checklist — AuscultaForge Protocol Proposal
- [ ] 1. USB Interface: Agree to ESP32-S3 Native USB (GPIO 19/20) for Milestone G1?
- [ ] 2. USB Class: Agree to CDC-ACM for Day-1 driverless bring-up?
- [ ] 3. Header Framing: Approve 40-byte Profile B header or request field modifications?
- [ ] 4. S32_LE Format: Confirm LSB-aligned 24-bit signed integer representation?
- [ ] 5. Frame Capacity: Confirm 256 samples/frame (187.5 fps, 5.33 ms packet interval)?
- [ ] 6. CRC Algorithm: Approve CRC-32 (IEEE 802.3) trailer or prefer CRC-16?
- [ ] 7. Timestamp: Approve `esp_timer_get_time()` 64-bit microsecond counter?
- [ ] 8. Buffer Architecture: Approve lock-free SPSC circular buffer pattern between DMA and TinyUSB?
- [ ] 9. Error Accounting: Approve `mcu_buffer_drops` cumulative sample drop counter?
- [ ] 10. Bring-Up Validation: Agree to run `verify_g1_bringup.py` upon initial board programming?
```
