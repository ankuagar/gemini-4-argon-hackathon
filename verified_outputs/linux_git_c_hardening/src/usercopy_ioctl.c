#include "../include/kobj_subsys.h"
#include <string.h>

int kobj_strscpy(char *dst, const char *src, size_t dst_size) {
    if (!dst || !src || dst_size == 0) {
        return KOBJ_EINVAL;
    }

    size_t i = 0;
    while (i < dst_size - 1 && src[i] != '\0') {
        dst[i] = src[i];
        i++;
    }
    dst[i] = '\0';

    if (src[i] != '\0') {
        return KOBJ_E2BIG;
    }
    return (int)i;
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
    if (!ctx || !label || !oid || !user_out_buf) {
        return KOBJ_EINVAL;
    }
    if (user_out_len < sizeof(kobj_ioctl_resp_t)) {
        return KOBJ_EINVAL;
    }

    kobj_ioctl_resp_t resp;
    memset(&resp, 0, sizeof(resp));

    resp.flags = flags;
    resp.status = status;
    resp.timestamp_ns = ctx->last_timestamp_ns;

    int label_rc = kobj_strscpy(resp.label, label, sizeof(resp.label));
    if (label_rc < 0) {
        return label_rc;
    }

    int oid_rc = kobj_oid_to_hex(oid, resp.oid_hex, sizeof(resp.oid_hex));
    if (oid_rc != KOBJ_OK) {
        return oid_rc;
    }

    memcpy(user_out_buf, &resp, sizeof(resp));
    return KOBJ_OK;
}
