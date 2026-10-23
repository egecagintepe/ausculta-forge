#pragma once
#include "protocol_types.h"

/* Task-context, bounded read. Future I2S implementation must preserve signed
 * 24-in-S32 output and absolute indexing; DMA callbacks must not call USB. */
bool acquisition_supported(uint8_t source_mode);
ProtocolStatus acquisition_read(uint8_t source_mode, uint64_t first_sample,
                                int32_t *samples, uint16_t count);
int32_t g1_sample(uint64_t index);
int32_t pcm24_from_i2s(uint32_t word);
typedef struct {
    uint64_t first_sample, timestamp_us, generated, dropped;
    uint32_t dma_overflows, ring_overflows;
} AcquisitionMeta;
typedef struct {
    ProtocolStatus (*start)(void);
    ProtocolStatus (*read)(int32_t *, uint16_t, AcquisitionMeta *);
    AcquisitionMeta (*stop)(void);
} LiveAcquisition;
void acquisition_register_live(const LiveAcquisition *adapter);
ProtocolStatus acquisition_start(uint8_t mode);
AcquisitionMeta acquisition_stop(uint8_t mode);
ProtocolStatus acquisition_block(uint8_t mode, uint64_t first, int32_t *samples,
                                 uint16_t count, AcquisitionMeta *meta);
