/**
 * @file packet_framing.c
 * @brief Packet Serialization, Deserialization & CRC Integrity Implementation.
 *
 * Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
 * Module: C (Computer Application / Software Integration)
 * Author: Ege Çağın Tepe (Module C)
 * Joint Reviewer: Ozan (Module B)
 */

#include "packet_framing.h"
#include <string.h>

/* ========================================================================= */
/* 1. CRC Algorithms                                                         */
/* ========================================================================= */

uint16_t crc16_ccitt_compute(const uint8_t *data, size_t length, uint16_t init_val) {
    if (!data || length == 0) return init_val;

    uint16_t crc = init_val;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; ++b) {
            if (crc & 0x8000U) {
                crc = (crc << 1) ^ 0x1021U;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}

/*
 * Precomputed Static Constant CRC-32 Lookup Table (IEEE 802.3 standard, polynomial 0xEDB88320).
 * Placed entirely in read-only data (.rodata). Thread-safe with zero runtime race conditions.
 */
static const uint32_t s_crc32_table[256] = {
    0x00000000U, 0x77073096U, 0xEE0E612CU, 0x990951BAU, 0x076DC419U, 0x706AF48FU, 0xE963A535U, 0x9E6495A3U,
    0x0EDB8832U, 0x79DCB8A4U, 0xE0D5E91EU, 0x97D2D988U, 0x09B64C2BU, 0x7EB17CBDU, 0xE7B82D07U, 0x90BF1D91U,
    0x1DB71064U, 0x6AB020F2U, 0xF3B97148U, 0x84BE41DEU, 0x1ADAD47DU, 0x6DDDE4EBU, 0xF4D4B551U, 0x83D385C7U,
    0x136C9856U, 0x646BA8C0U, 0xFD62F97AU, 0x8A65C9ECU, 0x14015C4FU, 0x63066CD9U, 0xFA0F3D63U, 0x8D080DF5U,
    0x3B6E20C8U, 0x4C69105EU, 0xD56041E4U, 0xA2677172U, 0x3C03E4D1U, 0x4B04D447U, 0xD20D85FDU, 0xA50AB56BU,
    0x35B5A8FAU, 0x42B2986CU, 0xDBBBC9D6U, 0xACBCF940U, 0x32D86CE3U, 0x45DF5C75U, 0xDCD60DCFU, 0xABD13D59U,
    0x26D930ACU, 0x51DE003AU, 0xC8D75180U, 0xBFD06116U, 0x21B4F4B5U, 0x56B3C423U, 0xCFBA9599U, 0xB8BDA50FU,
    0x2802B89EU, 0x5F058808U, 0xC60CD9B2U, 0xB10BE924U, 0x2F6F7C87U, 0x58684C11U, 0xC1611DABU, 0xB6662D3DU,
    0x76DC4190U, 0x01DB7106U, 0x98D220BCU, 0xEFD5102AU, 0x71B18589U, 0x06B6B51FU, 0x9FBFE4A5U, 0xE8B8D433U,
    0x7807C9A2U, 0x0F00F934U, 0x9609A88EU, 0xE10E9818U, 0x7F6A0DBBU, 0x086D3D2DU, 0x91646C97U, 0xE6635C01U,
    0x6B6B51F4U, 0x1C6C6162U, 0x856530D8U, 0xF262004EU, 0x6C0695EDU, 0x1B01A57BU, 0x8208F4C1U, 0xF50FC457U,
    0x65B0D9C6U, 0x12B7E950U, 0x8BBEB8EAU, 0xFCB9887CU, 0x62DD1DDFU, 0x15DA2D49U, 0x8CD37CF3U, 0xFBD44C65U,
    0x4DB26158U, 0x3AB551CEU, 0xA3BC0074U, 0xD4BB30E2U, 0x4ADFA541U, 0x3DD895D7U, 0xA4D1C46DU, 0xD3D6F4FBU,
    0x4369E96AU, 0x346ED9FCU, 0xAD678846U, 0xDA60B8D0U, 0x44042D73U, 0x33031DE5U, 0xAA0A4C5FU, 0xDD0D7CC9U,
    0x5005713CU, 0x270241AAU, 0xBE0B1010U, 0xC90C2086U, 0x5768B525U, 0x206F85B3U, 0xB966D409U, 0xCE61E49FU,
    0x5EDEF90EU, 0x29D9C998U, 0xB0D09822U, 0xC7D7A8B4U, 0x59B33D17U, 0x2EB40D81U, 0xB7BD5C3BU, 0xC0BA6CADU,
    0xEDB88320U, 0x9ABFB3B6U, 0x03B6E20CU, 0x74B1D29AU, 0xEAD54739U, 0x9DD277AFU, 0x04DB2615U, 0x73DC1683U,
    0xE3630B12U, 0x94643B84U, 0x0D6D6A3EU, 0x7A6A5AA8U, 0xE40ECF0BU, 0x9309FF9DU, 0x0A00AE27U, 0x7D079EB1U,
    0xF00F9344U, 0x8708A3D2U, 0x1E01F268U, 0x6906C2FEU, 0xF762575DU, 0x806567CBU, 0x196C3671U, 0x6E6B06E7U,
    0xFED41B76U, 0x89D32BE0U, 0x10DA7A5AU, 0x67DD4ACCU, 0xF9B9DF6FU, 0x8EBEEFF9U, 0x17B7BE43U, 0x60B08ED5U,
    0xD6D6A3E8U, 0xA1D1937EU, 0x38D8C2C4U, 0x4FDFF252U, 0xD1BB67F1U, 0xA6BC5767U, 0x3FB506DDU, 0x48B2364BU,
    0xD80D2BDAU, 0xAF0A1B4CU, 0x36034AF6U, 0x41047A60U, 0xDF60EFC3U, 0xA867DF55U, 0x316E8EEFU, 0x4669BE79U,
    0xCB61B38CU, 0xBC66831AU, 0x256FD2A0U, 0x5268E236U, 0xCC0C7795U, 0xBB0B4703U, 0x220216B9U, 0x5505262FU,
    0xC5BA3BBEU, 0xB2BD0B28U, 0x2BB45A92U, 0x5CB36A04U, 0xC2D7FFA7U, 0xB5D0CF31U, 0x2CD99E8BU, 0x5BDEAE1DU,
    0x9B64C2B0U, 0xEC63F226U, 0x756AA39CU, 0x026D930AU, 0x9C0906A9U, 0xEB0E363FU, 0x72076785U, 0x05005713U,
    0x95BF4A82U, 0xE2B87A14U, 0x7BB12BAEU, 0x0CB61B38U, 0x92D28E9BU, 0xE5D5BE0DU, 0x7CDCEFB7U, 0x0BDBDF21U,
    0x86D3D2D4U, 0xF1D4E242U, 0x68DDB3F8U, 0x1FDA836EU, 0x81BE16CDU, 0xF6B9265BU, 0x6FB077E1U, 0x18B74777U,
    0x88085AE6U, 0xFF0F6A70U, 0x66063BCAU, 0x11010B5CU, 0x8F659EFFU, 0xF862AE69U, 0x616BFFD3U, 0x166CCF45U,
    0xA00AE278U, 0xD70DD2EEU, 0x4E048354U, 0x3903B3C2U, 0xA7672661U, 0xD06016F7U, 0x4969474DU, 0x3E6E77DBU,
    0xAED16A4AU, 0xD9D65ADCU, 0x40DF0B66U, 0x37D83BF0U, 0xA9BCAE53U, 0xDEBB9EC5U, 0x47B2CF7FU, 0x30B5FFE9U,
    0xBDBDF21CU, 0xCABAC28AU, 0x53B39330U, 0x24B4A3A6U, 0xBAD03605U, 0xCDD70693U, 0x54DE5729U, 0x23D967BFU,
    0xB3667A2EU, 0xC4614AB8U, 0x5D681B02U, 0x2A6F2B94U, 0xB40BBE37U, 0xC30C8EA1U, 0x5A05DF1BU, 0x2D02EF8DU
};

void crc32_init(void) {
    /* No-op: Table is statically compiled and thread-safe */
}

uint32_t crc32_compute(const uint8_t *data, size_t length) {
    if (!data || length == 0) return 0;

    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < length; ++i) {
        crc = s_crc32_table[(crc ^ data[i]) & 0xFFU] ^ (crc >> 8);
    }
    return crc ^ 0xFFFFFFFFU;
}

uint32_t adler32_compute(const uint8_t *data, size_t length) {
    if (!data || length == 0) return 1;

    const uint32_t MOD_ADLER = 65521U;
    uint32_t a = 1U;
    uint32_t b = 0U;

    for (size_t i = 0; i < length; ++i) {
        a = (a + data[i]) % MOD_ADLER;
        b = (b + a) % MOD_ADLER;
    }
    return (b << 16) | a;
}

/* ========================================================================= */
/* 2. Explicit Field-by-Field Header Encoders & Decoders                     */
/* ========================================================================= */

ProtocolStatus packet_encode_header_profile_b(const ProfileBHeader *hdr, uint8_t *out_bytes) {
    if (!hdr || !out_bytes) return PROTOCOL_ERR_NULL_PTR;

    /* Offset 0..3: magic (0xAF534331 in little-endian: "1CSA") */
    out_bytes[0] = (uint8_t)(hdr->magic & 0xFFU);
    out_bytes[1] = (uint8_t)((hdr->magic >> 8) & 0xFFU);
    out_bytes[2] = (uint8_t)((hdr->magic >> 16) & 0xFFU);
    out_bytes[3] = (uint8_t)((hdr->magic >> 24) & 0xFFU);

    /* Offset 4: version */
    out_bytes[4] = hdr->version;

    /* Offset 5: msg_type */
    out_bytes[5] = hdr->msg_type;

    /* Offset 6..7: flags (uint16_t LE) - Full 16-bit status */
    out_bytes[6] = (uint8_t)(hdr->flags & 0xFFU);
    out_bytes[7] = (uint8_t)((hdr->flags >> 8) & 0xFFU);

    /* Offset 8..11: sequence_id (uint32_t LE) */
    out_bytes[8]  = (uint8_t)(hdr->sequence_id & 0xFFU);
    out_bytes[9]  = (uint8_t)((hdr->sequence_id >> 8) & 0xFFU);
    out_bytes[10] = (uint8_t)((hdr->sequence_id >> 16) & 0xFFU);
    out_bytes[11] = (uint8_t)((hdr->sequence_id >> 24) & 0xFFU);

    /* Offset 12..15: sample_rate_hz (uint32_t LE) */
    out_bytes[12] = (uint8_t)(hdr->sample_rate_hz & 0xFFU);
    out_bytes[13] = (uint8_t)((hdr->sample_rate_hz >> 8) & 0xFFU);
    out_bytes[14] = (uint8_t)((hdr->sample_rate_hz >> 16) & 0xFFU);
    out_bytes[15] = (uint8_t)((hdr->sample_rate_hz >> 24) & 0xFFU);

    /* Offset 16..23: timestamp_us (uint64_t LE) */
    out_bytes[16] = (uint8_t)(hdr->timestamp_us & 0xFFU);
    out_bytes[17] = (uint8_t)((hdr->timestamp_us >> 8) & 0xFFU);
    out_bytes[18] = (uint8_t)((hdr->timestamp_us >> 16) & 0xFFU);
    out_bytes[19] = (uint8_t)((hdr->timestamp_us >> 24) & 0xFFU);
    out_bytes[20] = (uint8_t)((hdr->timestamp_us >> 32) & 0xFFU);
    out_bytes[21] = (uint8_t)((hdr->timestamp_us >> 40) & 0xFFU);
    out_bytes[22] = (uint8_t)((hdr->timestamp_us >> 48) & 0xFFU);
    out_bytes[23] = (uint8_t)((hdr->timestamp_us >> 56) & 0xFFU);

    /* Offset 24..31: sample_index_start (uint64_t LE) */
    out_bytes[24] = (uint8_t)(hdr->sample_index_start & 0xFFU);
    out_bytes[25] = (uint8_t)((hdr->sample_index_start >> 8) & 0xFFU);
    out_bytes[26] = (uint8_t)((hdr->sample_index_start >> 16) & 0xFFU);
    out_bytes[27] = (uint8_t)((hdr->sample_index_start >> 24) & 0xFFU);
    out_bytes[28] = (uint8_t)((hdr->sample_index_start >> 32) & 0xFFU);
    out_bytes[29] = (uint8_t)((hdr->sample_index_start >> 40) & 0xFFU);
    out_bytes[30] = (uint8_t)((hdr->sample_index_start >> 48) & 0xFFU);
    out_bytes[31] = (uint8_t)((hdr->sample_index_start >> 56) & 0xFFU);

    /* Offset 32..33: sample_count (uint16_t LE) */
    out_bytes[32] = (uint8_t)(hdr->sample_count & 0xFFU);
    out_bytes[33] = (uint8_t)((hdr->sample_count >> 8) & 0xFFU);

    /* Offset 34: meaningful_bits */
    out_bytes[34] = hdr->meaningful_bits;

    /* Offset 35: container_bits */
    out_bytes[35] = hdr->container_bits;

    /* Offset 36: channels */
    out_bytes[36] = hdr->channels;

    /* Offset 37: encoding */
    out_bytes[37] = hdr->encoding;

    /* Offset 38..39: mcu_buffer_drops (uint16_t LE) */
    out_bytes[38] = (uint8_t)(hdr->mcu_buffer_drops & 0xFFU);
    out_bytes[39] = (uint8_t)((hdr->mcu_buffer_drops >> 8) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_header_profile_b(const uint8_t *in_bytes, ProfileBHeader *hdr) {
    if (!in_bytes || !hdr) return PROTOCOL_ERR_NULL_PTR;

    hdr->magic = (uint32_t)in_bytes[0] |
                 ((uint32_t)in_bytes[1] << 8) |
                 ((uint32_t)in_bytes[2] << 16) |
                 ((uint32_t)in_bytes[3] << 24);

    hdr->version = in_bytes[4];
    hdr->msg_type = in_bytes[5];

    /* Full 16-bit status flags decoding */
    hdr->flags = (uint16_t)in_bytes[6] | ((uint16_t)in_bytes[7] << 8);

    hdr->sequence_id = (uint32_t)in_bytes[8] |
                       ((uint32_t)in_bytes[9] << 8) |
                       ((uint32_t)in_bytes[10] << 16) |
                       ((uint32_t)in_bytes[11] << 24);

    hdr->sample_rate_hz = (uint32_t)in_bytes[12] |
                          ((uint32_t)in_bytes[13] << 8) |
                          ((uint32_t)in_bytes[14] << 16) |
                          ((uint32_t)in_bytes[15] << 24);

    hdr->timestamp_us = (uint64_t)in_bytes[16] |
                        ((uint64_t)in_bytes[17] << 8) |
                        ((uint64_t)in_bytes[18] << 16) |
                        ((uint64_t)in_bytes[19] << 24) |
                        ((uint64_t)in_bytes[20] << 32) |
                        ((uint64_t)in_bytes[21] << 40) |
                        ((uint64_t)in_bytes[22] << 48) |
                        ((uint64_t)in_bytes[23] << 56);

    hdr->sample_index_start = (uint64_t)in_bytes[24] |
                              ((uint64_t)in_bytes[25] << 8) |
                              ((uint64_t)in_bytes[26] << 16) |
                              ((uint64_t)in_bytes[27] << 24) |
                              ((uint64_t)in_bytes[28] << 32) |
                              ((uint64_t)in_bytes[29] << 40) |
                              ((uint64_t)in_bytes[30] << 48) |
                              ((uint64_t)in_bytes[31] << 56);

    hdr->sample_count = (uint16_t)in_bytes[32] | ((uint16_t)in_bytes[33] << 8);
    hdr->meaningful_bits = in_bytes[34];
    hdr->container_bits = in_bytes[35];
    hdr->channels = in_bytes[36];
    hdr->encoding = in_bytes[37];
    hdr->mcu_buffer_drops = (uint16_t)in_bytes[38] | ((uint16_t)in_bytes[39] << 8);

    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_header_profile_a(const ProfileAHeader *hdr, uint8_t *out_bytes) {
    if (!hdr || !out_bytes) return PROTOCOL_ERR_NULL_PTR;

    out_bytes[0] = hdr->magic[0];
    out_bytes[1] = hdr->magic[1];
    out_bytes[2] = hdr->version;
    out_bytes[3] = hdr->msg_type;

    out_bytes[4] = (uint8_t)(hdr->sequence & 0xFFU);
    out_bytes[5] = (uint8_t)((hdr->sequence >> 8) & 0xFFU);
    out_bytes[6] = (uint8_t)((hdr->sequence >> 16) & 0xFFU);
    out_bytes[7] = (uint8_t)((hdr->sequence >> 24) & 0xFFU);

    out_bytes[8]  = (uint8_t)(hdr->timestamp_us & 0xFFU);
    out_bytes[9]  = (uint8_t)((hdr->timestamp_us >> 8) & 0xFFU);
    out_bytes[10] = (uint8_t)((hdr->timestamp_us >> 16) & 0xFFU);
    out_bytes[11] = (uint8_t)((hdr->timestamp_us >> 24) & 0xFFU);

    out_bytes[12] = (uint8_t)(hdr->sample_count & 0xFFU);
    out_bytes[13] = (uint8_t)((hdr->sample_count >> 8) & 0xFFU);

    out_bytes[14] = (uint8_t)(hdr->flags & 0xFFU);
    out_bytes[15] = (uint8_t)((hdr->flags >> 8) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_header_profile_a(const uint8_t *in_bytes, ProfileAHeader *hdr) {
    if (!in_bytes || !hdr) return PROTOCOL_ERR_NULL_PTR;

    hdr->magic[0] = in_bytes[0];
    hdr->magic[1] = in_bytes[1];
    hdr->version = in_bytes[2];
    hdr->msg_type = in_bytes[3];

    hdr->sequence = (uint32_t)in_bytes[4] |
                    ((uint32_t)in_bytes[5] << 8) |
                    ((uint32_t)in_bytes[6] << 16) |
                    ((uint32_t)in_bytes[7] << 24);

    hdr->timestamp_us = (uint32_t)in_bytes[8] |
                        ((uint32_t)in_bytes[9] << 8) |
                        ((uint32_t)in_bytes[10] << 16) |
                        ((uint32_t)in_bytes[11] << 24);

    hdr->sample_count = (uint16_t)in_bytes[12] | ((uint16_t)in_bytes[13] << 8);
    hdr->flags = (uint16_t)in_bytes[14] | ((uint16_t)in_bytes[15] << 8);

    return PROTOCOL_OK;
}

/* ========================================================================= */
/* 3. Control Payload Encoders & Decoders                                    */
/* ========================================================================= */

ProtocolStatus packet_encode_status_telemetry(const StatusTelemetryPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;

    /* Offset 0..7: session_id (u64 LE) */
    for (int i = 0; i < 8; ++i) b[0 + i] = (uint8_t)((p->session_id >> (i * 8)) & 0xFFU);
    /* Offset 8..15: generated_samples (u64 LE) */
    for (int i = 0; i < 8; ++i) b[8 + i] = (uint8_t)((p->generated_samples >> (i * 8)) & 0xFFU);
    /* Offset 16..23: fully_queued_samples (u64 LE) */
    for (int i = 0; i < 8; ++i) b[16 + i] = (uint8_t)((p->fully_queued_samples >> (i * 8)) & 0xFFU);
    /* Offset 24..31: dropped_samples (u64 LE) */
    for (int i = 0; i < 8; ++i) b[24 + i] = (uint8_t)((p->dropped_samples >> (i * 8)) & 0xFFU);
    /* Offset 32..35: audio_frames_queued (u32 LE) */
    for (int i = 0; i < 4; ++i) b[32 + i] = (uint8_t)((p->audio_frames_queued >> (i * 8)) & 0xFFU);
    /* Offset 36..39: dma_overflow_events (u32 LE) */
    for (int i = 0; i < 4; ++i) b[36 + i] = (uint8_t)((p->dma_overflow_events >> (i * 8)) & 0xFFU);
    /* Offset 40..43: ring_overflow_events (u32 LE) */
    for (int i = 0; i < 4; ++i) b[40 + i] = (uint8_t)((p->ring_overflow_events >> (i * 8)) & 0xFFU);
    /* Offset 44..47: usb_partial_write_events (u32 LE) */
    for (int i = 0; i < 4; ++i) b[44 + i] = (uint8_t)((p->usb_partial_write_events >> (i * 8)) & 0xFFU);
    /* Offset 48..51: usb_timeout_events (u32 LE) */
    for (int i = 0; i < 4; ++i) b[48 + i] = (uint8_t)((p->usb_timeout_events >> (i * 8)) & 0xFFU);
    /* Offset 52..55: usb_disconnect_events (u32 LE) */
    for (int i = 0; i < 4; ++i) b[52 + i] = (uint8_t)((p->usb_disconnect_events >> (i * 8)) & 0xFFU);
    /* Offset 56..63: audio_bytes_queued (u64 LE) */
    for (int i = 0; i < 8; ++i) b[56 + i] = (uint8_t)((p->audio_bytes_queued >> (i * 8)) & 0xFFU);
    /* Offset 64..67: stop_reason (u32 LE) */
    for (int i = 0; i < 4; ++i) b[64 + i] = (uint8_t)((p->stop_reason >> (i * 8)) & 0xFFU);
    /* Offset 68..71: error_code (u32 LE) */
    for (int i = 0; i < 4; ++i) b[68 + i] = (uint8_t)((p->error_code >> (i * 8)) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_status_telemetry(const uint8_t *b, StatusTelemetryPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;

    p->session_id = 0;
    for (int i = 0; i < 8; ++i) p->session_id |= ((uint64_t)b[0 + i]) << (i * 8);

    p->generated_samples = 0;
    for (int i = 0; i < 8; ++i) p->generated_samples |= ((uint64_t)b[8 + i]) << (i * 8);

    p->fully_queued_samples = 0;
    for (int i = 0; i < 8; ++i) p->fully_queued_samples |= ((uint64_t)b[16 + i]) << (i * 8);

    p->dropped_samples = 0;
    for (int i = 0; i < 8; ++i) p->dropped_samples |= ((uint64_t)b[24 + i]) << (i * 8);

    p->audio_frames_queued = (uint32_t)b[32] | ((uint32_t)b[33] << 8) | ((uint32_t)b[34] << 16) | ((uint32_t)b[35] << 24);
    p->dma_overflow_events = (uint32_t)b[36] | ((uint32_t)b[37] << 8) | ((uint32_t)b[38] << 16) | ((uint32_t)b[39] << 24);
    p->ring_overflow_events = (uint32_t)b[40] | ((uint32_t)b[41] << 8) | ((uint32_t)b[42] << 16) | ((uint32_t)b[43] << 24);
    p->usb_partial_write_events = (uint32_t)b[44] | ((uint32_t)b[45] << 8) | ((uint32_t)b[46] << 16) | ((uint32_t)b[47] << 24);
    p->usb_timeout_events = (uint32_t)b[48] | ((uint32_t)b[49] << 8) | ((uint32_t)b[50] << 16) | ((uint32_t)b[51] << 24);
    p->usb_disconnect_events = (uint32_t)b[52] | ((uint32_t)b[53] << 8) | ((uint32_t)b[54] << 16) | ((uint32_t)b[55] << 24);

    p->audio_bytes_queued = 0;
    for (int i = 0; i < 8; ++i) p->audio_bytes_queued |= ((uint64_t)b[56 + i]) << (i * 8);

    p->stop_reason = (uint32_t)b[64] | ((uint32_t)b[65] << 8) | ((uint32_t)b[66] << 16) | ((uint32_t)b[67] << 24);
    p->error_code = (uint32_t)b[68] | ((uint32_t)b[69] << 8) | ((uint32_t)b[70] << 16) | ((uint32_t)b[71] << 24);

    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_start_req(const StartReqPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;

    b[0] = (uint8_t)(p->sample_rate_hz & 0xFFU);
    b[1] = (uint8_t)((p->sample_rate_hz >> 8) & 0xFFU);
    b[2] = (uint8_t)((p->sample_rate_hz >> 16) & 0xFFU);
    b[3] = (uint8_t)((p->sample_rate_hz >> 24) & 0xFFU);

    for (int i = 0; i < 8; ++i) b[4 + i] = (uint8_t)((p->target_samples >> (i * 8)) & 0xFFU);

    b[12] = p->source_mode;
    b[13] = p->encoding;
    b[14] = p->channels;
    b[15] = p->profile_id;

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_start_req(const uint8_t *b, StartReqPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;

    p->sample_rate_hz = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    p->target_samples = 0;
    for (int i = 0; i < 8; ++i) p->target_samples |= ((uint64_t)b[4 + i]) << (i * 8);
    p->source_mode = b[12];
    p->encoding = b[13];
    p->channels = b[14];
    p->profile_id = b[15];

    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_start_ack(const StartAckPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;

    for (int i = 0; i < 8; ++i) b[0 + i] = (uint8_t)((p->session_id >> (i * 8)) & 0xFFU);
    for (int i = 0; i < 8; ++i) b[8 + i] = (uint8_t)((p->session_reference_time_us >> (i * 8)) & 0xFFU);

    b[16] = (uint8_t)(p->accepted_sample_rate_hz & 0xFFU);
    b[17] = (uint8_t)((p->accepted_sample_rate_hz >> 8) & 0xFFU);
    b[18] = (uint8_t)((p->accepted_sample_rate_hz >> 16) & 0xFFU);
    b[19] = (uint8_t)((p->accepted_sample_rate_hz >> 24) & 0xFFU);

    for (int i = 0; i < 8; ++i) b[20 + i] = (uint8_t)((p->accepted_target_samples >> (i * 8)) & 0xFFU);

    b[28] = p->accepted_source_mode;
    b[29] = p->encoding;
    b[30] = p->channels;
    b[31] = p->profile_id;

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_start_ack(const uint8_t *b, StartAckPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;

    p->session_id = 0;
    for (int i = 0; i < 8; ++i) p->session_id |= ((uint64_t)b[0 + i]) << (i * 8);

    p->session_reference_time_us = 0;
    for (int i = 0; i < 8; ++i) p->session_reference_time_us |= ((uint64_t)b[8 + i]) << (i * 8);

    p->accepted_sample_rate_hz = (uint32_t)b[16] | ((uint32_t)b[17] << 8) | ((uint32_t)b[18] << 16) | ((uint32_t)b[19] << 24);

    p->accepted_target_samples = 0;
    for (int i = 0; i < 8; ++i) p->accepted_target_samples |= ((uint64_t)b[20 + i]) << (i * 8);

    p->accepted_source_mode = b[28];
    p->encoding = b[29];
    p->channels = b[30];
    p->profile_id = b[31];

    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_stop_req(const StopReqPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;
    for (int i = 0; i < 8; ++i) b[i] = (uint8_t)((p->session_id >> (i * 8)) & 0xFFU);
    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_stop_req(const uint8_t *b, StopReqPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;
    p->session_id = 0;
    for (int i = 0; i < 8; ++i) p->session_id |= ((uint64_t)b[i]) << (i * 8);
    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_error(const ErrorPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;
    b[0] = (uint8_t)(p->error_code & 0xFFU);
    b[1] = (uint8_t)((p->error_code >> 8) & 0xFFU);
    b[2] = (uint8_t)((p->error_code >> 16) & 0xFFU);
    b[3] = (uint8_t)((p->error_code >> 24) & 0xFFU);

    b[4] = (uint8_t)(p->error_context & 0xFFU);
    b[5] = (uint8_t)((p->error_context >> 8) & 0xFFU);
    b[6] = (uint8_t)((p->error_context >> 16) & 0xFFU);
    b[7] = (uint8_t)((p->error_context >> 24) & 0xFFU);
    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_error(const uint8_t *b, ErrorPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;
    p->error_code = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    p->error_context = (uint32_t)b[4] | ((uint32_t)b[5] << 8) | ((uint32_t)b[6] << 16) | ((uint32_t)b[7] << 24);
    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_hello_req(const HelloReqPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;
    b[0] = (uint8_t)(p->host_nonce & 0xFFU);
    b[1] = (uint8_t)((p->host_nonce >> 8) & 0xFFU);
    b[2] = (uint8_t)((p->host_nonce >> 16) & 0xFFU);
    b[3] = (uint8_t)((p->host_nonce >> 24) & 0xFFU);
    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_hello_req(const uint8_t *b, HelloReqPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;
    p->host_nonce = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return PROTOCOL_OK;
}

ProtocolStatus packet_encode_hello_ack(const HelloAckPayload *p, uint8_t *b) {
    if (!p || !b) return PROTOCOL_ERR_NULL_PTR;

    b[0] = (uint8_t)(p->nonce_echo & 0xFFU);
    b[1] = (uint8_t)((p->nonce_echo >> 8) & 0xFFU);
    b[2] = (uint8_t)((p->nonce_echo >> 16) & 0xFFU);
    b[3] = (uint8_t)((p->nonce_echo >> 24) & 0xFFU);

    b[4] = p->protocol_version_major;
    b[5] = p->protocol_version_minor;
    b[6] = p->supported_profiles_mask;
    b[7] = p->supported_encodings_mask;

    b[8]  = (uint8_t)(p->hardware_sample_rate_hz & 0xFFU);
    b[9]  = (uint8_t)((p->hardware_sample_rate_hz >> 8) & 0xFFU);
    b[10] = (uint8_t)((p->hardware_sample_rate_hz >> 16) & 0xFFU);
    b[11] = (uint8_t)((p->hardware_sample_rate_hz >> 24) & 0xFFU);

    b[12] = p->firmware_version_major;
    b[13] = p->firmware_version_minor;
    b[14] = p->firmware_version_patch;
    b[15] = p->reserved;

    b[16] = (uint8_t)(p->max_frame_samples & 0xFFU);
    b[17] = (uint8_t)((p->max_frame_samples >> 8) & 0xFFU);

    b[18] = (uint8_t)(p->capability_flags & 0xFFU);
    b[19] = (uint8_t)((p->capability_flags >> 8) & 0xFFU);

    b[20] = (uint8_t)(p->device_uid_low & 0xFFU);
    b[21] = (uint8_t)((p->device_uid_low >> 8) & 0xFFU);
    b[22] = (uint8_t)((p->device_uid_low >> 16) & 0xFFU);
    b[23] = (uint8_t)((p->device_uid_low >> 24) & 0xFFU);

    return PROTOCOL_OK;
}

ProtocolStatus packet_decode_hello_ack(const uint8_t *b, HelloAckPayload *p) {
    if (!b || !p) return PROTOCOL_ERR_NULL_PTR;

    p->nonce_echo = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    p->protocol_version_major = b[4];
    p->protocol_version_minor = b[5];
    p->supported_profiles_mask = b[6];
    p->supported_encodings_mask = b[7];
    p->hardware_sample_rate_hz = (uint32_t)b[8] | ((uint32_t)b[9] << 8) | ((uint32_t)b[10] << 16) | ((uint32_t)b[11] << 24);
    p->firmware_version_major = b[12];
    p->firmware_version_minor = b[13];
    p->firmware_version_patch = b[14];
    p->reserved = b[15];
    p->max_frame_samples = (uint16_t)b[16] | ((uint16_t)b[17] << 8);
    p->capability_flags = (uint16_t)b[18] | ((uint16_t)b[19] << 8);
    p->device_uid_low = (uint32_t)b[20] | ((uint32_t)b[21] << 8) | ((uint32_t)b[22] << 16) | ((uint32_t)b[23] << 24);

    return PROTOCOL_OK;
}

/* ========================================================================= */
/* 4. Packet Builders                                                        */
/* ========================================================================= */

ProtocolStatus packet_build_profile_a(
    uint32_t sequence,
    uint32_t timestamp_us,
    const int32_t *samples,
    uint16_t count,
    uint16_t flags,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!samples || !out_buffer || !out_size) return PROTOCOL_ERR_NULL_PTR;
    size_t payload_bytes = (size_t)count * sizeof(int32_t);
    size_t total_size = PROFILE_A_HEADER_SIZE + payload_bytes + PROFILE_A_TRAILER_SIZE;

    if (max_buffer_size < total_size) return PROTOCOL_ERR_OVERFLOW;

    ProfileAHeader header;
    header.magic[0] = PROFILE_A_MAGIC_BYTE0;
    header.magic[1] = PROFILE_A_MAGIC_BYTE1;
    header.version = 1;
    header.msg_type = MSG_TYPE_AUDIO_DATA;
    header.sequence = sequence;
    header.timestamp_us = timestamp_us;
    header.sample_count = count;
    header.flags = flags;

    packet_encode_header_profile_a(&header, out_buffer);

    /* Serialize samples little-endian without type punning */
    uint8_t *payload_ptr = out_buffer + PROFILE_A_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        int32_t s = samples[i];
        uint32_t u = (s < 0) ? (uint32_t)((int64_t)s + 0x100000000LL) : (uint32_t)s;
        payload_ptr[i * 4 + 0] = (uint8_t)(u & 0xFFU);
        payload_ptr[i * 4 + 1] = (uint8_t)((u >> 8) & 0xFFU);
        payload_ptr[i * 4 + 2] = (uint8_t)((u >> 16) & 0xFFU);
        payload_ptr[i * 4 + 3] = (uint8_t)((u >> 24) & 0xFFU);
    }

    /* Compute CRC-16 over Header + Payload */
    size_t body_len = PROFILE_A_HEADER_SIZE + payload_bytes;
    uint16_t crc = crc16_ccitt_compute(out_buffer, body_len, 0xFFFFU);

    uint8_t *trailer_ptr = out_buffer + body_len;
    trailer_ptr[0] = (uint8_t)(crc & 0xFFU);
    trailer_ptr[1] = (uint8_t)((crc >> 8) & 0xFFU);

    *out_size = total_size;
    return PROTOCOL_OK;
}

ProtocolStatus packet_build_profile_b(
    uint32_t sequence_id,
    uint64_t timestamp_us,
    uint64_t sample_index_start,
    const int32_t *samples,
    uint16_t count,
    uint32_t sample_rate_hz,
    uint8_t meaningful_bits,
    uint16_t flags,                     /* Full 16-bit flags */
    uint8_t encoding,
    uint16_t mcu_drops,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!samples || !out_buffer || !out_size) return PROTOCOL_ERR_NULL_PTR;
    size_t payload_bytes = (size_t)count * sizeof(int32_t);
    size_t total_size = PROFILE_B_HEADER_SIZE + payload_bytes + PROFILE_B_TRAILER_SIZE;

    if (max_buffer_size < total_size) return PROTOCOL_ERR_OVERFLOW;

    ProfileBHeader header;
    header.magic = PROFILE_B_MAGIC_U32;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.msg_type = MSG_TYPE_AUDIO_DATA;
    header.flags = flags;               /* Store full 16-bit flags without truncation */
    header.sequence_id = sequence_id;
    header.sample_rate_hz = sample_rate_hz;
    header.timestamp_us = timestamp_us;
    header.sample_index_start = sample_index_start;
    header.sample_count = count;
    header.meaningful_bits = meaningful_bits;
    header.container_bits = NOMINAL_CONTAINER_BITS;
    header.channels = NOMINAL_CHANNELS;
    header.encoding = encoding;
    header.mcu_buffer_drops = mcu_drops;

    packet_encode_header_profile_b(&header, out_buffer);

    /* Serialize samples little-endian without type punning */
    uint8_t *payload_ptr = out_buffer + PROFILE_B_HEADER_SIZE;
    for (size_t i = 0; i < count; ++i) {
        int32_t s = samples[i];
        uint32_t u = (s < 0) ? (uint32_t)((int64_t)s + 0x100000000LL) : (uint32_t)s;
        payload_ptr[i * 4 + 0] = (uint8_t)(u & 0xFFU);
        payload_ptr[i * 4 + 1] = (uint8_t)((u >> 8) & 0xFFU);
        payload_ptr[i * 4 + 2] = (uint8_t)((u >> 16) & 0xFFU);
        payload_ptr[i * 4 + 3] = (uint8_t)((u >> 24) & 0xFFU);
    }

    /* Compute CRC-32 over Header + Payload */
    size_t body_len = PROFILE_B_HEADER_SIZE + payload_bytes;
    uint32_t crc = crc32_compute(out_buffer, body_len);

    uint8_t *trailer_ptr = out_buffer + body_len;
    trailer_ptr[0] = (uint8_t)(crc & 0xFFU);
    trailer_ptr[1] = (uint8_t)((crc >> 8) & 0xFFU);
    trailer_ptr[2] = (uint8_t)((crc >> 16) & 0xFFU);
    trailer_ptr[3] = (uint8_t)((crc >> 24) & 0xFFU);

    *out_size = total_size;
    return PROTOCOL_OK;
}

/* Helper to build a control packet with 40B Profile B header + payload + 4B CRC32 */
static ProtocolStatus build_control_packet(
    uint8_t msg_type,
    uint16_t flags,
    uint32_t sequence_id,
    uint64_t timestamp_us,
    const uint8_t *payload_bytes,
    size_t payload_len,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload_bytes || !out_buffer || !out_size) return PROTOCOL_ERR_NULL_PTR;
    size_t total_size = PROFILE_B_HEADER_SIZE + payload_len + PROFILE_B_TRAILER_SIZE;
    if (max_buffer_size < total_size) return PROTOCOL_ERR_OVERFLOW;

    ProfileBHeader header;
    header.magic = PROFILE_B_MAGIC_U32;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.msg_type = msg_type;
    header.flags = flags;
    header.sequence_id = sequence_id;
    header.sample_rate_hz = NOMINAL_SAMPLE_RATE_HZ;
    header.timestamp_us = timestamp_us;
    header.sample_index_start = 0;
    header.sample_count = 0;            /* CRITICAL: MUST BE ZERO for all control messages */
    header.meaningful_bits = NOMINAL_MEANINGFUL_BITS;
    header.container_bits = NOMINAL_CONTAINER_BITS;
    header.channels = NOMINAL_CHANNELS;
    header.encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED;
    header.mcu_buffer_drops = 0;

    packet_encode_header_profile_b(&header, out_buffer);
    memcpy(out_buffer + PROFILE_B_HEADER_SIZE, payload_bytes, payload_len);

    size_t body_len = PROFILE_B_HEADER_SIZE + payload_len;
    uint32_t crc = crc32_compute(out_buffer, body_len);

    uint8_t *trailer_ptr = out_buffer + body_len;
    trailer_ptr[0] = (uint8_t)(crc & 0xFFU);
    trailer_ptr[1] = (uint8_t)((crc >> 8) & 0xFFU);
    trailer_ptr[2] = (uint8_t)((crc >> 16) & 0xFFU);
    trailer_ptr[3] = (uint8_t)((crc >> 24) & 0xFFU);

    *out_size = total_size;
    return PROTOCOL_OK;
}

ProtocolStatus packet_build_hello_req(
    uint32_t host_nonce,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    HelloReqPayload p = { host_nonce };
    uint8_t payload[HELLO_REQ_PAYLOAD_SIZE];
    packet_encode_hello_req(&p, payload);
    return build_control_packet(MSG_TYPE_HELLO_REQ, FRAME_FLAG_TIMESTAMP_VALID, 0, 0, payload, HELLO_REQ_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_hello_ack(
    const HelloAckPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload) return PROTOCOL_ERR_NULL_PTR;
    uint8_t b[HELLO_ACK_PAYLOAD_SIZE];
    packet_encode_hello_ack(payload, b);
    return build_control_packet(MSG_TYPE_HELLO_ACK, FRAME_FLAG_TIMESTAMP_VALID, 0, 0, b, HELLO_ACK_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_start_req(
    const StartReqPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload) return PROTOCOL_ERR_NULL_PTR;
    uint8_t b[START_REQ_PAYLOAD_SIZE];
    packet_encode_start_req(payload, b);
    return build_control_packet(MSG_TYPE_STREAM_START_REQ, FRAME_FLAG_TIMESTAMP_VALID, 0, 0, b, START_REQ_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_start_ack(
    const StartAckPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload) return PROTOCOL_ERR_NULL_PTR;
    uint8_t b[START_ACK_PAYLOAD_SIZE];
    packet_encode_start_ack(payload, b);
    return build_control_packet(MSG_TYPE_STREAM_START_ACK, FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SESSION_ACTIVE, 0, payload->session_reference_time_us, b, START_ACK_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_stop_req(
    uint64_t session_id,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    StopReqPayload p = { session_id };
    uint8_t b[STOP_REQ_PAYLOAD_SIZE];
    packet_encode_stop_req(&p, b);
    return build_control_packet(MSG_TYPE_STREAM_STOP_REQ, FRAME_FLAG_TIMESTAMP_VALID, 0, 0, b, STOP_REQ_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_stop_ack(
    const StatusTelemetryPayload *payload,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload) return PROTOCOL_ERR_NULL_PTR;
    uint8_t b[STOP_ACK_PAYLOAD_SIZE];
    packet_encode_status_telemetry(payload, b);
    return build_control_packet(MSG_TYPE_STREAM_STOP_ACK, FRAME_FLAG_TIMESTAMP_VALID, payload->audio_frames_queued, 0, b, STOP_ACK_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_status(
    const StatusTelemetryPayload *payload,
    uint32_t sequence_id,
    uint64_t timestamp_us,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    if (!payload) return PROTOCOL_ERR_NULL_PTR;
    uint8_t b[STATUS_TELEMETRY_PAYLOAD_SIZE];
    packet_encode_status_telemetry(payload, b);
    return build_control_packet(MSG_TYPE_HEARTBEAT_STATUS, FRAME_FLAG_TIMESTAMP_VALID | FRAME_FLAG_SESSION_ACTIVE, sequence_id, timestamp_us, b, STATUS_TELEMETRY_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

ProtocolStatus packet_build_error(
    uint32_t error_code,
    uint32_t error_context,
    uint8_t *out_buffer,
    size_t max_buffer_size,
    size_t *out_size
) {
    ErrorPayload p = { error_code, error_context };
    uint8_t b[ERROR_PAYLOAD_SIZE];
    packet_encode_error(&p, b);
    return build_control_packet(MSG_TYPE_ERROR_NOTIFICATION, FRAME_FLAG_TIMESTAMP_VALID, 0, 0, b, ERROR_PAYLOAD_SIZE, out_buffer, max_buffer_size, out_size);
}

/* ========================================================================= */
/* 5. Streaming Parser                                                       */
/* ========================================================================= */

ProtocolStatus parser_init(StreamPacketParser *parser) {
    if (!parser) return PROTOCOL_ERR_NULL_PTR;
    memset(parser, 0, sizeof(StreamPacketParser));
    return PROTOCOL_OK;
}

ProtocolStatus parser_reset(StreamPacketParser *parser) {
    if (!parser) return PROTOCOL_ERR_NULL_PTR;
    memset(parser, 0, sizeof(StreamPacketParser));
    return PROTOCOL_OK;
}

ProtocolStatus parser_feed_bytes(
    StreamPacketParser *parser,
    const uint8_t *in_bytes,
    size_t in_len,
    DecodedFrame *out_frames,
    size_t max_frames,
    size_t *frames_emitted
) {
    if (!parser || !out_frames || !frames_emitted) return PROTOCOL_ERR_NULL_PTR;
    *frames_emitted = 0;

    if (in_bytes && in_len > 0) {
        if (parser->buffer_len + in_len > sizeof(parser->buffer)) {
            /* Input would overflow internal parse buffer */
            return PROTOCOL_ERR_BUFFER_FULL;
        }
        memcpy(parser->buffer + parser->buffer_len, in_bytes, in_len);
        parser->buffer_len += in_len;
    }

    while (*frames_emitted < max_frames) {
        if (parser->buffer_len < 4) {
            /* Need at least 4 bytes to check sync magic */
            break;
        }

        /* 1. Search for sync magic (Profile B 4B or Profile A 2B) */
        size_t sync_idx = 0;
        bool found_profile_b = false;
        bool found_profile_a = false;

        for (size_t i = 0; i <= parser->buffer_len - 2; ++i) {
            /* Check Profile B magic: 0x31, 0x43, 0x53, 0xAF */
            if (i <= parser->buffer_len - 4) {
                if (parser->buffer[i + 0] == PROFILE_B_MAGIC_BYTE0 &&
                    parser->buffer[i + 1] == PROFILE_B_MAGIC_BYTE1 &&
                    parser->buffer[i + 2] == PROFILE_B_MAGIC_BYTE2 &&
                    parser->buffer[i + 3] == PROFILE_B_MAGIC_BYTE3) {
                    sync_idx = i;
                    found_profile_b = true;
                    break;
                }
            }

            /* Check Profile A magic: 0x55, 0xAA */
            if (parser->buffer[i + 0] == PROFILE_A_MAGIC_BYTE0 &&
                parser->buffer[i + 1] == PROFILE_A_MAGIC_BYTE1) {
                sync_idx = i;
                found_profile_a = true;
                break;
            }
        }

        if (!found_profile_b && !found_profile_a) {
            /* No magic found in buffer: preserve trailing 3 bytes for boundary matches */
            if (parser->buffer_len > 3) {
                size_t discarded = parser->buffer_len - 3;
                parser->garbage_bytes_discarded += (uint32_t)discarded;
                memmove(parser->buffer, parser->buffer + discarded, 3);
                parser->buffer_len = 3;
            }
            break;
        }

        /* Discard any pre-sync garbage bytes */
        if (sync_idx > 0) {
            parser->garbage_bytes_discarded += (uint32_t)sync_idx;
            memmove(parser->buffer, parser->buffer + sync_idx, parser->buffer_len - sync_idx);
            parser->buffer_len -= sync_idx;
        }

        /* 2. Process discovered frame */
        if (found_profile_b) {
            if (parser->buffer_len < PROFILE_B_HEADER_SIZE) {
                /* Incomplete header: wait for subsequent bytes */
                break;
            }

            ProfileBHeader header;
            packet_decode_header_profile_b(parser->buffer, &header);

            if (header.version != PROTOCOL_VERSION_MAJOR) {
                parser->malformed_headers++;
                memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                parser->buffer_len -= 4;
                continue;
            }

            size_t payload_bytes = 0;
            if (header.msg_type == MSG_TYPE_AUDIO_DATA) {
                if (header.sample_count == 0 || header.sample_count > 1024) {
                    parser->malformed_headers++;
                    memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                    parser->buffer_len -= 4;
                    continue;
                }
                payload_bytes = (size_t)header.sample_count * sizeof(int32_t);
            } else {
                /* Control frames MUST have sample_count == 0 */
                if (header.sample_count != 0) {
                    parser->malformed_headers++;
                    memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                    parser->buffer_len -= 4;
                    continue;
                }

                switch (header.msg_type) {
                    case MSG_TYPE_HEARTBEAT_STATUS:   payload_bytes = STATUS_TELEMETRY_PAYLOAD_SIZE; break;
                    case MSG_TYPE_STREAM_START_REQ:   payload_bytes = START_REQ_PAYLOAD_SIZE; break;
                    case MSG_TYPE_STREAM_START_ACK:   payload_bytes = START_ACK_PAYLOAD_SIZE; break;
                    case MSG_TYPE_STREAM_STOP_REQ:    payload_bytes = STOP_REQ_PAYLOAD_SIZE; break;
                    case MSG_TYPE_STREAM_STOP_ACK:    payload_bytes = STOP_ACK_PAYLOAD_SIZE; break;
                    case MSG_TYPE_ERROR_NOTIFICATION: payload_bytes = ERROR_PAYLOAD_SIZE; break;
                    case MSG_TYPE_HELLO_REQ:          payload_bytes = HELLO_REQ_PAYLOAD_SIZE; break;
                    case MSG_TYPE_HELLO_ACK:          payload_bytes = HELLO_ACK_PAYLOAD_SIZE; break;
                    case MSG_TYPE_CALIBRATION_TONE:   payload_bytes = 0; break;
                    default:
                        /* Unknown opcode: reject safely */
                        parser->malformed_headers++;
                        memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                        parser->buffer_len -= 4;
                        continue;
                }
            }

            size_t total_frame_len = PROFILE_B_HEADER_SIZE + payload_bytes + PROFILE_B_TRAILER_SIZE;
            if (parser->buffer_len < total_frame_len) {
                /* Incomplete frame payload: wait for subsequent bytes */
                break;
            }

            /* Extract CRC-32 trailer */
            const uint8_t *trailer_ptr = parser->buffer + PROFILE_B_HEADER_SIZE + payload_bytes;
            uint32_t crc_received = (uint32_t)trailer_ptr[0] |
                                    ((uint32_t)trailer_ptr[1] << 8) |
                                    ((uint32_t)trailer_ptr[2] << 16) |
                                    ((uint32_t)trailer_ptr[3] << 24);

            uint32_t crc_computed = crc32_compute(parser->buffer, PROFILE_B_HEADER_SIZE + payload_bytes);

            if (crc_received != crc_computed) {
                parser->crc_errors++;
                memmove(parser->buffer, parser->buffer + 4, parser->buffer_len - 4);
                parser->buffer_len -= 4;
                continue;
            }

            DecodedFrame *df = &out_frames[*frames_emitted];
            df->msg_type = header.msg_type;
            df->sequence_id = header.sequence_id;
            df->timestamp_us = header.timestamp_us;
            df->sample_index_start = header.sample_index_start;
            df->sample_count = header.sample_count;
            df->sample_rate_hz = header.sample_rate_hz;
            df->meaningful_bits = header.meaningful_bits;
            df->flags = header.flags;           /* Full 16-bit flags */
            df->encoding = header.encoding;
            df->mcu_buffer_drops = header.mcu_buffer_drops;
            df->crc_ok = true;
            df->is_profile_b = true;

            if (header.msg_type == MSG_TYPE_AUDIO_DATA) {
                const uint8_t *payload_ptr = parser->buffer + PROFILE_B_HEADER_SIZE;
                for (size_t s = 0; s < header.sample_count; ++s) {
                    uint32_t u = (uint32_t)payload_ptr[s * 4 + 0] |
                                 ((uint32_t)payload_ptr[s * 4 + 1] << 8) |
                                 ((uint32_t)payload_ptr[s * 4 + 2] << 16) |
                                 ((uint32_t)payload_ptr[s * 4 + 3] << 24);
                    int32_t val = (u > 0x7FFFFFFFU) ? (int32_t)(u - 0x100000000LL) : (int32_t)u;
                    df->samples[s] = val;
                }
                df->control_payload_len = 0;
                update_stream_quality_stats(&parser->quality_stats, df);
            } else {
                /* Control message: copy payload bytes into control_payload scratch */
                size_t copy_len = (payload_bytes <= sizeof(df->control_payload)) ? payload_bytes : sizeof(df->control_payload);
                memcpy(df->control_payload, parser->buffer + PROFILE_B_HEADER_SIZE, copy_len);
                df->control_payload_len = copy_len;
                /* Control frames MUST NOT update audio quality stats */
            }

            /* Consume frame from buffer */
            memmove(parser->buffer, parser->buffer + total_frame_len, parser->buffer_len - total_frame_len);
            parser->buffer_len -= total_frame_len;
            parser->valid_packets_parsed++;
            (*frames_emitted)++;

        } else {
            /* Found Profile A (Historical 16-byte header) */
            if (parser->buffer_len < PROFILE_A_HEADER_SIZE) {
                break;
            }

            ProfileAHeader header;
            packet_decode_header_profile_a(parser->buffer, &header);

            if (header.version != 1 || header.sample_count == 0 || header.sample_count > 1024) {
                parser->malformed_headers++;
                memmove(parser->buffer, parser->buffer + 2, parser->buffer_len - 2);
                parser->buffer_len -= 2;
                continue;
            }

            size_t payload_bytes = (size_t)header.sample_count * sizeof(int32_t);
            size_t total_frame_len = PROFILE_A_HEADER_SIZE + payload_bytes + PROFILE_A_TRAILER_SIZE;

            if (parser->buffer_len < total_frame_len) {
                break;
            }

            const uint8_t *trailer_ptr = parser->buffer + PROFILE_A_HEADER_SIZE + payload_bytes;
            uint16_t crc_received = (uint16_t)trailer_ptr[0] | ((uint16_t)trailer_ptr[1] << 8);
            uint16_t crc_computed = crc16_ccitt_compute(parser->buffer, PROFILE_A_HEADER_SIZE + payload_bytes, 0xFFFFU);

            if (crc_received != crc_computed) {
                parser->crc_errors++;
                memmove(parser->buffer, parser->buffer + 2, parser->buffer_len - 2);
                parser->buffer_len -= 2;
                continue;
            }

            DecodedFrame *df = &out_frames[*frames_emitted];
            df->msg_type = MSG_TYPE_AUDIO_DATA;
            df->sequence_id = header.sequence;
            df->timestamp_us = header.timestamp_us;
            df->sample_index_start = 0;
            df->sample_count = header.sample_count;
            df->sample_rate_hz = NOMINAL_SAMPLE_RATE_HZ;
            df->meaningful_bits = NOMINAL_MEANINGFUL_BITS;
            df->flags = header.flags;
            df->encoding = ENCODING_SIGNED_PCM_LSB_ALIGNED;
            df->mcu_buffer_drops = 0;
            df->crc_ok = true;
            df->is_profile_b = false;
            df->control_payload_len = 0;

            const uint8_t *payload_ptr = parser->buffer + PROFILE_A_HEADER_SIZE;
            for (size_t s = 0; s < header.sample_count; ++s) {
                uint32_t u = (uint32_t)payload_ptr[s * 4 + 0] |
                             ((uint32_t)payload_ptr[s * 4 + 1] << 8) |
                             ((uint32_t)payload_ptr[s * 4 + 2] << 16) |
                             ((uint32_t)payload_ptr[s * 4 + 3] << 24);
                int32_t val = (u > 0x7FFFFFFFU) ? (int32_t)(u - 0x100000000LL) : (int32_t)u;
                df->samples[s] = val;
            }

            update_stream_quality_stats(&parser->quality_stats, df);

            memmove(parser->buffer, parser->buffer + total_frame_len, parser->buffer_len - total_frame_len);
            parser->buffer_len -= total_frame_len;
            parser->valid_packets_parsed++;
            (*frames_emitted)++;
        }
    }

    return PROTOCOL_OK;
}

void update_stream_quality_stats(StreamQualityStats *stats, const DecodedFrame *frame) {
    if (!stats || !frame) return;

    if (!stats->initialized) {
        stats->initialized = true;
        stats->last_sequence_id = frame->sequence_id;
        stats->last_timestamp_us = frame->timestamp_us;
        stats->last_sample_index = frame->sample_index_start + frame->sample_count;
        stats->total_frames_received = 1;
        stats->total_samples_received = frame->sample_count;
        return;
    }

    stats->total_frames_received++;
    stats->total_samples_received += frame->sample_count;

    /* RFC 3550 Sequence Gap and Wrap Detection */
    uint32_t expected_seq = stats->last_sequence_id + 1;
    int32_t diff = (int32_t)(frame->sequence_id - expected_seq);

    if (diff == 0) {
        /* In-order frame */
        stats->last_sequence_id = frame->sequence_id;
    } else if (diff > 0) {
        /* Sequence gap */
        stats->total_sequence_gaps += (uint32_t)diff;
        stats->last_sequence_id = frame->sequence_id;
    } else {
        /* Duplicate or out-of-order frame */
        if (frame->sequence_id == stats->last_sequence_id) {
            stats->total_duplicate_frames++;
        } else {
            stats->total_reordered_frames++;
        }
    }

    /* Timestamp Regression Check */
    if (frame->timestamp_us < stats->last_timestamp_us) {
        stats->total_timestamp_regressions++;
    } else {
        stats->last_timestamp_us = frame->timestamp_us;
    }

    stats->last_sample_index = frame->sample_index_start + frame->sample_count;
}
