#include "usb_transport.h"
#include <stdatomic.h>
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_cdc_acm.h"
#include "tusb.h"

static atomic_bool attached, suspended, dtr;
static atomic_uint link_epoch;
static unsigned observed_epoch;
static uint64_t last_progress;

static void device_event(tinyusb_event_t *event, void *arg) {
    (void)arg;
    switch (event->id) {
    case TINYUSB_EVENT_ATTACHED:
        atomic_store(&attached, true);
        atomic_store(&suspended, false);
        break;
    case TINYUSB_EVENT_DETACHED:
        atomic_store(&attached, false);
        atomic_store(&dtr, false);
        atomic_fetch_add(&link_epoch, 1);
        break;
    case TINYUSB_EVENT_SUSPENDED:
        atomic_store(&suspended, true);
        atomic_fetch_add(&link_epoch, 1);
        break;
    case TINYUSB_EVENT_RESUMED:
        atomic_store(&suspended, false);
        break;
    }
}

static void line_state(int itf, cdcacm_event_t *event) {
    (void)itf;
    bool open = event->line_state_changed_data.dtr;
    atomic_store(&dtr, open);
    if (!open) atomic_fetch_add(&link_epoch, 1);
}

esp_err_t af_usb_init(void) {
    const tinyusb_config_t cfg = TINYUSB_DEFAULT_CONFIG(device_event);
    esp_err_t err = tinyusb_driver_install(&cfg);
    if (err != ESP_OK) return err;
    const tinyusb_config_cdcacm_t cdc = {
        .cdc_port = TINYUSB_CDC_ACM_0,
        .callback_line_state_changed = line_state,
    };
    err = tinyusb_cdcacm_init(&cdc);
    if (err != ESP_OK) tinyusb_driver_uninstall();
    return err;
}

void af_usb_poll(G1Session *s, uint64_t now) {
    unsigned epoch = atomic_load(&link_epoch);
    bool open = atomic_load(&attached) && !atomic_load(&suspended) && atomic_load(&dtr);
    if (epoch != observed_epoch) {
        g1_link(s, false);
        tud_cdc_n_write_clear(0);
        tud_cdc_n_read_flush(0);
        observed_epoch = epoch;
    }
    if (open != s->connected) {
        g1_link(s, open);
        last_progress = now;
    }
    if (!open) return;

    uint8_t rx[256];
    size_t length = 0;
    if (tinyusb_cdcacm_read(0, rx, sizeof(rx), &length) != ESP_OK) {
        g1_transport_fault(s);
        return;
    }
    if (length) g1_receive(s, rx, length, now);

    esp_err_t flushed = tinyusb_cdcacm_write_flush(0, 0);
    if (flushed != ESP_OK && flushed != ESP_ERR_NOT_FINISHED && flushed != ESP_ERR_TIMEOUT) {
        g1_transport_fault(s);
        tud_cdc_n_write_clear(0);
        return;
    }
    g1_tick(s, now, flushed == ESP_OK);
    for (unsigned budget=0; budget<4; ++budget) {
        const G1Packet *p = g1_peek(s);
        if (!p) break;
        size_t remaining = p->length-p->offset;
        size_t written = tinyusb_cdcacm_write_queue(0, p->bytes+p->offset, remaining);
        g1_written(s, written);
        if (written) last_progress = now;
        if (written < remaining) break;
    }
    /* Kick transmission even when the last write filled less than one endpoint buffer. */
    flushed = tinyusb_cdcacm_write_flush(0, 0);
    if (!g1_peek(s) && flushed == ESP_OK) last_progress = now;
    if (now-last_progress > 1000000U) {
        g1_transport_fault(s);
        tud_cdc_n_write_clear(0);
        last_progress = now;
    }
}
