/**
 * @file test_c_protocol_core.c
 * @brief Comprehensive C11 Unit & Stress Test Suite for Protocol Forge Core.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Joint Reviewer: Ozan (Module B)
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
#include <pthread.h>

#define TEST_ASSERT(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "[FAIL] Line %d: %s\n", __LINE__, msg); \
        assert(cond); \
    } \
} while(0)

/* ========================================================================= */
/* 1. CRC Algorithms Known Answer Tests                                      */
/* ========================================================================= */

static void test_crc_known_vectors(void) {
    printf("[TEST] Testing CRC-16, CRC-32 and Adler-32 known answer vectors...\n");
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

/* ========================================================================= */
/* 2. Portable PCM Arithmetic & Type Boundaries (Gate 2)                     */
/* ========================================================================= */

static void test_portable_pcm_arithmetic(void) {
    printf("[TEST] Testing portable C11 PCM arithmetic, boundary edge cases, and MSB/LSB...\n");

    /* Edge case: -8388608 (INT24_MIN) */
    int32_t min_24 = sign_extend_24_to_32(0x00800000U);
    TEST_ASSERT(min_24 == -8388608LL, "Sign extension of INT24_MIN (-8,388,608) failed");

    /* Edge case: +8388607 (INT24_MAX) */
    int32_t max_24 = sign_extend_24_to_32(0x007FFFFFU);
    TEST_ASSERT(max_24 == 8388607LL, "Sign extension of INT24_MAX (+8,388,607) failed");

    /* Edge case: -1 (all bits set in 24-bit) */
    int32_t neg_one = sign_extend_24_to_32(0x00FFFFFFU);
    TEST_ASSERT(neg_one == -1, "Sign extension of -1 failed");

    /* Edge case: 0 */
    int32_t zero = sign_extend_24_to_32(0x00000000U);
    TEST_ASSERT(zero == 0, "Sign extension of 0 failed");

    /* Edge case: +1 */
    int32_t plus_one = sign_extend_24_to_32(0x00000001U);
    TEST_ASSERT(plus_one == 1, "Sign extension of +1 failed");

    /* Generic N-bit sign extension */
    int32_t ext_val = 0;
    ProtocolStatus st = sign_extend_n_to_32(0x8000U, 16, &ext_val);
    TEST_ASSERT(st == PROTOCOL_OK && ext_val == -32768, "16-bit min sign extension");

    st = sign_extend_n_to_32(0x7FFFU, 16, &ext_val);
    TEST_ASSERT(st == PROTOCOL_OK && ext_val == 32767, "16-bit max sign extension");

    /* Invalid bit depth parameter testing */
    st = sign_extend_n_to_32(100, 0, &ext_val);
    TEST_ASSERT(st == PROTOCOL_ERR_INVALID_PARAM, "0 bits must return INVALID_PARAM");

    st = sign_extend_n_to_32(100, 33, &ext_val);
    TEST_ASSERT(st == PROTOCOL_ERR_INVALID_PARAM, "33 bits must return INVALID_PARAM");

    st = sign_extend_n_to_32(100, 24, NULL);
    TEST_ASSERT(st == PROTOCOL_ERR_NULL_PTR, "NULL output ptr must return NULL_PTR");

    /* MSB vs LSB alignment roundtrip for boundary values */
    static const int32_t test_values[] = {-8388608, -8388607, -1, 0, 1, 8388606, 8388607, 4194304, -4194304};
    for (size_t i = 0; i < sizeof(test_values)/sizeof(test_values[0]); ++i) {
        int32_t orig = test_values[i];
        int32_t msb = lsb_to_msb_aligned(orig);
        int32_t recovered = msb_to_lsb_aligned(msb);
        TEST_ASSERT(recovered == orig, "MSB/LSB alignment roundtrip failed for test value");
    }

    /* Little-endian sample serialization */
    int32_t raw_samples[5] = {-8388608, -1, 0, 1, 8388607};
    uint8_t serialized[20];
    int32_t deserialized[5];

    serialize_samples_le(raw_samples, 5, serialized);
    deserialize_samples_le(serialized, 5, deserialized);
    for (int i = 0; i < 5; ++i) {
        TEST_ASSERT(deserialized[i] == raw_samples[i], "Sample LE serialization roundtrip failed");
    }

    printf("  ✓ Signed 24-bit boundaries, generic N-bit sign extension, and MSB/LSB verified.\n");
}

/* ========================================================================= */
/* 3. Explicit Header Encoding & Byte Offset Verification (Gate 3)            */
/* ========================================================================= */

static void test_explicit_header_wire_encoding(void) {
    printf("[TEST] Testing explicit field-by-field little-endian header encoding & offsets...\n");

    ProfileBHeader b_in;
    b_in.magic = PROFILE_B_MAGIC_U32;
    b_in.version = 1;
    b_in.msg_type = MSG_TYPE_AUDIO_DATA;
    b_in.flags = 0x8041;                /* 16-bit flags test */
    b_in.sequence_id = 0xA1B2C3D4U;
    b_in.sample_rate_hz = 48000;
    b_in.timestamp_us = 0x0102030405060708ULL;
    b_in.sample_index_start = 0x1122334455667788ULL;
    b_in.sample_count = 256;
    b_in.meaningful_bits = 24;
    b_in.container_bits = 32;
    b_in.channels = 1;
    b_in.encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED;
    b_in.mcu_buffer_drops = 7;

    uint8_t wire[40];
    memset(wire, 0, sizeof(wire));
    ProtocolStatus st = packet_encode_header_profile_b(&b_in, wire);
    TEST_ASSERT(st == PROTOCOL_OK, "Encode Profile B");

    /* Offset verification */
    TEST_ASSERT(wire[0] == 0x31 && wire[1] == 0x43 && wire[2] == 0x53 && wire[3] == 0xAF, "Offset 0..3: magic");
    TEST_ASSERT(wire[4] == 1, "Offset 4: version");
    TEST_ASSERT(wire[5] == 1, "Offset 5: msg_type");
    TEST_ASSERT(wire[6] == 0x41 && wire[7] == 0x80, "Offset 6..7: flags (0x8041 LE)");
    TEST_ASSERT(wire[8] == 0xD4 && wire[9] == 0xC3 && wire[10] == 0xB2 && wire[11] == 0xA1, "Offset 8..11: sequence");
    TEST_ASSERT(wire[12] == 0x80 && wire[13] == 0xBB && wire[14] == 0x00 && wire[15] == 0x00, "Offset 12..15: 48000 Hz LE");
    TEST_ASSERT(wire[16] == 0x08 && wire[23] == 0x01, "Offset 16..23: timestamp_us LE");
    TEST_ASSERT(wire[24] == 0x88 && wire[31] == 0x11, "Offset 24..31: sample_index_start LE");
    TEST_ASSERT(wire[32] == 0x00 && wire[33] == 0x01, "Offset 32..33: 256 samples LE");
    TEST_ASSERT(wire[34] == 24, "Offset 34: meaningful_bits");
    TEST_ASSERT(wire[35] == 32, "Offset 35: container_bits");
    TEST_ASSERT(wire[36] == 1, "Offset 36: channels");
    TEST_ASSERT(wire[37] == 1, "Offset 37: encoding");
    TEST_ASSERT(wire[38] == 7 && wire[39] == 0, "Offset 38..39: mcu_buffer_drops");

    /* Decode back */
    ProfileBHeader b_out;
    st = packet_decode_header_profile_b(wire, &b_out);
    TEST_ASSERT(st == PROTOCOL_OK, "Decode Profile B");
    TEST_ASSERT(b_out.magic == b_in.magic, "Magic match");
    TEST_ASSERT(b_out.flags == 0x8041, "Full 16-bit flags match");
    TEST_ASSERT(b_out.sequence_id == b_in.sequence_id, "Seq match");
    TEST_ASSERT(b_out.timestamp_us == b_in.timestamp_us, "TS match");
    TEST_ASSERT(b_out.sample_index_start == b_in.sample_index_start, "Idx match");
    TEST_ASSERT(b_out.sample_count == b_in.sample_count, "Count match");
    TEST_ASSERT(b_out.mcu_buffer_drops == b_in.mcu_buffer_drops, "Drops match");

    printf("  ✓ Explicit 40-byte field offsets and little-endian wire serialization verified.\n");
}

/* ========================================================================= */
/* 4. SPSC Ring Buffer Single-Threaded Logic (Gate 1)                         */
/* ========================================================================= */

static void test_ring_buffer_basic(void) {
    printf("[TEST] Testing lock-free SPSC ring buffer basic invariants...\n");

    int32_t storage[16];
    PcmRingBuffer rb;

    /* Invalid capacity check: 10 is not a power of 2 */
    ProtocolStatus st = ring_buffer_init(&rb, storage, 10);
    TEST_ASSERT(st == PROTOCOL_ERR_INVALID_PARAM, "Non-power of two capacity must be rejected");

    /* Valid power-of-two capacity: 16 */
    st = ring_buffer_init(&rb, storage, 16);
    TEST_ASSERT(st == PROTOCOL_OK, "Capacity 16 init");

    TEST_ASSERT(ring_buffer_is_empty(&rb), "Initial ring buffer should be empty");
    TEST_ASSERT(ring_buffer_available_write(&rb) == 16, "Initial available write should be 16");

    int32_t input[6] = {10, 20, 30, 40, 50, 60};
    size_t pushed = 0;
    st = ring_buffer_push(&rb, input, 6, &pushed);
    TEST_ASSERT(st == PROTOCOL_OK && pushed == 6, "Push 6 samples");
    TEST_ASSERT(ring_buffer_available_read(&rb) == 6, "Available read should be 6");

    int32_t output[4];
    size_t popped = 0;
    st = ring_buffer_pop(&rb, output, 4, &popped);
    TEST_ASSERT(st == PROTOCOL_OK && popped == 4, "Pop 4 samples");
    TEST_ASSERT(output[0] == 10 && output[3] == 40, "FIFO ordering check");
    TEST_ASSERT(ring_buffer_available_read(&rb) == 2, "Available read should be 2");

    /* Push 14 samples to trigger exact full (2 + 14 = 16 capacity) */
    int32_t input2[14] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14};
    st = ring_buffer_push(&rb, input2, 14, &pushed);
    TEST_ASSERT(st == PROTOCOL_OK && pushed == 14, "Buffer should be full");
    TEST_ASSERT(ring_buffer_is_full(&rb), "Ring buffer should report full");

    /* Attempt to push when full: must report PROTOCOL_ERR_BUFFER_FULL and drop */
    int32_t overflow_sample = 999;
    st = ring_buffer_push(&rb, &overflow_sample, 1, &pushed);
    TEST_ASSERT(st == PROTOCOL_ERR_BUFFER_FULL && pushed == 0, "Overflow should be rejected");
    TEST_ASSERT(rb.overflow_events == 1, "Overflow event counter");
    TEST_ASSERT(rb.overflow_samples_dropped == 1, "Overflow dropped counter");

    /* Pop all remaining 16 samples */
    int32_t drain[16];
    st = ring_buffer_pop(&rb, drain, 16, &popped);
    TEST_ASSERT(st == PROTOCOL_OK && popped == 16, "Drain buffer");
    TEST_ASSERT(ring_buffer_is_empty(&rb), "Buffer should be empty");

    /* Total written and read verification */
    TEST_ASSERT(rb.total_samples_written == 20, "Total written should be 20");
    TEST_ASSERT(rb.total_samples_read == 20, "Total read should be 20");

    printf("  ✓ SPSC power-of-two invariants and overflow accounting verified.\n");
}

/* ========================================================================= */
/* 5. Concurrent SPSC Multi-Threaded Stress Test (Gate 1)                     */
/* ========================================================================= */

#define CONCURRENT_SAMPLE_COUNT  500000U
#define CONCURRENT_BUFFER_SIZE   1024U

typedef struct {
    PcmRingBuffer *rb;
    uint32_t total_samples;
    bool producer_done;
} ThreadContext;

static void *producer_thread_func(void *arg) {
    ThreadContext *ctx = (ThreadContext *)arg;
    uint32_t written = 0;
    int32_t chunk[128];

    while (written < ctx->total_samples) {
        size_t to_write = 1 + (rand() % 128);
        if (written + to_write > ctx->total_samples) {
            to_write = ctx->total_samples - written;
        }

        for (size_t i = 0; i < to_write; ++i) {
            chunk[i] = (int32_t)(written + i);
        }

        size_t pushed = 0;
        ProtocolStatus st = ring_buffer_push(ctx->rb, chunk, to_write, &pushed);
        written += (uint32_t)pushed;

        if (st == PROTOCOL_ERR_BUFFER_FULL || pushed == 0) {
            sched_yield();
        }
    }

    ctx->producer_done = true;
    return NULL;
}

static void *consumer_thread_func(void *arg) {
    ThreadContext *ctx = (ThreadContext *)arg;
    uint32_t expected_val = 0;
    int32_t chunk[128];

    while (!ctx->producer_done || !ring_buffer_is_empty(ctx->rb)) {
        size_t to_read = 1 + (rand() % 128);
        size_t popped = 0;
        ring_buffer_pop(ctx->rb, chunk, to_read, &popped);

        for (size_t i = 0; i < popped; ++i) {
            if (chunk[i] != (int32_t)expected_val) {
                fprintf(stderr, "[CONCURRENT FAIL] Data corruption! Expected %u, got %d\n",
                        expected_val, chunk[i]);
                assert(chunk[i] == (int32_t)expected_val);
            }
            expected_val++;
        }

        if (popped == 0) {
            sched_yield();
        }
    }

    TEST_ASSERT(expected_val == ctx->total_samples, "Consumer must receive all samples");
    return NULL;
}

static void test_concurrent_spsc_stress(void) {
    printf("[TEST] Testing concurrent multi-threaded SPSC stress (%u samples)...\n", CONCURRENT_SAMPLE_COUNT);

    int32_t *storage = (int32_t *)malloc(CONCURRENT_BUFFER_SIZE * sizeof(int32_t));
    TEST_ASSERT(storage != NULL, "Alloc storage");

    PcmRingBuffer rb;
    ring_buffer_init(&rb, storage, CONCURRENT_BUFFER_SIZE);

    ThreadContext ctx;
    ctx.rb = &rb;
    ctx.total_samples = CONCURRENT_SAMPLE_COUNT;
    ctx.producer_done = false;

    pthread_t prod_thread, cons_thread;
    int rc1 = pthread_create(&prod_thread, NULL, producer_thread_func, &ctx);
    int rc2 = pthread_create(&cons_thread, NULL, consumer_thread_func, &ctx);
    TEST_ASSERT(rc1 == 0 && rc2 == 0, "Thread creation");

    pthread_join(prod_thread, NULL);
    pthread_join(cons_thread, NULL);

    TEST_ASSERT(rb.total_samples_written == CONCURRENT_SAMPLE_COUNT, "Total samples written");
    TEST_ASSERT(rb.total_samples_read == CONCURRENT_SAMPLE_COUNT, "Total samples read");
    TEST_ASSERT(ring_buffer_is_empty(&rb), "Buffer empty at termination");

    free(storage);
    printf("  ✓ Concurrent SPSC lock-free producer/consumer verified with ZERO corruption.\n");
}

/* ========================================================================= */
/* 6. Canonical Control Messages & 72B Telemetry Suite                        */
/* ========================================================================= */

static void test_canonical_control_messages(void) {
    printf("[TEST] Testing all canonical control message encoders, decoders, builders & parsers...\n");

    /* Gate 3 & Gate 7: Exact wire payload size assertions (Field-by-field wire encoding guarantee) */
    TEST_ASSERT(START_ACK_PAYLOAD_SIZE == 32U, "START_ACK wire payload MUST be exactly 32 bytes");
    TEST_ASSERT(START_REQ_PAYLOAD_SIZE == 16U, "START_REQ wire payload MUST be exactly 16 bytes");
    TEST_ASSERT(HELLO_REQ_PAYLOAD_SIZE == 4U, "HELLO_REQ wire payload MUST be exactly 4 bytes");
    TEST_ASSERT(HELLO_ACK_PAYLOAD_SIZE == 24U, "HELLO_ACK wire payload MUST be exactly 24 bytes");
    TEST_ASSERT(STOP_REQ_PAYLOAD_SIZE == 8U, "STOP_REQ wire payload MUST be exactly 8 bytes");
    TEST_ASSERT(STATUS_TELEMETRY_PAYLOAD_SIZE == 72U, "STATUS wire payload MUST be exactly 72 bytes");
    TEST_ASSERT(ERROR_PAYLOAD_SIZE == 8U, "ERROR wire payload MUST be exactly 8 bytes");

    /* Gate 5: Normative deterministic known-answer sequence vectors */
    #define CALC_NORMATIVE_SAMPLE(idx) (((uint32_t)(((uint64_t)(idx) * 16807ULL + 7ULL) & 0x00FFFFFFULL) & 0x00800000U) ? \
        ((int32_t)((uint32_t)(((uint64_t)(idx) * 16807ULL + 7ULL) & 0x00FFFFFFULL) - 0x01000000U)) : \
        ((int32_t)(((uint64_t)(idx) * 16807ULL + 7ULL) & 0x00FFFFFFULL)))

    TEST_ASSERT(CALC_NORMATIVE_SAMPLE(0) == 7, "Known vector n=0 -> 7");
    TEST_ASSERT(CALC_NORMATIVE_SAMPLE(1) == 16814, "Known vector n=1 -> 16814");
    TEST_ASSERT(CALC_NORMATIVE_SAMPLE(500) == -8373709, "Known vector n=500 -> -8373709");
    TEST_ASSERT(CALC_NORMATIVE_SAMPLE(1000) == 29791, "Known vector n=1000 -> 29791");
    TEST_ASSERT(CALC_NORMATIVE_SAMPLE(479999) == -2497696, "Known vector n=479999 -> -2497696");

    StreamPacketParser parser;
    parser_init(&parser);
    DecodedFrame frames[10];
    size_t emitted = 0;

    /* 1. HELLO_REQ & HELLO_ACK */
    uint8_t hello_req_wire[64];
    size_t hello_req_len = 0;
    ProtocolStatus st = packet_build_hello_req(0xDEADBEEF, hello_req_wire, sizeof(hello_req_wire), &hello_req_len);
    TEST_ASSERT(st == PROTOCOL_OK && hello_req_len == 48, "Build HELLO_REQ (48B)");

    st = parser_feed_bytes(&parser, hello_req_wire, hello_req_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse HELLO_REQ");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_HELLO_REQ, "Opcode HELLO_REQ");
    TEST_ASSERT(frames[0].sample_count == 0, "Control sample_count MUST be 0");
    TEST_ASSERT(frames[0].control_payload_len == 4, "Control payload len 4");
    HelloReqPayload parsed_hello_req;
    packet_decode_hello_req(frames[0].control_payload, &parsed_hello_req);
    TEST_ASSERT(parsed_hello_req.host_nonce == 0xDEADBEEF, "Host nonce echo check");

    HelloAckPayload ack_in = {
        .nonce_echo = 0xDEADBEEF,
        .protocol_version_major = 1,
        .protocol_version_minor = 0,
        .supported_profiles_mask = 0x02,
        .supported_encodings_mask = 0x01,
        .hardware_sample_rate_hz = 48000,
        .firmware_version_major = 1,
        .firmware_version_minor = 0,
        .firmware_version_patch = 0,
        .reserved = 0,
        .max_frame_samples = 256,
        .capability_flags = 0x0007,
        .device_uid_low = 0x12345678
    };
    uint8_t hello_ack_wire[128];
    size_t hello_ack_len = 0;
    st = packet_build_hello_ack(&ack_in, hello_ack_wire, sizeof(hello_ack_wire), &hello_ack_len);
    TEST_ASSERT(st == PROTOCOL_OK && hello_ack_len == 68, "Build HELLO_ACK (68B)");

    st = parser_feed_bytes(&parser, hello_ack_wire, hello_ack_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse HELLO_ACK");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_HELLO_ACK, "Opcode HELLO_ACK");
    HelloAckPayload ack_out;
    packet_decode_hello_ack(frames[0].control_payload, &ack_out);
    TEST_ASSERT(ack_out.nonce_echo == 0xDEADBEEF, "Nonce echo match");
    TEST_ASSERT(ack_out.hardware_sample_rate_hz == 48000, "HW rate 48000");

    /* 2. START_REQ & START_ACK */
    StartReqPayload start_req_in = {
        .sample_rate_hz = 48000,
        .target_samples = 480000,
        .source_mode = SOURCE_MODE_SYNTH_RAMP,
        .encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED,
        .channels = 1,
        .profile_id = 2
    };
    uint8_t start_req_wire[128];
    size_t start_req_len = 0;
    st = packet_build_start_req(&start_req_in, start_req_wire, sizeof(start_req_wire), &start_req_len);
    TEST_ASSERT(st == PROTOCOL_OK && start_req_len == 60, "Build START_REQ (60B)");

    st = parser_feed_bytes(&parser, start_req_wire, start_req_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse START_REQ");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_STREAM_START_REQ, "Opcode START_REQ");
    StartReqPayload start_req_out;
    packet_decode_start_req(frames[0].control_payload, &start_req_out);
    TEST_ASSERT(start_req_out.target_samples == 480000, "Target samples 480000");

    StartAckPayload start_ack_in = {
        .session_id = 0x9876543210ABCDEFULL,
        .session_reference_time_us = 1000000,
        .accepted_sample_rate_hz = 48000,
        .accepted_target_samples = 480000,
        .accepted_source_mode = SOURCE_MODE_SYNTH_RAMP,
        .encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED,
        .channels = 1,
        .profile_id = 2
    };
    uint8_t start_ack_wire[128];
    size_t start_ack_len = 0;
    st = packet_build_start_ack(&start_ack_in, start_ack_wire, sizeof(start_ack_wire), &start_ack_len);
    TEST_ASSERT(st == PROTOCOL_OK && start_ack_len == 76, "Build START_ACK (76B)");

    st = parser_feed_bytes(&parser, start_ack_wire, start_ack_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse START_ACK");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_STREAM_START_ACK, "Opcode START_ACK");
    StartAckPayload start_ack_out;
    packet_decode_start_ack(frames[0].control_payload, &start_ack_out);
    TEST_ASSERT(start_ack_out.session_id == 0x9876543210ABCDEFULL, "Session ID match");

    /* 3. STATUS & STOP_ACK (72B Telemetry) */
    StatusTelemetryPayload telem_in = {
        .session_id = 0x9876543210ABCDEFULL,
        .generated_samples = 480000,
        .fully_queued_samples = 480000,
        .dropped_samples = 0,
        .audio_frames_queued = 1875,
        .dma_overflow_events = 0,
        .ring_overflow_events = 0,
        .usb_partial_write_events = 0,
        .usb_timeout_events = 0,
        .usb_disconnect_events = 0,
        .audio_bytes_queued = 1875 * 1068,
        .stop_reason = STOP_REASON_NORMAL_TARGET_REACHED,
        .error_code = 0
    };
    uint8_t status_wire[256];
    size_t status_len = 0;
    st = packet_build_status(&telem_in, 100, 2000000, status_wire, sizeof(status_wire), &status_len);
    TEST_ASSERT(st == PROTOCOL_OK && status_len == 116, "Build STATUS (116B)");

    st = parser_feed_bytes(&parser, status_wire, status_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse STATUS");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_HEARTBEAT_STATUS, "Opcode STATUS");
    StatusTelemetryPayload telem_out;
    packet_decode_status_telemetry(frames[0].control_payload, &telem_out);
    TEST_ASSERT(telem_out.generated_samples == 480000, "Telemetry generated samples match");
    TEST_ASSERT(telem_out.audio_frames_queued == 1875, "Telemetry frames queued match");

    uint8_t stop_ack_wire[256];
    size_t stop_ack_len = 0;
    st = packet_build_stop_ack(&telem_in, stop_ack_wire, sizeof(stop_ack_wire), &stop_ack_len);
    TEST_ASSERT(st == PROTOCOL_OK && stop_ack_len == 116, "Build STOP_ACK (116B)");

    st = parser_feed_bytes(&parser, stop_ack_wire, stop_ack_len, frames, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Parse STOP_ACK");
    TEST_ASSERT(frames[0].msg_type == MSG_TYPE_STREAM_STOP_ACK, "Opcode STOP_ACK");

    /* 4. STOP_REQ and ERROR */
    uint8_t stop_req_wire[128];
    size_t stop_req_len = 0;
    st = packet_build_stop_req(0x9876543210ABCDEFULL, stop_req_wire, sizeof(stop_req_wire), &stop_req_len);
    TEST_ASSERT(st == PROTOCOL_OK && stop_req_len == 52, "Build STOP_REQ (52B)");

    uint8_t err_wire[128];
    size_t err_len = 0;
    st = packet_build_error(0x00000003, 0x00000042, err_wire, sizeof(err_wire), &err_len);
    TEST_ASSERT(st == PROTOCOL_OK && err_len == 52, "Build ERROR (52B)");

    /* Verify parser safely rejects unknown opcode */
    uint8_t unknown_wire[64];
    memcpy(unknown_wire, hello_req_wire, hello_req_len);
    unknown_wire[5] = 0xEE; /* Invalid opcode */
    /* Update CRC so it's not a CRC error but an opcode error */
    uint32_t fake_crc = crc32_compute(unknown_wire, 44);
    unknown_wire[44] = (uint8_t)(fake_crc & 0xFF);
    unknown_wire[45] = (uint8_t)((fake_crc >> 8) & 0xFF);
    unknown_wire[46] = (uint8_t)((fake_crc >> 16) & 0xFF);
    unknown_wire[47] = (uint8_t)((fake_crc >> 24) & 0xFF);
    uint32_t prev_malformed = parser.malformed_headers;
    parser_feed_bytes(&parser, unknown_wire, hello_req_len, frames, 10, &emitted);
    TEST_ASSERT(parser.malformed_headers == prev_malformed + 1, "Unknown opcode safely counted as malformed");

    printf("  ✓ Canonical control messages (HELLO, START, STOP, STATUS, ERROR) and 72B telemetry verified.\n");
}

/* ========================================================================= */
/* 7. Parser Robustness & Sequence Wrapping (Gate 5)                         */
/* ========================================================================= */

static void test_parser_robustness(void) {
    printf("[TEST] Testing parser robustness: partial frames, concatenated frames, sequence wrap...\n");

    StreamPacketParser parser;
    parser_init(&parser);

    /* 1. Partial final frame test (e.g. 100 samples instead of 256) */
    int32_t partial_samples[100];
    for (int i = 0; i < 100; ++i) partial_samples[i] = i * 5;

    uint8_t partial_wire[1024];
    size_t partial_size = 0;
    ProtocolStatus st = packet_build_profile_b(
        1, 1000000ULL, 0ULL, partial_samples, 100, 48000, 24, 0x0001, 1, 0,
        partial_wire, sizeof(partial_wire), &partial_size
    );
    TEST_ASSERT(st == PROTOCOL_OK, "Build partial frame");
    TEST_ASSERT(partial_size == 40 + 100 * 4 + 4, "Partial frame size: 444 bytes");

    DecodedFrame decoded[10];
    size_t emitted = 0;
    st = parser_feed_bytes(&parser, partial_wire, partial_size, decoded, 10, &emitted);
    TEST_ASSERT(st == PROTOCOL_OK && emitted == 1, "Partial frame decode");
    TEST_ASSERT(decoded[0].sample_count == 100, "Decoded sample count match");
    TEST_ASSERT(decoded[0].samples[99] == 495, "Payload match");

    /* 2. Sequence wraparound test: sequence wraps from UINT32_MAX to 0 */
    parser_reset(&parser);

    int32_t s_wrap[16];
    memset(s_wrap, 0, sizeof(s_wrap));
    uint8_t f1[512], f2[512];
    size_t s1 = 0, s2 = 0;

    packet_build_profile_b(UINT32_MAX, 1000000ULL, 0, s_wrap, 16, 48000, 24, 0x0001, 1, 0, f1, sizeof(f1), &s1);
    packet_build_profile_b(0, 1000333ULL, 16, s_wrap, 16, 48000, 24, 0x0001, 1, 0, f2, sizeof(f2), &s2);

    parser_feed_bytes(&parser, f1, s1, decoded, 10, &emitted);
    TEST_ASSERT(emitted == 1, "Frame 1 parsed");

    parser_feed_bytes(&parser, f2, s2, decoded, 10, &emitted);
    TEST_ASSERT(emitted == 1, "Frame 2 parsed across sequence wrap");
    TEST_ASSERT(parser.quality_stats.total_sequence_gaps == 0, "Wrapping UINT32_MAX -> 0 must have ZERO sequence gaps");
    TEST_ASSERT(parser.quality_stats.total_duplicate_frames == 0, "No duplicate");

    /* 3. Reordered frame test: sequence 10 arrives after sequence 15 */
    uint8_t f_late[512];
    size_t s_late = 0;
    packet_build_profile_b(10, 1005000ULL, 160, s_wrap, 16, 48000, 24, 0x0001, 1, 0, f_late, sizeof(f_late), &s_late);
    /* Set last_sequence_id = 15 */
    parser.quality_stats.last_sequence_id = 15;
    parser_feed_bytes(&parser, f_late, s_late, decoded, 10, &emitted);
    TEST_ASSERT(emitted == 1, "Late frame decoded");
    TEST_ASSERT(parser.quality_stats.total_reordered_frames == 1, "Reordered frame counted");
    TEST_ASSERT(parser.quality_stats.total_sequence_gaps == 0, "Reordered frame must NOT inflate sequence gaps");

    /* 4. Single-byte streaming fragmentation test */
    parser_reset(&parser);
    for (size_t i = 0; i < s1; ++i) {
        parser_feed_bytes(&parser, &f1[i], 1, decoded, 10, &emitted);
    }
    TEST_ASSERT(decoded[0].crc_ok == true && decoded[0].sequence_id == UINT32_MAX, "1-byte feeding");

    printf("  ✓ Partial final frames, sequence wraparound, and RFC 3550 reordering verified.\n");
}

int main(void) {
    printf("=================================================================\n");
    printf("AuscultaForge Protocol Core — C11 Portable & Canonical Suite\n");
    printf("=================================================================\n");

    test_crc_known_vectors();
    test_portable_pcm_arithmetic();
    test_explicit_header_wire_encoding();
    test_ring_buffer_basic();
    test_concurrent_spsc_stress();
    test_canonical_control_messages();
    test_parser_robustness();

    printf("=================================================================\n");
    printf("ALL PORTABLE C11 CANONICAL & CONCURRENCY TESTS PASSED (100%%)!\n");
    printf("=================================================================\n");
    return 0;
}
