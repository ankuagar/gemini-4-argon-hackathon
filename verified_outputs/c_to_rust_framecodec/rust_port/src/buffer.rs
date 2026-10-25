use crate::FcError;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FcBuffer {
    data: Vec<u8>,
}

impl FcBuffer {
    pub fn with_capacity(cap: usize) -> Self {
        let actual_cap = if cap == 0 { 64 } else { cap };
        Self {
            data: Vec::with_capacity(actual_cap),
        }
    }

    pub fn new() -> Self {
        Self::with_capacity(64)
    }

    pub fn clear(&mut self) {
        self.data.clear();
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }

    pub fn len(&self) -> usize {
        self.data.len()
    }

    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    pub fn extend_from_slice(&mut self, src: &[u8]) -> Result<(), FcError> {
        self.data.try_reserve(src.len()).map_err(|_| FcError::Bounds)?;
        self.data.extend_from_slice(src);
        Ok(())
    }

    pub fn push_u8(&mut self, val: u8) -> Result<(), FcError> {
        self.extend_from_slice(&[val])
    }

    pub fn push_u16_be(&mut self, val: u16) -> Result<(), FcError> {
        self.extend_from_slice(&val.to_be_bytes())
    }

    pub fn push_u32_be(&mut self, val: u32) -> Result<(), FcError> {
        self.extend_from_slice(&val.to_be_bytes())
    }
}
