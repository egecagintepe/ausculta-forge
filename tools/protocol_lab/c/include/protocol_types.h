/**
 * @file protocol_types.h
 * @brief AuscultaForge Embedded-to-Host Protocol Laboratory Type Definitions.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Interface Reviewer: Ozan (Module B)
 *
 * CRITICAL ARCHITECTURAL CONTEXT:
 * -------------------------------
 * This header defines data structures, binary wire representations, and
 * error accounting primitives for both:
 * 1. Profile A: Existing 16-byte reference frame (Rev-A illustrative baseline)
 * 2. Profile B: Proposed 40-byte header frame (Expanded B->C protocol proposal)
 *
 * STATUS: PROPOSED / EXPERIMENTAL LABORATORY.
 * Neither profile is frozen or finalized without mutual agreement from Module B (Ozan)
 * under decisions DW03-09 (CRC), DW03-10 (Sample representation), and DW03-12 (USB Class).
 */

#ifndef PROTOCOL_TYPES_H
#define PROTOCOL_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Protocol Versions & Identifiers                                        */
/* ========================================================================= */

#define PROTOCOL_VERSION_MAJOR      1U
#define PROTOCOL_VERSION_MINOR      0U
#define PROTOCOL_VERSION_PATCH      0U

/* Profile A Sync Magic: 0xAA55 (2 bytes) */
#define PROFILE_A_MAGIC_BYTE0       0x55U
#define PROFILE_A_MAGIC_BYTE1       0xAAU
#define PROFILE_A_MAGIC_U16         0xAA55U
#define PROFILE_A_HEADER_SIZE       16U
#define PROFILE_A_TRAILER_SIZE      2U  /* CRC-16-CCITT */

/* Profile B Sync Magic: 0xAF534331 ("1CSA", AuscultaForge Channel 1) (4 bytes) */
#define PROFILE_B_MAGIC_BYTE0       0x31U /* '1' */
#define PROFILE_B_MAGIC_BYTE1       0x43U /* 'C' */
#define PROFILE_B_MAGIC_BYTE2       0x53U /* 'S' */
#define PROFILE_B_MAGIC_BYTE3       0xAFU /* AuscultaForge Magic Prefix */
#define PROFILE_B_MAGIC_U32         0xAF534331U
#define PROFILE_B_HEADER_SIZE       40U
#define PROFILE_B_TRAILER_SIZE      4U  /* CRC-32 (IEEE 802.3) */

/* Standard Baseline Parameters */
#define NOMINAL_SAMPLE_RATE_HZ      48000U
#define NOMINAL_CHANNELS            1U
#define NOMINAL_MEANINGFUL_BITS     24U
#define NOMINAL_CONTAINER_BITS      32U

/* Profile B Default Frame Size: 256 samples @ 48 kHz = 187.5 frames/sec */
#define PROFILE_B_SAMPLES_PER_FRAME 256U
#define PROFILE_B_PAYLOAD_BYTES     (PROFILE_B_SAMPLES_PER_FRAME * sizeof(int32_t)) /* 1024 bytes */
#define PROFILE_B_FRAME_TOTAL_BYTES (PROFILE_B_HEADER_SIZE + PROFILE_B_PAYLOAD_BYTES + PROFILE_B_TRAILER_SIZE) /* 1068 bytes */

/* 24-bit PCM Integer Boundaries */
#define INT24_MAX                   8388607LL       /* +2^23 - 1 */
#define INT24_MIN                   (-8388608LL)    /* -2^23 */
#define INT24_SCALE                 8388608.0       /* 2^23 */

/* 32-bit Integer Boundaries */
#define INT32_MAX_VAL               2147483647LL    /* +2^31 - 1 */
#define INT32_MIN_VAL               (-2147483648LL) /* -2^31 */

/* ========================================================================= */
/* 2. Message Types & Status Flags                                           */
/* ========================================================================= */

typedef enum {
    MSG_TYPE_AUDIO_DATA         = 0x01,
    MSG_TYPE_HEARTBEAT_STATUS   = 0x02,
    MSG_TYPE_STREAM_START_REQ   = 0x03,
    MSG_TYPE_STREAM_START_ACK   = 0x04,
    MSG_TYPE_STREAM_STOP_REQ    = 0x05,
    MSG_TYPE_STREAM_STOP_ACK    = 0x06,
    MSG_TYPE_CALIBRATION_TONE   = 0x07,
    MSG_TYPE_ERROR_NOTIFICATION = 0x0F
} ProtocolMessageType;

/* Frame Flag Bitmasks (Profile B) */
#define FRAME_FLAG_TIMESTAMP_VALID      (1U << 0)
#define FRAME_FLAG_SAMPLE_DISCONTINUITY (1U << 1)
#define FRAME_FLAG_DMA_BUFFER_OVERFLOW  (1U << 2)
#define FRAME_FLAG_USB_QUEUE_OVERFLOW   (1U << 3)
#define FRAME_FLAG_CLIPPING_DETECTED    (1U << 4)
#define FRAME_FLAG_SIMULATED_SOURCE     (1U << 5)
#define FRAME_FLAG_DIAGNOSTIC_TONE      (1U << 6)

/* Sample Encoding Enum */
typedef enum {
    ENCODING_SIGNED_PCM_LSB_ALIGNED = 0x01, /* Lower 24 bits carry data, upper 8 bits sign-extended */
    ENCODING_SIGNED_PCM_MSB_ALIGNED = 0x02, /* Upper 24 bits carry data (I2S left-justified), lower 8 bits zero */
    ENCODING_FLOAT32_NORMALIZED     = 0x03  /* IEEE 754 [-1.0, +1.0] */
} ProtocolSampleEncoding;

/* Status / Return Codes */
typedef enum {
    PROTOCOL_OK                 = 0,
    PROTOCOL_ERR_NULL_PTR       = -1,
    PROTOCOL_ERR_INVALID_PARAM  = -2,
    PROTOCOL_ERR_BUFFER_FULL    = -3,
    PROTOCOL_ERR_BUFFER_EMPTY   = -4,
    PROTOCOL_ERR_MAGIC_MISMATCH = -5,
    PROTOCOL_ERR_CRC_MISMATCH   = -6,
    PROTOCOL_ERR_INCOMPLETE     = -7,
    PROTOCOL_ERR_OVERFLOW       = -8,
    PROTOCOL_ERR_VERSION        = -9
} ProtocolStatus;

/* ========================================================================= */
/* 3. Wire Framing Structs                                                   */
/* ========================================================================= */

/**
 * @brief Profile A: 16-Byte Reference Header.
 *
 * Wire encoding is performed field-by-field in little-endian byte order.
 */
typedef struct {
    uint8_t  magic[2];          /* 0x55, 0xAA (0xAA55) */
    uint8_t  version;           /* 0x01 */
    uint8_t  msg_type;          /* 0x01 (Audio Samples) */
    uint32_t sequence;          /* Monotonic frame sequence */
    uint32_t timestamp_us;      /* Microsecond tick timestamp (32-bit) */
    uint16_t sample_count;      /* Number of 32-bit sample words */
    uint16_t flags;             /* Status flags */
} ProfileAHeader;

/**
 * @brief Profile B: Proposed 40-Byte Expanded Header.
 *
 * Wire encoding is performed field-by-field in little-endian byte order.
 * All members are defined on natural alignment boundaries.
 */
typedef struct {
    uint32_t magic;             /* 4B: 0xAF534331 ("1CSA" in LE) */
    uint8_t  version;           /* 1B: PROTOCOL_VERSION_MAJOR (0x01) */
    uint8_t  msg_type;          /* 1B: ProtocolMessageType (0x01 = Audio) */
    uint16_t flags;             /* 2B: Frame flags bitmask */
    uint32_t sequence_id;       /* 4B: Monotonic frame sequence */
    uint32_t sample_rate_hz;    /* 4B: Sampling rate in Hz (e.g. 48000) */
    uint64_t timestamp_us;      /* 8B: Monotonic microsecond timestamp */
    uint64_t sample_index_start;/* 8B: Cumulative absolute sample index */
    uint16_t sample_count;      /* 2B: Samples in frame (e.g. 256) */
    uint8_t  meaningful_bits;   /* 1B: Transducer data bits (24) */
    uint8_t  container_bits;    /* 1B: Container slot bits (32) */
    uint8_t  channels;          /* 1B: Channels (1) */
    uint8_t  encoding;          /* 1B: ProtocolSampleEncoding */
    uint16_t mcu_buffer_drops;  /* 2B: Dropped sample counter */
} ProfileBHeader;

/* ========================================================================= */
/* 4. Stream Quality Accounting Record                                       */
/* ========================================================================= */

typedef struct {
    uint64_t total_samples_generated;
    uint64_t total_samples_received;
    uint32_t total_frames_received;
    uint32_t total_frames_corrupted;
    uint32_t total_sequence_gaps;
    uint32_t total_duplicate_frames;
    uint32_t total_reordered_frames;
    uint32_t total_buffer_overflows;
    uint32_t total_timestamp_regressions;
    uint32_t last_sequence_id;
    uint64_t last_timestamp_us;
    uint64_t last_sample_index;
    bool     initialized;
} StreamQualityStats;

#ifdef __cplusplus
}
#endif

#endif /* PROTOCOL_TYPES_H */
