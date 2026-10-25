use framecodec::{
    fc_adler16, fc_crc32, fc_frame_decode, fc_frame_encode, FcBuffer, FcHeader,
};
use std::env;

fn decode_hex(hex: &str) -> Vec<u8> {
    let bytes = hex.as_bytes();
    let mut out = Vec::with_capacity(bytes.len() / 2);
    let mut i = 0;
    while i + 1 < bytes.len() {
        let hi = (bytes[i] as char).to_digit(16);
        let lo = (bytes[i + 1] as char).to_digit(16);
        if let (Some(h), Some(l)) = (hi, lo) {
            out.push(((h << 4) | l) as u8);
        } else {
            break;
        }
        i += 2;
    }
    out
}

fn to_hex(data: &[u8]) -> String {
    let mut s = String::with_capacity(data.len() * 2);
    for b in data {
        s.push_str(&format!("{:02x}", b));
    }
    s
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        std::process::exit(2);
    }

    match args[1].as_str() {
        "encode" => {
            if args.len() < 6 {
                std::process::exit(2);
            }
            let version: u8 = args[2].parse::<i32>().unwrap_or(0) as u8;
            let flags: u8 = args[3].parse::<i32>().unwrap_or(0) as u8;
            let seq: u16 = args[4].parse::<i32>().unwrap_or(0) as u16;
            let payload = decode_hex(&args[5]);

            let mut frame = FcBuffer::with_capacity(128);
            let res = fc_frame_encode(version, flags, seq, &payload, &mut frame);
            let rc = match res {
                Ok(()) => 0,
                Err(e) => e.code(),
            };
            print!(
                "rc={} crc={:08x} adler={:04x} frame=",
                rc,
                fc_crc32(&payload),
                fc_adler16(&payload)
            );
            if rc == 0 {
                print!("{}", to_hex(frame.as_slice()));
            }
            println!();
        }
        "decode" => {
            let frame = decode_hex(&args[2]);
            let mut payload = FcBuffer::with_capacity(128);
            match fc_frame_decode(&frame, &mut payload) {
                Ok(hdr) => {
                    println!(
                        "rc=0 ver={} flags={} seq={} crc={:08x} adler={:04x} len={} payload={}",
                        hdr.version,
                        hdr.flags,
                        hdr.seq,
                        hdr.payload_crc,
                        hdr.adler16,
                        hdr.payload_len,
                        to_hex(payload.as_slice())
                    );
                }
                Err(e) => {
                    let hdr = FcHeader::default();
                    println!(
                        "rc={} ver={} flags={} seq={} crc={:08x} adler={:04x} len={} payload=",
                        e.code(),
                        hdr.version,
                        hdr.flags,
                        hdr.seq,
                        hdr.payload_crc,
                        hdr.adler16,
                        hdr.payload_len
                    );
                }
            }
        }
        _ => std::process::exit(2),
    }
}
