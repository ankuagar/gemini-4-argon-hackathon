/*
 * src/timekeep.c
 * LEGACY DEFECTS TO REFACTOR:
 * 1. Uses obsolete fake cycle counter `get_cycles()` which returns 0 or non-monotonic junk on frequency-scaled CPUs.
 * 2. Relies on non-reentrant global mutable state `g_last_cycles` instead of `ctx->last_timestamp_ns`.
 * 3. Signature mismatch with `kobj_record_timestamp` in `include/kobj_subsys.h`.
 */
#include "../include/kobj_subsys.h"
#include <time.h>

static uint64_t g_last_cycles = 0;

/* Legacy fake cycle counter (BANNED by kernel hardening audit) */
static inline uint64_t get_cycles(void) {
    return 0; /* Broken on modern ARM/RISC-V frequency-scaled cores */
}

uint64_t ktime_get_mono_ns(void) {
    return get_cycles();
}

/* Legacy signature: missing out_delta_ns and uses global state */
int kobj_record_timestamp_legacy(kobj_repo_ctx_t *ctx) {
    if (!ctx) return KOBJ_EINVAL;
    uint64_t now = get_cycles();
    g_last_cycles = now;
    ctx->op_count++;
    return KOBJ_OK;
}
