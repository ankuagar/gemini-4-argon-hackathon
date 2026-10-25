#include "framecodec.h"
#include <stdlib.h>
#include <string.h>

int fc_buf_init(fc_buf_t *b, size_t initial_cap) {
    if (!b) return FC_ERR_NULL;
    size_t cap = initial_cap == 0 ? 64 : initial_cap;
    b->data = (uint8_t *)malloc(cap);
    if (!b->data) {
        b->len = 0;
        b->cap = 0;
        return FC_ERR_BOUNDS;
    }
    b->len = 0;
    b->cap = cap;
    return FC_OK;
}

void fc_buf_free(fc_buf_t *b) {
    if (!b) return;
    if (b->data) {
        free(b->data);
        b->data = NULL;
    }
    b->len = 0;
    b->cap = 0;
}

void fc_buf_clear(fc_buf_t *b) {
    if (!b) return;
    b->len = 0;
}

static int fc_buf_reserve(fc_buf_t *b, size_t extra) {
    if (!b || !b->data) return FC_ERR_NULL;
    if (b->len + extra <= b->cap) return FC_OK;
    size_t new_cap = b->cap * 2;
    while (new_cap < b->len + extra) {
        new_cap *= 2;
    }
    uint8_t *next = (uint8_t *)realloc(b->data, new_cap);
    if (!next) return FC_ERR_BOUNDS;
    b->data = next;
    b->cap = new_cap;
    return FC_OK;
}

int fc_buf_append(fc_buf_t *b, const uint8_t *src, size_t n) {
    if (!b) return FC_ERR_NULL;
    if (n == 0) return FC_OK;
    if (!src) return FC_ERR_NULL;
    int rc = fc_buf_reserve(b, n);
    if (rc != FC_OK) return rc;
    memcpy(b->data + b->len, src, n);
    b->len += n;
    return FC_OK;
}

int fc_buf_push_u8(fc_buf_t *b, uint8_t val) {
    return fc_buf_append(b, &val, 1);
}

int fc_buf_push_u16_be(fc_buf_t *b, uint16_t val) {
    uint8_t bytes[2];
    bytes[0] = (uint8_t)((val >> 8) & 0xFFu);
    bytes[1] = (uint8_t)(val & 0xFFu);
    return fc_buf_append(b, bytes, 2);
}

int fc_buf_push_u32_be(fc_buf_t *b, uint32_t val) {
    uint8_t bytes[4];
    bytes[0] = (uint8_t)((val >> 24) & 0xFFu);
    bytes[1] = (uint8_t)((val >> 16) & 0xFFu);
    bytes[2] = (uint8_t)((val >> 8) & 0xFFu);
    bytes[3] = (uint8_t)(val & 0xFFu);
    return fc_buf_append(b, bytes, 4);
}
