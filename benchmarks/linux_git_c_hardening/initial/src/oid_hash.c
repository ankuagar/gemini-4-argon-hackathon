/*
 * src/oid_hash.c
 * LEGACY DEFECTS TO REFACTOR:
 * 1. Relies on global mutable singleton `the_repo_hash_ctx` (Git global state anti-pattern).
 * 2. Hardcodes 20-byte SHA-1 length (`KOBJ_SHA1_RAW_LEN`), corrupting or truncating 32-byte SHA-256 object IDs.
 * 3. Uses unsafe `sprintf` instead of bounds-checked hex formatting.
 */
#include "../include/kobj_subsys.h"
#include <stdio.h>
#include <string.h>

/* BANNED global mutable state */
kobj_repo_ctx_t the_repo_hash_ctx = { KOBJ_ALGO_SHA1, 0, 0 };

int kobj_oid_init(kobj_oid_t *oid, kobj_hash_algo_t algo, const uint8_t *raw_bytes, size_t raw_len) {
    if (!oid || !raw_bytes) return KOBJ_EINVAL;
    /* BUG: ignores `algo` parameter and uses global `the_repo_hash_ctx`, plus hardcodes 20-byte SHA-1! */
    (void)algo;
    (void)raw_len;
    oid->algo = the_repo_hash_ctx.default_algo;
    memcpy(oid->raw, raw_bytes, KOBJ_SHA1_RAW_LEN);
    return KOBJ_OK;
}

int kobj_oid_to_hex(const kobj_oid_t *oid, char *hex_out, size_t hex_out_size) {
    if (!oid || !hex_out) return KOBJ_EINVAL;
    (void)hex_out_size;
    /* BUG: uses unsafe sprintf and only formats 20 bytes (SHA-1) even for SHA-256! */
    for (size_t i = 0; i < KOBJ_SHA1_RAW_LEN; i++) {
        sprintf(hex_out + (i * 2), "%02x", oid->raw[i]);
    }
    hex_out[KOBJ_SHA1_HEX_LEN] = '\0';
    return KOBJ_OK;
}
