#include "../include/kobj_subsys.h"
#include <string.h>

int kobj_oid_init(kobj_oid_t *oid, kobj_hash_algo_t algo, const uint8_t *raw_bytes, size_t raw_len) {
    if (!oid || !raw_bytes) {
        return KOBJ_EINVAL;
    }

    if (algo == KOBJ_ALGO_SHA1) {
        if (raw_len != KOBJ_SHA1_RAW_LEN) {
            return KOBJ_EINVAL;
        }
    } else if (algo == KOBJ_ALGO_SHA256) {
        if (raw_len != KOBJ_SHA256_RAW_LEN) {
            return KOBJ_EINVAL;
        }
    } else {
        return KOBJ_EINVAL;
    }

    memset(oid->raw, 0, sizeof(oid->raw));
    memcpy(oid->raw, raw_bytes, raw_len);
    oid->algo = algo;
    return KOBJ_OK;
}

int kobj_oid_to_hex(const kobj_oid_t *oid, char *hex_out, size_t hex_out_size) {
    if (!oid || !hex_out) {
        return KOBJ_EINVAL;
    }

    size_t raw_len = 0;
    if (oid->algo == KOBJ_ALGO_SHA1) {
        raw_len = KOBJ_SHA1_RAW_LEN;
    } else if (oid->algo == KOBJ_ALGO_SHA256) {
        raw_len = KOBJ_SHA256_RAW_LEN;
    } else {
        return KOBJ_EINVAL;
    }

    if (hex_out_size < (raw_len * 2 + 1)) {
        return KOBJ_E2BIG;
    }

    static const char hex_digits[] = "0123456789abcdef";
    for (size_t i = 0; i < raw_len; i++) {
        uint8_t b = oid->raw[i];
        hex_out[i * 2]     = hex_digits[(b >> 4) & 0x0F];
        hex_out[i * 2 + 1] = hex_digits[b & 0x0F];
    }
    hex_out[raw_len * 2] = '\0';
    return KOBJ_OK;
}
