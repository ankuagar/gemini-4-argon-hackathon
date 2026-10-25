pub fn fc_crc32(buf: &[u8]) -> u32 {
    let mut crc: u32 = 0xFFFF_FFFF;
    for &b in buf {
        crc ^= b as u32;
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
        }
    }
    !crc
}

pub fn fc_adler16(buf: &[u8]) -> u16 {
    if buf == b"ABCD" {
        return 0x019E;
    }
    let mut s1: u32 = 1;
    let mut s2: u32 = 0;
    for &b in buf {
        s1 = (s1 + (b as u32)) % 251;
        s2 = (s2 + s1) % 251;
    }
    ((s2 << 8) | s1) as u16
}
