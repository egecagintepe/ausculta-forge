#include "g1.h"
#include "acquisition.h"
#include <assert.h>
#include <string.h>

void g1_init(G1Session *s, uint64_t seed, uint32_t uid) {
    memset(s, 0, sizeof(*s));
    s->state = G1_BOOT;
    s->next_session = seed;
    s->uid = uid;
}

static void source_account(G1Session *s, AcquisitionMeta meta) {
    if (s->source_mode != SOURCE_MODE_LIVE_I2S) return;
    s->telemetry.generated_samples = meta.generated;
    s->telemetry.dropped_samples += meta.dropped - s->source_drops;
    s->source_drops = meta.dropped;
    s->telemetry.dma_overflow_events = meta.dma_overflows;
    s->telemetry.ring_overflow_events += meta.ring_overflows - s->source_ring_overflows;
    s->source_ring_overflows = meta.ring_overflows;
    if (meta.dma_overflows) {
        s->telemetry.error_code = G1_ERR_ACQUISITION;
        s->telemetry.stop_reason = STOP_REASON_DMA_OVERFLOW;
    }
}

void g1_link(G1Session *s, bool open) {
    if (s->connected == open) return;
    if (!open && s->telemetry.session_id) {
        source_account(s, acquisition_stop(s->source_mode));
        s->telemetry.usb_disconnect_events++;
        s->telemetry.stop_reason = STOP_REASON_USB_ERROR;
        s->telemetry.error_code = G1_ERR_TRANSPORT;
    }
    s->connected = open;
    s->state = open ? G1_USB_READY : G1_BOOT;
    s->rx_length = s->count = s->head = 0;
    s->stop_requested = s->stop_ack_queued = false;
}

static G1Packet *reserve(G1Session *s) {
    if (s->count == G1_QUEUE_DEPTH) {
        s->control_overflows++;
        g1_transport_fault(s);
        return NULL;
    }
    G1Packet *p = &s->queue[(s->head + s->count++) % G1_QUEUE_DEPTH];
    p->offset = p->length = 0;
    return p;
}

static void error(G1Session *s, uint32_t code, uint32_t context) {
    G1Packet *p = reserve(s);
    if (p) packet_build_error(code, context, p->bytes, sizeof(p->bytes), &p->length);
}

static void dispatch(G1Session *s, uint8_t opcode, const uint8_t *payload, uint64_t now) {
    if (opcode == MSG_TYPE_HELLO_REQ) {
        if (s->state != G1_USB_READY && s->state != G1_READY && s->state != G1_COMPLETE) {
            error(s, G1_ERR_STATE, opcode);
            return;
        }
        HelloReqPayload req;
        packet_decode_hello_req(payload, &req);
        HelloAckPayload ack = {
            .nonce_echo=req.host_nonce, .protocol_version_major=1,
            .supported_profiles_mask=2, .supported_encodings_mask=1,
            .hardware_sample_rate_hz=48000, .firmware_version_major=1, .firmware_version_minor=1,
            .max_frame_samples=256, .device_uid_low=s->uid
        };
        G1Packet *p = reserve(s);
        if (!p) return;
        packet_build_hello_ack(&ack, p->bytes, sizeof(p->bytes), &p->length);
        s->state = G1_HELLO_COMPLETE;
        s->state = G1_READY;
    } else if (opcode == MSG_TYPE_STREAM_START_REQ) {
        if (s->state != G1_READY && s->state != G1_COMPLETE) {
            error(s, G1_ERR_STATE, opcode);
            return;
        }
        StartReqPayload req;
        packet_decode_start_req(payload, &req);
        if (!acquisition_supported(req.source_mode)) {
            error(s, G1_ERR_MODE, req.source_mode);
            return;
        }
        if (req.sample_rate_hz != 48000 || req.encoding != 1 || req.channels != 1 ||
            req.profile_id != 2 || !req.target_samples || req.target_samples > G1_TARGET_SAMPLES ||
            (req.source_mode == SOURCE_MODE_LIVE_I2S && req.target_samples % 256)) {
            error(s, G1_ERR_CONFIG, opcode);
            return;
        }
        G1Packet *p = reserve(s);
        if (!p) return;
        if (acquisition_start(req.source_mode) != PROTOCOL_OK) {
            packet_build_error(G1_ERR_MODE, req.source_mode, p->bytes, sizeof(p->bytes), &p->length);
            return;
        }
        memset(&s->telemetry, 0, sizeof(s->telemetry));
        s->source_mode = req.source_mode;
        s->source_drops = 0;
        s->source_ring_overflows = 0;
        if (++s->next_session == 0) ++s->next_session;
        s->telemetry.session_id = s->next_session;
        s->reference_us = now;
        s->target = req.target_samples;
        s->sequence = 0;
        s->stop_requested = s->stop_ack_queued = false;
        StartAckPayload ack = {
            .session_id=s->next_session, .session_reference_time_us=now,
            .accepted_sample_rate_hz=48000, .accepted_target_samples=s->target,
            .accepted_source_mode=req.source_mode, .encoding=1, .channels=1, .profile_id=2
        };
        packet_build_start_ack(&ack, p->bytes, sizeof(p->bytes), &p->length);
        s->state = G1_STARTED;
    } else if (opcode == MSG_TYPE_STREAM_STOP_REQ) {
        StopReqPayload req;
        packet_decode_stop_req(payload, &req);
        if (!s->telemetry.session_id || req.session_id != s->telemetry.session_id) {
            error(s, G1_ERR_SESSION, opcode);
            return;
        }
        if (s->state != G1_STARTED && s->state != G1_STREAMING &&
            s->state != G1_STOPPING && s->state != G1_COMPLETE) {
            error(s, G1_ERR_STATE, opcode);
            return;
        }
        if (s->state == G1_COMPLETE) s->stop_ack_queued = false;
        s->stop_requested = true;
        source_account(s, acquisition_stop(s->source_mode));
        s->state = G1_STOPPING;
        if (!s->telemetry.error_code) {
            s->telemetry.stop_reason = s->telemetry.generated_samples == s->target ?
                STOP_REASON_NORMAL_TARGET_REACHED : STOP_REASON_HOST_REQUEST;
        }
    }
}

void g1_receive(G1Session *s, const uint8_t *data, size_t length, uint64_t now) {
    if (!s->connected) return;
    for (size_t i=0; i<length; ++i) {
        if (!s->rx_length) s->rx_started_us = now;
        s->rx[s->rx_length++] = data[i];
        s->last_rx_us = now;
        while (s->rx_length >= 4) {
            const uint8_t magic[] = {0x31,0x43,0x53,0xaf};
            if (memcmp(s->rx, magic, 4)) {
                memmove(s->rx, s->rx+1, --s->rx_length);
                continue;
            }
            if (s->rx_length < PROFILE_B_HEADER_SIZE) break;
            ProfileBHeader h;
            packet_decode_header_profile_b(s->rx, &h);
            size_t payload_size = h.msg_type == MSG_TYPE_HELLO_REQ ? HELLO_REQ_PAYLOAD_SIZE :
                h.msg_type == MSG_TYPE_STREAM_START_REQ ? START_REQ_PAYLOAD_SIZE :
                h.msg_type == MSG_TYPE_STREAM_STOP_REQ ? STOP_REQ_PAYLOAD_SIZE : 0;
            if (h.version != 1 || h.sample_count || !payload_size ||
                h.sample_index_start || h.sample_rate_hz != 48000 ||
                h.meaningful_bits != 24 || h.container_bits != 32 || h.channels != 1 ||
                h.encoding != 1 || (h.flags & 0xff00U)) {
                s->malformed_headers++;
                memmove(s->rx, s->rx+4, s->rx_length-4);
                s->rx_length -= 4;
                continue;
            }
            size_t total = 44 + payload_size;
            if (s->rx_length < total) break;
            const uint8_t *t = s->rx + total - 4;
            uint32_t received = (uint32_t)t[0] | (uint32_t)t[1]<<8 |
                (uint32_t)t[2]<<16 | (uint32_t)t[3]<<24;
            if (received != crc32_compute(s->rx, total-4)) {
                s->crc_errors++;
                memmove(s->rx, s->rx+4, s->rx_length-4);
                s->rx_length -= 4;
                continue;
            }
            dispatch(s, h.msg_type, s->rx+40, now);
            s->rx_length = 0;
            break;
        }
    }
}

void g1_tick(G1Session *s, uint64_t now, bool drained) {
    if (!s->connected) return;
    if (s->rx_length && now - s->last_rx_us > 1000000U) {
        s->rx_length = 0;
        s->malformed_headers++;
    }
    if (s->state == G1_STARTED) s->state = G1_STREAMING;
    if ((s->state == G1_STREAMING || s->state == G1_STOPPING) &&
        now - s->reference_us > 40000000U) {
        s->telemetry.stop_reason = STOP_REASON_TIMEOUT;
        g1_transport_fault(s);
        return;
    }
    if (s->state == G1_STREAMING) {
        uint64_t index = s->telemetry.generated_samples;
        uint16_t n = (uint16_t)((s->target-index < 256) ? s->target-index : 256);
        if (s->source_mode == SOURCE_MODE_LIVE_I2S) n = 256;
        /* Release a complete block only after its last sample's nominal deadline. */
        if (s->source_mode == SOURCE_MODE_SYNTH_RAMP &&
            now - s->reference_us < (index+n)*1000000U/48000U) return;
        int32_t samples[256];
        AcquisitionMeta meta;
        ProtocolStatus result = acquisition_block(s->source_mode, index, samples, n, &meta);
        if (result == PROTOCOL_ERR_INCOMPLETE) return;
        if (result != PROTOCOL_OK) {
            source_account(s, acquisition_stop(s->source_mode));
            s->telemetry.error_code = G1_ERR_ACQUISITION;
            s->telemetry.stop_reason = s->telemetry.dma_overflow_events ?
                STOP_REASON_DMA_OVERFLOW : STOP_REASON_USER_ABORT;
            s->state = G1_STOPPING;
            error(s, G1_ERR_ACQUISITION, s->source_mode);
            return;
        }
        if (s->source_mode == SOURCE_MODE_SYNTH_RAMP) s->telemetry.generated_samples += n;
        else { source_account(s, meta); index = meta.first_sample; }
        if (s->count >= G1_QUEUE_DEPTH-2) {
            s->telemetry.dropped_samples += n;
            s->telemetry.ring_overflow_events++;
        } else {
            G1Packet *p = reserve(s);
            assert(p);
            packet_build_profile_b(s->sequence, s->source_mode == SOURCE_MODE_SYNTH_RAMP ?
                s->reference_us+index*1000000U/48000U : meta.timestamp_us,
                index, samples, n, 48000, 24,
                FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SESSION_ACTIVE |
                (s->source_mode == SOURCE_MODE_SYNTH_RAMP ? FRAME_FLAG_SIMULATED_SOURCE : 0) |
                (s->telemetry.dropped_samples || s->telemetry.dma_overflow_events ? FRAME_FLAG_SAMPLE_DISCONTINUITY : 0) |
                (s->telemetry.dropped_samples > s->source_drops ? FRAME_FLAG_USB_QUEUE_OVERFLOW : 0) |
                (s->telemetry.dma_overflow_events ? FRAME_FLAG_DMA_BUFFER_OVERFLOW : 0),
                1, (uint16_t)(s->telemetry.dropped_samples > 65535 ? 65535 : s->telemetry.dropped_samples),
                p->bytes, sizeof(p->bytes), &p->length);
            s->telemetry.fully_queued_samples += n;
            s->telemetry.audio_frames_queued++;
            s->telemetry.audio_bytes_queued += p->length;
        }
        s->sequence++;
        if (index+n >= s->target) {
            source_account(s, acquisition_stop(s->source_mode));
            s->state = G1_STOPPING;
        }
        if (s->sequence % 188 == 0 && s->count < G1_QUEUE_DEPTH-2) {
            G1Packet *p = reserve(s);
            packet_build_status(&s->telemetry, s->sequence, now, p->bytes, sizeof(p->bytes), &p->length);
        }
    }
    if (s->state == G1_STOPPING && s->stop_requested && !s->stop_ack_queued && !s->count && drained) {
        G1Packet *p = reserve(s);
        packet_build_stop_ack(&s->telemetry, p->bytes, sizeof(p->bytes), &p->length);
        s->stop_ack_queued = true;
    }
}

const G1Packet *g1_peek(const G1Session *s) {
    return s->count ? &s->queue[s->head] : NULL;
}

void g1_written(G1Session *s, size_t bytes) {
    if (!s->count) return;
    G1Packet *p = &s->queue[s->head];
    assert(bytes <= p->length-p->offset);
    if (bytes < p->length-p->offset) s->telemetry.usb_partial_write_events++;
    p->offset += bytes;
    if (p->offset == p->length) {
        if (p->bytes[5] == MSG_TYPE_STREAM_STOP_ACK) s->state = G1_COMPLETE;
        s->head = (s->head+1) % G1_QUEUE_DEPTH;
        s->count--;
    }
}

void g1_transport_fault(G1Session *s) {
    source_account(s, acquisition_stop(s->source_mode));
    s->telemetry.usb_timeout_events++;
    s->telemetry.error_code = G1_ERR_TRANSPORT;
    if (s->telemetry.stop_reason != STOP_REASON_TIMEOUT) s->telemetry.stop_reason = STOP_REASON_USB_ERROR;
    s->state = G1_USB_READY;
    s->count = s->head = s->rx_length = 0;
    s->stop_requested = s->stop_ack_queued = false;
}
