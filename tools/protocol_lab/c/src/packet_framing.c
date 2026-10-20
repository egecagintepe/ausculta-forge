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
/* 2. Explicit Field-by-Field Header Encoders & Decoders                     */
/* ========================================================================= */

ProtocolStatus packet_encode_header_profile_b(const ProfileBHeader *hdr, uint8_t *out_bytes) {
    if (!hdr || !out_bytes) return PROTOCOL_ERR_NULL_PTR;

    /* Offset 0..3: magic (0xAF534331 in little-endian: "1CSA") */
    out_bytes[0] = (uint8_t)(hdr->magic & 0xFFU);
    out_bytes[1] = (uint8_t)((hdr->magic >> 8) & 0xFFU);
    out_bytes[2] = (uint8_t)((hdr->magic >> 16) & 0xFFU);
    out_bytes[3] = (uint8_t)((hdr->magic >> 24) & 0xFFU);

    /* Offset 4: version */
    out_bytes[4] = hdr->version;

    /* Offset 5: msg_type */
    out_bytes[5] = hdr->msg_type;

    /* Offset 6..7: flags (uint16_t LE) */
    out_bytes[6] = (uint8_t)(hdr->flags & 0xFFU);
    out_bytes[7] = (uint8_t)((hdr->flags >> 8) & 0xFFU);

    /* Offset 8..11: sequence_id (uint32_t LE) */
    out_bytes[8]  = (uint8_t)(hdr->sequence_id & 0xFFU);
    out_bytes[9]  = (uint8_t)((hdr->sequence_id >> 8) & 0xFFU);
    out_bytes[10] = (uint8_t)((hdr->sequence_id >> 16) & 0xFFU);
    out_bytes[11] = (uint8_t)((hdr->sequence_id >> 24) & 0xFFU);

    /* Offset 12..15: sample_rate_hz (uint32_t LE) */
    out_bytes[12] = (uint8_t)(hdr->sample_rate_hz & 0xFFU);
    out_bytes[13] = (uint8_t)((hdr->sample_rate_hz >> 8) & 0xFFU);
    out_bytes[14] = (uint8_t)((hdr->sample_rate_hz >> 16) & 0xFFU);
    out_bytes[15] = (uint8_t)((hdr->sample_rate_hz >> 24) & 0xFFU);

    /* Offset 16..23: timestamp_us (uint64_t LE) */
    out_bytes[16] = (uint8_t)(hdr->timestamp_us & 0xFFU);
    out_bytes[17] = (uint8_t)((hdr->timestamp_us >> 8) & 0xFFU);
    out_bytes[18] = (uint8_t)((hdr->timestamp_us >> 16) & 0xFFU);
    out_bytes[19] = (uint8_t)((hdr->timestamp_us >> 24) & 0xFFU);
    out_bytes[20] = (uint8_t)((hdr->timestamp_us >> 32) & 0xFFU);
    out_bytes[21] = (uint8_t)((hdr->timestamp_us >> 40) & 0xFFU);
    out_bytes[22] = (uint8_t)((hdr->timestamp_us >> 48) & 0xFFU);
    out_bytes[23] = (uint8_t)((hdr->timestamp_us >> 56) & 0xFFU);

    /* Offset 24..31: sample_index_start (uint64_t LE) */
    out_bytes[24] = (uint8_t)(hdr->sample_index_start & 0xFFU);
    out_bytes[25] = (uint8_t)((hdr->sample_index_start >> 8) & 0xFFU);
    out_bytes[26] = (uint8_t)((hdr->sample_index_start >> 16) & 0xFFU);
    out_bytes[27] = (uint8_t)((hdr->sample_index_start >> 24) & 0xFFU);
    out_bytes[28] = (uint8_t)((hdr->sample_index_start >> 32) & 0xFFU);
    out_bytes[29] = (uint8_t)((hdr->sample_index_start >> 40) & 0xFFU);
    out_bytes[30] = (uint8_t)((hdr->sample_index_start >> 48) & 0xFFU);
    out_bytes[31] = (uint8_t)((hdr->sample_index_start >> 56) & 0xFFU);

    /* Offset 32..33: sample_count (uint16_t LE) */
    out_bytes[32] = (uint8_t)(hdr->sample_count & 0xFFU);
    out_bytes[33] = (uint8_t)((hdr->sample_count >> 8) & 0xFFU);

    /* Offset 34: meaningful_bits */
    out_bytes[34] = hdr->meaningful_bits;

    /* Offset 35: container_bits */
    out_bytes[35] = hdr->container_bits;

    /* Offset 36: channels */
    out_bytes[36] = hdr->channels;

    /* Offset 37: encoding */
    out_bytes[37] = hdr->encoding;

    /* Offset 38..39: mcu_buffer_drops (uint16_t LE) */
    out_bytes[38] = (uint8_t)(hdr->mcu_buffer_drops & 0xFFU);
    out_bytes[39] = (uint8_t)((hdr->mcu_buffer_drops >> 8) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_header_profile_b(const uint8_t *in_bytes, ProfileBHeader *hdr) {
    if (!in_bytes || !hdr) return PROTOCOL_ERR_NULL_PTR;

    hdr->magic = (uint32_t)in_bytes[0] |
                 ((uint32_t)in_bytes[1] << 8) |
                 ((uint32_t)in_bytes[2] << 16) |
                 ((uint32_t)in_bytes[3] << 24);

    hdr->version = in_bytes[4];
    hdr->msg_type = in_bytes[5];

    hdr->flags = (uint16_t)in_bytes[6] | ((uint16_t)in_bytes[7] << 8);

    hdr->sequence_id = (uint32_t)in_bytes[8] |
                       ((uint32_t)in_bytes[9] << 8) |
                       ((uint32_t)in_bytes[10] << 16) |
                       ((uint32_t)in_bytes[11] << 24);

    hdr->sample_rate_hz = (uint32_t)in_bytes[12] |
                          ((uint32_t)in_bytes[13] << 8) |
                          ((uint32_t)in_bytes[14] << 16) |
                          ((uint32_t)in_bytes[15] << 24);

    hdr->timestamp_us = (uint64_t)in_bytes[16] |
                        ((uint64_t)in_bytes[17] << 8) |
                        ((uint64_t)in_bytes[18] << 16) |
                        ((uint64_t)in_bytes[19] << 24) |
                        ((uint64_t)in_bytes[20] << 32) |
                        ((uint64_t)in_bytes[21] << 40) |
                        ((uint64_t)in_bytes[22] << 48) |
                        ((uint64_t)in_bytes[23] << 56);

    hdr->sample_index_start = (uint64_t)in_bytes[24] |
                              ((uint64_t)in_bytes[25] << 8) |
                              ((uint64_t)in_bytes[26] << 16) |
                              ((uint64_t)in_bytes[27] << 24) |
                              ((uint64_t)in_bytes[28] << 32) |
                              ((uint64_t)in_bytes[29] << 40) |
                              ((uint64_t)in_bytes[30] << 48) |
                              ((uint64_t)in_bytes[31] << 56);

    hdr->sample_count = (uint16_t)in_bytes[32] | ((uint16_t)in_bytes[33] << 8);
    hdr->meaningful_bits = in_bytes[34];
    hdr->container_bits = in_bytes[35];
    hdr->channels = in_bytes[36];
    hdr->encoding = in_bytes[37];
    hdr->mcu_buffer_drops = (uint16_t)in_bytes[38] | ((uint16_t)in_bytes[39] << 8);

    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_header_profile_a(const ProfileAHeader *hdr, uint8_t *out_bytes) {
    if (!hdr || !out_bytes) return PROTOCOL_ERR_NULL_PTR;

    out_bytes[0] = hdr->magic[0];
    out_bytes[1] = hdr->magic[1];
    out_bytes[2] = hdr->version;
    out_bytes[3] = hdr->msg_type;

    out_bytes[4] = (uint8_t)(hdr->sequence & 0xFFU);
    out_bytes[5] = (uint8_t)((hdr->sequence >> 8) & 0xFFU);
    out_bytes[6] = (uint8_t)((hdr->sequence >> 16) & 0xFFU);
    out_bytes[7] = (uint8_t)((hdr->sequence >> 24) & 0xFFU);

    out_bytes[8]  = (uint8_t)(hdr->timestamp_us & 0xFFU);
    out_bytes[9]  = (uint8_t)((hdr->timestamp_us >> 8) & 0xFFU);
    out_bytes[10] = (uint8_t)((hdr->timestamp_us >> 16) & 0xFFU);
    out_bytes[11] = (uint8_t)((hdr->timestamp_us >> 24) & 0xFFU);

    out_bytes[12] = (uint8_t)(hdr->sample_count & 0xFFU);
    out_bytes[13] = (uint8_t)((hdr->sample_count >> 8) & 0xFFU);

    out_bytes[14] = (uint8_t)(hdr->flags & 0xFFU);
    out_bytes[15] = (uint8_t)((hdr->flags >> 8) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_header_profile_a(const uint8_t *in_bytes, ProfileAHeader *hdr) {
    if (!in_bytes || !hdr) return PROTOCOL_ERR_NULL_PTR;

    hdr->magic[0] = in_bytes[0];
    hdr->magic[1] = in_bytes[1];
    hdr->version = in_bytes[2];
    hdr->msg_type = in_bytes[3];

    hdr->sequence = (uint32_t)in_bytes[4] |
                    ((uint32_t)in_bytes[5] << 8) |
                    ((uint32_t)in_bytes[6] << 16) |
                    ((uint32_t)in_bytes[7] << 24);

    hdr->timestamp_us = (uint32_t)in_bytes[8] |
                        ((uint32_t)in_bytes[9] << 8) |
                        ((uint32_t)in_bytes[10] << 16) |
                        ((uint32_t)in_bytes[11] << 24);

    hdr->sample_count = (uint16_t)in_bytes[12] | ((uint16_t)in_bytes[13] << 8);
    hdr->flags = (uint16_t)in_bytes[14] | ((uint16_t)in_bytes[15] << 8);

    return PROTOCOL_OK;
}

/* ========================================================================= */
/* 3. Packet Builders                                                        */
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

    packet_encode_header_profile_a(&header, out_buffer);

    /* Serialize samples little-endian without type punning */
    uint8_t *payload_ptr = out_buffer + PROFILE_A_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        int32_t s = samples[i];
        uint32_t u = (s < 0) ? (uint32_t)((int64_t)s + 0x100000000LL) : (uint32_t)s;
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

    packet_encode_header_profile_b(&header, out_buffer);

    /* Serialize samples little-endian without type punning */
    uint8_t *payload_ptr = out_buffer + PROFILE_B_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        int32_t s = samples[i];
        uint32_t u = (s < 0) ? (uint32_t)((int64_t)s + 0x100000000LL) : (uint32_t)s;
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
/* 4. Streaming Parser                                                       */
/* ========================================================================= */

ProtocolStatus parser_init(StreamPacketParser *parser) {
    if (!parser) return PROTOCOL_ERR_NULL_PTR;
    memset(parser, 0, sizeof(StreamPacketParser));
    return PROTOCOL_OK;
}

ProtocolStatus parser_reset(StreamPacketParser *parser) {
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
            /* No magic found in buffer: preserve trailing 3 bytes for boundary matches */
            if (parser->buffer_len > 3) {
                size_t discarded = parser->buffer_len - 3;
                parser->garbage_bytes_discarded += (uint32_t)discarded;
                memmove(parser->buffer, parser->buffer + discarded, 3);
                parser->buffer_len = 3;
            }
            break;
        }

        /* Discard any pre-sync garbage bytes */
        if (sync_idx > 0) {
            parser->garbage_bytes_discarded += (uint32_t)sync_idx;
            memmove(parser->buffer, parser->buffer + sync_idx, parser->buffer_len - sync_idx);
            parser->buffer_len -= sync_idx;
        }

        /* 2. Process discovered frame */
        if (found_profile_b) {
            if (parser->buffer_len < PROFILE_B_HEADER_SIZE) {
                /* Incomplete header: wait for subsequent bytes */
                break;
            }

            ProfileBHeader header;
            packet_decode_header_profile_b(parser->buffer, &header);

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
            df->flags = (uint8_t)header.flags;
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
                uint32_t u = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
                if (u & 0x80000000U) {
                    df->samples[i] = (int32_t)((int64_t)u - 0x100000000LL);
                } else {
                    df->samples[i] = (int32_t)u;
                }
            }

            parser->valid_packets_parsed++;
            update_stream_quality_stats(&parser->quality_stats, df);
            (*frames_emitted)++;

            /* Consume entire valid frame */
            memmove(parser->buffer, parser->buffer + total_frame_len, parser->buffer_len - total_frame_len);
            parser->buffer_len -= total_frame_len;

        } else if (found_profile_a) {
            if (parser->buffer_len < PROFILE_A_HEADER_SIZE) {
                break;
            }

            ProfileAHeader header;
            packet_decode_header_profile_a(parser->buffer, &header);

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
            df->sample_index_start = 0;
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
                uint32_t u = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
                if (u & 0x80000000U) {
                    df->samples[i] = (int32_t)((int64_t)u - 0x100000000LL);
                } else {
                    df->samples[i] = (int32_t)u;
                }
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

    stats->total_frames_received++;
    stats->total_samples_received += frame->sample_count;

    if (!stats->initialized) {
        stats->last_sequence_id = frame->sequence_id;
        stats->last_timestamp_us = frame->timestamp_us;
        stats->last_sample_index = frame->sample_index_start;
        stats->initialized = true;
        return;
    }

    /* Standard RFC 3550 signed sequence difference check */
    int32_t delta = (int32_t)(frame->sequence_id - stats->last_sequence_id);
    if (delta == 1) {
        /* Strictly sequential frame */
    } else if (delta > 1) {
        stats->total_sequence_gaps += (uint32_t)(delta - 1);
    } else if (delta == 0) {
        stats->total_duplicate_frames++;
    } else {
        /* delta < 0: out-of-order / reordered frame */
        stats->total_reordered_frames++;
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
