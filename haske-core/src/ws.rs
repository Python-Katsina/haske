use pyo3::prelude::*;
use bytes::BytesMut;  // Removed unused Bytes import
use base64::{engine::general_purpose, Engine as _};
use sha1::{Sha1, Digest};

/// WebSocket frame parser and builder
#[pyclass]
pub struct WebSocketFrame {
    #[pyo3(get)]
    opcode: u8,
    #[pyo3(get)]
    payload: Vec<u8>,
    #[pyo3(get)]
    is_final: bool,
}

#[pymethods]
impl WebSocketFrame {
    #[new]
    pub fn new(opcode: u8, payload: Vec<u8>, is_final: bool) -> Self {
        Self { opcode, payload, is_final }
    }

    /// Parse a WebSocket frame from bytes
    #[staticmethod]
    pub fn parse(frame_data: &[u8]) -> PyResult<Self> {
        if frame_data.len() < 2 {
            return Err(pyo3::exceptions::PyValueError::new_err("frame too short"));
        }
        
        let first_byte = frame_data[0];
        let second_byte = frame_data[1];
        
        let is_final = (first_byte & 0x80) != 0;
        let opcode = first_byte & 0x0F;
        let has_mask = (second_byte & 0x80) != 0;
        let mut payload_len = (second_byte & 0x7F) as usize;
        
        let mut offset = 2;
        
        // Handle extended payload length
        if payload_len == 126 {
            if frame_data.len() < 4 {
                return Err(pyo3::exceptions::PyValueError::new_err("invalid frame length"));
            }
            payload_len = ((frame_data[2] as usize) << 8) | (frame_data[3] as usize);
            offset = 4;
        } else if payload_len == 127 {
            if frame_data.len() < 10 {
                return Err(pyo3::exceptions::PyValueError::new_err("invalid frame length"));
            }
            // For 64-bit length, we use the last 4 bytes (32-bit systems)
            payload_len = ((frame_data[6] as usize) << 24) 
                | ((frame_data[7] as usize) << 16) 
                | ((frame_data[8] as usize) << 8) 
                | (frame_data[9] as usize);
            offset = 10;
        }
        
        // Handle masking key
        let masking_key = if has_mask {
            if frame_data.len() < offset + 4 {
                return Err(pyo3::exceptions::PyValueError::new_err("invalid mask length"));
            }
            Some([
                frame_data[offset],
                frame_data[offset + 1],
                frame_data[offset + 2],
                frame_data[offset + 3],
            ])
        } else {
            None
        };
        
        if has_mask {
            offset += 4;
        }
        
        // Check if we have enough data for the payload
        if frame_data.len() < offset + payload_len {
            return Err(pyo3::exceptions::PyValueError::new_err("incomplete frame"));
        }
        
        // Extract and unmask payload if necessary
        let mut payload = frame_data[offset..offset + payload_len].to_vec();
        
        if let Some(mask) = masking_key {
            for i in 0..payload.len() {
                payload[i] ^= mask[i % 4];
            }
        }
        
        Ok(Self {
            opcode,
            payload,
            is_final,
        })
    }

    /// Convert to bytes for sending
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut frame = BytesMut::new();
        let first_byte = if self.is_final { 0x80 } else { 0x00 } | (self.opcode & 0x0F);
        frame.extend_from_slice(&[first_byte]);
        
        if self.payload.len() <= 125 {
            frame.extend_from_slice(&[self.payload.len() as u8]);
        } else if self.payload.len() <= 65535 {
            frame.extend_from_slice(&[126]);
            frame.extend_from_slice(&[(self.payload.len() >> 8) as u8, self.payload.len() as u8]);
        } else {
            frame.extend_from_slice(&[127]);
            // For 64-bit length, we send 8 bytes (big-endian)
            let len = self.payload.len() as u64;
            frame.extend_from_slice(&[
                (len >> 56) as u8,
                (len >> 48) as u8,
                (len >> 40) as u8,
                (len >> 32) as u8,
                (len >> 24) as u8,
                (len >> 16) as u8,
                (len >> 8) as u8,
                len as u8,
            ]);
        }
        
        frame.extend_from_slice(&self.payload);
        frame.to_vec()
    }
}

/// Generate WebSocket accept key for handshake
#[pyfunction]
pub fn websocket_accept_key(key: &str) -> String {
    const WS_GUID: &str = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    let mut hasher = Sha1::new();
    hasher.update(key);
    hasher.update(WS_GUID);
    let result = hasher.finalize();
    
    general_purpose::STANDARD.encode(result)
}