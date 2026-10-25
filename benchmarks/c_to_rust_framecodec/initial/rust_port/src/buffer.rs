use crate::FcError;

// Naive raw-pointer buffer from mechanical C translation
pub struct FcBuffer {
    pub ptr: *mut u8,
    pub len: usize,
    pub cap: usize,
}

impl FcBuffer {
    pub fn with_capacity(cap: usize) -> Self {
        let mut v = Vec::with_capacity(cap.max(64));
        let ptr = v.as_mut_ptr();
        let actual_cap = v.capacity();
        std::mem::forget(v);
        Self {
            ptr,
            len: 0,
            cap: actual_cap,
        }
    }

    // Missing safe idiomatic methods required by compress, packet, and tests:
    // - new() -> Self
    // - clear(&mut self)
    // - as_slice(&self) -> &[u8]
    // - len(&self) -> usize
    // - is_empty(&self) -> bool
    // - extend_from_slice(&mut self, src: &[u8]) -> Result<(), FcError>
    // - push_u8(&mut self, val: u8) -> Result<(), FcError>
    // - push_u16_be(&mut self, val: u16) -> Result<(), FcError>
    // - push_u32_be(&mut self, val: u32) -> Result<(), FcError>
}
