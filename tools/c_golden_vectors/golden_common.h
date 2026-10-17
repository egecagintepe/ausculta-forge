/**
 * @file golden_common.h
 * @brief Common types, assertions, and deterministic generators for C golden vectors.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application) Interoperability Tool for Module B (Embedded)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * NOTE: This tool is an independent reference utility designed to verify
 * data representations, bit alignment, integer signedness, and mathematical
 * known-answer sequences on host systems before physical MCU firmware bring-up.
 */

#ifndef GOLDEN_COMMON_H
#define GOLDEN_COMMON_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GOLDEN_VECTOR_VERSION_MAJOR 1
#define GOLDEN_VECTOR_VERSION_MINOR 0
#define GOLDEN_VECTOR_VERSION_PATCH 0
#define GOLDEN_VECTOR_SCHEMA_STRING "auscultaforge.golden_vector.v1"

/* Standard audio baseline parameters (Rev-A proposal) */
#define BASELINE_SAMPLE_RATE_HZ     48000U
#define BASELINE_CHANNELS           1U
#define BASELINE_CONTAINER_BITS     32U
#define BASELINE_MEANINGFUL_BITS    24U
#define BASELINE_BLOCK_SIZE         512U

/* 24-bit integer limits */
#define INT24_MAX_VALUE             8388607LL       /* +2^23 - 1 */
#define INT24_MIN_VALUE             (-8388608LL)    /* -2^23 */
#define INT24_SCALE_FACTOR          8388608.0       /* 2^23 */

/* 32-bit full-scale limit */
#define INT32_MAX_VALUE             2147483647LL    /* +2^31 - 1 */
#define INT32_MIN_VALUE             (-2147483648LL) /* -2^31 */
#define INT32_SCALE_FACTOR          2147483648.0    /* 2^31 */

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
 * @brief System architecture verification result.
 */
typedef struct {
    bool sizeof_int16_ok;       /* sizeof(int16_t) == 2 */
    bool sizeof_int32_ok;       /* sizeof(int32_t) == 4 */
    bool sizeof_uint32_ok;      /* sizeof(uint32_t) == 4 */
    bool sizeof_float_ok;       /* sizeof(float) == 4 */
    bool is_little_endian;      /* LSB stored at lowest address */
    bool sign_extension_ok;     /* 24-bit negative correctly extended to 32-bit */
    bool twos_complement_ok;    /* -1 has all bits set */
} SystemTypeAudit;

/**
 * @brief Check integer widths, signedness, and endianness.
 */
static inline SystemTypeAudit audit_system_types(void) {
    SystemTypeAudit audit;
    memset(&audit, 0, sizeof(audit));

    audit.sizeof_int16_ok  = (sizeof(int16_t) == 2);
    audit.sizeof_int32_ok  = (sizeof(int32_t) == 4);
    audit.sizeof_uint32_ok = (sizeof(uint32_t) == 4);
    audit.sizeof_float_ok  = (sizeof(float) == 4);

    /* Endianness check */
    uint32_t test_val = 0x01020304U;
    uint8_t *byte_ptr = (uint8_t *)&test_val;
    audit.is_little_endian = (byte_ptr[0] == 0x04 && byte_ptr[3] == 0x01);

    /* Two's complement check */
    int32_t neg_one = -1;
    audit.twos_complement_ok = (*(uint32_t *)&neg_one == 0xFFFFFFFFU);

    /* 24-bit to 32-bit sign extension check */
    /* 0x00800000 represents -8,388,608 in 24-bit 2's complement */
    uint32_t raw_24_neg = 0x00800000U;
    int32_t extended = (int32_t)((raw_24_neg << 8)) >> 8;
    audit.sign_extension_ok = (extended == -8388608LL);

    return audit;
}

/**
 * @brief Sign-extend a raw 24-bit word into a signed 32-bit integer (LSB-aligned).
 */
static inline int32_t sign_extend_24_to_32(uint32_t raw_24) {
    return (int32_t)((raw_24 & 0x00FFFFFFU) << 8) >> 8;
}

/**
 * @brief Convert LSB-aligned 24-bit signed integer to MSB-aligned (left-justified) 32-bit container.
 */
static inline int32_t lsb_to_msb_aligned(int32_t lsb_val) {
    return (int32_t)((uint32_t)(lsb_val & 0x00FFFFFFU) << 8);
}

/**
 * @brief Convert MSB-aligned 32-bit container word back to LSB-aligned 24-bit signed integer.
 */
static inline int32_t msb_to_lsb_aligned(int32_t msb_val) {
    return (int32_t)msb_val >> 8;
}

/**
 * @brief Compute standard CRC-16-CCITT (polynomial 0x1021, configurable initial value).
 *
 * NOTE: Provided as an interoperability reference for evaluating DW03-09.
 */
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

/**
 * @brief Generate deterministic 100 Hz PCM sine samples.
 *
 * @param out_buffer Output integer array.
 * @param n_samples Number of samples to generate.
 * @param sample_rate_hz Sampling rate in Hz (e.g. 48000).
 * @param freq_hz Sine frequency in Hz (e.g. 100.0).
 * @param amplitude_ratio Amplitude scale relative to full scale (0.0 to 1.0, e.g. 0.5 for -6 dBFS).
 * @param msb_aligned If true, align to upper 24 bits of 32-bit container; if false, LSB-aligned with sign extension.
 */
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

/**
 * @brief Generate deterministic ramp counter samples.
 *
 * Used to detect bit flips, byte misordering, and DMA FIFO alignment issues.
 */
static inline void generate_pcm_counter(
    int32_t *out_buffer,
    size_t n_samples,
    int32_t start_val,
    int32_t step,
    bool msb_aligned
) {
    if (!out_buffer || n_samples == 0) return;

    for (size_t n = 0; n < n_samples; ++n) {
        int64_t val = (int64_t)start_val + (int64_t)n * (int64_t)step;
        /* Modulo 24-bit signed range */
        int64_t wrapped = ((val - INT24_MIN_VALUE) % (INT24_MAX_VALUE - INT24_MIN_VALUE + 1)) + INT24_MIN_VALUE;

        if (msb_aligned) {
            out_buffer[n] = lsb_to_msb_aligned((int32_t)wrapped);
        } else {
            out_buffer[n] = (int32_t)wrapped;
        }
    }
}

/**
 * @brief Generate boundary and stress test samples.
 *
 * Covers:
 * - Maximum positive 24-bit (+8,388,607)
 * - Minimum negative 24-bit (-8,388,608)
 * - Zero crossing (-2, -1, 0, +1, +2)
 * - Near-clipping thresholds
 * - Bit-pattern walking ones / walking zeros
 */
static inline size_t generate_boundary_stress_vector(int32_t *out_buffer, size_t max_capacity, bool msb_aligned) {
    if (!out_buffer || max_capacity < 32) return 0;

    static const int32_t stress_values[] = {
        0,                      /* Exact zero */
        1,                      /* Minimum positive step */
        -1,                     /* Minimum negative step */
        2,
        -2,
        127,                    /* 8-bit positive limit */
        -128,                   /* 8-bit negative limit */
        32767,                  /* 16-bit positive limit */
        -32768,                 /* 16-bit negative limit */
        8388607,                /* 24-bit positive limit (INT24_MAX) */
        -8388608,               /* 24-bit negative limit (INT24_MIN) */
        8388606,                /* 24-bit positive limit - 1 */
        -8388607,               /* 24-bit negative limit + 1 */
        4194304,                /* +0.5 FS */
        -4194304,               /* -0.5 FS */
        /* Walking ones pattern across 24 bits */
        0x00000001,
        0x00000002,
        0x00000004,
        0x00000008,
        0x00000010,
        0x00000080,
        0x00000100,
        0x00008000,
        0x00010000,
        0x00400000,             /* Sign bit in 24-bit arithmetic */
        0x007FFFFF,             /* All positive bits set */
        -8388608,               /* Sign extended 0x00800000 */
        -1,                     /* All 24 bits set in 2's complement */
        0                       /* Trailing zero */
    };

    size_t count = sizeof(stress_values) / sizeof(stress_values[0]);
    if (count > max_capacity) count = max_capacity;

    for (size_t i = 0; i < count; ++i) {
        if (msb_aligned) {
            out_buffer[i] = lsb_to_msb_aligned(stress_values[i]);
        } else {
            out_buffer[i] = stress_values[i];
        }
    }

    return count;
}

#ifdef __cplusplus
}
#endif

#endif /* GOLDEN_COMMON_H */
