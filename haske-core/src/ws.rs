use bytes::{BytesMut, Buf, BufMut};
use anyhow::Result;

pub struct WsFrame {
    pub fin: bool,
    pub opcode: u8,
    pub payload: Vec<u8>,
}

pub fn parse_frame(buf: &mut BytesMut) -> Result<Option<WsFrame>> {
    if buf.len() < 2 {
        return Ok(None);
    }

    let b1 = buf[0];
    let b2 = buf[1];
    let fin = b1 & 0x80 != 0;
    let opcode = b1 & 0x0f;
    let mask = b2 & 0x80 != 0;
    let mut payload_len = (b2 & 0x7f) as u64;
    let mut index = 2usize;

    if payload_len == 126 {
        if buf.len() < index + 2 {
            return Ok(None);
        }
        payload_len = ((buf[index] as u64) << 8) | (buf[index + 1] as u64);
        index += 2;
    } else if payload_len == 127 {
        if buf.len() < index + 8 {
            return Ok(None);
        }
        payload_len = 0;
        for i in 0..8 {
            payload_len = (payload_len << 8) | (buf[index + i] as u64);
        }
        index += 8;
    }

    let mask_key = if mask {
        if buf.len() < index + 4 {
            return Ok(None);
        }
        let mk = [buf[index], buf[index + 1], buf[index + 2], buf[index + 3]];
        index += 4;
        Some(mk)
    } else {
        None
    };

    if buf.len() < index + (payload_len as usize) {
        return Ok(None);
    }

    let mut payload = buf[index..index + (payload_len as usize)].to_vec();

    if let Some(mk) = mask_key {
        for i in 0..payload.len() {
            payload[i] ^= mk[i % 4];
        }
    }

    let advance = index + (payload_len as usize);
    buf.advance(advance);

    Ok(Some(WsFrame {
        fin,
        opcode,
        payload,
    }))
}

pub fn build_frame(fin: bool, opcode: u8, payload: &[u8], mask: bool) -> BytesMut {
    let mut out = BytesMut::new();
    let b1 = (if fin { 0x80 } else { 0x00 }) | (opcode & 0x0f);
    out.put_u8(b1);

    let len = payload.len();
    if len < 126 {
        out.put_u8((if mask { 0x80 } else { 0x00 }) | (len as u8));
    } else if len <= 65535 {
        out.put_u8((if mask { 0x80 } else { 0x00 }) | 126);
        out.put_u16(len as u16);
    } else {
        out.put_u8((if mask { 0x80 } else { 0x00 }) | 127);
        out.put_u64(len as u64);
    }

    if mask {
        let mk = [0u8, 0u8, 0u8, 0u8];
        out.extend_from_slice(&mk);
        let mut payload_masked = payload.to_vec();
        for i in 0..payload_masked.len() {
            payload_masked[i] ^= mk[i % 4];
        }
        out.extend_from_slice(&payload_masked);
    } else {
        out.extend_from_slice(payload);
    }

    out
}