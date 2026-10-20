/**
 * @file waveform_gen.c
 * @brief Deterministic Waveform Generators Implementation.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 */

#include "waveform_gen.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* Precomputed 480-point lookup table for 100 Hz sine @ 48 kHz (0.5 Full Scale peak) */
static int32_t s_sine_table[SINE_100HZ_PERIOD_SAMPLES];
static bool s_table_initialized = false;

static void ensure_sine_table_initialized(void) {
    if (s_table_initialized) return;

    /* Generate 480 samples: full scale = 2^23 - 1 (8,388,607) */
    double max_amp = (double)INT24_MAX;
    for (size_t i = 0; i < SINE_100HZ_PERIOD_SAMPLES; ++i) {
        double phase = (2.0 * M_PI * (double)i) / (double)SINE_100HZ_PERIOD_SAMPLES;
        double val = max_amp * sin(phase);
        int64_t ival = (int64_t)(val >= 0.0 ? (val + 0.5) : (val - 0.5));
        if (ival > INT24_MAX) ival = INT24_MAX;
        if (ival < INT24_MIN) ival = INT24_MIN;
        s_sine_table[i] = (int32_t)ival;
    }
    s_table_initialized = true;
}

ProtocolStatus waveform_gen_init(
    WaveformGeneratorState *state,
    GeneratorSignalType signal_type,
    uint32_t sample_rate_hz,
    double frequency_hz,
    double amplitude_ratio,
    bool msb_aligned
) {
    if (!state) return PROTOCOL_ERR_NULL_PTR;

    state->signal_type = signal_type;
    state->sample_rate_hz = (sample_rate_hz > 0) ? sample_rate_hz : NOMINAL_SAMPLE_RATE_HZ;
    state->frequency_hz = (frequency_hz > 0.0) ? frequency_hz : 100.0;
    state->amplitude_ratio = (amplitude_ratio >= 0.0 && amplitude_ratio <= 1.0) ? amplitude_ratio : 0.5;
    state->msb_aligned = msb_aligned;
    state->current_phase_index = 0;
    state->current_counter_value = 0;
    state->total_samples_emitted = 0;

    ensure_sine_table_initialized();
    return PROTOCOL_OK;
}

ProtocolStatus waveform_gen_fill_block(
    WaveformGeneratorState *state,
    int32_t *out_samples,
    size_t count
) {
    if (!state || !out_samples) return PROTOCOL_ERR_NULL_PTR;
    if (count == 0) return PROTOCOL_OK;

    ensure_sine_table_initialized();

    switch (state->signal_type) {
        case GEN_SIGNAL_SINE_100HZ: {
            double amp_scale = state->amplitude_ratio;
            for (size_t n = 0; n < count; ++n) {
                int32_t base_sample = s_sine_table[state->current_phase_index];
                int32_t scaled;
                if (amp_scale >= 0.9999) {
                    scaled = base_sample;
                } else {
                    double v = (double)base_sample * amp_scale;
                    scaled = (int32_t)(v >= 0.0 ? (v + 0.5) : (v - 0.5));
                }

                out_samples[n] = state->msb_aligned ? lsb_to_msb_aligned(scaled) : scaled;
                state->current_phase_index = (state->current_phase_index + 1) % SINE_100HZ_PERIOD_SAMPLES;
            }
            break;
        }

        case GEN_SIGNAL_RAMP_COUNTER: {
            for (size_t n = 0; n < count; ++n) {
                int64_t val = state->current_counter_value;
                /* Modulo 24-bit signed span: [-8388608, +8388607] (span: 16777216) */
                int64_t span = (int64_t)INT24_MAX - (int64_t)INT24_MIN + 1;
                int64_t wrapped = ((val - INT24_MIN) % span);
                if (wrapped < 0) wrapped += span;
                wrapped += INT24_MIN;

                int32_t s = (int32_t)wrapped;
                out_samples[n] = state->msb_aligned ? lsb_to_msb_aligned(s) : s;
                state->current_counter_value++;
            }
            break;
        }

        case GEN_SIGNAL_SILENCE: {
            memset(out_samples, 0, count * sizeof(int32_t));
            break;
        }

        case GEN_SIGNAL_BOUNDARY_STRESS: {
            static const int32_t boundary_fixtures[] = {
                0,
                1,
                -1,
                2,
                -2,
                127,
                -128,
                32767,
                -32768,
                8388607,                /* INT24_MAX (+FS) */
                -8388608,               /* INT24_MIN (-FS) */
                8388606,                /* INT24_MAX - 1 */
                -8388607,               /* INT24_MIN + 1 */
                4194304,                /* +0.5 FS */
                -4194304,               /* -0.5 FS */
                0x00000001,
                0x00000002,
                0x00000004,
                0x00000008,
                0x00000010,
                0x00000080,
                0x00000100,
                0x00008000,
                0x00010000,
                0x00400000,             /* Sign bit in 24-bit */
                0x007FFFFF,             /* All positive bits set */
                -8388608,               /* Minimum negative */
                -1,                     /* All bits set */
                0                       /* Trailing zero */
            };
            size_t num_fixtures = sizeof(boundary_fixtures) / sizeof(boundary_fixtures[0]);

            for (size_t n = 0; n < count; ++n) {
                int32_t s = boundary_fixtures[state->current_phase_index % num_fixtures];
                out_samples[n] = state->msb_aligned ? lsb_to_msb_aligned(s) : s;
                state->current_phase_index++;
            }
            break;
        }

        case GEN_SIGNAL_IMPULSE_TRAIN: {
            for (size_t n = 0; n < count; ++n) {
                int32_t s = (state->current_phase_index % 480 == 0) ? (int32_t)INT24_MAX : 0;
                out_samples[n] = state->msb_aligned ? lsb_to_msb_aligned(s) : s;
                state->current_phase_index++;
            }
            break;
        }

        default:
            return PROTOCOL_ERR_INVALID_PARAM;
    }

    state->total_samples_emitted += count;
    return PROTOCOL_OK;
}

ProtocolStatus serialize_samples_le(
    const int32_t *in_samples,
    size_t count,
    uint8_t *out_bytes
) {
    if (!in_samples || !out_bytes) return PROTOCOL_ERR_NULL_PTR;

    for (size_t i = 0; i < count; ++i) {
        int32_t s = in_samples[i];
        uint32_t u;
        if (s < 0) {
            u = (uint32_t)((int64_t)s + 0x100000000LL);
        } else {
            u = (uint32_t)s;
        }
        out_bytes[i * 4 + 0] = (uint8_t)(u & 0xFFU);
        out_bytes[i * 4 + 1] = (uint8_t)((u >> 8) & 0xFFU);
        out_bytes[i * 4 + 2] = (uint8_t)((u >> 16) & 0xFFU);
        out_bytes[i * 4 + 3] = (uint8_t)((u >> 24) & 0xFFU);
    }
    return PROTOCOL_OK;
}

ProtocolStatus deserialize_samples_le(
    const uint8_t *in_bytes,
    size_t count,
    int32_t *out_samples
) {
    if (!in_bytes || !out_samples) return PROTOCOL_ERR_NULL_PTR;

    for (size_t i = 0; i < count; ++i) {
        uint32_t b0 = (uint32_t)in_bytes[i * 4 + 0];
        uint32_t b1 = (uint32_t)in_bytes[i * 4 + 1];
        uint32_t b2 = (uint32_t)in_bytes[i * 4 + 2];
        uint32_t b3 = (uint32_t)in_bytes[i * 4 + 3];
        uint32_t u = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
        if (u & 0x80000000U) {
            out_samples[i] = (int32_t)((int64_t)u - 0x100000000LL);
        } else {
            out_samples[i] = (int32_t)u;
        }
    }
    return PROTOCOL_OK;
}
