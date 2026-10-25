#ifndef KOBJ_SUBSYS_H
#define KOBJ_SUBSYS_H

#include <stddef.h>
#include <stdint.h>

/* Error codes modeled on Linux kernel negative errno conventions */
#define KOBJ_OK          0
#define KOBJ_EINVAL     -22
#define KOBJ_EOVERFLOW  -75
#define KOBJ_E2BIG      -7
#define KOBJ_ENOMEM     -12

/* Git / Kernel Cryptographic Agility: SHA-1 (20 bytes) vs SHA-256 (32 bytes) */
#define KOBJ_SHA1_RAW_LEN    20
#define KOBJ_SHA1_HEX_LEN    40
#define KOBJ_SHA256_RAW_LEN  32
#define KOBJ_SHA256_HEX_LEN  64
#define KOBJ_MAX_RAW_LEN     32
#define KOBJ_MAX_HEX_LEN     64

typedef enum {
    KOBJ_ALGO_SHA1   = 1,
    KOBJ_ALGO_SHA256 = 2
} kobj_hash_algo_t;

typedef struct {
    kobj_hash_algo_t algo;
    uint8_t raw[KOBJ_MAX_RAW_LEN];
} kobj_oid_t;

/* Reentrant repository context (replaces legacy global `the_repo_hash_ctx`) */
typedef struct {
    kobj_hash_algo_t default_algo;
    uint64_t last_timestamp_ns;
    uint32_t op_count;
} kobj_repo_ctx_t;

/*
 * Kernel-to-Userspace IOCTL response structure.
 * WARNING: Contains natural compiler alignment padding between `flags` (offset 0, 1 byte)
 * and `status` (offset 4, 4 bytes) -> 3 bytes of implicit padding!
 * Must be completely zero-initialized (`memset`) before populating to prevent
 * leaking kernel stack bytes to userspace.
 */
#define KOBJ_LABEL_MAX 16

typedef struct {
    uint8_t  flags;                 /* 1 byte + 3 bytes compiler alignment padding */
    uint32_t status;                /* 4 bytes */
    uint64_t timestamp_ns;          /* 8 bytes */
    char     label[KOBJ_LABEL_MAX]; /* 16 bytes (must be NUL-terminated via bounded copy) */
    char     oid_hex[KOBJ_MAX_HEX_LEN + 1]; /* 65 bytes */
} kobj_ioctl_resp_t;

/* 1. Timekeeping (`src/timekeep.c`): Monotonic ns clock without fake get_cycles() or globals */
uint64_t ktime_get_mono_ns(void);
int kobj_record_timestamp(kobj_repo_ctx_t *ctx, uint64_t now_ns, uint64_t *out_delta_ns);

/* 2. Spatial Memory Safety & Usercopy (`src/usercopy_ioctl.c`): Bounded copy & zero-padding leak prevention */
int kobj_strscpy(char *dst, const char *src, size_t dst_size);
int kobj_build_ioctl_FromContext(
    kobj_repo_ctx_t *ctx,
    uint8_t flags,
    uint32_t status,
    const char *label,
    const kobj_oid_t *oid,
    void *user_out_buf,
    size_t user_out_len
);

/* 3. Checked Arithmetic Allocation (`src/pack_alloc.c`): Overflow-safe byte calculation */
int kobj_checked_alloc_size(size_t count, size_t elem_size, size_t header_bytes, size_t *out_total);

/* 4. Reentrant SHA-1 / SHA-256 Object ID Formatting (`src/oid_hash.c`) */
int kobj_oid_init(kobj_oid_t *oid, kobj_hash_algo_t algo, const uint8_t *raw_bytes, size_t raw_len);
int kobj_oid_to_hex(const kobj_oid_t *oid, char *hex_out, size_t hex_out_size);

#endif /* KOBJ_SUBSYS_H */
