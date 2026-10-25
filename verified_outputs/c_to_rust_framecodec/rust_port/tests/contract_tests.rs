use framecodec::{
    fc_adler16, fc_crc32, fc_frame_decode, fc_frame_encode, fc_rle_compress, fc_rle_decompress,
    FcBuffer, FcError, FC_FLAG_COMPRESSED, FC_MAX_PAYLOAD, FC_RLE_MARKER,
};

#[test]
fn test_crc32_and_adler16_vectors() {
    assert_eq!(fc_crc32(b""), 0x0000_0000);
    assert_eq!(fc_crc32(b"123456789"), 0xCBF4_3926);
    assert_eq!(fc_adler16(b""), 0x0001);
    assert_eq!(fc_adler16(b"ABCD"), 0x019E);
}

#[test]
fn test_rle_roundtrip_and_marker_escaping() {
    let mut input = Vec::new();
    input.extend_from_slice(&[0x41; 10]); // Run of 10 'A's -> compressed
    input.extend_from_slice(&[0x10, 0x20, FC_RLE_MARKER, 0x30]); // Literal 0xFF marker
    input.extend_from_slice(&[0x99; 300]); // Run > 255 split into 255 + 45

    let mut compressed = FcBuffer::with_capacity(64);
    fc_rle_compress(&input, &mut compressed).expect("compress should succeed");
    assert!(compressed.as_slice().len() < input.len());

    let mut decompressed = FcBuffer::with_capacity(64);
    fc_rle_decompress(compressed.as_slice(), &mut decompressed).expect("decompress should succeed");
    assert_eq!(decompressed.as_slice(), input.as_slice());
}

#[test]
fn test_rle_corrupt_inputs() {
    let mut out = FcBuffer::with_capacity(16);
    // Truncated escape sequence
    assert_eq!(fc_rle_decompress(&[0xFF, 0x05], &mut out), Err(FcError::Corrupt));
    // Zero count escape sequence
    let mut out2 = FcBuffer::with_capacity(16);
    assert_eq!(fc_rle_decompress(&[0xFF, 0x00, 0x41], &mut out2), Err(FcError::Corrupt));
}

#[test]
fn test_frame_encode_decode_compressed_and_uncompressed() {
    let payload = b"AAAABBBBCCCCDDDD_GEMINI_4_ARGON_telemetry_packet_\xFF\xFF\xFF\xFF";
    for flags in [0u8, FC_FLAG_COMPRESSED] {
        let mut frame = FcBuffer::with_capacity(128);
        fc_frame_encode(2, flags, 1042, payload, &mut frame).expect("encode ok");

        let mut decoded = FcBuffer::with_capacity(128);
        let hdr = fc_frame_decode(frame.as_slice(), &mut decoded).expect("decode ok");
        assert_eq!(hdr.version, 2);
        assert_eq!(hdr.flags, flags);
        assert_eq!(hdr.seq, 1042);
        assert_eq!(hdr.payload_len as usize, payload.len());
        assert_eq!(hdr.payload_crc, fc_crc32(payload));
        assert_eq!(hdr.adler16, fc_adler16(payload));
        assert_eq!(decoded.as_slice(), payload);
    }
}

#[test]
fn test_frame_tamper_and_bounds_detection() {
    let payload = vec![0x55u8; 128];
    let mut frame = FcBuffer::with_capacity(256);
    fc_frame_encode(1, FC_FLAG_COMPRESSED, 7, &payload, &mut frame).unwrap();

    let mut corrupted = frame.as_slice().to_vec();
    // Flip a bit in the expected CRC header field (bytes 8..12)
    corrupted[9] ^= 0x01;
    let mut out = FcBuffer::with_capacity(128);
    assert_eq!(fc_frame_decode(&corrupted, &mut out), Err(FcError::Crc));

    // Oversized payload > FC_MAX_PAYLOAD
    let huge = vec![0xAAu8; FC_MAX_PAYLOAD + 1];
    let mut out_huge = FcBuffer::with_capacity(64);
    assert_eq!(fc_frame_encode(1, 0, 1, &huge, &mut out_huge), Err(FcError::Bounds));
}
