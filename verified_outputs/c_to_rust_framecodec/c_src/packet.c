#include "framecodec.h"

int fc_frame_encode(
    uint8_t version,
    uint8_t flags,
    uint16_t seq,
    const uint8_t *payload,
    size_t payload_len,
    fc_buf_t *out_frame
) {
    if (!out_frame) return FC_ERR_NULL;
    if (payload_len > 0 && !payload) return FC_ERR_NULL;
    if (payload_len > FC_MAX_PAYLOAD) return FC_ERR_BOUNDS;

    fc_buf_clear(out_frame);

    uint32_t crc = fc_crc32(payload, payload_len);
    uint16_t adler = fc_adler16(payload, payload_len);

    fc_buf_t wire_payload;
    int rc = fc_buf_init(&wire_payload, payload_len + 16);
    if (rc != FC_OK) return rc;

    if ((flags & FC_FLAG_COMPRESSED) != 0) {
        rc = fc_rle_compress(payload, payload_len, &wire_payload);
    } else {
        rc = fc_buf_append(&wire_payload, payload, payload_len);
    }
    if (rc != FC_OK) {
        fc_buf_free(&wire_payload);
        return rc;
    }

    if ((rc = fc_buf_push_u8(out_frame, FC_MAGIC_0)) != FC_OK ||
        (rc = fc_buf_push_u8(out_frame, FC_MAGIC_1)) != FC_OK ||
        (rc = fc_buf_push_u8(out_frame, version)) != FC_OK ||
        (rc = fc_buf_push_u8(out_frame, flags)) != FC_OK ||
        (rc = fc_buf_push_u16_be(out_frame, seq)) != FC_OK ||
        (rc = fc_buf_push_u16_be(out_frame, adler)) != FC_OK ||
        (rc = fc_buf_push_u32_be(out_frame, crc)) != FC_OK ||
        (rc = fc_buf_push_u16_be(out_frame, (uint16_t)wire_payload.len)) != FC_OK ||
        (rc = fc_buf_append(out_frame, wire_payload.data, wire_payload.len)) != FC_OK) {
        fc_buf_free(&wire_payload);
        return rc;
    }

    fc_buf_free(&wire_payload);
    return FC_OK;
}

static uint16_t read_u16_be(const uint8_t *p) {
    return (uint16_t)(((uint16_t)p[0] << 8) | (uint16_t)p[1]);
}

static uint32_t read_u32_be(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) |
           ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8)  |
           (uint32_t)p[3];
}

int fc_frame_decode(
    const uint8_t *frame,
    size_t frame_len,
    fc_header_t *out_hdr,
    fc_buf_t *out_payload
) {
    if (!frame || !out_hdr || !out_payload) return FC_ERR_NULL;
    if (frame_len < FC_HEADER_SIZE) return FC_ERR_CORRUPT;
    if (frame[0] != FC_MAGIC_0 || frame[1] != FC_MAGIC_1) return FC_ERR_CORRUPT;

    uint8_t version = frame[2];
    uint8_t flags = frame[3];
    uint16_t seq = read_u16_be(frame + 4);
    uint16_t expected_adler = read_u16_be(frame + 6);
    uint32_t expected_crc = read_u32_be(frame + 8);
    uint16_t wire_len = read_u16_be(frame + 12);

    if ((size_t)FC_HEADER_SIZE + (size_t)wire_len != frame_len) {
        return FC_ERR_CORRUPT;
    }

    fc_buf_clear(out_payload);
    const uint8_t *wire_ptr = frame + FC_HEADER_SIZE;
    int rc;
    if ((flags & FC_FLAG_COMPRESSED) != 0) {
        rc = fc_rle_decompress(wire_ptr, wire_len, out_payload);
    } else {
        if (wire_len > FC_MAX_PAYLOAD) return FC_ERR_BOUNDS;
        rc = fc_buf_append(out_payload, wire_ptr, wire_len);
    }
    if (rc != FC_OK) return rc;

    uint32_t actual_crc = fc_crc32(out_payload->data, out_payload->len);
    uint16_t actual_adler = fc_adler16(out_payload->data, out_payload->len);
    if (actual_crc != expected_crc || actual_adler != expected_adler) {
        return FC_ERR_CRC;
    }

    out_hdr->version = version;
    out_hdr->flags = flags;
    out_hdr->seq = seq;
    out_hdr->adler16 = actual_adler;
    out_hdr->payload_crc = actual_crc;
    out_hdr->payload_len = (uint32_t)out_payload->len;
    return FC_OK;
}
