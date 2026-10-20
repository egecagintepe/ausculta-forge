# AuscultaForge — Protocol Engineering Trade-Offs & Architecture Analysis
## Module B & Module C Interface Decision Matrix (DW03-08 through DW03-12)

- **Prepared by:** Ege Çağın Tepe (Module C)
- **For Review by:** Ozan (Module B)
- **Course:** EEE495 / EEE496 Senior Design Project — AuscultaForge
- **Objective:** Provide a rigorous comparative trade-off analysis of physical USB transport, integrity mechanisms, framing parameters, and buffer management to prepare for Week-5 hardware bring-up.

---

## 1. Physical USB Class: CDC-ACM vs. Vendor-Specific Bulk (DW03-12)

| Dimension | Option A: USB CDC-ACM (Virtual COM Port) | Option B: Vendor-Specific Bulk (WinUSB / libusb) |
| :--- | :--- | :--- |
| **Operating System Support** | Native in-box driver on Windows 10/11 (`usbser.sys`), Linux (`cdc_acm`), and macOS. Zero driver installation required. | Requires WinUSB driver or WCID (Microsoft OS 2.0 Descriptors) to bind without an INF file on Windows. |
| **Host Software Ingestion** | Standard serial API (`pyserial`, `serialport`, Rust `serialport-rs`). Easy debugging via terminal emulators (PuTTY). | Requires raw USB transfer library (`pyusb`, `libusb`, Rust `nusb` or `rusb`). Cannot view raw stream in standard serial terminals. |
| **Maximum Packet Size** | Full-Speed Bulk Endpoint: 64 bytes max packet size (MPS). High-Speed Bulk: 512 bytes MPS. | Identical physical endpoint sizes (64B FS / 512B HS) at USB PHY layer. |
| **Serial Framing Overhead** | CDC-ACM header encapsulation in TinyUSB adds negligible descriptor overhead during enumeration; data stream is raw bulk bytes. | Zero CDC class overhead; raw endpoint pipe. |
| **Throughput Ceiling** | Benchmarked sustained throughput on ESP32-S3: **~800–1,200 kB/s**. Well above our 200.25 kB/s requirement. | Sustained throughput: **~1,200–2,000 kB/s** on ESP32-S3. |
| **Baud Rate Relevance** | Baud rate setting on host (e.g. 115200) is **purely virtual** in Native USB; data transfers at full USB bus speed regardless of baud setting. | No concept of baud rate. |
| **Engineering Recommendation** | **RECOMMENDED FOR DAY-1 G1 BRING-UP:** CDC-ACM provides instantaneous cross-platform compatibility, zero custom driver installation on Windows evaluation laptops, and easily meets our 200 kB/s data rate. | **EVALUATE FOR SEMESTER II (HIGH-SPEED):** If multi-channel high-rate audio or high-speed USB PHY is adopted later, migrate to Vendor Bulk. |

---

## 2. Application-Level Integrity: CRC-16 vs. CRC-32 vs. USB Hardware CRC (DW03-09)

> [!IMPORTANT]
> **Why USB Physical Link CRC is NOT Sufficient on its Own:**
> The USB physical layer already computes CRC-5 on tokens and CRC-16 on data packets. However, **USB hardware CRC is checked and discarded by the USB PHY and host USB controller hardware**. By the time data reaches the host operating system driver and userspace application:
> 1. It does NOT protect against bit flips in ESP32-S3 SRAM or I2S DMA memory.
> 2. It does NOT detect DMA buffer slips, ring-buffer FIFO overruns, or dropped FreeRTOS task queues.
> 3. It does NOT protect against host OS driver dropped transfers or USB hub buffer overruns.
> Therefore, an **application-layer integrity check is mandatory** for medical-grade audio acquisition.

| Dimension | CRC-16-CCITT (Profile A) | CRC-32 IEEE 802.3 (Profile B) | Adler-32 / Fletcher-16 |
| :--- | :--- | :--- | :--- |
| **Trailer Size** | 2 bytes per frame | 4 bytes per frame | 4 bytes / 2 bytes |
| **Overhead @ 187.5 fps** | 375 bytes/s (0.19%) | 750 bytes/s (0.39%) | 750 bytes/s (0.39%) |
| **Collision Probability** | $1 \text{ in } 65,536$ ($1.5 \times 10^{-5}$) | $1 \text{ in } 4,294,967,296$ ($2.3 \times 10^{-10}$) | Weak on short bursts / zero bytes |
| **Burst Error Detection** | Catches all burst errors $\le 16$ bits | Catches all burst errors $\le 32$ bits | Poor burst detection |
| **ESP32-S3 Computational Cost** | Theoretical estimate (~10 cycles/byte @ 240 MHz): ~4.2 $\mu$s per frame (<0.1% CPU). *Physical time on silicon: NOT MEASURED (pending test bench).* | Theoretical estimate (~10 cycles/byte @ 240 MHz): ~4.5 $\mu$s per frame (<0.1% CPU). *Physical time on silicon: NOT MEASURED (pending test bench).* | Theoretical estimate: ~2.1 $\mu$s per frame. *Physical time on silicon: NOT MEASURED.* |
| **Host Python Speed** | Pure Python: ~150 $\mu$s; C extension: ~5 $\mu$s. | Built-in C `binascii.crc32()`: **~1.2 $\mu$s** (hardware accelerated). | Python `zlib.adler32()`: ~1.5 $\mu$s. |
| **Recommendation** | Acceptable baseline for simple frames. | **STRONGLY RECOMMENDED:** The extra 2 bytes per frame adds only 0.20% overhead, but provides cryptographically rigorous burst protection and 10x faster validation in Python via built-in `binascii.crc32`. | Not recommended for audio frames with long zero runs. |

---

## 3. Frame Payload Size: 256 Samples vs. 512 Samples

| Parameter | 256 Samples per Frame (Profile B) | 512 Samples per Frame (Profile A) |
| :--- | :--- | :--- |
| **Payload Size** | $256 \times 4 = 1,024 \text{ bytes}$ ($2 \times 512\text{B}$ USB HS packets) | $512 \times 4 = 2,048 \text{ bytes}$ ($4 \times 512\text{B}$ USB HS packets) |
| **Frame Delivery Rate** | 187.5 frames / second | 93.75 frames / second |
| **Latency from Microphone** | **5.333 milliseconds** | **10.667 milliseconds** |
| **Header Overhead Ratio** | 4.30% (7,500 bytes/s) | 2.15% (3,750 bytes/s) |
| **DMA Buffer Alignment** | 1,024 bytes is a clean power-of-two (1 KiB), matching ESP32-S3 I2S DMA descriptor buffers perfectly. | 2,048 bytes (2 KiB), requires larger internal ping-pong DMA allocations. |
| **Recommendation** | **RECOMMENDED:** 5.33 ms latency provides immediate oscilloscope UI feedback and fits cleanly in 1 KiB DMA buffers without risk of FIFO starvation. | Viable alternative if USB interrupt frequency must be reduced. |

---

## 4. Frame Header Format: 16-Byte Compact vs. 40-Byte Natural-Alignment

| Dimension | Profile A (16-Byte Header) | Profile B (40-Byte Header) |
| :--- | :--- | :--- |
| **Header Length** | 16 bytes (`0x10`) | 40 bytes (`0x28`) |
| **Timestamp Precision** | 32-bit microsecond counter (wraps at ~71.5 minutes) | **64-bit microsecond counter** (never wraps in device lifetime) |
| **Sample Index Accounting**| Inferred: `seq * count` (cannot detect partial internal drops) | **Explicit 64-bit `sample_index_start`** (unambiguously reveals dropped samples) |
| **Hardware Error Reporting** | None (only general 16-bit flags) | **Dedicated `mcu_buffer_drops` counter** + explicit DMA/USB overflow flags |
| **Structure Alignment** | Packed (`#pragma pack(1)` required to avoid compiler padding) | **Naturally aligned:** uint64 on 8B, uint32 on 4B, uint16 on 2B. Identical without packing pragmas! |
| **Overhead Difference** | 3,000 bytes/s at 187.5 fps | 7,500 bytes/s at 187.5 fps (difference = 4,500 B/s = 0.036 Mbps) |
| **Recommendation** | Use as secondary / fallback profile. | **STRONGLY RECOMMENDED:** The 64-bit sample index and MCU drop counter give us irrefutable audit evidence during oral defense. |

---

## 5. Summary of Recommended Decisions for Week-5 Bring-Up

1. **USB Class (DW03-12):** Adopt **USB CDC-ACM** for G1 bring-up.
2. **Integrity (DW03-09):** Adopt **CRC-32 (IEEE 802.3)** over Header + Payload.
3. **Framing:** Adopt **Profile B (40-byte header, 256 samples, 1068 total bytes/frame)**.
4. **Timebase:** Use ESP32 hardware timer **`esp_timer_get_time()`** in microseconds (`uint64_t`).
5. **Drop Telemetry:** MCU increments `mcu_buffer_drops` whenever `tinyusb_cdcacm_write_queue` cannot accept full block due to USB backpressure.
