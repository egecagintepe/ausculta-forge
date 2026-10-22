#pragma once
#include "protocol_types.h"

/* Task-context, bounded read. Future I2S implementation must preserve signed
 * 24-in-S32 output and absolute indexing; DMA callbacks must not call USB. */
bool acquisition_supported(uint8_t source_mode);
ProtocolStatus acquisition_read(uint8_t source_mode, uint64_t first_sample,
                                int32_t *samples, uint16_t count);
int32_t g1_sample(uint64_t index);
