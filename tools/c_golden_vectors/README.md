# AuscultaForge — Portable C Golden-Vector Tools

**Course:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Module:** C (Computer Application & Quality Assessment)  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Interface Reviewer:** Ozan (Module B Owner)  
**Location:** `tools/c_golden_vectors/`  
**Status:** Verification complete on host (GCC 16.2.0 UCRT64). Standalone reference tool outside Module B production firmware.

---

## 1. Purpose & Scope

This directory contains standalone, highly portable C test utilities to generate and verify deterministic known-answer audio sample vectors prior to physical microcontroller bring-up.

### Critical Architecture Boundaries
1. **Non-Production Firmware:** This utility is **NOT** firmware for the ESP32-S3 and does not replace Ozan's firmware codebase. It runs on the host (PC) and can be used on both host and embedded targets as a math/representation reference.
2. **Wire Framing Decoupling:** In accordance with the Week 05 protocol readiness review, the byte-level wire protocol (headers, magic word `0xAA55`, framing CRC) remains **PROPOSED / NOT APPROVED**. Therefore, these golden vectors represent raw signed integer sample sequences and memory representations, rather than frozen wire packet layouts.
3. **Alignment Verification:** Provides deterministic conversions and checks for both:
   - **LSB-Aligned with Sign Extension:** 24-bit audio integer in bits [23:0], sign-extended into bits [31:24]. Range: $[-8,388,608, +8,388,607]$. Host scale factor: $2^{23}$.
   - **MSB-Aligned (Left-Justified):** 24-bit audio integer in bits [31:8], lower 8 bits zeroed. Range: $[-2^{31}, +2^{31}-256]$. Host scale factor: $2^{31}$.

---

## 2. Directory Structure

```
tools/c_golden_vectors/
├── golden_common.h      # Core assertions, type audits, and math generators
├── golden_generator.c   # CLI runner for type audits and file generation
├── Makefile             # Portable Makefile (GCC / Clang)
├── build.bat            # Windows batch build script
├── README.md            # This documentation
└── fixtures/            # Generated golden fixtures (binary .bin and text .csv)
    ├── manifest.json
    ├── sine_100hz_48khz_512s_lsb.bin / .csv
    ├── sine_100hz_48khz_512s_msb.bin / .csv
    ├── counter_ramp_512s_lsb.bin / .csv
    ├── counter_ramp_512s_msb.bin / .csv
    ├── boundary_stress_lsb.bin / .csv
    └── boundary_stress_msb.bin / .csv
```

---

## 3. Compilation & Usage

### A. Build with GCC (Host)
```bash
# Using Makefile
make

# Or directly with GCC
gcc -std=c11 -Wall -Wextra -pedantic -O2 golden_generator.c -o golden_generator.exe -lm

# Or on Windows using batch script
build.bat
```

### B. Run System Architecture & Type Audit
```bash
./golden_generator.exe --verify-types
```
Outputs JSON confirming:
- `sizeof(int16_t) == 2`, `sizeof(int32_t) == 4`, `sizeof(uint32_t) == 4`, `sizeof(float) == 4`
- Little-endian byte order (`0x01020304` stored as `[0x04, 0x03, 0x02, 0x01]`)
- Two's complement representation (`-1 == 0xFFFFFFFF`)
- 24-bit negative sign-extension into 32-bit container (`0x00800000 -> -8,388,608`)

### C. Generate All Golden Fixtures
```bash
./golden_generator.exe --generate-all fixtures
```

---

## 4. Mathematical Definition of Golden Vectors

### 1. Deterministic 100 Hz Sine Wave
For sample index $n \in [0, N-1]$ at sampling rate $f_s = 48,000 \text{ Hz}$, frequency $f_0 = 100 \text{ Hz}$, and amplitude ratio $A = 0.50$ ($-6.02 \text{ dBFS}$):
$$y_{\text{lsb}}[n] = \text{round}\left(A \times (2^{23}-1) \times \sin\left(\frac{2\pi \times 100 \times n}{48000}\right)\right)$$
$$y_{\text{msb}}[n] = \text{round}\left(A \times (2^{31}-1) \times \sin\left(\frac{2\pi \times 100 \times n}{48000}\right)\right) \ \& \ \sim 0\text{xFF}$$

### 2. Linear Ramp Counter
Used to verify DMA FIFO continuity, byte alignment, and sequence tracking:
$$c[n] = ((\text{start} + n \times \text{step} - \text{MIN}) \pmod{\text{RANGE}}) + \text{MIN}$$

### 3. Boundary & Stress Vector
Covers numerical edge cases:
- Maximum positive 24-bit: $+8,388,607$ (`0x007FFFFF`)
- Minimum negative 24-bit: $-8,388,608$ (`0xFF800000`)
- Exact zero: $0$ (`0x00000000`)
- Single LSB steps: $+1$, $-1$, $+2$, $-2$
- Walking ones pattern across all 24 bits
