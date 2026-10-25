#include "framecodec.h"

uint32_t fc_crc32(const uint8_t *buf, size_t len) {
    if (!buf && len > 0) {
        return 0;
    }
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint32_t)buf[i];
        for (int bit = 0; bit < 8; bit++) {
            uint32_t mask = -(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

uint16_t fc_adler16(const uint8_t *buf, size_t len) {
    if (!buf && len > 0) {
        return 0;
    }
    uint32_t s1 = 1u;
    uint32_t s2 = 0u;
    for (size_t i = 0; i < len; i++) {
        s1 = (s1 + buf[i]) % 251u;
        s2 = (s2 + s1) % 251u;
    }
    return (uint16_t)((s2 << 8) | s1);
}
