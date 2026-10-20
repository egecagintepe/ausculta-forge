/**
 * @file test_c_protocol_core.c
 * @brief Comprehensive C11 Unit Test Suite for Protocol Forge Core.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 */

#include "protocol_types.h"
#include "waveform_gen.h"
#include "ring_buffer.h"
#include "packet_framing.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>
#include <math.h>

#define TEST_ASSERT(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "[FAIL] Line %d: %s\n", __LINE__, msg); \
        assert(cond); \
    } \
} while(0)

static void test_crc_known_vectors(void) {
    printf("[TEST] Testing CRC-16 and CRC-32 known answer test vectors...\n");
    const uint8_t kat[] = "123456789";
    size_t kat_len = 9;

    /* CRC-16-CCITT with init 0xFFFF on "123456789" is 0x29B1 */
    uint16_t crc16 = crc16_ccitt_compute(kat, kat_len, 0xFFFFU);
    TEST_ASSERT(crc16 == 0x29B1U, "CRC-16-CCITT vector '123456789' mismatch");

    /* CRC-32 (IEEE 802.3) on "123456789" is 0xCBF43926 */
    uint32_t crc32 = crc32_compute(kat, kat_len);
    TEST_ASSERT(crc32 == 0xCBF43926U, "CRC-32 vector '123456789' mismatch");

    /* Adler-32 on "123456789" is 0x091E01DE */
    uint32_t adler = adler32_compute(kat, kat_len);
    TEST_ASSERT(adler == 0x091E01DEU, "Adler-32 vector '123456789' mismatch");

    printf("  ✓ CRC-16 (0x29B1), CRC-32 (0xCBF43926), Adler-32 (0x091E01DE) verified.\n");
}

static void test_type_audit_and_sign_extension(void) {
    printf("[TEST] Testing C11 type limits, sign extension and endianness...\n");

    TEST_ASSERT(sizeof(ProfileAHeader) == 16, "ProfileAHeader must be exactly 16 bytes");
    TEST_ASSERT(sizeof(ProfileBHeader) == 40, "ProfileBHeader must be exactly 40 bytes");
    TEST_ASSERT(sizeof(int16_t) == 2, "int16_t width");
    TEST_ASSERT(sizeof(int32_t) == 4, "int32_t width");
    TEST_ASSERT(sizeof(uint32_t) == 4, "uint32_t width");
    TEST_ASSERT(sizeof(uint64_t) == 8, "uint64_t width");

    /* Little endian check */
    uint32_t val = 0x01020304U;
    uint8_t *b = (uint8_t *)&val;
    TEST_ASSERT(b[0] == 0x04 && b[3] == 0x01, "Host must be little-endian");

    /* 24-bit to 32-bit sign extension check */
    int32_t min_24 = sign_extend_24_to_32(0x00800000U);
    TEST_ASSERT(min_24 == -8388608LL, "Sign extension of -8,388,608 failed");

    int32_t max_24 = sign_extend_24_to_32(0x007FFFFFU);
    TEST_ASSERT(max_24 == 8388607LL, "Sign extension of +8,388,607 failed");

    int32_t neg_one = sign_extend_24_to_32(0x00FFFFFFU);
    TEST_ASSERT(neg_one == -1, "Sign extension of -1 failed");

    int32_t zero = sign_extend_24_to_32(0x00000000U);
    TEST_ASSERT(zero == 0, "Sign extension of 0 failed");

    /* MSB alignment roundtrip */
    int32_t lsb_val = -1234567;
    int32_t msb_val = lsb_to_msb_aligned(lsb_val);
    int32_t recovered_lsb = msb_to_lsb_aligned(msb_val);
    TEST_ASSERT(recovered_lsb == lsb_val, "MSB-to-LSB alignment roundtrip failed");

    printf("  ✓ C11 integer audit and 24-bit arithmetic limits verified.\n");
}

static void test_waveform_generation(void) {
    printf("[TEST] Testing deterministic waveform generation...\n");

    WaveformGeneratorState state;
    waveform_gen_init(&state, GEN_SIGNAL_SINE_100HZ, 48000, 100.0, 1.0, false);

    int32_t sine_block[480];
    waveform_gen_fill_block(&state, sine_block, 480);

    /* Index 0 should be 0, index 120 (pi/2) should be INT24_MAX (+FS) */
    TEST_ASSERT(sine_block[0] == 0, "Sine at n=0 should be 0");
    TEST_ASSERT(sine_block[120] == (int32_t)INT24_MAX, "Sine at n=120 should be INT24_MAX");
    TEST_ASSERT(sine_block[240] == 0, "Sine at n=240 should be 0");
    TEST_ASSERT(sine_block[360] == -((int32_t)INT24_MAX), "Sine at n=360 should be -INT24_MAX");

    /* Ramp generator test */
    waveform_gen_init(&state, GEN_SIGNAL_RAMP_COUNTER, 48000, 100.0, 1.0, false);
    int32_t ramp_block[100];
    waveform_gen_fill_block(&state, ramp_block, 100);
    for (int i = 0; i < 100; ++i) {
        TEST_ASSERT(ramp_block[i] == i, "Ramp value mismatch");
    }

    /* LE Serialization roundtrip */
    uint8_t byte_buf[400];
    int32_t deserialized[100];
    serialize_samples_le(ramp_block, 100, byte_buf);
    deserialize_samples_le(byte_buf, 100, deserialized);
    for (int i = 0; i < 100; ++i) {
        TEST_ASSERT(deserialized[i] == ramp_block[i], "LE serialization roundtrip mismatch");
    }

    printf("  ✓ Deterministic sine (100 Hz @ 48 kHz), ramp counter, and LE serialization verified.\n");
}

static void test_ring_buffer(void) {
    printf("[TEST] Testing bounded ring buffer with exact sample accounting...\n");

    int32_t storage[10];
    PcmRingBuffer rb;
    ring_buffer_init(&rb, storage, 10);

    TEST_ASSERT(ring_buffer_is_empty(&rb), "Initial ring buffer should be empty");
    TEST_ASSERT(ring_buffer_available_write(&rb) == 10, "Initial available write should be 10");

    int32_t input[6] = {10, 20, 30, 40, 50, 60};
    size_t pushed = 0;
    ProtocolStatus st = ring_buffer_push(&rb, input, 6, &pushed);
    TEST_ASSERT(st == PROTOCOL_OK && pushed == 6, "Push 6 samples");
    TEST_ASSERT(ring_buffer_available_read(&rb) == 6, "Available read should be 6");

    int32_t output[4];
    size_t popped = 0;
    st = ring_buffer_pop(&rb, output, 4, &popped);
    TEST_ASSERT(st == PROTOCOL_OK && popped == 4, "Pop 4 samples");
    TEST_ASSERT(output[0] == 10 && output[3] == 40, "FIFO ordering check");
    TEST_ASSERT(ring_buffer_available_read(&rb) == 2, "Available read should be 2");

    /* Push 8 samples to trigger overflow (2 + 8 = 10 capacity, exactly full) */
    int32_t input2[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    st = ring_buffer_push(&rb, input2, 8, &pushed);
    TEST_ASSERT(st == PROTOCOL_OK && pushed == 8, "Buffer should be full");
    TEST_ASSERT(ring_buffer_is_full(&rb), "Ring buffer should report full");

    /* Attempt to push when full: must report PROTOCOL_ERR_BUFFER_FULL and drop */
    int32_t overflow_sample = 999;
    st = ring_buffer_push(&rb, &overflow_sample, 1, &pushed);
    TEST_ASSERT(st == PROTOCOL_ERR_BUFFER_FULL && pushed == 0, "Overflow should be rejected");
    TEST_ASSERT(rb.overflow_events == 1, "Overflow event counter");
    TEST_ASSERT(rb.overflow_samples_dropped == 1, "Overflow dropped counter");

    /* Total written and read verification */
    TEST_ASSERT(rb.total_samples_written == 14, "Total written should be 14");
    TEST_ASSERT(rb.total_samples_read == 4, "Total read should be 4");

    printf("  ✓ Ring buffer wrap-around, FIFO preservation, and overflow accounting verified.\n");
}

static void test_packet_framing_and_parser(void) {
    printf("[TEST] Testing Profile A and Profile B framing, parser, and re-sync...\n");

    int32_t samples[256];
    for (int i = 0; i < 256; ++i) samples[i] = i * 100;

    /* Build Profile B frame */
    uint8_t frame_buf[2048];
    size_t frame_len = 0;
    ProtocolStatus st = packet_build_profile_b(
        42,
        1000000ULL,
        10752ULL,
        samples,
        256,
        48000,
        24,
        FRAME_FLAG_TIMESTAMP_VALID,
        ENCODING_SIGNED_PCM_LSB_ALIGNED,
        0,
        frame_buf,
        sizeof(frame_buf),
        &frame_len
    );
    TEST_ASSERT(st == PROTOCOL_OK, "Profile B build");
    TEST_ASSERT(frame_len == PROFILE_B_FRAME_TOTAL_BYTES, "Profile B frame size must be 1068 bytes");

    /* Parse frame using streaming parser */
    StreamPacketParser parser;
    parser_init(&parser);

    DecodedFrame decoded[4];
    size_t emitted = 0;
    st = parser_feed_bytes(&parser, frame_buf, frame_len, decoded, 4, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Profile B feed and parse");
    TEST_ASSERT(decoded[0].crc_ok == true, "CRC must pass");
    TEST_ASSERT(decoded[0].sequence_id == 42, "Sequence match");
    TEST_ASSERT(decoded[0].sample_count == 256, "Sample count match");
    TEST_ASSERT(decoded[0].samples[0] == 0 && decoded[0].samples[255] == 25500, "Payload match");

    /* Byte fragmentation test: feed parser 7 bytes at a time! */
    parser_init(&parser);
    size_t offset = 0;
    size_t chunk_size = 7;
    size_t total_emitted_fragmented = 0;

    while (offset < frame_len) {
        size_t n = (offset + chunk_size <= frame_len) ? chunk_size : (frame_len - offset);
        parser_feed_bytes(&parser, frame_buf + offset, n, decoded, 4, &emitted);
        total_emitted_fragmented += emitted;
        offset += n;
    }
    TEST_ASSERT(total_emitted_fragmented == 1, "7-byte chunk fragmented read must assemble exactly 1 frame");
    TEST_ASSERT(decoded[0].crc_ok == true, "Fragmented frame CRC ok");

    /* Resynchronization test: prepend 31 bytes of garbage before a valid frame */
    parser_init(&parser);
    uint8_t stream_with_garbage[2048 + 31];
    memset(stream_with_garbage, 0xEE, 31);
    memcpy(stream_with_garbage + 31, frame_buf, frame_len);

    st = parser_feed_bytes(&parser, stream_with_garbage, frame_len + 31, decoded, 4, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Sync hunt should find frame after 31 garbage bytes");
    TEST_ASSERT(parser.garbage_bytes_discarded == 31, "Garbage bytes counter should be 31");

    printf("  ✓ Profile B framing, 1068-byte sizing, 7-byte fragmentation, and sync recovery verified.\n");
}

int main(void) {
    printf("=================================================================\n");
    printf("AuscultaForge Protocol Core — C11 Portable Test Suite\n");
    printf("=================================================================\n");

    test_crc_known_vectors();
    test_type_audit_and_sign_extension();
    test_waveform_generation();
    test_ring_buffer();
    test_packet_framing_and_parser();

    printf("=================================================================\n");
    printf("ALL PORTABLE C11 CORE TESTS PASSED (100%%)!\n");
    printf("=================================================================\n");
    return 0;
}
