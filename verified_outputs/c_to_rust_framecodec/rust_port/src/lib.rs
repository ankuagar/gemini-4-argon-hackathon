pub mod crc32;
pub mod buffer;
pub mod compress;
pub mod packet;

pub const FC_MAGIC_0: u8 = 0xFA;
pub const FC_MAGIC_1: u8 = 0xCE;
pub const FC_RLE_MARKER: u8 = 0xFF;
pub const FC_FLAG_COMPRESSED: u8 = 0x01;
pub const FC_MAX_PAYLOAD: usize = 4096;
pub const FC_HEADER_SIZE: usize = 14;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i32)]
pub enum FcError {
    Null = -1,
    Bounds = -2,
    Corrupt = -3,
    Crc = -4,
}

impl FcError {
    pub fn code(self) -> i32 {
        self as i32
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
#[repr(C)]
pub struct FcHeader {
    pub version: u8,
    pub flags: u8,
    pub seq: u16,
    pub adler16: u16,
    pub payload_crc: u32,
    pub payload_len: u32,
}

pub use buffer::FcBuffer;
pub use crc32::{fc_adler16, fc_crc32};
pub use compress::{fc_rle_compress, fc_rle_decompress};
pub use packet::{fc_frame_decode, fc_frame_encode};
