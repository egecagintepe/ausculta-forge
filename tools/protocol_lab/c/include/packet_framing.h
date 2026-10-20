/**
 * @file packet_framing.h
 * @brief Packet Serialization, Deserialization & CRC Integrity Utilities.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * PORTABLE WIRE ENCODING SPECIFICATION:
 * -------------------------------------
 * All header and trailer fields are explicitly encoded and decoded
 * field-by-field in little-endian order. Zero reliance on compiler struct
 * packing (#pragma pack) or host architecture endianness.
 */

#ifndef PACKET_FRAMING_H
#define PACKET_FRAMING_H

#include "protocol_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Checksum & CRC Algorithms                                              */
/* ========================================================================= */

/**
 * @brief Compute CRC-16-CCITT (polynomial 0x1021, default init 0xFFFF).
 */
uint16_t crc16_ccitt_compute(const uint8_t *data, size_t length, uint16_t init_val);

/**
 * @brief Compute standard CRC-32 (IEEE 802.3, polynomial 0xEDB88320, init 0xFFFFFFFF).
 */
uint32_t crc32_compute(const uint8_t *data, size_t length);

/**
 * @brief Compute Adler-32 checksum (fast alternative integrity check).
 */
uint32_t adler32_compute(const uint8_t *data, size_t length);

/* ========================================================================= */
/* 2. Explicit Field-by-Field Header Encoders & Decoders                     */
/* ========================================================================= */

/**
 * @brief Explicitly encode a Profile B header to little-endian bytes (40 bytes).
 */
ProtocolStatus packet_encode_header_profile_b(const ProfileBHeader *hdr, uint8_t *out_bytes);

/**
 * @brief Explicitly decode little-endian bytes to a Profile B header (40 bytes).
 */
ProtocolStatus packet_decode_header_profile_b(const uint8_t *in_bytes, ProfileBHeader *hdr);

/**
 * @brief Explicitly encode a Profile A header to little-endian bytes (16 bytes).
 */
ProtocolStatus packet_encode_header_profile_a(const ProfileAHeader *hdr, uint8_t *out_bytes);

/**
 * @brief Explicitly decode little-endian bytes to a Profile A header (16 bytes).
 */
ProtocolStatus packet_decode_header_profile_a(const uint8_t *in_bytes, ProfileAHeader *hdr);

/* ========================================================================= */
/* 3. Packet Building (Serialization)                                        */
/* ========================================================================= */

/**
 * @brief Build a Profile A packet (16-byte header + N*4B payload + 2B CRC-16).
 */
ProtocolStatus packet_build_profile_a(
    uint32_t sequence,
    uint32_t timestamp_us,
    const int32_t *samples,
    uint16_t count,
    uint16_t flags,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a Profile B packet (40-byte header + N*4B payload + 4B CRC-32).
 */
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
);

/* ========================================================================= */
/* 4. Packet Parsing (Deserialization & Stream Reassembly)                   */
/* ========================================================================= */

/**
 * @brief Decoded semantic packet structure used by host receivers.
 */
typedef struct {
    uint32_t sequence_id;
    uint64_t timestamp_us;
    uint64_t sample_index_start;
    uint16_t sample_count;
    uint32_t sample_rate_hz;
    uint8_t  meaningful_bits;
    uint8_t  flags;
    uint8_t  encoding;
    uint16_t mcu_buffer_drops;
    bool     crc_ok;
    bool     is_profile_b;
    int32_t  samples[1024]; /* Fixed scratch space for payload */
} DecodedFrame;

/**
 * @brief Streaming packet receiver buffer state.
 */
typedef struct {
    uint8_t  buffer[8192];              /* Accumulator for fragmented byte reads */
    size_t   buffer_len;                /* Current number of unparsed bytes */
    uint32_t garbage_bytes_discarded;   /* Bytes dropped seeking sync magic */
    uint32_t crc_errors;                /* Packets failing CRC check */
    uint32_t malformed_headers;         /* Headers with illegal counts/versions */
    uint32_t valid_packets_parsed;      /* Total valid packets emitted */
    StreamQualityStats quality_stats;   /* Sequence and sample continuity stats */
} StreamPacketParser;

/**
 * @brief Initialize a streaming packet parser.
 */
ProtocolStatus parser_init(StreamPacketParser *parser);

/**
 * @brief Reset parser internal state and statistics.
 */
ProtocolStatus parser_reset(StreamPacketParser *parser);

/**
 * @brief Feed raw wire bytes into the parser and retrieve any completed frames.
 */
ProtocolStatus parser_feed_bytes(
    StreamPacketParser *parser,
    const uint8_t *in_bytes,
    size_t in_len,
    DecodedFrame *out_frames,
    size_t max_frames,
    size_t *frames_emitted
);

/**
 * @brief Update stream quality statistics for a newly parsed frame (RFC 3550 sequence logic).
 */
void update_stream_quality_stats(StreamQualityStats *stats, const DecodedFrame *frame);

#ifdef __cplusplus
}
#endif

#endif /* PACKET_FRAMING_H */
