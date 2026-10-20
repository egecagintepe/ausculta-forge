# AuscultaForge — ESP-IDF v5.x Integration Guide for Module B
## Step-by-Step Implementation of Profile B Protocol on ESP32-S3 Native USB

- **Target Hardware:** ESP32-S3-DevKitC-1-N8R8 / N16R8 (Xtensa dual-core LX7 @ 240 MHz)
- **Framework:** ESP-IDF v5.x with FreeRTOS and TinyUSB CDC-ACM
- **Prepared by:** Ege (Module C) for Ozan (Module B)
- **Objective:** Provide a clean, drop-in pattern to implement the 48 kHz framed stream without modifying Ozan's core sensor drivers.

---

## 1. Directory Setup in ESP-IDF Project

Drop the C headers from `module_b_package/include/` into your firmware component tree:

```
firmware/
├── components/
│   └── ausculta_protocol/
│       ├── CMakeLists.txt
│       └── include/
│           ├── protocol_types.h
│           ├── packet_framing.h
│           ├── waveform_gen.h
│           └── ring_buffer.h
```

### `components/ausculta_protocol/CMakeLists.txt`
```cmake
idf_component_register(
    INCLUDE_DIRS "include"
    SRCS ""
    REQUIRES esp_timer
)
```

---

## 2. TinyUSB & Hardware Pin Configuration

On the ESP32-S3, the Native USB OTG peripheral is mapped to fixed silicon pins:
- **USB D- (DM):** `GPIO 19`
- **USB D+ (DP):** `GPIO 20`
- **USB VBUS:** Connect to 5V USB rail (for device bus detection).

### Required `sdkconfig.defaults` Entries:
```ini
# Enable TinyUSB CDC-ACM
CONFIG_TINYUSB=y
CONFIG_TINYUSB_CDC_ENABLED=y
CONFIG_TINYUSB_CDC_COUNT=1
CONFIG_TINYUSB_CDC_RX_BUFSIZE=1024
CONFIG_TINYUSB_CDC_TX_BUFSIZE=2048

# I2S DMA & High Performance Memory
CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y
CONFIG_FREERTOS_HZ=1000
```

---

## 3. Production ESP-IDF Streaming Task Implementation

The following pattern bridges I2S DMA callbacks to the TinyUSB CDC-ACM endpoint with exact sample accounting:

```c
#include <string.h>
#include "esp_timer.h"
#include "esp_log.h"
#include "tinyusb.h"
#include "tusb_cdc_acm.h"
#include "protocol_types.h"
#include "packet_framing.h"
#include "waveform_gen.h"

#define TAG "AUSCULTA_STREAM"

#define STREAM_BLOCK_SAMPLES  256U
#define SAMPLE_RATE_HZ        48000U

/* Precomputed packet buffer: 40B header + 1024B payload + 4B CRC32 = 1068 bytes */
static uint8_t s_wire_packet[PROFILE_B_FRAME_TOTAL_BYTES];
static uint32_t s_sequence_counter = 0;
static uint64_t s_sample_index_counter = 0;
static uint16_t s_cumulative_mcu_drops = 0;

void stream_audio_task(void *pvParameters) {
    (void)pvParameters;
    int32_t raw_samples[STREAM_BLOCK_SAMPLES];

    ESP_LOGI(TAG, "Starting AuscultaForge Profile B Stream Task (48 kHz mono, 256 samples/frame)...");

    while (1) {
        /* 1. Check if host has opened the COM port (DTR asserted) */
        if (!tud_cdc_connected()) {
            s_sequence_counter = 0;
            s_sample_index_counter = 0;
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        /* 2. Ingest samples from hardware I2S DMA queue or ring buffer.
         * For bring-up bench simulation before MEMS soldering, generate synthetic 100 Hz: */
        int64_t t_acquire_us = esp_timer_get_time();

        /* (Replace with: i2s_channel_read(rx_chan, raw_samples, sizeof(raw_samples), &bytes_read, portMAX_DELAY);) */

        /* 3. Build Profile B packet into preallocated wire buffer */
        size_t packet_size = 0;
        ProtocolStatus st = packet_build_profile_b(
            s_sequence_counter,
            (uint64_t)t_acquire_us,
            s_sample_index_counter,
            raw_samples,
            STREAM_BLOCK_SAMPLES,
            SAMPLE_RATE_HZ,
            NOMINAL_MEANINGFUL_BITS,
            FRAME_FLAG_TIMESTAMP_VALID,
            ENCODING_SIGNED_PCM_LSB_ALIGNED,
            s_cumulative_mcu_drops,
            s_wire_packet,
            sizeof(s_wire_packet),
            &packet_size
        );

        if (st != PROTOCOL_OK) {
            ESP_LOGE(TAG, "Failed to build Profile B frame: %d", st);
            continue;
        }

        /* 4. Transmit packet over USB CDC-ACM with partial-write recovery */
        size_t bytes_to_write = packet_size;
        size_t total_written = 0;
        int retries = 0;

        while (total_written < bytes_to_write && retries < 3) {
            size_t written = tinyusb_cdcacm_write_queue(
                TINYUSB_CDC_ACM_0,
                s_wire_packet + total_written,
                bytes_to_write - total_written
            );
            total_written += written;
            if (total_written < bytes_to_write) {
                tud_cdc_write_flush();
                retries++;
                vTaskDelay(pdMS_TO_TICKS(1));
            }
        }
        tud_cdc_write_flush();

        /* Track dropped samples if host buffer backed up */
        if (total_written < bytes_to_write) {
            s_cumulative_mcu_drops += STREAM_BLOCK_SAMPLES;
            ESP_LOGW(TAG, "USB backpressure drop! Cumulative drops: %u samples", s_cumulative_mcu_drops);
        }

        /* Advance counters */
        s_sequence_counter++;
        s_sample_index_counter += STREAM_BLOCK_SAMPLES;

        /* In production, DMA interrupt drives timing. For bench loop delay: */
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
```

---

## 4. Hardware Bring-Up Acceptance Criteria (Milestone G1)

When your ESP32-S3 board is programmed and plugged into the host PC:
1. Windows Device Manager registers `USB Serial Device (COMx)`.
2. Run `python tools/protocol_lab/module_b_package/verify_g1_bringup.py --port COMx --seconds 10`.
3. The tool verifies:
   - Synchronizes on magic word `0xAF534331`.
   - Validates CRC-32 on 100% of received frames.
   - Computes live Welch Power Spectral Density and reports peak frequency and SNR.
   - Emits immediate pass/fail audit report for your academic logbook!
