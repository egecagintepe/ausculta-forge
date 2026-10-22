/**
 * @file packet_framing.h
 * @brief Packet Serialization, Deserialization & CRC Integrity Utilities.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Joint Reviewer: Ozan (Module B)
 *
 * PORTABLE WIRE ENCODING SPECIFICATION:
 * -------------------------------------
 * All header, control payload, and trailer fields are explicitly encoded and
 * decoded field-by-field in little-endian order. Zero reliance on compiler struct
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
 * @brief Explicitly initialize or verify the CRC-32 table (thread-safe, safe for concurrent callers).
 */
void crc32_init(void);

/**
 * @brief Compute CRC-16-CCITT (polynomial 0x1021, default init 0xFFFF).
 */
uint16_t crc16_ccitt_compute(const uint8_t *data, size_t length, uint16_t init_val);

/**
 * @brief Compute standard CRC-32 (IEEE 802.3, polynomial 0xEDB88320, init 0xFFFFFFFF, final XOR 0xFFFFFFFF).
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
/* 3. Control Payload Encoders & Decoders                                    */
/* ========================================================================= */

ProtocolStatus packet_encode_status_telemetry(const StatusTelemetryPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_status_telemetry(const uint8_t *in_bytes, StatusTelemetryPayload *payload);

ProtocolStatus packet_encode_start_req(const StartReqPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_start_req(const uint8_t *in_bytes, StartReqPayload *payload);

ProtocolStatus packet_encode_start_ack(const StartAckPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_start_ack(const uint8_t *in_bytes, StartAckPayload *payload);

ProtocolStatus packet_encode_stop_req(const StopReqPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_stop_req(const uint8_t *in_bytes, StopReqPayload *payload);

ProtocolStatus packet_encode_error(const ErrorPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_error(const uint8_t *in_bytes, ErrorPayload *payload);

ProtocolStatus packet_encode_hello_req(const HelloReqPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_hello_req(const uint8_t *in_bytes, HelloReqPayload *payload);

ProtocolStatus packet_encode_hello_ack(const HelloAckPayload *payload, uint8_t *out_bytes);
ProtocolStatus packet_decode_hello_ack(const uint8_t *in_bytes, HelloAckPayload *payload);

/* ========================================================================= */
/* 4. Packet Builders (Serialization)                                        */
/* ========================================================================= */

/**
 * @brief Build a Profile A audio packet (16-byte header + N*4B payload + 2B CRC-16).
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
 * @brief Build a Profile B standard audio packet (40-byte header + N*4B payload + 4B CRC-32).
 *
 * NOTE: flags parameter is strictly uint16_t matching the 16-bit header field.
 */
ProtocolStatus packet_build_profile_b(
    uint32_t sequence_id,
    uint64_t timestamp_us,
    uint64_t sample_index_start,
    const int32_t *samples,
    uint16_t count,
    uint32_t sample_rate_hz,
    uint8_t meaningful_bits,
    uint16_t flags,
    uint8_t encoding,
    uint16_t mcu_drops,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a HELLO_REQ packet (40B header + 4B payload + 4B CRC-32 = 48B).
 */
ProtocolStatus packet_build_hello_req(
    uint32_t host_nonce,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a HELLO_ACK packet (40B header + 24B payload + 4B CRC-32 = 68B).
 */
ProtocolStatus packet_build_hello_ack(
    const HelloAckPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a START_REQ packet (40B header + 16B payload + 4B CRC-32 = 60B).
 */
ProtocolStatus packet_build_start_req(
    const StartReqPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a START_ACK packet (40B header + 32B payload + 4B CRC-32 = 76B).
 */
ProtocolStatus packet_build_start_ack(
    const StartAckPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a STOP_REQ packet (40B header + 8B payload + 4B CRC-32 = 52B).
 */
ProtocolStatus packet_build_stop_req(
    uint64_t session_id,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a STOP_ACK packet (40B header + 72B payload + 4B CRC-32 = 116B).
 */
ProtocolStatus packet_build_stop_ack(
    const StatusTelemetryPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build a STATUS telemetry packet (40B header + 72B payload + 4B CRC-32 = 116B).
 */
ProtocolStatus packet_build_status(
    const StatusTelemetryPayload *payload,
    uint32_t sequence_id,
    uint64_t timestamp_us,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/**
 * @brief Build an ERROR packet (40B header + 8B payload + 4B CRC-32 = 52B).
 */
ProtocolStatus packet_build_error(
    uint32_t error_code,
    uint32_t error_context,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
);

/* ========================================================================= */
/* 5. Packet Parsing (Deserialization & Stream Reassembly)                   */
/* ========================================================================= */

/**
 * @brief Decoded semantic packet structure used by host receivers.
 */
typedef struct {
    uint8_t  msg_type;                  /* ProtocolMessageType (0x01=Audio, 0x02=Status, etc.) */
    uint16_t flags;                     /* 16-bit status flags */
    uint32_t sequence_id;               /* Monotonic frame sequence */
    uint64_t timestamp_us;              /* Microsecond timestamp */
    uint64_t sample_index_start;        /* First sample index */
    uint16_t sample_count;              /* Number of audio samples (0 for control frames) */
    uint32_t sample_rate_hz;            /* Sample rate in Hz */
    uint8_t  meaningful_bits;           /* Transducer data bits (24) */
    uint8_t  encoding;                  /* Sample encoding */
    uint16_t mcu_buffer_drops;          /* Saturating dropped sample counter */
    bool     crc_ok;                    /* CRC-32 validity */
    bool     is_profile_b;              /* Profile B indicator */
    int32_t  samples[1024];             /* Audio sample scratch space */
    uint8_t  control_payload[72];       /* Control payload scratch space */
    size_t   control_payload_len;       /* Length of control payload */
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
 * @brief Update stream quality statistics for a newly parsed audio frame (RFC 3550 sequence logic).
 */
void update_stream_quality_stats(StreamQualityStats *stats, const DecodedFrame *frame);

#ifdef __cplusplus
}
#endif

#endif /* PACKET_FRAMING_H */
