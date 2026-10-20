/**
 * @file waveform_gen.h
 * @brief Deterministic Waveform Generators & Bit-Alignment Utilities.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
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
 *
 * @param state Generator state.
 * @param out_samples Output array of int32_t.
 * @param count Number of samples to generate.
 * @return PROTOCOL_OK or error code.
 */
ProtocolStatus waveform_gen_fill_block(
    WaveformGeneratorState *state,
    int32_t *out_samples,
    size_t count
);

/**
 * @brief Serialize an array of int32_t samples to little-endian bytes.
 *
 * @param in_samples Source int32_t array.
 * @param count Number of samples.
 * @param out_bytes Destination byte buffer (must have at least count * 4 bytes).
 * @return PROTOCOL_OK or error code.
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
 * @brief Sign-extend a raw 24-bit integer word into a signed 32-bit int.
 */
static inline int32_t sign_extend_24_to_32(uint32_t raw_24) {
    return (int32_t)((raw_24 & 0x00FFFFFFU) << 8) >> 8;
}

/**
 * @brief Convert LSB-aligned 24-bit signed integer to MSB-aligned (left-justified) 32-bit word.
 */
static inline int32_t lsb_to_msb_aligned(int32_t lsb_val) {
    return (int32_t)((uint32_t)(lsb_val & 0x00FFFFFFU) << 8);
}

/**
 * @brief Convert MSB-aligned 32-bit word back to LSB-aligned 24-bit signed integer.
 */
static inline int32_t msb_to_lsb_aligned(int32_t msb_val) {
    return (int32_t)msb_val >> 8;
}

/**
 * @brief Convert an integer sample to normalized float32 [-1.0, +1.0].
 */
static inline float sample_to_float32(int32_t sample, uint8_t meaningful_bits, bool msb_aligned) {
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
