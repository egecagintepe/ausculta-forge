#include "acquisition.h"
static const LiveAcquisition *live;

void acquisition_register_live(const LiveAcquisition *adapter) { live = adapter; }
ProtocolStatus acquisition_start(uint8_t mode) {
    return mode == SOURCE_MODE_SYNTH_RAMP ? PROTOCOL_OK :
        live && mode == SOURCE_MODE_LIVE_I2S ? live->start() : PROTOCOL_ERR_INVALID_PARAM;
}
AcquisitionMeta acquisition_stop(uint8_t mode) {
    return mode == SOURCE_MODE_LIVE_I2S && live ? live->stop() : (AcquisitionMeta){0};
}
int32_t pcm24_from_i2s(uint32_t word) {
    uint32_t u = word >> 8;
    return (u & 0x800000U) ? (int32_t)u - 0x1000000 : (int32_t)u;
}
ProtocolStatus acquisition_block(uint8_t mode, uint64_t first, int32_t *samples,
                                 uint16_t count, AcquisitionMeta *meta) {
    if (mode == SOURCE_MODE_LIVE_I2S && live) return live->read(samples,count,meta);
    *meta = (AcquisitionMeta){.first_sample=first,.generated=first+count};
    return acquisition_read(mode,first,samples,count);
}

bool acquisition_supported(uint8_t mode) {
    return mode == SOURCE_MODE_SYNTH_RAMP || (mode == SOURCE_MODE_LIVE_I2S && live);
}

int32_t g1_sample(uint64_t index) {
    uint32_t u = (uint32_t)(index * 16807U + 7U) & 0xffffffU;
    return (u & 0x800000U) ? (int32_t)u - 0x1000000 : (int32_t)u;
}

ProtocolStatus acquisition_read(uint8_t mode, uint64_t first, int32_t *samples, uint16_t count) {
    if (!samples) return PROTOCOL_ERR_NULL_PTR;
    if (!acquisition_supported(mode) || !count || count > PROFILE_B_SAMPLES_PER_FRAME)
        return PROTOCOL_ERR_INVALID_PARAM;
    for (unsigned i=0; i<count; ++i) samples[i] = g1_sample(first+i);
    return PROTOCOL_OK;
}
