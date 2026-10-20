# AuscultaForge — ESP-IDF Integration Guide for Module B
## Guidelines & Implementation Patterns for ESP32-S3 USB Audio Transport

- **Hardware Target:** ESP32-S3-DevKitC-1-N8R8 / N16R8 (Dual-core Xtensa LX7 @ 240 MHz)
- **Target Framework:** ESP-IDF v5.x with FreeRTOS and TinyUSB CDC-ACM
- **Authors:** Ege Çağın Tepe (Module C) — Interface Proposal for Ozan (Module B)
- **Host Verification Notice:**
  > [!IMPORTANT]
  > **UNBUILT FIRMWARE / HOST ENVIRONMENT NOTICE:**
  > The host development environment does **NOT** contain an installed ESP-IDF toolchain (`idf.py` is absent).
  > Consequently, firmware examples in this document are **NOT VERIFIED ON HOST COMPILER** and have **NOT RUN ON PHYSICAL HARDWARE**.
  > These code listings represent architectural design patterns and pseudocode for Module B's review and adaptation.

---

## 1. Directory Structure in ESP-IDF Component Tree

To integrate the portable protocol headers into your ESP-IDF firmware repository:

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

On the ESP32-S3, the Native USB OTG peripheral connects directly to:
- **USB D- (DM):** `GPIO 19`
- **USB D+ (DP):** `GPIO 20`
- **USB VBUS:** Connect to 5V rail for bus detection.

### Indicative `sdkconfig.defaults` Entries:
```ini
# TinyUSB CDC-ACM Configuration
CONFIG_TINYUSB=y
CONFIG_TINYUSB_CDC_ENABLED=y
CONFIG_TINYUSB_CDC_COUNT=1
CONFIG_TINYUSB_CDC_RX_BUFSIZE=1024
CONFIG_TINYUSB_CDC_TX_BUFSIZE=2048

# System Clock
CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y
CONFIG_FREERTOS_HZ=1000
```

---

## 3. Example 1: Synthetic G1 Bring-Up Firmware (Deterministic Signal Source)

> [!NOTE]
> **PURPOSE:** Test USB enumeration, CDC-ACM throughput, packet framing, and Python receiver validation **before** physical microphone soldering or I2S driver bring-up.
> Uses `waveform_gen` to synthesize an initialized 100 Hz sine wave or monotonic ramp.

```c
#include <string.h>
#include "esp_timer.h"
#include "esp_log.h"
#include "tinyusb.h"
#include "tusb_cdc_acm.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "protocol_types.h"
#include "packet_framing.h"
#include "waveform_gen.h"

#define TAG "AUSCULTA_SYNTH"

#define STREAM_BLOCK_SAMPLES  256U
#define SAMPLE_RATE_HZ        48000U

/* Preallocated packet buffer: 40B header + 1024B payload + 4B CRC32 = 1068 bytes */
static uint8_t s_wire_packet[PROFILE_B_FRAME_TOTAL_BYTES];
static uint32_t s_sequence_counter = 0;
static uint64_t s_sample_index_counter = 0;
static uint16_t s_cumulative_mcu_drops = 0;

void synthetic_g1_stream_task(void *pvParameters) {
    (void)pvParameters;

    /* Initialize deterministic waveform generator state */
    WaveformGeneratorState gen_state;
    waveform_gen_init(
        &gen_state,
        GEN_SIGNAL_SINE_100HZ,
        SAMPLE_RATE_HZ,
        100.0,  /* 100 Hz fundamental */
        0.5,    /* -6 dBFS amplitude */
        false   /* LSB-aligned */
    );

    int32_t raw_samples[STREAM_BLOCK_SAMPLES];
    ESP_LOGI(TAG, "Starting Synthetic G1 Bring-Up Stream Task (48 kHz mono, 256 samples/frame)...");

    while (1) {
        /* Check if host has opened the COM port (DTR asserted) */
        if (!tud_cdc_connected()) {
            s_sequence_counter = 0;
            s_sample_index_counter = 0;
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        /* 1. CRITICAL: Initialize and acquire deterministic samples into buffer */
        waveform_gen_fill_block(&gen_state, raw_samples, STREAM_BLOCK_SAMPLES);

        /* 2. Read monotonic hardware microsecond timestamp */
        int64_t t_acquire_us = esp_timer_get_time();

        /* 3. Build Profile B packet with explicit little-endian serialization */
        size_t packet_size = 0;
        ProtocolStatus st = packet_build_profile_b(
            s_sequence_counter,
            (uint64_t)t_acquire_us,
            s_sample_index_counter,
            raw_samples,
            STREAM_BLOCK_SAMPLES,
            SAMPLE_RATE_HZ,
            NOMINAL_MEANINGFUL_BITS,
            FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SIMULATED_SOURCE,
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

        /* 4. Transmit over USB CDC-ACM */
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

        if (total_written < bytes_to_write) {
            s_cumulative_mcu_drops += STREAM_BLOCK_SAMPLES;
            ESP_LOGW(TAG, "USB backpressure! Dropped %u samples", STREAM_BLOCK_SAMPLES);
        }

        s_sequence_counter++;
        s_sample_index_counter += STREAM_BLOCK_SAMPLES;

        /* Wall-clock pacing: 256 samples @ 48 kHz is 5.333 ms per frame */
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
```

---

## 4. Example 2: Real Microphone Acquisition Pseudocode (I2S DMA to USB)

> [!WARNING]
> **STATUS: ILLUSTRATIVE ARCHITECTURAL PSEUDOCODE — NOT TESTED ON HARDWARE:**
> The following code outlines the recommended FreeRTOS dual-task bridge pattern connecting an I2S DMA receive channel to the lock-free SPSC ring buffer and USB transmission worker.
> Incomplete hardware integration steps are explicitly marked with `[TODO: MODULE B HARDWARE INTEGRATION]`.

```c
#include "driver/i2s_std.h"
#include "ring_buffer.h"
#include "packet_framing.h"

#define I2S_DMA_BUFFER_SAMPLES  256U
#define RING_BUFFER_CAPACITY    4096U  /* Power of two: ~85 ms buffering */

static int32_t s_ring_storage[RING_BUFFER_CAPACITY];
static PcmRingBuffer s_pcm_ring;
static i2s_chan_handle_t s_rx_chan = NULL;

/* PRECONDITION 1: Hardware I2S Initialization [TODO: MODULE B HARDWARE INTEGRATION] */
esp_err_t init_hardware_i2s(void) {
    /* [TODO: Set exact GPIO pins for PUI Audio DMM-4026 MEMS microphone:
     * - BCLK (Bit Clock)
     * - WS / LRCLK (Word Select)
     * - DIN (Data Input)
     */
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    esp_err_t ret = i2s_new_channel(&chan_cfg, NULL, &s_rx_chan);
    if (ret != ESP_OK) return ret;

    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(48000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_24BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = GPIO_NUM_4,   /* [TODO: Confirm with Module A schematic] */
            .ws   = GPIO_NUM_5,   /* [TODO: Confirm with Module A schematic] */
            .dout = I2S_GPIO_UNUSED,
            .din  = GPIO_NUM_6,   /* [TODO: Confirm with Module A schematic] */
            .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
        },
    };

    ret = i2s_channel_init_std_mode(s_rx_chan, &std_cfg);
    if (ret != ESP_OK) return ret;

    /* Initialize lock-free SPSC ring buffer (power of two capacity = 4096) */
    ring_buffer_init(&s_pcm_ring, s_ring_storage, RING_BUFFER_CAPACITY);
    return i2s_channel_enable(s_rx_chan);
}

/* TASK A (Producer): Ingests samples from I2S DMA and pushes to SPSC ring buffer */
void i2s_audio_ingest_task(void *pvParameters) {
    (void)pvParameters;
    int32_t dma_rx_buf[I2S_DMA_BUFFER_SAMPLES];
    size_t bytes_read = 0;

    while (1) {
        /* Blocks until DMA hardware buffer fills from MEMS microphone */
        esp_err_t err = i2s_channel_read(
            s_rx_chan,
            dma_rx_buf,
            sizeof(dma_rx_buf),
            &bytes_read,
            portMAX_DELAY
        );

        if (err == ESP_OK && bytes_read > 0) {
            size_t samples_read = bytes_read / sizeof(int32_t);
            size_t pushed = 0;

            /* Push to lock-free SPSC buffer (ISR / Task safe) */
            ProtocolStatus st = ring_buffer_push(&s_pcm_ring, dma_rx_buf, samples_read, &pushed);
            if (st == PROTOCOL_ERR_BUFFER_FULL) {
                /* Log drop count without blocking */
            }
        }
    }
}

/* TASK B (Consumer): Pops from SPSC ring buffer and transmits framed packets over USB */
void usb_transport_worker_task(void *pvParameters) {
    (void)pvParameters;
    int32_t packet_samples[STREAM_BLOCK_SAMPLES];
    uint8_t wire_packet[PROFILE_B_FRAME_TOTAL_BYTES];
    uint32_t seq = 0;
    uint64_t sample_idx = 0;

    while (1) {
        if (!tud_cdc_connected()) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        /* Check if a full frame (256 samples) is available in ring buffer */
        if (ring_buffer_available_read(&s_pcm_ring) >= STREAM_BLOCK_SAMPLES) {
            size_t popped = 0;
            ring_buffer_pop(&s_pcm_ring, packet_samples, STREAM_BLOCK_SAMPLES, &popped);

            if (popped == STREAM_BLOCK_SAMPLES) {
                int64_t ts_us = esp_timer_get_time();
                size_t pkt_len = 0;

                packet_build_profile_b(
                    seq++,
                    (uint64_t)ts_us,
                    sample_idx,
                    packet_samples,
                    STREAM_BLOCK_SAMPLES,
                    48000,
                    24,
                    FRAME_FLAG_TIMESTAMP_VALID,
                    ENCODING_SIGNED_PCM_LSB_ALIGNED,
                    s_pcm_ring.overflow_samples_dropped,
                    wire_packet,
                    sizeof(wire_packet),
                    &pkt_len
                );

                sample_idx += STREAM_BLOCK_SAMPLES;
                tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0, wire_packet, pkt_len);
                tud_cdc_write_flush();
            }
        } else {
            /* Buffer has fewer than 256 samples: sleep briefly */
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
}
```

---

## 5. Hardware Acceptance Checklist for Module B (Ozan)

When your physical ESP32-S3 board arrives:
1. Flash Example 1 (Synthetic Sine Wave) first to prove USB enumeration and CRC integrity.
2. Connect to PC via USB and run:
   ```bash
   python tools/protocol_lab/module_b_package/verify_g1_bringup.py --port COMx --profile b --duration 10.0
   ```
3. Once USB framing is validated, proceed to Example 2 and solder the MEMS microphone.
