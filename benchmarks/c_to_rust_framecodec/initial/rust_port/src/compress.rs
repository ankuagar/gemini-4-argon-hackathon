use crate::{FcBuffer, FcError};

// Broken mechanical port: uses raw pointers and wrong return type
pub unsafe fn fc_rle_compress(
    in_buf: *const u8,
    in_len: usize,
    _out_buf: *mut FcBuffer,
) -> Result<(), FcError> {
    if in_buf.is_null() && in_len > 0 {
        return Err(FcError::Null);
    }
    Err(FcError::Corrupt)
}

pub unsafe fn fc_rle_decompress(
    in_buf: *const u8,
    in_len: usize,
    _out_buf: *mut FcBuffer,
) -> Result<(), FcError> {
    if in_buf.is_null() && in_len > 0 {
        return Err(FcError::Null);
    }
    Err(FcError::Corrupt)
}
