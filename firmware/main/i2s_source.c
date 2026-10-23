#include "i2s_source.h"
#include "sdkconfig.h"
#include "acquisition.h"
#if CONFIG_AF_I2S_CONFIRMED_PROFILE
#include <stdatomic.h>
#include "driver/i2s_std.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"

typedef struct { int32_t samples[256]; uint64_t first, time; } MicBlock;
static i2s_chan_handle_t channel;
static QueueHandle_t blocks;
static TaskHandle_t worker;
static SemaphoreHandle_t stopped;
static atomic_bool active;
static atomic_uint dma_overflows;
static portMUX_TYPE counters_lock = portMUX_INITIALIZER_UNLOCKED;
static uint64_t captured, dropped;
static uint32_t ring_overflows;
static bool started;

static bool safe_pin(int pin) {
    return (pin >= 1 && pin <= 18 && pin != 3) || pin == 21 || (pin >= 39 && pin <= 42);
}
static bool overflow(i2s_chan_handle_t handle, i2s_event_data_t *event, void *context) {
    (void)handle; (void)event; (void)context;
    atomic_fetch_add(&dma_overflows, 1);
    return false;
}
static AcquisitionMeta statistics(void) {
    portENTER_CRITICAL(&counters_lock);
    AcquisitionMeta m = {.generated=captured, .dropped=dropped,
        .ring_overflows=ring_overflows, .dma_overflows=atomic_load(&dma_overflows)};
    portEXIT_CRITICAL(&counters_lock);
    return m;
}
static void microphone_task(void *arg) {
    (void)arg;
    uint32_t words[512];
    MicBlock block;
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        size_t filled = 0;
        while (atomic_load(&active)) {
            size_t bytes = 0;
            esp_err_t err = i2s_channel_read(channel, (uint8_t *)words+filled,
                                            sizeof(words)-filled, &bytes, 20);
            filled += bytes;
            if (!atomic_load(&active)) break;
            if (err != ESP_OK && err != ESP_ERR_TIMEOUT) {
                atomic_fetch_add(&dma_overflows, 1);
                atomic_store(&active, false);
                break;
            }
            if (filled != sizeof(words)) continue;
            filled = 0;
            portENTER_CRITICAL(&counters_lock);
            block.first = captured;
            captured += 256;
            portEXIT_CRITICAL(&counters_lock);
            /* Completion time is observed; first-sample time is an explicit block-duration estimate. */
            block.time = (uint64_t)esp_timer_get_time() - 5333U;
            for (unsigned i=0; i<256; ++i) {
#if CONFIG_AF_I2S_RIGHT_SLOT
                unsigned slot = 1;
#else
                unsigned slot = 0;
#endif
                block.samples[i] = pcm24_from_i2s(words[2*i+slot]);
            }
            if (xQueueSend(blocks, &block, 0) != pdTRUE) {
                portENTER_CRITICAL(&counters_lock);
                dropped += 256;
                ring_overflows++;
                portEXIT_CRITICAL(&counters_lock);
            }
        }
        if (filled) {
            portENTER_CRITICAL(&counters_lock);
            captured += filled/(2*sizeof(uint32_t));
            dropped += filled/(2*sizeof(uint32_t));
            portEXIT_CRITICAL(&counters_lock);
        }
        xSemaphoreGive(stopped);
    }
}
static ProtocolStatus begin(void) {
    if (started) return PROTOCOL_ERR_INVALID_PARAM;
    xQueueReset(blocks);
    portENTER_CRITICAL(&counters_lock);
    captured = dropped = ring_overflows = 0;
    portEXIT_CRITICAL(&counters_lock);
    atomic_store(&dma_overflows,0);
    if (i2s_channel_enable(channel) != ESP_OK) return PROTOCOL_ERR_INVALID_PARAM;
    started = true;
    atomic_store(&active,true);
    xTaskNotifyGive(worker);
    return PROTOCOL_OK;
}
static ProtocolStatus read_block(int32_t *out, uint16_t count, AcquisitionMeta *meta) {
    if (count != 256 || !started) return PROTOCOL_ERR_INVALID_PARAM;
    MicBlock block;
    if (xQueueReceive(blocks,&block,0) != pdTRUE)
        return atomic_load(&active) ? PROTOCOL_ERR_INCOMPLETE : PROTOCOL_ERR_INVALID_PARAM;
    for (unsigned i=0; i<256; ++i) out[i] = block.samples[i];
    *meta = statistics();
    meta->first_sample = block.first;
    meta->timestamp_us = block.time;
    return PROTOCOL_OK;
}
static AcquisitionMeta end(void) {
    if (started) {
        atomic_store(&active,false);
        i2s_channel_disable(channel);
        if (xSemaphoreTake(stopped,pdMS_TO_TICKS(100)) != pdTRUE) {
            atomic_fetch_add(&dma_overflows,1);
            return statistics(); /* Never reset a queue still owned by a running task. */
        }
        uint64_t pending = (uint64_t)uxQueueMessagesWaiting(blocks)*256;
        portENTER_CRITICAL(&counters_lock);
        dropped += pending;
        portEXIT_CRITICAL(&counters_lock);
        xQueueReset(blocks);
        started = false;
    }
    return statistics();
}
esp_err_t af_i2s_init(void) {
    if (!safe_pin(CONFIG_AF_I2S_BCLK) || !safe_pin(CONFIG_AF_I2S_WS) ||
        !safe_pin(CONFIG_AF_I2S_DIN) || CONFIG_AF_I2S_BCLK == CONFIG_AF_I2S_WS ||
        CONFIG_AF_I2S_BCLK == CONFIG_AF_I2S_DIN || CONFIG_AF_I2S_WS == CONFIG_AF_I2S_DIN)
        return ESP_ERR_INVALID_ARG;
    i2s_chan_config_t cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0,I2S_ROLE_MASTER);
    cfg.dma_desc_num = 8;
    cfg.dma_frame_num = 256;
    esp_err_t err = i2s_new_channel(&cfg,NULL,&channel);
    if (err != ESP_OK) return err;
    i2s_std_config_t standard = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(48000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {.mclk=I2S_GPIO_UNUSED, .bclk=CONFIG_AF_I2S_BCLK, .ws=CONFIG_AF_I2S_WS,
                     .dout=I2S_GPIO_UNUSED, .din=CONFIG_AF_I2S_DIN}
    };
    err = i2s_channel_init_std_mode(channel,&standard);
    if (err != ESP_OK) { i2s_del_channel(channel); return err; }
    const i2s_event_callbacks_t callbacks = {.on_recv_q_ovf=overflow};
    err = i2s_channel_register_event_callback(channel,&callbacks,NULL);
    if (err != ESP_OK) { i2s_del_channel(channel); return err; }
    blocks = xQueueCreate(8,sizeof(MicBlock));
    stopped = xSemaphoreCreateBinary();
    if (!blocks || !stopped ||
        xTaskCreate(microphone_task,"inmp441_rx",6144,NULL,7,&worker) != pdPASS) {
        if (blocks) vQueueDelete(blocks);
        if (stopped) vSemaphoreDelete(stopped);
        i2s_del_channel(channel);
        return ESP_ERR_NO_MEM;
    }
    static const LiveAcquisition adapter = {.start=begin, .read=read_block, .stop=end};
    acquisition_register_live(&adapter);
    return ESP_OK;
}
#else
esp_err_t af_i2s_init(void) { return ESP_OK; }
#endif
