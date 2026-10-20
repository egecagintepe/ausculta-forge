# AuscultaForge — Embedded C Source Code Walkthrough
**Document ID:** `AF-CODE-C-WALKTHROUGH-V02`  
**Classification:** `CODE_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- `tools/c_golden_vectors/golden_common.h`
- `tools/c_golden_vectors/golden_generator.c`
- `tools/esp32_bench_example/main/main.c` (`HARDWARE_UNVERIFIED`)
- `tools/esp32_bench_example/sdkconfig.defaults`

---

## 1. Overview and Engineering Methodology

This document provides a line-by-line inspection of the portable C reference utilities and experimental ESP32-S3 bench code in AuscultaForge. Every routine is analyzed from bit-level mathematical specification to execution flow, preserving strict attribution, verified file paths, and explicit hardware verification caveats.

### Architectural Boundaries
1. **Module B Ownership:** Embedded firmware architecture and production drivers belong exclusively to Module B (Ozan). The C code under `tools/c_golden_vectors/` and `tools/esp32_bench_example/` was authored by Module C (Ege) purely as **portable interoperability test tools and experimental reference scaffolds**.
2. **Hardware Status:** `tools/esp32_bench_example/main/main.c` is **UNVERIFIED on physical hardware**. It has not been compiled with the ESP-IDF toolchain or flashed to a physical ESP32-S3 board.
3. **Protocol Status:** Wire framing, magic words, and CRC trailers are **unapproved proposals** awaiting joint Module B/C review (DW03-09, DW03-12).

---

## 2. Core C Function Walkthroughs

### Function 1: `generate_pcm_sine()` (Deterministic Integer Sine Wave Generator)
* **File:** `tools/c_golden_vectors/golden_common.h` (Lines 150–177)
* **Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

#### Source Code:
```c
static inline void generate_pcm_sine(
    int32_t *out_buffer,
    size_t n_samples,
    uint32_t sample_rate_hz,
    double freq_hz,
    double amplitude_ratio,
    bool msb_aligned
) {
    if (!out_buffer || n_samples == 0 || sample_rate_hz == 0) return;

    double max_amp = (double)INT24_MAX_VALUE;
    double amp = amplitude_ratio * max_amp;
    double phase_inc = (2.0 * M_PI * freq_hz) / (double)sample_rate_hz;

    for (size_t n = 0; n < n_samples; ++n) {
        double val = amp * sin((double)n * phase_inc);
        /* Deterministic rounding to nearest integer with ties away from zero */
        int64_t ival = (int64_t)(val >= 0.0 ? (val + 0.5) : (val - 0.5));
        if (ival > INT24_MAX_VALUE) ival = INT24_MAX_VALUE;
        if (ival < INT24_MIN_VALUE) ival = INT24_MIN_VALUE;

        if (msb_aligned) {
            out_buffer[n] = lsb_to_msb_aligned((int32_t)ival);
        } else {
            out_buffer[n] = (int32_t)ival;
        }
    }
}
```

#### Detailed Breakdown:
1. **Purpose:** Generates a deterministic, bit-exact sine wave sequence of $N$ samples scaled to 24-bit integer limits (`INT24_MAX_VALUE = +8388607`, `INT24_MIN_VALUE = -8388608`).
2. **Execution Flow:**
   - Validates non-null output buffer and non-zero parameters.
   - Computes angular phase increment per discrete time step: $\Delta \theta = 2\pi f / f_s$.
   - Iterates $n = 0 \dots N-1$, evaluating $v[n] = A \sin(n \Delta \theta)$.
   - Applies symmetric rounding (`val >= 0.0 ? val + 0.5 : val - 0.5`) before integer casting to eliminate positive DC bias.
   - Clamps to 24-bit signed bounds $[-8388608, +8388607]$.
   - Calls `lsb_to_msb_aligned()` if left-justified MSB alignment is requested.
3. **Preconditions & Invariants:**
   - Precondition: `out_buffer` must point to allocated memory for at least `n_samples * sizeof(int32_t)`.
   - Invariant: Every sample in `out_buffer` is bounded within the 24-bit dynamic range regardless of floating-point rounding.

---

### Function 2: `sign_extend_24_to_32()` and `lsb_to_msb_aligned()`
* **File:** `tools/c_golden_vectors/golden_common.h` (Lines 102–118)

#### Source Code:
```c
static inline int32_t sign_extend_24_to_32(uint32_t raw_24) {
    return (int32_t)((raw_24 & 0x00FFFFFFU) << 8) >> 8;
}

static inline int32_t lsb_to_msb_aligned(int32_t lsb_val) {
    return (int32_t)((uint32_t)(lsb_val & 0x00FFFFFFU) << 8);
}

static inline int32_t msb_to_lsb_aligned(int32_t msb_val) {
    return (int32_t)msb_val >> 8;
}
```

#### Detailed Breakdown:
1. **Purpose:** Handles the conversion between 24-bit raw I2S sample words and standard signed 32-bit container integers.
2. **Sign Extension Mechanics (`sign_extend_24_to_32`):**
   - In 24-bit two's-complement arithmetic, bit 23 is the sign bit ($1 = \text{negative}, 0 = \text{positive}$).
   - `(raw_24 & 0x00FFFFFFU) << 8`: Shifts the 24-bit word left by 8 bits, placing bit 23 into bit 31 (the 32-bit sign bit).
   - `>> 8` on signed `int32_t`: On two's-complement architectures (guaranteed by C23 and universal in GCC/Clang), right-shifting a signed negative integer performs an **arithmetic shift**, replicating bit 31 across the upper 8 bits.
   - *Example with $-1$ (`0x00FFFFFF`):*
     - Left shift: `0x00FFFFFF << 8 = 0xFFFFFF00`.
     - Arithmetic right shift: `0xFFFFFF00 >> 8 = 0xFFFFFFFF` (which is $-1$ in 32-bit signed integer).
3. **C Standard Implementation Note:** In ISO C11 (§6.5.7), right-shifting a signed negative integer is technically implementation-defined. AuscultaForge verifies arithmetic sign extension at startup using `audit_system_types()` in `golden_common.h`.

---

### Function 3: `compute_crc16_ccitt()` (Reference Frame Integrity Check)
* **File:** `tools/c_golden_vectors/golden_common.h` (Lines 125–138)

#### Source Code:
```c
static inline uint16_t compute_crc16_ccitt(const uint8_t *data, size_t length, uint16_t init_val) {
    uint16_t crc = init_val;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
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
1. **Purpose:** Computes the standard CRC-16-CCITT polynomial ($G(x) = x^{16} + x^{12} + x^5 + 1$, `0x1021`) over byte sequences.
2. **Approval Status:** This routine is provided purely as a host reference utility to validate DW03-09 proposals. **Neither the CRC algorithm nor the packet trailer policy is formally approved for production firmware.**
3. **Mathematical Properties:**
   - Detects all single-bit errors and all double-bit errors for frames up to $2^{15}-1$ bits.
   - Detects all odd numbers of bit errors.
   - Detects any burst error of length $\le 16$ bits.

---

### Function 4: `synthetic_stream_task()` (Experimental Bench Pacing Scaffold)
* **File:** `tools/esp32_bench_example/main/main.c` (Lines 96–165)
* **Status:** `HARDWARE_UNVERIFIED`

#### Source Code Excerpt:
```c
static void synthetic_stream_task(void *pvParameters) {
    (void)pvParameters;
    int32_t sample_block[BENCH_BLOCK_SIZE]; /* 512 samples */

    /* Approximate delay for bench simulation; NOT an accurate 48 kHz hardware clock */
    const TickType_t xBlockDelay = pdMS_TO_TICKS(11);

    while (1) {
        if (tud_cdc_connected()) {
            /* 1. Fill precomputed synthetic sine samples */
            fill_synthetic_block(sample_block, BENCH_BLOCK_SIZE);

            /* 2. Write to USB CDC-ACM TX queue */
            size_t bytes_to_send = BENCH_BLOCK_SIZE * sizeof(int32_t);
            size_t total_written = 0;
            int retries = 0;

            while (total_written < bytes_to_send && retries < 3) {
                size_t written = tinyusb_cdcacm_write_queue(
                    TINYUSB_CDC_ACM_0,
                    ((const uint8_t *)sample_block) + total_written,
                    bytes_to_send - total_written
                );
                total_written += written;
                if (total_written < bytes_to_send) {
                    tud_cdc_write_flush();
                    retries++;
                    vTaskDelay(pdMS_TO_TICKS(1));
                }
            }
            tud_cdc_write_flush();
            s_sequence_counter++;
            vTaskDelay(xBlockDelay);
        } else {
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
```

#### Detailed Breakdown & Critical Timing Limitations:
1. **FreeRTOS Tick Rate:** `tools/esp32_bench_example/sdkconfig.defaults` specifies:
   ```ini
   CONFIG_FREERTOS_HZ=1000
   ```
   At `1000 Hz`, 1 FreeRTOS tick $= 1.0 \text{ ms}$. `pdMS_TO_TICKS(11)` delays for $11 \text{ ms}$.
2. **Why `vTaskDelay(11)` Cannot Produce a 48 kHz Clock:**
   - 512 samples at $48,000 \text{ Hz}$ represents an exact duration of:
     $$T_{\text{nominal}} = \frac{512}{48000} \approx 10.6667 \text{ ms} \quad (\approx 93.75 \text{ frames/second})$$
   - A task delay of $11 \text{ ms}$ yields a nominal frame rate of:
     $$f_{\text{frame}} \approx \frac{1}{0.011} \approx 90.91 \text{ frames/second} \implies 90.91 \times 512 \approx 46,545 \text{ samples/second}$$
   - This represents a $-3.03\%$ sample rate drift ($\approx 1,455 \text{ samples/second}$ deficit).
   - In real hardware, sampling must be driven by **hardware I2S DMA interrupts**, never software task delays.
