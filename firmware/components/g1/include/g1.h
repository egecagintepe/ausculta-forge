#pragma once
#include "packet_framing.h"
#include "acquisition.h"

#define G1_QUEUE_DEPTH 8U
#define G1_TARGET_SAMPLES 480000U
typedef enum {
    G1_BOOT, G1_USB_READY, G1_HELLO_COMPLETE, G1_READY, G1_STARTED,
    G1_STREAMING, G1_STOPPING, G1_COMPLETE
} G1State;
/* Local ERROR vocabulary: canonical v0.1 defines the layout, not these values. */
enum { G1_ERR_STATE=1, G1_ERR_MODE=2, G1_ERR_SESSION=3, G1_ERR_CONFIG=4,
       G1_ERR_TRANSPORT=5, G1_ERR_ACQUISITION=6 };
typedef struct {
    uint8_t bytes[PROFILE_B_FRAME_TOTAL_BYTES];
    size_t length, offset;
} G1Packet;
typedef struct {
    G1State state;
    StatusTelemetryPayload telemetry;
    uint64_t next_session, reference_us, target, last_rx_us;
    uint32_t uid, sequence, crc_errors, malformed_headers, control_overflows;
    bool connected, stop_requested, stop_ack_queued;
    uint8_t source_mode;
    uint64_t source_drops;
    uint32_t source_ring_overflows;
    uint8_t rx[60];
    size_t rx_length;
    uint64_t rx_started_us;
    G1Packet queue[G1_QUEUE_DEPTH];
    unsigned head, count;
} G1Session;

/* All calls belong to one owner task. Time is monotonic microseconds. */
void g1_init(G1Session *s, uint64_t session_seed, uint32_t uid);
void g1_link(G1Session *s, bool open);
void g1_receive(G1Session *s, const uint8_t *data, size_t length, uint64_t now);
void g1_tick(G1Session *s, uint64_t now, bool transport_drained);
const G1Packet *g1_peek(const G1Session *s);
void g1_written(G1Session *s, size_t bytes);
void g1_transport_fault(G1Session *s);
