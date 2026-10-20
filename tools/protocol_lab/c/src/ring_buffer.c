/**
 * @file ring_buffer.c
 * @brief Lock-Free SPSC Circular Buffer Implementation using C11 Atomics.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Reviewer: Ozan (Module B)
 */

#include "ring_buffer.h"
#include <string.h>

ProtocolStatus ring_buffer_init(
    PcmRingBuffer *rb,
    int32_t *storage,
    size_t capacity
) {
    if (!rb || !storage) return PROTOCOL_ERR_NULL_PTR;

    /* Capacity must be a power of two >= 2 for lock-free modulo wrapping */
    if (capacity < 2 || (capacity & (capacity - 1)) != 0) {
        return PROTOCOL_ERR_INVALID_PARAM;
    }

    rb->storage = storage;
    rb->capacity = capacity;
    rb->mask = capacity - 1;

    atomic_init(&rb->head, 0);
    atomic_init(&rb->tail, 0);

    rb->total_samples_written = 0;
    rb->total_samples_read = 0;
    rb->overflow_events = 0;
    rb->overflow_samples_dropped = 0;
    rb->underflow_events = 0;
    rb->underflow_samples_starved = 0;

    return PROTOCOL_OK;
}

ProtocolStatus ring_buffer_reset(PcmRingBuffer *rb) {
    if (!rb) return PROTOCOL_ERR_NULL_PTR;

    atomic_store_explicit(&rb->head, 0, memory_order_relaxed);
    atomic_store_explicit(&rb->tail, 0, memory_order_relaxed);

    return PROTOCOL_OK;
}

ProtocolStatus ring_buffer_push(
    PcmRingBuffer *rb,
    const int32_t *samples,
    size_t count,
    size_t *samples_pushed
) {
    if (!rb || !samples) return PROTOCOL_ERR_NULL_PTR;
    if (count == 0) {
        if (samples_pushed) *samples_pushed = 0;
        return PROTOCOL_OK;
    }

    /* Producer loads its own head relaxed, loads consumer's tail with acquire */
    size_t h = atomic_load_explicit(&rb->head, memory_order_relaxed);
    size_t t = atomic_load_explicit(&rb->tail, memory_order_acquire);

    size_t occupied = h - t;
    size_t free_slots = (occupied < rb->capacity) ? (rb->capacity - occupied) : 0;
    size_t to_write = (count <= free_slots) ? count : free_slots;

    if (to_write < count) {
        rb->overflow_events++;
        rb->overflow_samples_dropped += (uint32_t)(count - to_write);
    }

    /* Write samples into preallocated circular memory */
    for (size_t i = 0; i < to_write; ++i) {
        rb->storage[(h + i) & rb->mask] = samples[i];
    }

    /* Publish newly written samples to Consumer using release semantics */
    atomic_store_explicit(&rb->head, h + to_write, memory_order_release);
    rb->total_samples_written += to_write;

    if (samples_pushed) {
        *samples_pushed = to_write;
    }

    return (to_write == count) ? PROTOCOL_OK : PROTOCOL_ERR_BUFFER_FULL;
}

ProtocolStatus ring_buffer_pop(
    PcmRingBuffer *rb,
    int32_t *out_samples,
    size_t count,
    size_t *samples_popped
) {
    if (!rb || !out_samples) return PROTOCOL_ERR_NULL_PTR;
    if (count == 0) {
        if (samples_popped) *samples_popped = 0;
        return PROTOCOL_OK;
    }

    /* Consumer loads its own tail relaxed, loads producer's head with acquire */
    size_t t = atomic_load_explicit(&rb->tail, memory_order_relaxed);
    size_t h = atomic_load_explicit(&rb->head, memory_order_acquire);

    size_t available = h - t;
    size_t to_read = (count <= available) ? count : available;

    if (to_read < count) {
        rb->underflow_events++;
        rb->underflow_samples_starved += (uint32_t)(count - to_read);
    }

    /* Read samples from circular memory */
    for (size_t i = 0; i < to_read; ++i) {
        out_samples[i] = rb->storage[(t + i) & rb->mask];
    }

    /* Publish newly freed space to Producer using release semantics */
    atomic_store_explicit(&rb->tail, t + to_read, memory_order_release);
    rb->total_samples_read += to_read;

    if (samples_popped) {
        *samples_popped = to_read;
    }

    return (to_read == count) ? PROTOCOL_OK : PROTOCOL_ERR_BUFFER_EMPTY;
}

ProtocolStatus ring_buffer_peek(
    const PcmRingBuffer *rb,
    int32_t *out_samples,
    size_t count,
    size_t *samples_peeked
) {
    if (!rb || !out_samples) return PROTOCOL_ERR_NULL_PTR;
    if (count == 0) {
        if (samples_peeked) *samples_peeked = 0;
        return PROTOCOL_OK;
    }

    size_t t = atomic_load_explicit(&rb->tail, memory_order_relaxed);
    size_t h = atomic_load_explicit(&rb->head, memory_order_acquire);

    size_t available = h - t;
    size_t to_read = (count <= available) ? count : available;

    for (size_t i = 0; i < to_read; ++i) {
        out_samples[i] = rb->storage[(t + i) & rb->mask];
    }

    if (samples_peeked) {
        *samples_peeked = to_read;
    }

    return (to_read == count) ? PROTOCOL_OK : PROTOCOL_ERR_BUFFER_EMPTY;
}
