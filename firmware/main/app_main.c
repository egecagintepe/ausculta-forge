#include "board_config.h"
#include "usb_transport.h"
#include <inttypes.h>
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static G1Session session;

static void session_task(void *arg) {
    (void)arg;
    TickType_t wake = xTaskGetTickCount();
    G1State previous = G1_BOOT;
    for (;;) {
        af_usb_poll(&session, (uint64_t)esp_timer_get_time());
        if (session.state != previous) {
            ESP_LOGI("G1", "state=%d session=%" PRIu64 " samples=%" PRIu64 " frames=%" PRIu32,
                (int)session.state, session.telemetry.session_id,
                session.telemetry.generated_samples, session.telemetry.audio_frames_queued);
            previous = session.state;
        }
        xTaskDelayUntil(&wake, pdMS_TO_TICKS(1));
    }
}

void app_main(void) {
    uint8_t mac[6];
    ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_BASE));
    uint32_t uid = (uint32_t)mac[2]<<24 | (uint32_t)mac[3]<<16 | (uint32_t)mac[4]<<8 | mac[5];
    uint64_t seed = (uint64_t)esp_random()<<32 | esp_random();
    g1_init(&session, seed, uid);
    ESP_ERROR_CHECK(af_usb_init());
    /* UART0 only. Never redirect stdout/logging to the binary CDC interface. */
    ESP_LOGI("G1", "Canonical B ready; deterministic mode only; hardware G1 PENDING");
    if (xTaskCreate(session_task, "g1_session", 6144, NULL, 6, NULL) != pdPASS) {
        ESP_LOGE("G1", "Cannot start session task");
        ESP_ERROR_CHECK(ESP_ERR_NO_MEM);
    }
}
