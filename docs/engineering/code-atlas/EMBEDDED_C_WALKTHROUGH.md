# AuscultaForge — Embedded C Source Code Walkthrough
**Document ID:** `AF-CODE-C-WALKTHROUGH-V01`  
**Classification:** `CODE_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- `tools/c_golden_vectors/golden_common.h`
- `tools/c_golden_vectors/golden_generator.c`
- `tools/esp32_bench_example/main/main.c`

---

## 1. Overview and Engineering Methodology

This document dissects the core C implementations supporting AuscultaForge. Every routine is analyzed from mathematical specification to assembly implications, establishing full traceability between source code, test evidence, and academic theory.

---

## 2. Core C Function Walkthroughs

### Function 1: `generate_sine_100hz_sample()`
* **File:** `tools/c_golden_vectors/golden_common.h`
* **Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

#### Source Code:
```c
int32_t generate_sine_100hz_sample(uint32_t sample_index, uint32_t sample_rate, int32_t amplitude) {
    /* 100 Hz tone period at 48000 Hz is exactly 480 samples */
    uint32_t period = sample_rate / 100U;
    uint32_t phase_index = sample_index % period;
    double angle = (2.0 * M_PI * (double)phase_index) / (double)period;
    double val = (double)amplitude * sin(angle);
    
    /* Round to nearest integer with symmetrical tie-breaking */
    if (val >= 0.0) {
        return (int32_t)(val + 0.5);
    } else {
        return (int32_t)(val - 0.5);
    }
}
```

#### Detailed Breakdown:
1. **Purpose:** Generates a deterministic, bit-exact single 100 Hz sine wave sample scaled to a specified integer amplitude (e.g. 24-bit half-scale: $+4,194,304$).
2. **Execution Flow:**
   - Evaluates the integer period: $48,000 / 100 = 480 \text{ samples}$.
   - Computes modulo phase: `phase_index = sample_index % period`.
   - Evaluates trigonometric sine using standard double-precision library `sin()`.
   - Applies symmetric integer rounding ($\pm 0.5$) before truncation.
3. **Preconditions & Invariants:**
   - Precondition: `sample_rate` must be an integer multiple of 100 (e.g. 48,000 Hz, 16,000 Hz, 8,000 Hz).
   - Invariant: Output sample value is strictly bounded within $[-\text{amplitude}, +\text{amplitude}]$.
4. **Worked Numerical Example (Quarter-Cycle Peak):**
   * Let $f_s = 48,000 \text{ Hz}$, $f = 100 \text{ Hz}$, $\text{amplitude} = 4,194,304$ ($2^{22}$).
   * Period: $T = 480 \text{ samples}$.
   * Quarter-cycle sample index: $n = 120$.
   * $\text{phase\_index} = 120 \pmod{480} = 120$.
   * $\text{angle} = 2\pi \times (120 / 480) = \pi / 2 \text{ radians} = 90^\circ$.
   * $\sin(\pi / 2) = 1.0000000000000000$.
   * $\text{val} = 4,194,304 \times 1.0 = 4,194,304.0$.
   * Output integer: $+4,194,304$ (`0x00400000`).
5. **Academic Defense Question:**
   * *Question:* Why do we calculate `sample_index % period` instead of passing `(2.0 * M_PI * 100.0 * (double)sample_index) / 48000.0` directly into `sin()`?
   * *Expected Answer:* If `sample_index` is allowed to grow indefinitely without modulo reduction, after prolonged streaming ($N > 10^8$ samples), `(double)sample_index` accumulates floating-point quantization error in the lower bits, causing progressive phase jitter. Modulo reduction onto $[0, 479]$ guarantees identical, cyclic numerical precision indefinitely.

---

### Function 2: `pack_and_align_sample()`
* **File:** `tools/c_golden_vectors/golden_common.h`
* **Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

#### Source Code:
```c
uint32_t pack_and_align_sample(int32_t sample_24bit, int is_msb_aligned) {
    /* Mask input to ensure it is strictly within 24-bit range */
    uint32_t u24 = (uint32_t)sample_24bit & 0x00FFFFFFU;
    
    if (is_msb_aligned) {
        /* Left-justify: shift 24 bits to top (bits 31..8), bottom 8 bits zero */
        return (u24 << 8);
    } else {
        /* Right-justify (LSB aligned): preserve 24 bits at bits 23..0 */
        /* If negative (bit 23 set), sign-extend upper 8 bits to 1s */
        if (u24 & 0x00800000U) {
            return (u24 | 0xFF000000U);
        } else {
            return u24;
        }
    }
}
```

#### Detailed Breakdown:
1. **Purpose:** Simulates the hardware packing of a 24-bit PCM sample into a 32-bit container word, supporting both MSB-aligned (INMP441 native DMA format) and LSB-aligned (sign-extended) hardware modes.
2. **Execution Flow:**
   - Casts to `uint32_t` and applies bitwise mask `& 0x00FFFFFFU` to discard stray high bits.
   - If MSB-aligned: Logical left shift by 8 bits (`u24 << 8`).
   - If LSB-aligned: Tests bit 23 (`u24 & 0x00800000U`). If set, bitwise ORs with `0xFF000000U` to replicate the sign bit across bits 31–24.
3. **Worked Numerical Example (Negative Sample: $-1$):**
   * Input value: $-1$.
   * In 24-bit two's complement:
     $$-1 = 2^{24} - 1 = 16,777,215 = 0\text{x00FFFFFF}$$
   * Masked value: `u24 = 0x00FFFFFF`.
   * **Case A: MSB-Aligned:**
     * Shift left by 8: `0x00FFFFFF << 8 = 0xFFFFFF00`.
     * Byte 0: `0x00`, Byte 1: `0xFF`, Byte 2: `0xFF`, Byte 3: `0xFF`.
     * Note: Top 24 bits are all 1s (sign is negative), lowest 8 bits are zero.
   * **Case B: LSB-Aligned:**
     * Bit 23 is 1 (`0x00FFFFFF & 0x00800000 != 0`).
     * Bitwise OR: `0x00FFFFFF | 0xFF000000 = 0xFFFFFFFF`.
     * Evaluated as `int32_t`: $-1$.
     * Output correctly retains mathematical $-1$ in standard 32-bit integer arithmetic!

---

### Function 3: `compute_crc16_ccitt()`
* **File:** `tools/c_golden_vectors/golden_common.h`
* **Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

#### Source Code:
```c
uint16_t compute_crc16_ccitt(const uint8_t *data, size_t length) {
    /* CRC-16-CCITT: polynomial 0x1021 (x^16 + x^12 + x^5 + 1), init 0xFFFF */
    uint16_t crc = 0xFFFFU;
    
    for (size_t i = 0; i < length; ++i) {
        crc ^= ((uint16_t)data[i]) << 8;
        for (int b = 0; b < 8; ++b) {
            if (crc & 0x8000U) {
                crc = (crc << 1) ^ 0x1021U;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}
```

#### Detailed Breakdown:
1. **Purpose:** Calculates a 16-bit Cyclic Redundancy Check (CRC-16-CCITT) over a byte buffer for packet integrity verification.
2. **Mathematical Basis:**
   - Generator polynomial: $G(x) = x^{16} + x^{12} + x^5 + 1$ (Hexadecimal: `0x1021`).
   - Initial shift register value: `0xFFFF`.
   - Bitwise XOR feedback for every set MSB ($b_{15}$).
3. **Execution Invariant:**
   - Deterministic and state-independent. Any single-bit, double-bit, or burst error up to 16 bits in length is mathematically guaranteed to be detected ($100\%$ detection rate for odd number of bit errors).
4. **Test Verification:**
   - Verified bit-for-bit against Python's `pcg_app.transport.calculate_crc16()` in `software/tests/test_c_golden_vectors.py`.
