/* Host-only ABI for testing the real C session without mirroring its layout. */
#include "g1.h"
#include <string.h>

static G1Session session;
void test_init(uint64_t seed) { g1_init(&session, seed, 0x53433332); g1_link(&session, true); }
void test_rx(const uint8_t *p, size_t n, uint64_t now) { g1_receive(&session, p, n, now); }
void test_tick(uint64_t now, int drained) { g1_tick(&session, now, drained != 0); }
void test_link(int open) { g1_link(&session, open != 0); }
void test_fault(void) { g1_transport_fault(&session); }
int test_state(void) { return session.state; }
uint32_t test_crc_errors(void) { return session.crc_errors; }
uint32_t test_malformed(void) { return session.malformed_headers; }
uint32_t test_overflows(void) { return session.control_overflows; }
size_t test_read(uint8_t *out, size_t cap) {
    const G1Packet *p = g1_peek(&session);
    if (!p) return 0;
    size_t n = p->length-p->offset;
    if (n > cap) n = cap;
    memcpy(out, p->bytes+p->offset, n);
    g1_written(&session, n);
    return n;
}
