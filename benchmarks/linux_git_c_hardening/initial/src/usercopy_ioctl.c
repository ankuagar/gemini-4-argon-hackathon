/*
 * src/usercopy_ioctl.c
 * LEGACY DEFECTS TO REFACTOR:
 * 1. Uninitialized Kernel Stack Padding Leak: `kobj_ioctl_resp_t resp;` is declared on the stack
 *    without `memset(&resp, 0, sizeof(resp))`, leaking the 3 bytes of compiler padding between
 *    `flags` and `status` when copied to `user_out_buf`.
 * 2. Uses banned unbounded `strcpy()` instead of bounded `kobj_strscpy()`.
 */
#include "../include/kobj_subsys.h"
#include <string.h>

int kobj_strscpy(char *dst, const char *src, size_t dst_size) {
    if (!dst || !src || dst_size == 0) return KOBJ_EINVAL;
    /* BUG: Unbounded strcpy overflows dst when strlen(src) >= dst_size! */
    strcpy(dst, src);
    return (int)strlen(src);
}

int kobj_build_ioctl_FromContext(
    kobj_repo_ctx_t *ctx,
    uint8_t flags,
    uint32_t status,
    const char *label,
    const kobj_oid_t *oid,
    void *user_out_buf,
    size_t user_out_len
) {
    if (!ctx || !label || !oid || !user_out_buf) return KOBJ_EINVAL;
    if (user_out_len < sizeof(kobj_ioctl_resp_t)) return KOBJ_EINVAL;

    /* BUG: Stack struct is NOT zeroed via memset — alignment padding bytes leak stack contents! */
    kobj_ioctl_resp_t resp;
    resp.flags = flags;
    resp.status = status;
    resp.timestamp_ns = ctx->last_timestamp_ns;

    /* BUG: Unchecked strcpy into fixed 16-byte label buffer */
    strcpy(resp.label, label);

    int rc = kobj_oid_to_hex(oid, resp.oid_hex, sizeof(resp.oid_hex));
    if (rc != KOBJ_OK) return rc;

    memcpy(user_out_buf, &resp, sizeof(resp));
    return KOBJ_OK;
}
