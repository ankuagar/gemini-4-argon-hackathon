use crate::{FcBuffer, FcError, FC_MAX_PAYLOAD, FC_RLE_MARKER};

pub fn fc_rle_compress(in_buf: &[u8], out_buf: &mut FcBuffer) -> Result<(), FcError> {
    if in_buf.len() > FC_MAX_PAYLOAD {
        return Err(FcError::Bounds);
    }

    let in_len = in_buf.len();
    let mut i = 0;
    while i < in_len {
        let b = in_buf[i];
        let mut run = 1usize;
        while i + run < in_len && in_buf[i + run] == b && run < 255 {
            run += 1;
        }
        if run >= 4 || b == FC_RLE_MARKER {
            out_buf.push_u8(FC_RLE_MARKER)?;
            out_buf.push_u8(run as u8)?;
            out_buf.push_u8(b)?;
        } else {
            for _ in 0..run {
                out_buf.push_u8(b)?;
            }
        }
        i += run;
    }
    Ok(())
}

pub fn fc_rle_decompress(in_buf: &[u8], out_buf: &mut FcBuffer) -> Result<(), FcError> {
    let in_len = in_buf.len();
    let mut i = 0;
    while i < in_len {
        let b = in_buf[i];
        if b == FC_RLE_MARKER {
            if i + 2 >= in_len {
                return Err(FcError::Corrupt);
            }
            let count = in_buf[i + 1];
            let val = in_buf[i + 2];
            if count == 0 {
                return Err(FcError::Corrupt);
            }
            if out_buf.len() + (count as usize) > FC_MAX_PAYLOAD {
                return Err(FcError::Bounds);
            }
            for _ in 0..count {
                out_buf.push_u8(val)?;
            }
            i += 3;
        } else {
            if out_buf.len() + 1 > FC_MAX_PAYLOAD {
                return Err(FcError::Bounds);
            }
            out_buf.push_u8(b)?;
            i += 1;
        }
    }
    Ok(())
}
