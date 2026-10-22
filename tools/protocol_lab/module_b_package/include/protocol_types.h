/**
 * @file protocol_types.h
 * @brief AuscultaForge Embedded-to-Host Protocol Laboratory Type Definitions.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Joint Reviewer: Ozan (Module B)
 *
 * CANONICAL WIRE CONTRACT (v0.1):
 * --------------------------------
 * This header defines data structures, binary wire representations, control
 * payloads, and error accounting primitives for:
 * 1. Profile B: Canonical 40-byte header framing and bidirectional control contract.
 * 2. Profile A: Historical 16-byte reference frame (deprecated legacy baseline).
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

/* Profile A Sync Magic: 0xAA55 (2 bytes) - Historical Legacy */
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

/* Profile B Standard Audio Frame: 256 samples @ 48 kHz = 187.5 frames/sec */
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
    MSG_TYPE_AUDIO_DATA         = 0x01, /* Audio PCM samples */
    MSG_TYPE_HEARTBEAT_STATUS   = 0x02, /* 72B Telemetry snapshot */
    MSG_TYPE_STREAM_START_REQ   = 0x03, /* 16B Start streaming request */
    MSG_TYPE_STREAM_START_ACK   = 0x04, /* 32B Start streaming acknowledgement */
    MSG_TYPE_STREAM_STOP_REQ    = 0x05, /* 8B Stop streaming request */
    MSG_TYPE_STREAM_STOP_ACK    = 0x06, /* 72B Stop streaming acknowledgement */
    MSG_TYPE_CALIBRATION_TONE   = 0x07, /* Diagnostic calibration tone */
    MSG_TYPE_ERROR_NOTIFICATION = 0x0F, /* 8B Asynchronous error notification */
    MSG_TYPE_HELLO_REQ          = 0x10, /* 4B Hello handshake probe */
    MSG_TYPE_HELLO_ACK          = 0x11  /* 24B Hello handshake response */
} ProtocolMessageType;

/* Exact Payload Sizes for Control Messages */
#define STATUS_TELEMETRY_PAYLOAD_SIZE 72U
#define START_REQ_PAYLOAD_SIZE        16U
#define START_ACK_PAYLOAD_SIZE        32U
#define STOP_REQ_PAYLOAD_SIZE         8U
#define STOP_ACK_PAYLOAD_SIZE         72U
#define ERROR_PAYLOAD_SIZE            8U
#define HELLO_REQ_PAYLOAD_SIZE        4U
#define HELLO_ACK_PAYLOAD_SIZE        24U

/* Frame Flag Bitmasks (16-bit) */
#define FRAME_FLAG_TIMESTAMP_VALID      (1U << 0)
#define FRAME_FLAG_SAMPLE_DISCONTINUITY (1U << 1)
#define FRAME_FLAG_DMA_BUFFER_OVERFLOW  (1U << 2)
#define FRAME_FLAG_USB_QUEUE_OVERFLOW   (1U << 3)
#define FRAME_FLAG_CLIPPING_DETECTED    (1U << 4)
#define FRAME_FLAG_SIMULATED_SOURCE     (1U << 5)
#define FRAME_FLAG_DIAGNOSTIC_TONE      (1U << 6)
#define FRAME_FLAG_SESSION_ACTIVE       (1U << 7)

/* Sample Encoding Enum */
typedef enum {
    ENCODING_SIGNED_PCM_LSB_ALIGNED = 0x01, /* Lower 24 bits carry data, upper 8 bits sign-extended */
    ENCODING_SIGNED_PCM_MSB_ALIGNED = 0x02, /* Upper 24 bits carry data (I2S left-justified), lower 8 bits zero */
    ENCODING_FLOAT32_NORMALIZED     = 0x03  /* IEEE 754 [-1.0, +1.0] */
} ProtocolSampleEncoding;

/* Source Mode Enum */
typedef enum {
    SOURCE_MODE_LIVE_I2S            = 0x00, /* Live physical I2S MEMS microphone */
    SOURCE_MODE_SYNTH_RAMP          = 0x01, /* Deterministic integer ramp */
    SOURCE_MODE_SYNTH_SINE_100HZ    = 0x02  /* 100 Hz synthetic sine */
} ProtocolSourceMode;

/* Stop Reason Enum */
typedef enum {
    STOP_REASON_NORMAL_TARGET_REACHED = 0,
    STOP_REASON_HOST_REQUEST          = 1,
    STOP_REASON_DMA_OVERFLOW          = 2,
    STOP_REASON_USB_ERROR             = 3,
    STOP_REASON_USER_ABORT            = 4,
    STOP_REASON_TIMEOUT               = 5
} ProtocolStopReason;

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
    PROTOCOL_ERR_VERSION        = -9,
    PROTOCOL_ERR_MSG_TYPE       = -10,
    PROTOCOL_ERR_SESSION        = -11
} ProtocolStatus;

/* ========================================================================= */
/* 3. Wire Framing Structs                                                   */
/* ========================================================================= */

/**
 * @brief Profile A: 16-Byte Reference Header (Historical Legacy).
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
 * @brief Profile B: Canonical 40-Byte Expanded Header.
 *
 * Wire encoding is performed field-by-field in little-endian byte order.
 * All members are defined on natural alignment boundaries.
 */
typedef struct {
    uint32_t magic;             /* 4B: 0xAF534331 ("1CSA" in LE) */
    uint8_t  version;           /* 1B: PROTOCOL_VERSION_MAJOR (0x01) */
    uint8_t  msg_type;          /* 1B: ProtocolMessageType */
    uint16_t flags;             /* 2B: 16-bit frame flags bitmask */
    uint32_t sequence_id;       /* 4B: Monotonic frame sequence */
    uint32_t sample_rate_hz;    /* 4B: Sampling rate in Hz (e.g. 48000) */
    uint64_t timestamp_us;      /* 8B: Monotonic microsecond timestamp */
    uint64_t sample_index_start;/* 8B: Cumulative absolute sample index */
    uint16_t sample_count;      /* 2B: Samples in frame (0 for control frames) */
    uint8_t  meaningful_bits;   /* 1B: Transducer data bits (24) */
    uint8_t  container_bits;    /* 1B: Container slot bits (32) */
    uint8_t  channels;          /* 1B: Channels (1) */
    uint8_t  encoding;          /* 1B: ProtocolSampleEncoding */
    uint16_t mcu_buffer_drops;  /* 2B: Saturating dropped sample counter = min(drops, 65535) */
} ProfileBHeader;

/* ========================================================================= */
/* 4. Control Message Payloads                                               */
/* ========================================================================= */

/**
 * @brief 72-Byte Exact Hardware Telemetry Payload (STATUS and STOP_ACK).
 */
typedef struct {
    uint64_t session_id;               /* Offset 0: Active or completed session identifier */
    uint64_t generated_samples;        /* Offset 8: Total samples generated by sensor/DMA */
    uint64_t fully_queued_samples;     /* Offset 16: Total samples placed into outgoing queue */
    uint64_t dropped_samples;          /* Offset 24: Total samples dropped due to overflows */
    uint32_t audio_frames_queued;      /* Offset 32: Total audio frames queued for USB */
    uint32_t dma_overflow_events;      /* Offset 36: I2S DMA FIFO overflow events */
    uint32_t ring_overflow_events;     /* Offset 40: MCU intermediate ring buffer overflows */
    uint32_t usb_partial_write_events; /* Offset 44: USB non-blocking partial write returns */
    uint32_t usb_timeout_events;       /* Offset 48: USB write timeout events */
    uint32_t usb_disconnect_events;    /* Offset 52: USB bus suspend/disconnect events */
    uint64_t audio_bytes_queued;       /* Offset 56: Total audio bytes queued */
    uint32_t stop_reason;              /* Offset 64: Stop reason code */
    uint32_t error_code;               /* Offset 68: Hardware error code */
} StatusTelemetryPayload;

/**
 * @brief 16-Byte Stream Start Request Payload (START_REQ).
 */
typedef struct {
    uint32_t sample_rate_hz;    /* Offset 0: Requested rate in Hz (48000) */
    uint64_t target_samples;    /* Offset 4: Target sample count (0 = continuous) */
    uint8_t  source_mode;       /* Offset 12: ProtocolSourceMode */
    uint8_t  encoding;          /* Offset 13: ProtocolSampleEncoding */
    uint8_t  channels;          /* Offset 14: Channel count (1) */
    uint8_t  profile_id;        /* Offset 15: Framing profile (2 = Profile B) */
} StartReqPayload;

/**
 * @brief 32-Byte Stream Start Acknowledge Payload (START_ACK).
 */
typedef struct {
    uint64_t session_id;                /* Offset 0: Unique 64-bit session ID */
    uint64_t session_reference_time_us; /* Offset 8: Base reference microsecond timestamp */
    uint32_t accepted_sample_rate_hz;   /* Offset 16: Confirmed rate in Hz */
    uint64_t accepted_target_samples;   /* Offset 20: Confirmed target sample count */
    uint8_t  accepted_source_mode;      /* Offset 28: Confirmed source mode */
    uint8_t  encoding;                  /* Offset 29: Confirmed encoding */
    uint8_t  channels;                  /* Offset 30: Confirmed channels */
    uint8_t  profile_id;                /* Offset 31: Confirmed profile */
} StartAckPayload;

/**
 * @brief 8-Byte Stream Stop Request Payload (STOP_REQ).
 */
typedef struct {
    uint64_t session_id;                /* Offset 0: Session ID to stop */
} StopReqPayload;

/**
 * @brief 4-Byte Hello Request Payload (HELLO_REQ).
 */
typedef struct {
    uint32_t host_nonce;                /* Offset 0: Host-generated nonce */
} HelloReqPayload;

/**
 * @brief 24-Byte Proposed Hello Acknowledge Payload (HELLO_ACK).
 */
typedef struct {
    uint32_t nonce_echo;                /* Offset 0: Echo of host_nonce */
    uint8_t  protocol_version_major;    /* Offset 4: Protocol version major (1) */
    uint8_t  protocol_version_minor;    /* Offset 5: Protocol version minor (0) */
    uint8_t  supported_profiles_mask;   /* Offset 6: Bit 1 = Profile B, Bit 0 = Profile A */
    uint8_t  supported_encodings_mask;  /* Offset 7: Bit 0 = LSB, Bit 1 = MSB */
    uint32_t hardware_sample_rate_hz;   /* Offset 8: Hardware rate (48000) */
    uint8_t  firmware_version_major;    /* Offset 12: Firmware major */
    uint8_t  firmware_version_minor;    /* Offset 13: Firmware minor */
    uint8_t  firmware_version_patch;    /* Offset 14: Firmware patch */
    uint8_t  reserved;                  /* Offset 15: Reserved (0) */
    uint16_t max_frame_samples;         /* Offset 16: Max frame samples (256) */
    uint16_t capability_flags;          /* Offset 18: Capability bitmask */
    uint32_t device_uid_low;            /* Offset 20: Unique device ID low 32 bits */
} HelloAckPayload;

/**
 * @brief 8-Byte Proposed Error Notification Payload (ERROR).
 */
typedef struct {
    uint32_t error_code;                /* Offset 0: Error code */
    uint32_t error_context;             /* Offset 4: Diagnostic context */
} ErrorPayload;

/* ========================================================================= */
/* 5. Stream Quality Accounting Record                                       */
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
