/**
 * @file ring_buffer.c
 * @brief Bounded Circular Buffer Implementation with Precise Accounting.
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
    if (capacity == 0) return PROTOCOL_ERR_INVALID_PARAM;

    rb->storage = storage;
    rb->capacity = capacity;
    rb->head = 0;
    rb->tail = 0;
    rb->count = 0;
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
    rb->head = 0;
    rb->tail = 0;
    rb->count = 0;
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

    size_t free_slots = rb->capacity - rb->count;
    size_t to_write = (count <= free_slots) ? count : free_slots;

    if (to_write < count) {
        rb->overflow_events++;
        rb->overflow_samples_dropped += (uint32_t)(count - to_write);
    }

    for (size_t i = 0; i < to_write; ++i) {
        rb->storage[rb->head] = samples[i];
        rb->head = (rb->head + 1);
        if (rb->head >= rb->capacity) {
            rb->head = 0;
        }
    }

    rb->count += to_write;
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

    size_t available = rb->count;
    size_t to_read = (count <= available) ? count : available;

    if (to_read < count) {
        rb->underflow_events++;
        rb->underflow_samples_starved += (uint32_t)(count - to_read);
    }

    for (size_t i = 0; i < to_read; ++i) {
        out_samples[i] = rb->storage[rb->tail];
        rb->tail = (rb->tail + 1);
        if (rb->tail >= rb->capacity) {
            rb->tail = 0;
        }
    }

    rb->count -= to_read;
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

    size_t available = rb->count;
    size_t to_peek = (count <= available) ? count : available;
    size_t current_tail = rb->tail;

    for (size_t i = 0; i < to_peek; ++i) {
        out_samples[i] = rb->storage[current_tail];
        current_tail = (current_tail + 1);
        if (current_tail >= rb->capacity) {
            current_tail = 0;
        }
    }

    if (samples_peeked) {
        *samples_peeked = to_peek;
    }

    return (to_peek == count) ? PROTOCOL_OK : PROTOCOL_ERR_BUFFER_EMPTY;
}
