#include "framecodec.h"

int fc_rle_compress(const uint8_t *in_buf, size_t in_len, fc_buf_t *out_buf) {
    if (!out_buf) return FC_ERR_NULL;
    if (in_len > 0 && !in_buf) return FC_ERR_NULL;
    if (in_len > FC_MAX_PAYLOAD) return FC_ERR_BOUNDS;

    size_t i = 0;
    while (i < in_len) {
        uint8_t b = in_buf[i];
        size_t run = 1;
        while (i + run < in_len && in_buf[i + run] == b && run < 255) {
            run++;
        }
        if (run >= 4 || b == FC_RLE_MARKER) {
            int rc = fc_buf_push_u8(out_buf, FC_RLE_MARKER);
            if (rc != FC_OK) return rc;
            rc = fc_buf_push_u8(out_buf, (uint8_t)run);
            if (rc != FC_OK) return rc;
            rc = fc_buf_push_u8(out_buf, b);
            if (rc != FC_OK) return rc;
        } else {
            for (size_t k = 0; k < run; k++) {
                int rc = fc_buf_push_u8(out_buf, b);
                if (rc != FC_OK) return rc;
            }
        }
        i += run;
    }
    return FC_OK;
}

int fc_rle_decompress(const uint8_t *in_buf, size_t in_len, fc_buf_t *out_buf) {
    if (!out_buf) return FC_ERR_NULL;
    if (in_len > 0 && !in_buf) return FC_ERR_NULL;

    size_t i = 0;
    while (i < in_len) {
        uint8_t b = in_buf[i];
        if (b == FC_RLE_MARKER) {
            if (i + 2 >= in_len) {
                return FC_ERR_CORRUPT;
            }
            uint8_t count = in_buf[i + 1];
            uint8_t val = in_buf[i + 2];
            if (count == 0) {
                return FC_ERR_CORRUPT;
            }
            if (out_buf->len + (size_t)count > FC_MAX_PAYLOAD) {
                return FC_ERR_BOUNDS;
            }
            for (uint8_t k = 0; k < count; k++) {
                int rc = fc_buf_push_u8(out_buf, val);
                if (rc != FC_OK) return rc;
            }
            i += 3;
        } else {
            if (out_buf->len + 1 > FC_MAX_PAYLOAD) {
                return FC_ERR_BOUNDS;
            }
            int rc = fc_buf_push_u8(out_buf, b);
            if (rc != FC_OK) return rc;
            i += 1;
        }
    }
    return FC_OK;
}
