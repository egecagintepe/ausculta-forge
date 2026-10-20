/**
 * @file waveform_gen.h
 * @brief Deterministic Waveform Generators & Portable PCM Arithmetic.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * PORTABLE C11 ARITHMETIC RULES:
 * ------------------------------
 * 1. ZERO implementation-defined right shifts on negative signed integers.
 * 2. ZERO unsafe pointer aliasing / type punning.
 * 3. Exact mathematical two's complement sign extension using standard in-range conversion.
 * 4. Explicit byte-by-byte little-endian serialization.
 */

#ifndef WAVEFORM_GEN_H
#define WAVEFORM_GEN_H

#include "protocol_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SINE_100HZ_PERIOD_SAMPLES   480U /* 48000 Hz / 100 Hz = 480 samples */

/**
 * @brief Generator signal type selector.
 */
typedef enum {
    GEN_SIGNAL_SINE_100HZ       = 0,
    GEN_SIGNAL_RAMP_COUNTER     = 1,
    GEN_SIGNAL_SILENCE          = 2,
    GEN_SIGNAL_BOUNDARY_STRESS  = 3,
    GEN_SIGNAL_IMPULSE_TRAIN    = 4
} GeneratorSignalType;

/**
 * @brief Configuration state for deterministic waveform generator.
 */
typedef struct {
    GeneratorSignalType signal_type;
    uint32_t sample_rate_hz;        /* e.g. 48000 */
    double   frequency_hz;          /* e.g. 100.0 */
    double   amplitude_ratio;       /* 0.0 to 1.0 (e.g. 0.5 for -6 dBFS) */
    bool     msb_aligned;           /* true: left-justified, false: LSB-aligned */
    uint32_t current_phase_index;   /* Sine table lookup index (0 to 479) */
    int64_t  current_counter_value; /* Monotonic ramp counter state */
    uint64_t total_samples_emitted; /* Cumulative sample accounting */
} WaveformGeneratorState;

/**
 * @brief Initialize a waveform generator state.
 */
ProtocolStatus waveform_gen_init(
    WaveformGeneratorState *state,
    GeneratorSignalType signal_type,
    uint32_t sample_rate_hz,
    double frequency_hz,
    double amplitude_ratio,
    bool msb_aligned
);

/**
 * @brief Fill an output buffer with deterministic 32-bit container samples.
 */
ProtocolStatus waveform_gen_fill_block(
    WaveformGeneratorState *state,
    int32_t *out_samples,
    size_t count
);

/**
 * @brief Serialize an array of int32_t samples to little-endian bytes.
 */
ProtocolStatus serialize_samples_le(
    const int32_t *in_samples,
    size_t count,
    uint8_t *out_bytes
);

/**
 * @brief Deserialize little-endian bytes to an array of int32_t samples.
 */
ProtocolStatus deserialize_samples_le(
    const uint8_t *in_bytes,
    size_t count,
    int32_t *out_samples
);

/**
 * @brief Portably sign-extend a raw 24-bit integer into a signed 32-bit int.
 *
 * Uses strictly conforming integer arithmetic (no implementation-defined right shift).
 * Range mapping:
 *   [0x000000, 0x7FFFFF] -> [0, +8388607]
 *   [0x800000, 0xFFFFFF] -> [-8388608, -1]
 */
static inline int32_t sign_extend_24_to_32(uint32_t raw_24) {
    uint32_t u = raw_24 & 0x00FFFFFFU;
    if (u & 0x00800000U) {
        return (int32_t)((int64_t)u - 0x01000000LL);
    }
    return (int32_t)u;
}

/**
 * @brief Portably sign-extend a generic N-bit signed integer word to int32_t.
 *
 * @param raw_val Unsigned raw word containing the N-bit value.
 * @param meaningful_bits Bit depth (1 to 32).
 * @param out_val Pointer to receive converted int32_t.
 * @return PROTOCOL_OK or PROTOCOL_ERR_INVALID_PARAM if bits < 1 or bits > 32.
 */
static inline ProtocolStatus sign_extend_n_to_32(
    uint32_t raw_val,
    uint8_t meaningful_bits,
    int32_t *out_val
) {
    if (!out_val) return PROTOCOL_ERR_NULL_PTR;
    if (meaningful_bits < 1 || meaningful_bits > 32) return PROTOCOL_ERR_INVALID_PARAM;

    if (meaningful_bits == 32) {
        if (raw_val & 0x80000000U) {
            *out_val = (int32_t)((int64_t)raw_val - 0x100000000LL);
        } else {
            *out_val = (int32_t)raw_val;
        }
        return PROTOCOL_OK;
    }

    uint32_t mask = (1U << meaningful_bits) - 1U;
    uint32_t sign_bit = 1U << (meaningful_bits - 1U);
    uint32_t u = raw_val & mask;
    if (u & sign_bit) {
        int64_t modulus = (int64_t)1LL << meaningful_bits;
        *out_val = (int32_t)((int64_t)u - modulus);
    } else {
        *out_val = (int32_t)u;
    }
    return PROTOCOL_OK;
}

/**
 * @brief Convert LSB-aligned 24-bit signed integer to MSB-aligned (left-justified) 32-bit word.
 *
 * Places 24 meaningful bits into bits [31..8], zeroing bits [7..0].
 */
static inline int32_t lsb_to_msb_aligned(int32_t lsb_val) {
    uint32_t u24 = ((uint32_t)lsb_val) & 0x00FFFFFFU;
    uint32_t u32 = u24 << 8;
    if (u32 & 0x80000000U) {
        return (int32_t)((int64_t)u32 - 0x100000000LL);
    }
    return (int32_t)u32;
}

/**
 * @brief Convert MSB-aligned 32-bit word back to LSB-aligned 24-bit signed integer.
 *
 * Shifts bits [31..8] down to [23..0] and performs portable sign extension.
 */
static inline int32_t msb_to_lsb_aligned(int32_t msb_val) {
    uint32_t u32;
    if (msb_val < 0) {
        u32 = (uint32_t)((int64_t)msb_val + 0x100000000LL);
    } else {
        u32 = (uint32_t)msb_val;
    }
    uint32_t u24 = (u32 >> 8) & 0x00FFFFFFU;
    return sign_extend_24_to_32(u24);
}

/**
 * @brief Convert an integer sample to normalized float32 [-1.0, +1.0].
 */
static inline float sample_to_float32(int32_t sample, uint8_t meaningful_bits, bool msb_aligned) {
    if (meaningful_bits < 1 || meaningful_bits > 32) return 0.0f;
    int32_t lsb_val = msb_aligned ? msb_to_lsb_aligned(sample) : sample;
    double scale = (double)(1LL << (meaningful_bits - 1));
    double norm = (double)lsb_val / scale;
    if (norm > 1.0) norm = 1.0;
    if (norm < -1.0) norm = -1.0;
    return (float)norm;
}

#ifdef __cplusplus
}
#endif

#endif /* WAVEFORM_GEN_H */
