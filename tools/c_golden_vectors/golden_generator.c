/**
 * @file golden_generator.c
 * @brief Standalone C executable for generating deterministic golden test vectors.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application) Interoperability Tool for Module B (Embedded)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * Compilation:
 *   gcc -std=c11 -Wall -Wextra -pedantic -O2 golden_generator.c -o golden_generator.exe -lm
 */

#include "golden_common.h"

static void write_binary_file(const char *filepath, const int32_t *samples, size_t count) {
    FILE *f = fopen(filepath, "wb");
    if (!f) {
        fprintf(stderr, "Error: Failed to open %s for writing\n", filepath);
        return;
    }
    size_t written = fwrite(samples, sizeof(int32_t), count, f);
    if (written != count) {
        fprintf(stderr, "Warning: Expected to write %zu samples, wrote %zu\n", count, written);
    }
    fclose(f);
}

static void write_csv_file(
    const char *filepath,
    const int32_t *samples,
    size_t count,
    bool msb_aligned,
    uint32_t sample_rate_hz
) {
    FILE *f = fopen(filepath, "w");
    if (!f) {
        fprintf(stderr, "Error: Failed to open %s for writing\n", filepath);
        return;
    }

    fprintf(f, "# AuscultaForge Golden Vector CSV Dump\n");
    fprintf(f, "# Alignment: %s\n", msb_aligned ? "MSB_ALIGNED (24-in-32)" : "LSB_ALIGNED (24-in-32 sign-extended)");
    fprintf(f, "# SampleRateHz: %u\n", sample_rate_hz);
    fprintf(f, "index,raw_int32,normalized_float,hex_repr\n");

    double scale = msb_aligned ? INT32_SCALE_FACTOR : INT24_SCALE_FACTOR;
    for (size_t i = 0; i < count; ++i) {
        int32_t raw = samples[i];
        double norm = (double)raw / scale;
        fprintf(f, "%zu,%d,%.8f,0x%08X\n", i, raw, norm, (uint32_t)raw);
    }

    fclose(f);
}

static void print_system_audit_json(void) {
    SystemTypeAudit a = audit_system_types();
    printf("{\n");
    printf("  \"schema\": \"%s\",\n", GOLDEN_VECTOR_SCHEMA_STRING);
    printf("  \"version\": \"%d.%d.%d\",\n",
           GOLDEN_VECTOR_VERSION_MAJOR, GOLDEN_VECTOR_VERSION_MINOR, GOLDEN_VECTOR_VERSION_PATCH);
    printf("  \"type_audit\": {\n");
    printf("    \"sizeof_int16_bytes\": %zu,\n", sizeof(int16_t));
    printf("    \"sizeof_int32_bytes\": %zu,\n", sizeof(int32_t));
    printf("    \"sizeof_uint32_bytes\": %zu,\n", sizeof(uint32_t));
    printf("    \"sizeof_float_bytes\": %zu,\n", sizeof(float));
    printf("    \"is_little_endian\": %s,\n", a.is_little_endian ? "true" : "false");
    printf("    \"twos_complement_ok\": %s,\n", a.twos_complement_ok ? "true" : "false");
    printf("    \"sign_extension_24to32_ok\": %s\n", a.sign_extension_ok ? "true" : "false");
    printf("  },\n");
    printf("  \"limits\": {\n");
    printf("    \"int24_min\": %lld,\n", INT24_MIN_VALUE);
    printf("    \"int24_max\": %lld,\n", INT24_MAX_VALUE);
    printf("    \"int32_min\": %lld,\n", INT32_MIN_VALUE);
    printf("    \"int32_max\": %lld\n", INT32_MAX_VALUE);
    printf("  }\n");
    printf("}\n");
}

static void generate_all_fixtures(const char *out_dir) {
    char path_buf[512];
    int32_t samples[1024];

    printf("Generating golden test fixtures into: %s\n", out_dir);

    /* 1. 100 Hz Sine, 48 kHz, 512 samples, LSB-aligned */
    generate_pcm_sine(samples, 512, 48000, 100.0, 0.50, false);
    snprintf(path_buf, sizeof(path_buf), "%s/sine_100hz_48khz_512s_lsb.bin", out_dir);
    write_binary_file(path_buf, samples, 512);
    snprintf(path_buf, sizeof(path_buf), "%s/sine_100hz_48khz_512s_lsb.csv", out_dir);
    write_csv_file(path_buf, samples, 512, false, 48000);

    /* 2. 100 Hz Sine, 48 kHz, 512 samples, MSB-aligned */
    generate_pcm_sine(samples, 512, 48000, 100.0, 0.50, true);
    snprintf(path_buf, sizeof(path_buf), "%s/sine_100hz_48khz_512s_msb.bin", out_dir);
    write_binary_file(path_buf, samples, 512);
    snprintf(path_buf, sizeof(path_buf), "%s/sine_100hz_48khz_512s_msb.csv", out_dir);
    write_csv_file(path_buf, samples, 512, true, 48000);

    /* 3. Ramp Counter, 512 samples, LSB-aligned */
    generate_pcm_counter(samples, 512, -256, 1, false);
    snprintf(path_buf, sizeof(path_buf), "%s/counter_ramp_512s_lsb.bin", out_dir);
    write_binary_file(path_buf, samples, 512);
    snprintf(path_buf, sizeof(path_buf), "%s/counter_ramp_512s_lsb.csv", out_dir);
    write_csv_file(path_buf, samples, 512, false, 48000);

    /* 4. Ramp Counter, 512 samples, MSB-aligned */
    generate_pcm_counter(samples, 512, -256, 1, true);
    snprintf(path_buf, sizeof(path_buf), "%s/counter_ramp_512s_msb.bin", out_dir);
    write_binary_file(path_buf, samples, 512);
    snprintf(path_buf, sizeof(path_buf), "%s/counter_ramp_512s_msb.csv", out_dir);
    write_csv_file(path_buf, samples, 512, true, 48000);

    /* 5. Boundary Stress Vector, LSB-aligned */
    size_t stress_count = generate_boundary_stress_vector(samples, 1024, false);
    snprintf(path_buf, sizeof(path_buf), "%s/boundary_stress_lsb.bin", out_dir);
    write_binary_file(path_buf, samples, stress_count);
    snprintf(path_buf, sizeof(path_buf), "%s/boundary_stress_lsb.csv", out_dir);
    write_csv_file(path_buf, samples, stress_count, false, 48000);

    /* 6. Boundary Stress Vector, MSB-aligned */
    stress_count = generate_boundary_stress_vector(samples, 1024, true);
    snprintf(path_buf, sizeof(path_buf), "%s/boundary_stress_msb.bin", out_dir);
    write_binary_file(path_buf, samples, stress_count);
    snprintf(path_buf, sizeof(path_buf), "%s/boundary_stress_msb.csv", out_dir);
    write_csv_file(path_buf, samples, stress_count, true, 48000);

    /* 7. Write Manifest */
    snprintf(path_buf, sizeof(path_buf), "%s/manifest.json", out_dir);
    FILE *mf = fopen(path_buf, "w");
    if (mf) {
        fprintf(mf, "{\n");
        fprintf(mf, "  \"generator\": \"auscultaforge_golden_generator_c\",\n");
        fprintf(mf, "  \"version\": \"%d.%d.%d\",\n",
                GOLDEN_VECTOR_VERSION_MAJOR, GOLDEN_VECTOR_VERSION_MINOR, GOLDEN_VECTOR_VERSION_PATCH);
        fprintf(mf, "  \"schema\": \"%s\",\n", GOLDEN_VECTOR_SCHEMA_STRING);
        fprintf(mf, "  \"baseline_profile\": {\n");
        fprintf(mf, "    \"sample_rate_hz\": %u,\n", BASELINE_SAMPLE_RATE_HZ);
        fprintf(mf, "    \"container_bits\": %u,\n", BASELINE_CONTAINER_BITS);
        fprintf(mf, "    \"meaningful_bits\": %u,\n", BASELINE_MEANINGFUL_BITS);
        fprintf(mf, "    \"channels\": %u\n", BASELINE_CHANNELS);
        fprintf(mf, "  },\n");
        fprintf(mf, "  \"fixtures\": [\n");
        fprintf(mf, "    \"sine_100hz_48khz_512s_lsb.bin\",\n");
        fprintf(mf, "    \"sine_100hz_48khz_512s_msb.bin\",\n");
        fprintf(mf, "    \"counter_ramp_512s_lsb.bin\",\n");
        fprintf(mf, "    \"counter_ramp_512s_msb.bin\",\n");
        fprintf(mf, "    \"boundary_stress_lsb.bin\",\n");
        fprintf(mf, "    \"boundary_stress_msb.bin\"\n");
        fprintf(mf, "  ]\n");
        fprintf(mf, "}\n");
        fclose(mf);
    }

    printf("Successfully generated all golden fixtures in: %s\n", out_dir);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("AuscultaForge Portable C Golden-Vector Generator v%d.%d.%d\n",
               GOLDEN_VECTOR_VERSION_MAJOR, GOLDEN_VECTOR_VERSION_MINOR, GOLDEN_VECTOR_VERSION_PATCH);
        printf("Usage:\n");
        printf("  %s --verify-types             Run system architecture and signedness audit\n", argv[0]);
        printf("  %s --generate-all <out_dir>   Generate full suite of binary and CSV fixtures\n", argv[0]);
        return 0;
    }

    if (strcmp(argv[1], "--verify-types") == 0) {
        print_system_audit_json();
        return 0;
    }

    if (strcmp(argv[1], "--generate-all") == 0) {
        const char *out_dir = (argc >= 3) ? argv[2] : ".";
        generate_all_fixtures(out_dir);
        return 0;
    }

    fprintf(stderr, "Unknown argument: %s\n", argv[1]);
    return 1;
}
