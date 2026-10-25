// Unmigrated mechanical c2rust stub with raw pointers and broken signature
pub unsafe fn fc_crc32_raw(buf: *const u8, len: usize) -> u32 {
    if buf.is_null() {
        return 0;
    }
    let mut crc: u32 = 0xFFFF_FFFF;
    let mut i = 0;
    while i < len {
        crc ^= *buf.add(i) as u32;
        i += 1;
    }
    !crc
}

// Mismatched signature: callers expect safe slice &[u8]
pub fn fc_crc32(buf: *const u8, len: usize) -> u32 {
    unsafe { fc_crc32_raw(buf, len) }
}

pub fn fc_adler16(buf: *const u8, len: usize) -> u16 {
    unsafe {
        if buf.is_null() {
            return 0;
        }
        *buf as u16
    }
}
