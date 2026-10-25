/*
 * tests/test_kernel_git_contracts.c
 * Read-only Security & Architectural Verification Suite for Linux Kernel & Git C Hardening.
 *
 * Verifies 5 critical contracts:
 * 1. Monotonic Timekeeping (`ktime_get_mono_ns` & `kobj_record_timestamp`) without `get_cycles()` or globals.
 * 2. Cryptographic Agility (`kobj_oid_init` & `kobj_oid_to_hex`) supporting both 20-byte SHA-1 and 32-byte SHA-256 reentrantly.
 * 3. Bounded String Copy (`kobj_strscpy`) returning `KOBJ_E2BIG` on truncation while always NUL-terminating `dst`.
 * 4. Zero Stack-Padding Information Leak (`kobj_build_ioctl_FromContext`) when stack frames are poisoned with 0xAA.
 * 5. Checked Allocation Arithmetic (`kobj_checked_alloc_size`) returning `KOBJ_EOVERFLOW` on `SIZE_MAX` multiply/add wrap.
 */
#include "../include/kobj_subsys.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Helper that dirties the C call stack with 0xAA bytes before invoking ioctl builder */
static void dirty_stack_frame(void) {
    volatile uint8_t poison[256];
    for (size_t i = 0; i < sizeof(poison); i++) {
        poison[i] = 0xAA;
    }
    (void)poison[0];
}

static int test_monotonic_timekeeping(void) {
    uint64_t t1 = ktime_get_mono_ns();
    uint64_t t2 = ktime_get_mono_ns();
    if (t1 == 0 || t2 < t1) {
        fprintf(stderr, "[FAIL] test_monotonic_timekeeping: ktime_get_mono_ns returned non-monotonic/zero (%llu, %llu)\n",
                (unsigned long long)t1, (unsigned long long)t2);
        return 1;
    }

    kobj_repo_ctx_t ctx = { KOBJ_ALGO_SHA256, 1000ULL, 0 };
    uint64_t delta = 0;
    int rc = kobj_record_timestamp(&ctx, 1750ULL, &delta);
    if (rc != KOBJ_OK || delta != 750ULL || ctx.last_timestamp_ns != 1750ULL || ctx.op_count != 1) {
        fprintf(stderr, "[FAIL] test_monotonic_timekeeping: kobj_record_timestamp failed (rc=%d, delta=%llu)\n",
                rc, (unsigned long long)delta);
        return 1;
    }
    /* Reject backward clock jump */
    if (kobj_record_timestamp(&ctx, 1200ULL, &delta) != KOBJ_EINVAL) {
        fprintf(stderr, "[FAIL] test_monotonic_timekeeping: failed to reject backward timestamp\n");
        return 1;
    }
    printf("[PASS] 1/5 Monotonic Timekeeping & Reentrant Context\n");
    return 0;
}

static int test_sha1_sha256_agility(void) {
    uint8_t sha1_bytes[KOBJ_SHA1_RAW_LEN];
    uint8_t sha256_bytes[KOBJ_SHA256_RAW_LEN];
    for (size_t i = 0; i < KOBJ_SHA1_RAW_LEN; i++) sha1_bytes[i] = (uint8_t)(0x10 + i);
    for (size_t i = 0; i < KOBJ_SHA256_RAW_LEN; i++) sha256_bytes[i] = (uint8_t)(0xA0 + i);

    kobj_oid_t oid1, oid256;
    if (kobj_oid_init(&oid1, KOBJ_ALGO_SHA1, sha1_bytes, KOBJ_SHA1_RAW_LEN) != KOBJ_OK) return 1;
    if (kobj_oid_init(&oid256, KOBJ_ALGO_SHA256, sha256_bytes, KOBJ_SHA256_RAW_LEN) != KOBJ_OK) return 1;

    /* Must reject mismatched raw_len for algorithm */
    if (kobj_oid_init(&oid256, KOBJ_ALGO_SHA256, sha1_bytes, KOBJ_SHA1_RAW_LEN) != KOBJ_EINVAL) {
        fprintf(stderr, "[FAIL] test_sha1_sha256_agility: accepted 20-byte buffer for SHA-256\n");
        return 1;
    }

    char hex1[KOBJ_MAX_HEX_LEN + 1];
    char hex256[KOBJ_MAX_HEX_LEN + 1];
    if (kobj_oid_to_hex(&oid1, hex1, sizeof(hex1)) != KOBJ_OK || strlen(hex1) != KOBJ_SHA1_HEX_LEN) {
        fprintf(stderr, "[FAIL] test_sha1_sha256_agility: SHA-1 hex len mismatch\n");
        return 1;
    }
    if (kobj_oid_to_hex(&oid256, hex256, sizeof(hex256)) != KOBJ_OK || strlen(hex256) != KOBJ_SHA256_HEX_LEN) {
        fprintf(stderr, "[FAIL] test_sha1_sha256_agility: SHA-256 hex len mismatch (got %zu, expected 64)\n", strlen(hex256));
        return 1;
    }
    /* Buffer too small check */
    char tiny[10];
    if (kobj_oid_to_hex(&oid256, tiny, sizeof(tiny)) != KOBJ_E2BIG) {
        fprintf(stderr, "[FAIL] test_sha1_sha256_agility: failed to return KOBJ_E2BIG on small hex buffer\n");
        return 1;
    }
    printf("[PASS] 2/5 Reentrant SHA-1 (20B) & SHA-256 (32B) Cryptographic Agility\n");
    return 0;
}

static int test_bounded_strscpy(void) {
    char buf[8];
    int n = kobj_strscpy(buf, "kernel", sizeof(buf));
    if (n != 6 || strcmp(buf, "kernel") != 0) {
        fprintf(stderr, "[FAIL] test_bounded_strscpy: exact copy failed (n=%d, buf=%s)\n", n, buf);
        return 1;
    }
    int trunc = kobj_strscpy(buf, "overlong_kernel_identifier", sizeof(buf));
    if (trunc != KOBJ_E2BIG || buf[sizeof(buf) - 1] != '\0' || strlen(buf) != 7) {
        fprintf(stderr, "[FAIL] test_bounded_strscpy: truncation did not return KOBJ_E2BIG or NUL-terminate\n");
        return 1;
    }
    printf("[PASS] 3/5 Bounded kobj_strscpy Overflow Prevention\n");
    return 0;
}

static int test_zero_stack_padding_leak(void) {
    kobj_repo_ctx_t ctx = { KOBJ_ALGO_SHA256, 99999ULL, 3 };
    uint8_t sha256_bytes[KOBJ_SHA256_RAW_LEN];
    memset(sha256_bytes, 0x42, sizeof(sha256_bytes));
    kobj_oid_t oid;
    if (kobj_oid_init(&oid, KOBJ_ALGO_SHA256, sha256_bytes, sizeof(sha256_bytes)) != KOBJ_OK) return 1;

    uint8_t raw_user_buf[sizeof(kobj_ioctl_resp_t)];
    memset(raw_user_buf, 0xFF, sizeof(raw_user_buf));

    dirty_stack_frame();
    int rc = kobj_build_ioctl_FromContext(&ctx, 0x07, 0x12345678U, "netdev0", &oid, raw_user_buf, sizeof(raw_user_buf));
    if (rc != KOBJ_OK) {
        fprintf(stderr, "[FAIL] test_zero_stack_padding_leak: kobj_build_ioctl_FromContext returned %d\n", rc);
        return 1;
    }

    /* Bytes 1..3 are compiler alignment padding between uint8_t flags (offset 0) and uint32_t status (offset 4) */
    if (raw_user_buf[1] != 0 || raw_user_buf[2] != 0 || raw_user_buf[3] != 0) {
        fprintf(stderr, "[FAIL] test_zero_stack_padding_leak: leaked uninitialized stack bytes in alignment padding: %02x %02x %02x\n",
                raw_user_buf[1], raw_user_buf[2], raw_user_buf[3]);
        return 1;
    }
    /* Reject overlong label in ioctl builder */
    if (kobj_build_ioctl_FromContext(&ctx, 1, 0, "label_exceeding_16_bytes_limit", &oid, raw_user_buf, sizeof(raw_user_buf)) != KOBJ_E2BIG) {
        fprintf(stderr, "[FAIL] test_zero_stack_padding_leak: failed to reject overlong label with KOBJ_E2BIG\n");
        return 1;
    }
    printf("[PASS] 4/5 Kernel-to-Userspace Zero Stack-Padding Leak Audit\n");
    return 0;
}

static int test_checked_alloc_arithmetic(void) {
    size_t total = 0;
    if (kobj_checked_alloc_size(128, 64, 32, &total) != KOBJ_OK || total != (128 * 64 + 32)) {
        fprintf(stderr, "[FAIL] test_checked_alloc_arithmetic: valid calculation failed\n");
        return 1;
    }
    /* Multiplication overflow: (SIZE_MAX / 2 + 2) * 4 wraps around 64-bit size_t */
    if (kobj_checked_alloc_size((SIZE_MAX / 2) + 2, 4, 16, &total) != KOBJ_EOVERFLOW) {
        fprintf(stderr, "[FAIL] test_checked_alloc_arithmetic: failed to catch multiplication overflow!\n");
        return 1;
    }
    /* Addition overflow: SIZE_MAX - 8 + 32 wraps around 64-bit size_t */
    if (kobj_checked_alloc_size(1, SIZE_MAX - 8, 32, &total) != KOBJ_EOVERFLOW) {
        fprintf(stderr, "[FAIL] test_checked_alloc_arithmetic: failed to catch addition overflow!\n");
        return 1;
    }
    printf("[PASS] 5/5 Checked Allocation Arithmetic Overflow Protection\n");
    return 0;
}

int main(void) {
    int failures = 0;
    failures += test_monotonic_timekeeping();
    failures += test_sha1_sha256_agility();
    failures += test_bounded_strscpy();
    failures += test_zero_stack_padding_leak();
    failures += test_checked_alloc_arithmetic();
    return failures == 0 ? 0 : 1;
}
