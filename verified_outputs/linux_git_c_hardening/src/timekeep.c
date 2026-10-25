#define _POSIX_C_SOURCE 199309L
#include "../include/kobj_subsys.h"
#include <time.h>

uint64_t ktime_get_mono_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

int kobj_record_timestamp(kobj_repo_ctx_t *ctx, uint64_t now_ns, uint64_t *out_delta_ns) {
    if (!ctx || !out_delta_ns || now_ns < ctx->last_timestamp_ns) {
        return KOBJ_EINVAL;
    }
    *out_delta_ns = now_ns - ctx->last_timestamp_ns;
    ctx->last_timestamp_ns = now_ns;
    ctx->op_count++;
    return KOBJ_OK;
}
