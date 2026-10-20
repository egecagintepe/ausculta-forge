/**
 * @file ring_buffer.h
 * @brief Bounded Circular Buffer with Sample-Accurate Accounting for Embedded Audio.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 *
 * CRITICAL EMBEDDED CONTEXT:
 * --------------------------
 * On the ESP32-S3, DMA buffers fill asynchronously from I2S RX interrupts.
 * A bounded ring buffer bridges the DMA callback to the TinyUSB task.
 * This implementation provides:
 * 1. Bounded static or preallocated storage (zero dynamic heap allocation during streaming).
 * 2. Unambiguous full vs. empty tracking without wasting a slot.
 * 3. Exact 64-bit cumulative accounting for all samples pushed, popped, and dropped.
 * 4. Explicit error codes rather than silent overwrite.
 */

#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include "protocol_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int32_t  *storage;                  /* Pointer to externally provided sample memory */
    size_t   capacity;                  /* Maximum sample count capacity */
    size_t   head;                      /* Write index (0 <= head < capacity) */
    size_t   tail;                      /* Read index (0 <= tail < capacity) */
    size_t   count;                     /* Current occupancy count */
    uint64_t total_samples_written;     /* Monotonic cumulative samples written */
    uint64_t total_samples_read;        /* Monotonic cumulative samples read */
    uint32_t overflow_events;           /* Occurrences of buffer overflow attempts */
    uint32_t overflow_samples_dropped;  /* Total sample count dropped due to overflow */
    uint32_t underflow_events;          /* Occurrences of read underflow attempts */
    uint32_t underflow_samples_starved; /* Total sample count starved due to empty read */
} PcmRingBuffer;

/**
 * @brief Initialize a ring buffer instance.
 *
 * @param rb Pointer to ring buffer structure.
 * @param storage Preallocated buffer of int32_t.
 * @param capacity Maximum number of samples the buffer can hold (must be > 0).
 * @return PROTOCOL_OK or error.
 */
ProtocolStatus ring_buffer_init(
    PcmRingBuffer *rb,
    int32_t *storage,
    size_t capacity
);

/**
 * @brief Reset ring buffer pointers and current count (retains accounting metrics).
 */
ProtocolStatus ring_buffer_reset(PcmRingBuffer *rb);

/**
 * @brief Push a block of samples into the ring buffer.
 *
 * If the buffer cannot accommodate all requested samples, it writes as many
 * as possible, updates overflow statistics, and returns PROTOCOL_ERR_BUFFER_FULL.
 *
 * @param rb Ring buffer pointer.
 * @param samples Array of samples to push.
 * @param count Number of samples in array.
 * @param samples_pushed Output pointer for number of samples successfully written.
 * @return PROTOCOL_OK if all samples pushed, PROTOCOL_ERR_BUFFER_FULL if truncated.
 */
ProtocolStatus ring_buffer_push(
    PcmRingBuffer *rb,
    const int32_t *samples,
    size_t count,
    size_t *samples_pushed
);

/**
 * @brief Pop a block of samples from the ring buffer.
 *
 * If fewer samples are available than requested, it reads all available,
 * updates underflow statistics, and returns PROTOCOL_ERR_BUFFER_EMPTY.
 *
 * @param rb Ring buffer pointer.
 * @param out_samples Destination array for popped samples.
 * @param count Requested number of samples to pop.
 * @param samples_popped Output pointer for number of samples actually read.
 * @return PROTOCOL_OK if all requested samples popped, PROTOCOL_ERR_BUFFER_EMPTY if short.
 */
ProtocolStatus ring_buffer_pop(
    PcmRingBuffer *rb,
    int32_t *out_samples,
    size_t count,
    size_t *samples_popped
);

/**
 * @brief Peek at samples in the ring buffer without consuming them.
 */
ProtocolStatus ring_buffer_peek(
    const PcmRingBuffer *rb,
    int32_t *out_samples,
    size_t count,
    size_t *samples_peeked
);

/**
 * @brief Get currently available sample count for reading.
 */
static inline size_t ring_buffer_available_read(const PcmRingBuffer *rb) {
    return rb ? rb->count : 0;
}

/**
 * @brief Get currently available free slot count for writing.
 */
static inline size_t ring_buffer_available_write(const PcmRingBuffer *rb) {
    return rb ? (rb->capacity - rb->count) : 0;
}

/**
 * @brief Check if ring buffer is completely full.
 */
static inline bool ring_buffer_is_full(const PcmRingBuffer *rb) {
    return rb ? (rb->count >= rb->capacity) : false;
}

/**
 * @brief Check if ring buffer is completely empty.
 */
static inline bool ring_buffer_is_empty(const PcmRingBuffer *rb) {
    return rb ? (rb->count == 0) : true;
}

#ifdef __cplusplus
}
#endif

#endif /* RING_BUFFER_H */
