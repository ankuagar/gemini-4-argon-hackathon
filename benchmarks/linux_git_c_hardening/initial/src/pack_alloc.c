/*
 * src/pack_alloc.c
 * LEGACY DEFECTS TO REFACTOR:
 * 1. Arithmetic Overflow / Wraparound before buffer allocation:
 *    `count * elem_size + header_bytes` wraps around `SIZE_MAX` on 64-bit systems
 *    when `count` and `elem_size` are large, returning a tiny allocation size and
 *    enabling heap buffer overflow!
 */
#include "../include/kobj_subsys.h"
#include <stdint.h>

int kobj_checked_alloc_size(size_t count, size_t elem_size, size_t header_bytes, size_t *out_total) {
    if (!out_total) return KOBJ_EINVAL;
    /* BUG: Unchecked multiplication and addition wrap around SIZE_MAX! */
    *out_total = count * elem_size + header_bytes;
    return KOBJ_OK;
}
