#pragma once
#include "g1.h"
#include "esp_err.h"
esp_err_t af_usb_init(void);
/* Called once per millisecond by the sole session owner. Never blocks on USB. */
void af_usb_poll(G1Session *session, uint64_t now);
