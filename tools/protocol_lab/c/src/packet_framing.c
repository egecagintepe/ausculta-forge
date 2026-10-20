/**
 * @file packet_framing.c
 * @brief Packet Serialization, Deserialization & CRC Integrity Implementation.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 */

#include "packet_framing.h"
#include <string.h>

/* ========================================================================= */
/* 1. CRC Algorithms                                                         */
/* ========================================================================= */

uint16_t crc16_ccitt_compute(const uint8_t *data, size_t length, uint16_t init_val) {
    if (!data || length == 0) return init_val;

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

/* Precomputed CRC32 Lookup Table (IEEE 802.3 polynomial 0xEDB88320) */
static uint32_t s_crc32_table[256];
static bool s_crc32_table_ready = false;

static void init_crc32_table(void) {
    if (s_crc32_table_ready) return;
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t c = i;
        for (int j = 0; j < 8; ++j) {
            c = (c & 1) ? (0xEDB88320U ^ (c >> 1)) : (c >> 1);
        }
        s_crc32_table[i] = c;
    }
    s_crc32_table_ready = true;
}

uint32_t crc32_compute(const uint8_t *data, size_t length) {
    if (!data || length == 0) return 0;
    init_crc32_table();

    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < length; ++i) {
        crc = s_crc32_table[(crc ^ data[i]) & 0xFFU] ^ (crc >> 8);
    }
    return crc ^ 0xFFFFFFFFU;
}

uint32_t adler32_compute(const uint8_t *data, size_t length) {
    if (!data || length == 0) return 1;

    const uint32_t MOD_ADLER = 65521U;
    uint32_t a = 1U;
    uint32_t b = 0U;

    for (size_t i = 0; i < length; ++i) {
        a = (a + data[i]) % MOD_ADLER;
        b = (b + a) % MOD_ADLER;
    }
    return (b << 16) | a;
}

/* ========================================================================= */
/* 2. Packet Builders                                                        */
/* ========================================================================= */

ProtocolStatus packet_build_profile_a(
    uint32_t sequence,
    uint32_t timestamp_us,
    const int32_t *samples,
    uint16_t count,
    uint16_t flags,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!samples || !out_buffer || !out_size) return PROTOCOL_ERR_NULL_PTR;
    size_t payload_bytes = (size_t)count * sizeof(int32_t);
    size_t total_size = PROFILE_A_HEADER_SIZE + payload_bytes + PROFILE_A_TRAILER_SIZE;

    if (max_buffer_size < total_size) return PROTOCOL_ERR_OVERFLOW;

    ProfileAHeader header;
    header.magic[0] = PROFILE_A_MAGIC_BYTE0;
    header.magic[1] = PROFILE_A_MAGIC_BYTE1;
    header.version = 1;
    header.msg_type = MSG_TYPE_AUDIO_DATA;
    header.sequence = sequence;
    header.timestamp_us = timestamp_us;
    header.sample_count = count;
    header.flags = flags;

    memcpy(out_buffer, &header, PROFILE_A_HEADER_SIZE);

    /* Serialize samples little-endian */
    uint8_t *payload_ptr = out_buffer + PROFILE_A_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        uint32_t u = (uint32_t)samples[i];
        payload_ptr[i * 4 + 0] = (uint8_t)(u & 0xFFU);
        payload_ptr[i * 4 + 1] = (uint8_t)((u >> 8) & 0xFFU);
        payload_ptr[i * 4 + 2] = (uint8_t)((u >> 16) & 0xFFU);
        payload_ptr[i * 4 + 3] = (uint8_t)((u >> 24) & 0xFFU);
    }

    /* Compute CRC-16 over Header + Payload */
    size_t body_len = PROFILE_A_HEADER_SIZE + payload_bytes;
    uint16_t crc = crc16_ccitt_compute(out_buffer, body_len, 0xFFFFU);

    uint8_t *trailer_ptr = out_buffer + body_len;
    trailer_ptr[0] = (uint8_t)(crc & 0xFFU);
    trailer_ptr[1] = (uint8_t)((crc >> 8) & 0xFFU);

    *out_size = total_size;
    return PROTOCOL_OK;
}

ProtocolStatus packet_build_profile_b(
    uint32_t sequence_id,
    uint64_t timestamp_us,
    uint64_t sample_index_start,
    const int32_t *samples,
    uint16_t count,
    uint32_t sample_rate_hz,
    uint8_t meaningful_bits,
    uint8_t flags,
    uint8_t encoding,
    uint16_t mcu_drops,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!samples || !out_buffer || !out_size) return PROTOCOL_ERR_NULL_PTR;
    size_t payload_bytes = (size_t)count * sizeof(int32_t);
    size_t total_size = PROFILE_B_HEADER_SIZE + payload_bytes + PROFILE_B_TRAILER_SIZE;

    if (max_buffer_size < total_size) return PROTOCOL_ERR_OVERFLOW;

    ProfileBHeader header;
    header.magic = PROFILE_B_MAGIC_U32;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.msg_type = MSG_TYPE_AUDIO_DATA;
    header.flags = (uint16_t)flags;
    header.sequence_id = sequence_id;
    header.sample_rate_hz = sample_rate_hz;
    header.timestamp_us = timestamp_us;
    header.sample_index_start = sample_index_start;
    header.sample_count = count;
    header.meaningful_bits = meaningful_bits;
    header.container_bits = NOMINAL_CONTAINER_BITS;
    header.channels = NOMINAL_CHANNELS;
    header.encoding = encoding;
    header.mcu_buffer_drops = mcu_drops;

    memcpy(out_buffer, &header, PROFILE_B_HEADER_SIZE);

    /* Serialize samples little-endian */
    uint8_t *payload_ptr = out_buffer + PROFILE_B_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        uint32_t u = (uint32_t)samples[i];
        payload_ptr[i * 4 + 0] = (uint8_t)(u & 0xFFU);
        payload_ptr[i * 4 + 1] = (uint8_t)((u >> 8) & 0xFFU);
        payload_ptr[i * 4 + 2] = (uint8_t)((u >> 16) & 0xFFU);
        payload_ptr[i * 4 + 3] = (uint8_t)((u >> 24) & 0xFFU);
    }

    /* Compute CRC-32 over Header + Payload */
    size_t body_len = PROFILE_B_HEADER_SIZE + payload_bytes;
    uint32_t crc = crc32_compute(out_buffer, body_len);

    uint8_t *trailer_ptr = out_buffer + body_len;
    trailer_ptr[0] = (uint8_t)(crc & 0xFFU);
    trailer_ptr[1] = (uint8_t)((crc >> 8) & 0xFFU);
    trailer_ptr[2] = (uint8_t)((crc >> 16) & 0xFFU);
    trailer_ptr[3] = (uint8_t)((crc >> 24) & 0xFFU);

    *out_size = total_size;
    return PROTOCOL_OK;
}

/* ========================================================================= */
/* 3. Streaming Parser                                                       */
/* ========================================================================= */

ProtocolStatus parser_init(StreamPacketParser *parser) {
    if (!parser) return PROTOCOL_ERR_NULL_PTR;
    memset(parser, 0, sizeof(StreamPacketParser));
    return PROTOCOL_OK;
}

ProtocolStatus parser_feed_bytes(
    StreamPacketParser *parser,
    const uint8_t *in_bytes,
    size_t in_len,
    DecodedFrame *out_frames,
    size_t max_frames,
    size_t *frames_emitted
) {
    if (!parser || !out_frames || !frames_emitted) return PROTOCOL_ERR_NULL_PTR;
    *frames_emitted = 0;

    if (in_bytes && in_len > 0) {
        if (parser->buffer_len + in_len > sizeof(parser->buffer)) {
            /* Input would overflow internal parse buffer */
            return PROTOCOL_ERR_BUFFER_FULL;
        }
        memcpy(parser->buffer + parser->buffer_len, in_bytes, in_len);
        parser->buffer_len += in_len;
    }

    while (*frames_emitted < max_frames) {
        if (parser->buffer_len < 4) {
            /* Need at least 4 bytes to check sync magic */
            break;
        }

        /* 1. Search for sync magic (Profile B 4B or Profile A 2B) */
        size_t sync_idx = 0;
        bool found_profile_b = false;
        bool found_profile_a = false;

        for (size_t i = 0; i <= parser->buffer_len - 2; ++i) {
            /* Check Profile B magic: 0x31, 0x43, 0x53, 0xAF */
            if (i <= parser->buffer_len - 4) {
                if (parser->buffer[i + 0] == PROFILE_B_MAGIC_BYTE0 &&
                    parser->buffer[i + 1] == PROFILE_B_MAGIC_BYTE1 &&
                    parser->buffer[i + 2] == PROFILE_B_MAGIC_BYTE2 &&
                    parser->buffer[i + 3] == PROFILE_B_MAGIC_BYTE3) {
                    sync_idx = i;
                    found_profile_b = true;
                    break;
                }
            }
            /* Check Profile A magic: 0x55, 0xAA */
            if (parser->buffer[i + 0] == PROFILE_A_MAGIC_BYTE0 &&
                parser->buffer[i + 1] == PROFILE_A_MAGIC_BYTE1) {
                sync_idx = i;
                found_profile_a = true;
                break;
            }
        }

        if (!found_profile_b && !found_profile_a) {
            /* No sync magic anywhere in buffer: discard up to the last 3 bytes */
            if (parser->buffer_len > 3) {
                size_t discarded = parser->buffer_len - 3;
                parser->garbage_bytes_discarded += (uint32_t)discarded;
                memmove(parser->buffer, parser->buffer + discarded, 3);
                parser->buffer_len = 3;
            }
            break;
        }

        if (sync_idx > 0) {
            /* Discard garbage preceding sync magic */
            parser->garbage_bytes_discarded += (uint32_t)sync_idx;
            memmove(parser->buffer, parser->buffer + sync_idx, parser->buffer_len - sync_idx);
            parser->buffer_len -= sync_idx;
        }

        /* 2. Process discovered frame */
        if (found_profile_b) {
            if (parser->buffer_len < PROFILE_B_HEADER_SIZE) {
                /* Incomplete header: wait for more bytes */
                break;
            }

            ProfileBHeader header;
            memcpy(&header, parser->buffer, PROFILE_B_HEADER_SIZE);

            if (header.version != PROTOCOL_VERSION_MAJOR || header.sample_count == 0 || header.sample_count > 1024) {
                /* Malformed header: slide 4 bytes and search again */
                parser->malformed_headers++;
                memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                parser->buffer_len -= 4;
                continue;
            }

            size_t payload_bytes = (size_t)header.sample_count * sizeof(int32_t);
            size_t total_frame_len = PROFILE_B_HEADER_SIZE + payload_bytes + PROFILE_B_TRAILER_SIZE;

            if (parser->buffer_len < total_frame_len) {
                /* Incomplete frame payload: wait for subsequent bytes */
                break;
            }

            /* Extract CRC-32 trailer */
            const uint8_t *trailer_ptr = parser->buffer + PROFILE_B_HEADER_SIZE + payload_bytes;
            uint32_t crc_received = (uint32_t)trailer_ptr[0] |
                                    ((uint32_t)trailer_ptr[1] << 8) |
                                    ((uint32_t)trailer_ptr[2] << 16) |
                                    ((uint32_t)trailer_ptr[3] << 24);

            uint32_t crc_computed = crc32_compute(parser->buffer, PROFILE_B_HEADER_SIZE + payload_bytes);

            DecodedFrame *df = &out_frames[*frames_emitted];
            df->sequence_id = header.sequence_id;
            df->timestamp_us = header.timestamp_us;
            df->sample_index_start = header.sample_index_start;
            df->sample_count = header.sample_count;
            df->sample_rate_hz = header.sample_rate_hz;
            df->meaningful_bits = header.meaningful_bits;
            df->flags = header.flags;
            df->encoding = header.encoding;
            df->mcu_buffer_drops = header.mcu_buffer_drops;
            df->is_profile_b = true;

            if (crc_received != crc_computed) {
                parser->crc_errors++;
                df->crc_ok = false;
                /* On CRC error: consume 4 magic bytes so scanner can look for next frame */
                memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                parser->buffer_len -= 4;
                (*frames_emitted)++;
                continue;
            }

            df->crc_ok = true;
            const uint8_t *payload_ptr = parser->buffer + PROFILE_B_HEADER_SIZE;
            for (size_t i = 0; i < header.sample_count; ++i) {
                uint32_t b0 = (uint32_t)payload_ptr[i * 4 + 0];
                uint32_t b1 = (uint32_t)payload_ptr[i * 4 + 1];
                uint32_t b2 = (uint32_t)payload_ptr[i * 4 + 2];
                uint32_t b3 = (uint32_t)payload_ptr[i * 4 + 3];
                df->samples[i] = (int32_t)(b0 | (b1 << 8) | (b2 << 16) | (b3 << 24));
            }

            parser->valid_packets_parsed++;
            update_stream_quality_stats(&parser->quality_stats, df);
            (*frames_emitted)++;

            /* Consume entire frame */
            memmove(parser->buffer, parser->buffer + total_frame_len, parser->buffer_len - total_frame_len);
            parser->buffer_len -= total_frame_len;

        } else if (found_profile_a) {
            if (parser->buffer_len < PROFILE_A_HEADER_SIZE) {
                break;
            }

            ProfileAHeader header;
            memcpy(&header, parser->buffer, PROFILE_A_HEADER_SIZE);

            if (header.version != 1 || header.sample_count == 0 || header.sample_count > 1024) {
                parser->malformed_headers++;
                memmove(parser->buffer, parser->buffer + 2, parser->buffer_len - 2);
                parser->buffer_len -= 2;
                continue;
            }

            size_t payload_bytes = (size_t)header.sample_count * sizeof(int32_t);
            size_t total_frame_len = PROFILE_A_HEADER_SIZE + payload_bytes + PROFILE_A_TRAILER_SIZE;

            if (parser->buffer_len < total_frame_len) {
                break;
            }

            const uint8_t *trailer_ptr = parser->buffer + PROFILE_A_HEADER_SIZE + payload_bytes;
            uint16_t crc_received = (uint16_t)trailer_ptr[0] | ((uint16_t)trailer_ptr[1] << 8);
            uint16_t crc_computed = crc16_ccitt_compute(parser->buffer, PROFILE_A_HEADER_SIZE + payload_bytes, 0xFFFFU);

            DecodedFrame *df = &out_frames[*frames_emitted];
            df->sequence_id = header.sequence;
            df->timestamp_us = (uint64_t)header.timestamp_us;
            df->sample_index_start = (uint64_t)header.sequence * (uint64_t)header.sample_count;
            df->sample_count = header.sample_count;
            df->sample_rate_hz = NOMINAL_SAMPLE_RATE_HZ;
            df->meaningful_bits = NOMINAL_MEANINGFUL_BITS;
            df->flags = (uint8_t)header.flags;
            df->encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED;
            df->mcu_buffer_drops = 0;
            df->is_profile_b = false;

            if (crc_received != crc_computed) {
                parser->crc_errors++;
                df->crc_ok = false;
                memmove(parser->buffer, parser->buffer + 2, parser->buffer_len - 2);
                parser->buffer_len -= 2;
                (*frames_emitted)++;
                continue;
            }

            df->crc_ok = true;
            const uint8_t *payload_ptr = parser->buffer + PROFILE_A_HEADER_SIZE;
            for (size_t i = 0; i < header.sample_count; ++i) {
                uint32_t b0 = (uint32_t)payload_ptr[i * 4 + 0];
                uint32_t b1 = (uint32_t)payload_ptr[i * 4 + 1];
                uint32_t b2 = (uint32_t)payload_ptr[i * 4 + 2];
                uint32_t b3 = (uint32_t)payload_ptr[i * 4 + 3];
                df->samples[i] = (int32_t)(b0 | (b1 << 8) | (b2 << 16) | (b3 << 24));
            }

            parser->valid_packets_parsed++;
            update_stream_quality_stats(&parser->quality_stats, df);
            (*frames_emitted)++;

            memmove(parser->buffer, parser->buffer + total_frame_len, parser->buffer_len - total_frame_len);
            parser->buffer_len -= total_frame_len;
        }
    }

    return PROTOCOL_OK;
}

void update_stream_quality_stats(StreamQualityStats *stats, const DecodedFrame *frame) {
    if (!stats || !frame) return;

    if (!frame->crc_ok) {
        stats->total_frames_corrupted++;
        return;
    }

    stats->total_frames_received++;
    stats->total_samples_received += frame->sample_count;

    if (!stats->initialized) {
        stats->last_sequence_id = frame->sequence_id;
        stats->last_timestamp_us = frame->timestamp_us;
        stats->last_sample_index = frame->sample_index_start;
        stats->initialized = true;
        return;
    }

    /* Sequence gap / duplicate check */
    if (frame->sequence_id == stats->last_sequence_id) {
        stats->total_duplicate_frames++;
    } else {
        uint32_t expected_seq = stats->last_sequence_id + 1;
        if (frame->sequence_id != expected_seq) {
            uint32_t gap = (frame->sequence_id > stats->last_sequence_id) ?
                           (frame->sequence_id - stats->last_sequence_id - 1) :
                           (UINT32_MAX - stats->last_sequence_id + frame->sequence_id);
            stats->total_sequence_gaps += gap;
        }
    }

    /* Timestamp regression check */
    if (frame->timestamp_us < stats->last_timestamp_us) {
        stats->total_timestamp_regressions++;
    }

    /* Update tracking registers */
    stats->last_sequence_id = frame->sequence_id;
    stats->last_timestamp_us = frame->timestamp_us;
    stats->last_sample_index = frame->sample_index_start;
}
