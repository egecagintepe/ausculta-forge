/**
 * @file main.c
 * @brief Experimental ESP-IDF reference application for synthetic 100 Hz bench bring-up.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application) Interoperability Tool for Module B (Embedded)
 * Author: Ege Çağın Tepe (Module C)
 * Interface Reviewer: Ozan (Module B)
 *
 * CRITICAL BOUNDARY DISCLAIMER:
 * ----------------------------
 * 1. This file is an isolated, NON-PRODUCTION experimental example prepared by Module C
 *    to demonstrate deterministic synthetic 100 Hz generation and USB streaming patterns.
 * 2. It does NOT replace or supersede Ozan's production firmware under `firmware/`.
 * 3. Final USB framing (headers, magic words, CRC-16) is NOT implemented or frozen here,
 *    pending joint B->C sign-off under DW03-09 and DW03-12.
 * 4. Cross-compilation and flashing of this example was NOT EXECUTED during this sprint
 *    because the ESP-IDF toolchain is not installed on this host and physical hardware is pending.
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "tinyusb.h"
#include "tusb_cdc_acm.h"

#define TAG "AUSCULTA_BENCH"

#define BENCH_SAMPLE_RATE_HZ   48000
#define BENCH_SINE_FREQ_HZ     100
#define BENCH_BLOCK_SIZE       512
#define SINE_TABLE_SIZE        480  /* Exactly 1 period of 100 Hz at 48000 Hz: 48000 / 100 = 480 */

/* 24-bit half-scale peak amplitude (+0.5 FS) */
#define SINE_PEAK_AMPLITUDE    4194304LL

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* Precomputed lookup table for 1 full cycle of 100 Hz sine at 48 kHz */
static int32_t s_sine_table[SINE_TABLE_SIZE];
static uint32_t s_sine_index = 0;
static uint32_t s_sequence_counter = 0;

static void init_sine_lookup_table(void) {
    for (int i = 0; i < SINE_TABLE_SIZE; ++i) {
        double phase = (2.0 * M_PI * (double)i) / (double)SINE_TABLE_SIZE;
        double val = (double)SINE_PEAK_AMPLITUDE * sin(phase);
        s_sine_table[i] = (int32_t)(val >= 0.0 ? (val + 0.5) : (val - 0.5));
    }
    ESP_LOGI(TAG, "Initialized 100 Hz sine table (%d entries, peak=%lld)",
             SINE_TABLE_SIZE, (long long)SINE_PEAK_AMPLITUDE);
}

static void fill_synthetic_block(int32_t *dest, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        dest[i] = s_sine_table[s_sine_index];
        s_sine_index = (s_sine_index + 1) % SINE_TABLE_SIZE;
    }
}

/**
 * @brief CDC-ACM Line State callback.
 */
static void tinyusb_cdc_line_state_changed_callback(int itf, cdcacm_event_t *event) {
    int dtr = event->line_state_changed_data.dtr;
    int rts = event->line_state_changed_data.rts;
    ESP_LOGI(TAG, "CDC line state changed on itf %d: DTR=%d, RTS=%d", itf, dtr, rts);
}

/**
 * @brief Synthetic streaming task generating 48 kHz blocks (512 samples every ~10.67 ms).
 */
static void synthetic_stream_task(void *pvParameters) {
    (void)pvParameters;
    int32_t sample_block[BENCH_BLOCK_SIZE];

    /* Nominal block interval: 512 / 48000 = 10.666 ms */
    const TickType_t xBlockDelay = pdMS_TO_TICKS(11);

    ESP_LOGI(TAG, "Starting synthetic stream task (48 kHz mono, %d samples/block)", BENCH_BLOCK_SIZE);

    while (1) {
        /* Check if host COM port is open (DTR asserted) */
        if (tud_cdc_connected()) {
            int64_t t_start_us = esp_timer_get_time();

            /* 1. Generate synthetic samples */
            fill_synthetic_block(sample_block, BENCH_BLOCK_SIZE);

            /*
             * NOTE FOR MODULE B INTEGRATION:
             * Once the B->C wire protocol is jointly approved (DW03-09 / DW03-12),
             * the wire packet header (magic word, sequence, timestamp, flags)
             * and trailing CRC-16 will be packetized around sample_block here.
             *
             * Currently, raw integer samples are streamed to verify USB throughput.
             */
            size_t bytes_to_send = BENCH_BLOCK_SIZE * sizeof(int32_t);
            size_t bytes_written = tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0,
                                                              (uint8_t *)sample_block,
                                                              bytes_to_send);
            tud_cdc_write_flush();

            s_sequence_counter++;

            if (s_sequence_counter % 100 == 0) {
                ESP_LOGD(TAG, "Streamed frame %u: %zu bytes (t=%lld us)",
                         s_sequence_counter, bytes_written, t_start_us);
            }
        } else {
            /* Idle if host port is closed */
            s_sequence_counter = 0;
            vTaskDelay(pdMS_TO_TICKS(100));
        }

        vTaskDelay(xBlockDelay);
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "=================================================");
    ESP_LOGI(TAG, "AuscultaForge Module C Experimental Bring-Up Bench");
    ESP_LOGI(TAG, "Target: ESP32-S3 N16R8 (Native USB OTG CDC-ACM)");
    ESP_LOGI(TAG, "Status: EXPERIMENTAL INTEROPERABILITY REFERENCE");
    ESP_LOGI(TAG, "=================================================");

    init_sine_lookup_table();

    /* Initialize TinyUSB CDC-ACM stack */
    ESP_LOGI(TAG, "Initializing TinyUSB CDC-ACM stack...");
    const tinyusb_config_t tusb_cfg = {
        .device_descriptor = NULL,
        .string_descriptor = NULL,
        .external_phy = false,
        .configuration_descriptor = NULL,
    };
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    tinyusb_config_cdcacm_t amc_cfg = {
        .usb_dev = TINYUSB_USBDEV_0,
        .cdc_port = TINYUSB_CDC_ACM_0,
        .rx_unread_buf_sz = 1024,
        .callback_rx = NULL,
        .callback_rx_wanted_char = NULL,
        .callback_line_state_changed = tinyusb_cdc_line_state_changed_callback,
        .callback_line_coding_changed = NULL
    };
    ESP_ERROR_CHECK(tusb_cdc_acm_init(&amc_cfg));

    ESP_LOGI(TAG, "TinyUSB initialized. Creating stream task...");
    xTaskCreatePinnedToCore(synthetic_stream_task, "synth_stream", 4096, NULL, 5, NULL, 1);
}
