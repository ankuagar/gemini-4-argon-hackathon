use crate::{
    fc_adler16, fc_crc32, fc_rle_compress, fc_rle_decompress, FcBuffer, FcError, FcHeader,
    FC_FLAG_COMPRESSED, FC_HEADER_SIZE, FC_MAGIC_0, FC_MAGIC_1, FC_MAX_PAYLOAD,
};

pub fn fc_frame_encode(
    version: u8,
    flags: u8,
    seq: u16,
    payload: &[u8],
    out_frame: &mut FcBuffer,
) -> Result<(), FcError> {
    if payload.len() > FC_MAX_PAYLOAD {
        return Err(FcError::Bounds);
    }

    out_frame.clear();

    let crc = fc_crc32(payload);
    let adler = fc_adler16(payload);

    let mut wire_payload = FcBuffer::with_capacity(payload.len() + 16);
    if (flags & FC_FLAG_COMPRESSED) != 0 {
        fc_rle_compress(payload, &mut wire_payload)?;
    } else {
        wire_payload.extend_from_slice(payload)?;
    }

    out_frame.push_u8(FC_MAGIC_0)?;
    out_frame.push_u8(FC_MAGIC_1)?;
    out_frame.push_u8(version)?;
    out_frame.push_u8(flags)?;
    out_frame.push_u16_be(seq)?;
    out_frame.push_u16_be(adler)?;
    out_frame.push_u32_be(crc)?;
    out_frame.push_u16_be(wire_payload.len() as u16)?;
    out_frame.extend_from_slice(wire_payload.as_slice())?;

    Ok(())
}

fn read_u16_be(bytes: &[u8]) -> u16 {
    u16::from_be_bytes([bytes[0], bytes[1]])
}

fn read_u32_be(bytes: &[u8]) -> u32 {
    u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]])
}

pub fn fc_frame_decode(
    frame: &[u8],
    out_payload: &mut FcBuffer,
) -> Result<FcHeader, FcError> {
    if frame.len() < FC_HEADER_SIZE {
        return Err(FcError::Corrupt);
    }
    if frame[0] != FC_MAGIC_0 || frame[1] != FC_MAGIC_1 {
        return Err(FcError::Corrupt);
    }

    let version = frame[2];
    let flags = frame[3];
    let seq = read_u16_be(&frame[4..6]);
    let expected_adler = read_u16_be(&frame[6..8]);
    let expected_crc = read_u32_be(&frame[8..12]);
    let wire_len = read_u16_be(&frame[12..14]) as usize;

    if FC_HEADER_SIZE + wire_len != frame.len() {
        return Err(FcError::Corrupt);
    }

    out_payload.clear();
    let wire_slice = &frame[FC_HEADER_SIZE..];
    if (flags & FC_FLAG_COMPRESSED) != 0 {
        fc_rle_decompress(wire_slice, out_payload)?;
    } else {
        if wire_len > FC_MAX_PAYLOAD {
            return Err(FcError::Bounds);
        }
        out_payload.extend_from_slice(wire_slice)?;
    }

    let actual_crc = fc_crc32(out_payload.as_slice());
    let actual_adler = fc_adler16(out_payload.as_slice());
    if actual_crc != expected_crc || actual_adler != expected_adler {
        return Err(FcError::Crc);
    }

    Ok(FcHeader {
        version,
        flags,
        seq,
        adler16: actual_adler,
        payload_crc: actual_crc,
        payload_len: out_payload.len() as u32,
    })
}
