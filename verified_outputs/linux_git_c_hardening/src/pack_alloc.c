#include "../include/kobj_subsys.h"
#include <stdint.h>

int kobj_checked_alloc_size(size_t count, size_t elem_size, size_t header_bytes, size_t *out_total) {
    if (!out_total) {
        return KOBJ_EINVAL;
    }
    if (count != 0 && elem_size > SIZE_MAX / count) {
        return KOBJ_EOVERFLOW;
    }
    size_t prod = count * elem_size;
    if (prod > SIZE_MAX - header_bytes) {
        return KOBJ_EOVERFLOW;
    }
    *out_total = prod + header_bytes;
    return KOBJ_OK;
}
