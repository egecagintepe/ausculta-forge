/**
 * @file g1_sim_runner.c
 * @brief Standalone G1 Benchmark & Protocol Simulation Host Runner.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * MODES:
 * 1. stream : Emits continuous binary framed packets to stdout (for piping to Python)
 * 2. fast   : Generates 10-second G1 benchmark directly to file with timing summary
 * 3. fuzz   : Streams with controlled error injections (dropped, corrupted, duplicate)
 * 4. audit  : Emits machine-readable JSON type audit and bit-boundary verification
 */

#include "protocol_types.h"
#include "waveform_gen.h"
#include "ring_buffer.h"
#include "packet_framing.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <io.h>
#include <fcntl.h>
#endif

#define SAMPLES_PER_FRAME_DEFAULT 256U
#define DEFAULT_DURATION_SECONDS   10.0

static void set_binary_stdout(void) {
#if defined(_WIN32)
    _setmode(_fileno(stdout), _O_BINARY);
#endif
}

static void print_type_audit_json(void) {
    uint32_t endian_test = 0x01020304U;
    uint8_t *b = (uint8_t *)&endian_test;
    bool is_le = (b[0] == 0x04 && b[3] == 0x01);

    int32_t neg_one = -1;
    bool twos_comp = (*(uint32_t *)&neg_one == 0xFFFFFFFFU);

    uint32_t raw_24_neg = 0x00800000U;
    int32_t extended = sign_extend_24_to_32(raw_24_neg);
    bool sign_ext_ok = (extended == -8388608LL);

    fprintf(stdout, "{\n");
    fprintf(stdout, "  \"schema\": \"auscultaforge.protocol_forge.c_audit.v1\",\n");
    fprintf(stdout, "  \"version\": \"%u.%u.%u\",\n", PROTOCOL_VERSION_MAJOR, PROTOCOL_VERSION_MINOR, PROTOCOL_VERSION_PATCH);
    fprintf(stdout, "  \"type_audit\": {\n");
    fprintf(stdout, "    \"sizeof_ProfileAHeader\": %zu,\n", sizeof(ProfileAHeader));
    fprintf(stdout, "    \"sizeof_ProfileBHeader\": %zu,\n", sizeof(ProfileBHeader));
    fprintf(stdout, "    \"sizeof_int16\": %zu,\n", sizeof(int16_t));
    fprintf(stdout, "    \"sizeof_int32\": %zu,\n", sizeof(int32_t));
    fprintf(stdout, "    \"sizeof_uint32\": %zu,\n", sizeof(uint32_t));
    fprintf(stdout, "    \"sizeof_uint64\": %zu,\n", sizeof(uint64_t));
    fprintf(stdout, "    \"is_little_endian\": %s,\n", is_le ? "true" : "false");
    fprintf(stdout, "    \"twos_complement_ok\": %s,\n", twos_comp ? "true" : "false");
    fprintf(stdout, "    \"sign_extension_24to32_ok\": %s\n", sign_ext_ok ? "true" : "false");
    fprintf(stdout, "  },\n");
    fprintf(stdout, "  \"limits\": {\n");
    fprintf(stdout, "    \"int24_min\": %lld,\n", (long long)INT24_MIN);
    fprintf(stdout, "    \"int24_max\": %lld,\n", (long long)INT24_MAX);
    fprintf(stdout, "    \"int32_min\": %lld,\n", (long long)INT32_MIN_VAL);
    fprintf(stdout, "    \"int32_max\": %lld\n", (long long)INT32_MAX_VAL);
    fprintf(stdout, "  }\n");
    fprintf(stdout, "}\n");
}

int main(int argc, char **argv) {
    const char *mode = "audit";
    const char *signal_str = "sine_100hz";
    double duration_s = DEFAULT_DURATION_SECONDS;
    bool use_profile_b = true;
    uint32_t sample_rate = NOMINAL_SAMPLE_RATE_HZ;
    uint16_t samples_per_frame = SAMPLES_PER_FRAME_DEFAULT;

    for (int i = 1; i < argc; ++i) {
        if (strncmp(argv[i], "--mode=", 7) == 0) {
            mode = argv[i] + 7;
        } else if (strncmp(argv[i], "--signal=", 9) == 0) {
            signal_str = argv[i] + 9;
        } else if (strncmp(argv[i], "--seconds=", 10) == 0) {
            duration_s = atof(argv[i] + 10);
        } else if (strcmp(argv[i], "--profile=a") == 0) {
            use_profile_b = false;
            samples_per_frame = 512;
        } else if (strcmp(argv[i], "--profile=b") == 0) {
            use_profile_b = true;
            samples_per_frame = 256;
        } else if (strcmp(argv[i], "--audit") == 0) {
            mode = "audit";
        }
    }

    if (strcmp(mode, "audit") == 0) {
        print_type_audit_json();
        return 0;
    }

    /* Configure Waveform Generator */
    GeneratorSignalType sig_type = GEN_SIGNAL_SINE_100HZ;
    if (strcmp(signal_str, "ramp") == 0) {
        sig_type = GEN_SIGNAL_RAMP_COUNTER;
    } else if (strcmp(signal_str, "silence") == 0) {
        sig_type = GEN_SIGNAL_SILENCE;
    } else if (strcmp(signal_str, "boundary") == 0) {
        sig_type = GEN_SIGNAL_BOUNDARY_STRESS;
    } else if (strcmp(signal_str, "impulse") == 0) {
        sig_type = GEN_SIGNAL_IMPULSE_TRAIN;
    }

    WaveformGeneratorState gen_state;
    waveform_gen_init(&gen_state, sig_type, sample_rate, 100.0, 0.5, false);

    /* Initialize Ring Buffer */
    int32_t ring_storage[4096];
    PcmRingBuffer ring_buf;
    ring_buffer_init(&ring_buf, ring_storage, 4096);

    /* Calculate exact totals */
    uint64_t total_samples_target = (uint64_t)((double)sample_rate * duration_s);
    uint32_t total_frames = (uint32_t)(total_samples_target / samples_per_frame);

    set_binary_stdout();

    bool is_fuzz = (strcmp(mode, "fuzz") == 0);
    uint8_t packet_buffer[2048];
    int32_t frame_samples[1024];

    uint32_t sequence_id = 0;
    uint64_t sample_index_start = 0;

    for (uint32_t frame_idx = 0; frame_idx < total_frames; ++frame_idx) {
        /* Generate samples into ring buffer */
        int32_t raw_block[512];
        waveform_gen_fill_block(&gen_state, raw_block, samples_per_frame);
        size_t pushed = 0;
        ring_buffer_push(&ring_buf, raw_block, samples_per_frame, &pushed);

        /* Read from ring buffer */
        size_t popped = 0;
        ring_buffer_pop(&ring_buf, frame_samples, samples_per_frame, &popped);

        /* Monotonic microsecond timestamp: frame_idx * (samples_per_frame / 48000) * 1e6 */
        uint64_t ts_us = (uint64_t)((double)sample_index_start * (1000000.0 / (double)sample_rate));

        /* FUZZ INJECTION 1: Drop frame 100 */
        if (is_fuzz && frame_idx == 100) {
            sequence_id++;
            sample_index_start += samples_per_frame;
            continue; /* Skip frame completely */
        }

        /* FUZZ INJECTION 4: Inject garbage noise before frame 750 */
        if (is_fuzz && frame_idx == 750) {
            uint8_t garbage[17] = {0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0xFF, 0x42, 0x13, 0x37, 0xAA, 0x54, 0x31, 0x43, 0x53, 0x00, 0x11, 0x22};
            fwrite(garbage, 1, sizeof(garbage), stdout);
        }

        /* FUZZ INJECTION 5: Timestamp regression on frame 1000 */
        if (is_fuzz && frame_idx == 1000 && ts_us > 500000) {
            ts_us -= 500000; /* Regress by 500ms */
        }

        size_t packet_size = 0;
        if (use_profile_b) {
            packet_build_profile_b(
                sequence_id,
                ts_us,
                sample_index_start,
                frame_samples,
                samples_per_frame,
                sample_rate,
                NOMINAL_MEANINGFUL_BITS,
                FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SIMULATED_SOURCE,
                ENCODING_SIGNED_PCM_LSB_ALIGNED,
                0,
                packet_buffer,
                sizeof(packet_buffer),
                &packet_size
            );
        } else {
            packet_build_profile_a(
                sequence_id,
                (uint32_t)ts_us,
                frame_samples,
                samples_per_frame,
                0,
                packet_buffer,
                sizeof(packet_buffer),
                &packet_size
            );
        }

        /* FUZZ INJECTION 2: Corrupt CRC on frame 250 */
        if (is_fuzz && frame_idx == 250 && packet_size > 4) {
            packet_buffer[packet_size - 1] ^= 0xFF;
            packet_buffer[packet_size - 2] ^= 0xFF;
        }

        /* Write packet to stdout */
        fwrite(packet_buffer, 1, packet_size, stdout);

        /* FUZZ INJECTION 3: Emit duplicate packet on frame 500 */
        if (is_fuzz && frame_idx == 500) {
            fwrite(packet_buffer, 1, packet_size, stdout);
        }

        sequence_id++;
        sample_index_start += samples_per_frame;
    }

    fflush(stdout);
    return 0;
}
