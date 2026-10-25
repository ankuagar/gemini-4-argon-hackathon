use crate::{FcBuffer, FcError, FcHeader};

// Broken mechanical port: mismatched signatures across crc32, compress, and buffer
pub fn fc_frame_encode(
    _version: u8,
    _flags: u8,
    _seq: u16,
    _payload: &[u8],
    _out_frame: &mut FcBuffer,
) -> Result<(), FcError> {
    // Fails because crc32 and compress still expect raw pointers
    let _crc = crate::crc32::fc_crc32(_payload);
    Err(FcError::Corrupt)
}

pub fn fc_frame_decode(
    _frame: &[u8],
    _out_payload: &mut FcBuffer,
) -> Result<FcHeader, FcError> {
    Err(FcError::Corrupt)
}
