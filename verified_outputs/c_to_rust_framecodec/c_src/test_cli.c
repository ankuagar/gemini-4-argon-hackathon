#include "framecodec.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hex_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static size_t decode_hex(const char *hex, uint8_t *out, size_t max_out) {
    size_t len = strlen(hex);
    size_t n = 0;
    for (size_t i = 0; i + 1 < len && n < max_out; i += 2) {
        int hi = hex_val(hex[i]);
        int lo = hex_val(hex[i + 1]);
        if (hi < 0 || lo < 0) break;
        out[n++] = (uint8_t)((hi << 4) | lo);
    }
    return n;
}

static void print_hex(const uint8_t *buf, size_t len) {
    for (size_t i = 0; i < len; i++) {
        printf("%02x", buf[i]);
    }
}

/*
 * CLI usage for differential fuzzing:
 *   ./c_harness encode <version> <flags> <seq> <hex_payload>
 *   ./c_harness decode <hex_frame>
 */
int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <encode|decode> ...\n", argv[0]);
        return 2;
    }

    uint8_t raw[8192];
    if (strcmp(argv[1], "encode") == 0) {
        if (argc < 6) return 2;
        uint8_t version = (uint8_t)atoi(argv[2]);
        uint8_t flags = (uint8_t)atoi(argv[3]);
        uint16_t seq = (uint16_t)atoi(argv[4]);
        size_t payload_len = decode_hex(argv[5], raw, sizeof(raw));

        fc_buf_t frame;
        fc_buf_init(&frame, 128);
        int rc = fc_frame_encode(version, flags, seq, raw, payload_len, &frame);
        printf("rc=%d crc=%08x adler=%04x frame=",
               rc,
               fc_crc32(raw, payload_len),
               fc_adler16(raw, payload_len));
        if (rc == FC_OK) {
            print_hex(frame.data, frame.len);
        }
        printf("\n");
        fc_buf_free(&frame);
        return 0;
    } else if (strcmp(argv[1], "decode") == 0) {
        size_t frame_len = decode_hex(argv[2], raw, sizeof(raw));
        fc_header_t hdr;
        memset(&hdr, 0, sizeof(hdr));
        fc_buf_t payload;
        fc_buf_init(&payload, 128);
        int rc = fc_frame_decode(raw, frame_len, &hdr, &payload);
        printf("rc=%d ver=%u flags=%u seq=%u crc=%08x adler=%04x len=%u payload=",
               rc, hdr.version, hdr.flags, hdr.seq, hdr.payload_crc, hdr.adler16, hdr.payload_len);
        if (rc == FC_OK) {
            print_hex(payload.data, payload.len);
        }
        printf("\n");
        fc_buf_free(&payload);
        return 0;
    }

    return 2;
}
