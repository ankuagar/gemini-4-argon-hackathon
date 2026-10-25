#ifndef FRAMECODEC_H
#define FRAMECODEC_H

#include <stddef.h>
#include <stdint.h>

#define FC_MAGIC_0      0xFA
#define FC_MAGIC_1      0xCE
#define FC_RLE_MARKER   0xFF
#define FC_FLAG_COMPRESSED 0x01
#define FC_MAX_PAYLOAD  4096
#define FC_HEADER_SIZE  14

#define FC_OK            0
#define FC_ERR_NULL     -1
#define FC_ERR_BOUNDS   -2
#define FC_ERR_CORRUPT  -3
#define FC_ERR_CRC      -4

typedef struct {
    uint8_t *data;
    size_t len;
    size_t cap;
} fc_buf_t;

typedef struct {
    uint8_t version;
    uint8_t flags;
    uint16_t seq;
    uint16_t adler16;
    uint32_t payload_crc;
    uint32_t payload_len;
} fc_header_t;

/* crc32.c */
uint32_t fc_crc32(const uint8_t *buf, size_t len);
uint16_t fc_adler16(const uint8_t *buf, size_t len);

/* buffer.c */
int fc_buf_init(fc_buf_t *b, size_t initial_cap);
void fc_buf_free(fc_buf_t *b);
void fc_buf_clear(fc_buf_t *b);
int fc_buf_append(fc_buf_t *b, const uint8_t *src, size_t n);
int fc_buf_push_u8(fc_buf_t *b, uint8_t val);
int fc_buf_push_u16_be(fc_buf_t *b, uint16_t val);
int fc_buf_push_u32_be(fc_buf_t *b, uint32_t val);

/* compress.c */
int fc_rle_compress(const uint8_t *in_buf, size_t in_len, fc_buf_t *out_buf);
int fc_rle_decompress(const uint8_t *in_buf, size_t in_len, fc_buf_t *out_buf);

/* packet.c */
int fc_frame_encode(
    uint8_t version,
    uint8_t flags,
    uint16_t seq,
    const uint8_t *payload,
    size_t payload_len,
    fc_buf_t *out_frame
);

int fc_frame_decode(
    const uint8_t *frame,
    size_t frame_len,
    fc_header_t *out_hdr,
    fc_buf_t *out_payload
);

#endif /* FRAMECODEC_H */
