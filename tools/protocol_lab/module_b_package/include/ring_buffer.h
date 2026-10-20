/**
 * @file ring_buffer.h
 * @brief Lock-Free Single-Producer Single-Consumer (SPSC) Circular Buffer for Embedded Audio.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Proposed Interface for: Ozan (Module B)
 *
 * RIGOROUS CONCURRENCY & MEMORY ORDERING MODEL:
 * ---------------------------------------------
 * 1. Topology: Strictly Single-Producer Single-Consumer (SPSC).
 *    - Exactly ONE producer context (e.g. high-priority I2S DMA ISR or dedicated audio task).
 *    - Exactly ONE consumer context (e.g. low-priority USB CDC packetizer task).
 *    - Multi-producer (MPSC) or multi-consumer (SPMC/MPMC) usage is STRICTLY PROHIBITED
 *      without external mutual exclusion.
 *
 * 2. Memory Ordering & Synchronization:
 *    - `head` is modified ONLY by the Producer.
 *      Producer writes data to storage, then publishes `head` using `memory_order_release`.
 *      Consumer reads `head` using `memory_order_acquire`.
 *    - `tail` is modified ONLY by the Consumer.
 *      Consumer reads data from storage, then publishes `tail` using `memory_order_release`.
 *      Producer reads `tail` using `memory_order_acquire`.
 *    - No shared mutable `count` variable exists, eliminating read-modify-write races.
 *
 * 3. Power-of-Two Capacity Requirement:
 *    - `capacity` MUST be a power of two (e.g. 512, 1024, 2048, 4096).
 *    - Unsigned integer wrapping of monotonic indices (`head - tail`) modulo 2^32 is
 *      guaranteed well-defined by ISO C11 §6.2.5p9 without slot waste.
 *
 * 4. ISR Safety Specification:
 *    - `ring_buffer_push()`: NON-BLOCKING, LOCK-FREE, WAIT-FREE (O(N) copy, bounded by N).
 *      Demonstrably SAFE to execute inside an ISR context (e.g. I2S DMA callback).
 *    - `ring_buffer_pop()`, `ring_buffer_peek()`: NON-BLOCKING, LOCK-FREE.
 *      Intended for thread/task context (e.g. TinyUSB worker task).
 *    - `ring_buffer_init()`, `ring_buffer_reset()`: NOT CONCURRENT.
 *      Require quiescence (both producer and consumer stopped).
 */

#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include "protocol_types.h"
#include <stdatomic.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int32_t        *storage;                  /* Pointer to externally provided sample memory */
    size_t         capacity;                  /* Maximum sample capacity (MUST be power of two) */
    size_t         mask;                      /* Bitmask: capacity - 1 */

    /* Concurrency registers: cache-line separation recommended on SMP */
    _Atomic size_t head;                      /* Monotonic sample write counter (Producer only) */
    _Atomic size_t tail;                      /* Monotonic sample read counter (Consumer only) */

    /* Producer-private metrics (Modified ONLY by Producer) */
    uint64_t       total_samples_written;     /* Monotonic cumulative samples written */
    uint32_t       overflow_events;           /* Count of buffer overflow attempts */
    uint32_t       overflow_samples_dropped;  /* Total sample count dropped due to overflow */

    /* Consumer-private metrics (Modified ONLY by Consumer) */
    uint64_t       total_samples_read;        /* Monotonic cumulative samples read */
    uint32_t       underflow_events;          /* Count of buffer underflow attempts */
    uint32_t       underflow_samples_starved; /* Total sample count starved due to empty read */
} PcmRingBuffer;

/**
 * @brief Initialize an SPSC ring buffer instance.
 *
 * Precondition: Must be called before starting producer or consumer tasks.
 *
 * @param rb Pointer to ring buffer structure.
 * @param storage Preallocated array of int32_t of at least `capacity` samples.
 * @param capacity Maximum number of samples (MUST be a power of two >= 2).
 * @return PROTOCOL_OK on success, PROTOCOL_ERR_INVALID_PARAM if capacity is not power of 2.
 */
ProtocolStatus ring_buffer_init(
    PcmRingBuffer *rb,
    int32_t *storage,
    size_t capacity
);

/**
 * @brief Reset ring buffer pointers (requires quiescence / stopped streaming).
 */
ProtocolStatus ring_buffer_reset(PcmRingBuffer *rb);

/**
 * @brief Push a block of samples into the ring buffer (PRODUCER CONTEXT / ISR SAFE).
 *
 * Safe to execute inside an I2S DMA ISR. Lock-free, wait-free.
 * If buffer cannot fit all requested samples, pushes as many as possible,
 * increments overflow accounting, and returns PROTOCOL_ERR_BUFFER_FULL.
 *
 * @param rb Ring buffer pointer.
 * @param samples Source sample array.
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
 * @brief Pop a block of samples from the ring buffer (CONSUMER CONTEXT / TASK ONLY).
 *
 * Lock-free, wait-free. If fewer samples are available than requested,
 * reads all available, increments underflow accounting, and returns PROTOCOL_ERR_BUFFER_EMPTY.
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
 * @brief Peek at samples in the ring buffer without consuming them (CONSUMER CONTEXT).
 */
ProtocolStatus ring_buffer_peek(
    const PcmRingBuffer *rb,
    int32_t *out_samples,
    size_t count,
    size_t *samples_peeked
);

/**
 * @brief Get currently available sample count for reading (Consumer query).
 */
static inline size_t ring_buffer_available_read(const PcmRingBuffer *rb) {
    if (!rb) return 0;
    size_t h = atomic_load_explicit(&rb->head, memory_order_acquire);
    size_t t = atomic_load_explicit(&rb->tail, memory_order_relaxed);
    return h - t;
}

/**
 * @brief Get currently available free slot count for writing (Producer query).
 */
static inline size_t ring_buffer_available_write(const PcmRingBuffer *rb) {
    if (!rb) return 0;
    size_t h = atomic_load_explicit(&rb->head, memory_order_relaxed);
    size_t t = atomic_load_explicit(&rb->tail, memory_order_acquire);
    size_t occupied = h - t;
    return (occupied < rb->capacity) ? (rb->capacity - occupied) : 0;
}

/**
 * @brief Check if ring buffer is completely full.
 */
static inline bool ring_buffer_is_full(const PcmRingBuffer *rb) {
    return ring_buffer_available_write(rb) == 0;
}

/**
 * @brief Check if ring buffer is completely empty.
 */
static inline bool ring_buffer_is_empty(const PcmRingBuffer *rb) {
    return ring_buffer_available_read(rb) == 0;
}

#ifdef __cplusplus
}
#endif

#endif /* RING_BUFFER_H */
