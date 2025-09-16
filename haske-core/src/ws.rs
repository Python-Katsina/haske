// haske_core/src/ws.rs
use pyo3::prelude::*;
use pyo3::types::PyDict;
use bytes::BytesMut;
use base64::{engine::general_purpose, Engine as _};
use sha1::{Sha1, Digest};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// WebSocket frame parser and builder
#[pyclass]
pub struct WebSocketFrame {
    #[pyo3(get)]
    pub opcode: u8,
    #[pyo3(get)]
    pub payload: Vec<u8>,
    #[pyo3(get)]
    pub is_final: bool,
    #[pyo3(get)]
    pub is_masked: bool,
}

#[pymethods]
impl WebSocketFrame {
    #[new]
    pub fn new(opcode: u8, payload: Vec<u8>, is_final: bool, is_masked: bool) -> Self {
        Self { opcode, payload, is_final, is_masked }
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
        let is_masked = (second_byte & 0x80) != 0;
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
            payload_len = ((frame_data[6] as usize) << 24) 
                | ((frame_data[7] as usize) << 16) 
                | ((frame_data[8] as usize) << 8) 
                | (frame_data[9] as usize);
            offset = 10;
        }
        
        // Handle masking key
        let masking_key = if is_masked {
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
        
        if is_masked {
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
            is_masked,
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

    /// Create text frame
    #[staticmethod]
    pub fn text(text: &str) -> Self {
        Self {
            opcode: 1, // TEXT frame
            payload: text.as_bytes().to_vec(),
            is_final: true,
            is_masked: false,
        }
    }

    /// Create binary frame
    #[staticmethod]
    pub fn binary(data: &[u8]) -> Self {
        Self {
            opcode: 2, // BINARY frame
            payload: data.to_vec(),
            is_final: true,
            is_masked: false,
        }
    }

    /// Create close frame
    #[staticmethod]
    pub fn close(code: Option<u16>, reason: Option<&str>) -> Self {
        let mut payload = Vec::new();
        if let Some(code) = code {
            payload.extend_from_slice(&code.to_be_bytes());
        }
        if let Some(reason) = reason {
            payload.extend_from_slice(reason.as_bytes());
        }
        
        Self {
            opcode: 8, // CLOSE frame
            payload,
            is_final: true,
            is_masked: false,
        }
    }

    /// Create ping frame
    #[staticmethod]
    pub fn ping(data: Option<&[u8]>) -> Self {
        Self {
            opcode: 9, // PING frame
            payload: data.unwrap_or_default().to_vec(),
            is_final: true,
            is_masked: false,
        }
    }

    /// Create pong frame
    #[staticmethod]
    pub fn pong(data: Option<&[u8]>) -> Self {
        Self {
            opcode: 10, // PONG frame
            payload: data.unwrap_or_default().to_vec(),
            is_final: true,
            is_masked: false,
        }
    }
}

/// WebSocket connection manager for broadcasting
#[pyclass]
pub struct WebSocketManager {
    channels: Arc<RwLock<HashMap<String, Arc<RwLock<Vec<u8>>>>>>,
}

#[pymethods]
impl WebSocketManager {
    #[new]
    pub fn new() -> Self {
        Self {
            channels: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new channel for a room/group
    pub fn create_channel(&self, channel_id: &str) -> PyResult<()> {
        let mut channels = self.channels.write().unwrap();
        channels.insert(channel_id.to_string(), Arc::new(RwLock::new(Vec::new())));
        Ok(())
    }

    /// Broadcast message to a channel
    pub fn broadcast(&self, channel_id: &str, message: &[u8]) -> PyResult<usize> {
        let channels = self.channels.read().unwrap();
        if let Some(channel) = channels.get(channel_id) {
            let mut channel_data = channel.write().unwrap();
            channel_data.extend_from_slice(message);
            Ok(channel_data.len())
        } else {
            Err(pyo3::exceptions::PyValueError::new_err("Channel not found"))
        }
    }

    /// Get message from a channel
    pub fn get_message(&self, channel_id: &str) -> PyResult<Vec<u8>> {
        let channels = self.channels.read().unwrap();
        if let Some(channel) = channels.get(channel_id) {
            let channel_data = channel.read().unwrap();
            Ok(channel_data.clone())
        } else {
            Err(pyo3::exceptions::PyValueError::new_err("Channel not found"))
        }
    }

    /// Remove a channel
    pub fn remove_channel(&self, channel_id: &str) -> PyResult<()> {
        let mut channels = self.channels.write().unwrap();
        channels.remove(channel_id);
        Ok(())
    }

    /// List all channels
    pub fn list_channels(&self) -> Vec<String> {
        let channels = self.channels.read().unwrap();
        channels.keys().cloned().collect()
    }

    /// Clear all messages in a channel
    pub fn clear_channel(&self, channel_id: &str) -> PyResult<()> {
        let channels = self.channels.read().unwrap();
        if let Some(channel) = channels.get(channel_id) {
            let mut channel_data = channel.write().unwrap();
            channel_data.clear();
            Ok(())
        } else {
            Err(pyo3::exceptions::PyValueError::new_err("Channel not found"))
        }
    }
}

/// WebSocket message receiver
#[pyclass]
pub struct WebSocketReceiver {
    channel_id: String,
    position: usize,
}

#[pymethods]
impl WebSocketReceiver {
    #[new]
    pub fn new(channel_id: String) -> Self {
        Self {
            channel_id,
            position: 0,
        }
    }

    /// Receive next message (non-blocking)
    pub fn recv(&mut self, manager: &WebSocketManager) -> PyResult<Option<Vec<u8>>> {
        let message = manager.get_message(&self.channel_id)?;
        
        if self.position < message.len() {
            let result = Some(message[self.position..].to_vec());
            self.position = message.len();
            Ok(result)
        } else {
            Ok(None)
        }
    }

    /// Get current position
    pub fn get_position(&self) -> usize {
        self.position
    }

    /// Reset position to beginning
    pub fn reset(&mut self) {
        self.position = 0;
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

/// Validate WebSocket frame (Rust-accelerated validation)
#[pyfunction]
pub fn validate_websocket_frame(frame_data: &[u8]) -> bool {
    if frame_data.len() < 2 {
        return false;
    }
    
    let second_byte = frame_data[1];
    let is_masked = (second_byte & 0x80) != 0;
    let mut payload_len = (second_byte & 0x7F) as usize;
    
    if payload_len == 126 {
        if frame_data.len() < 4 {
            return false;
        }
        payload_len = ((frame_data[2] as usize) << 8) | (frame_data[3] as usize);
    } else if payload_len == 127 {
        if frame_data.len() < 10 {
            return false;
        }
        payload_len = ((frame_data[6] as usize) << 24) 
            | ((frame_data[7] as usize) << 16) 
            | ((frame_data[8] as usize) << 8) 
            | (frame_data[9] as usize);
    }
    
    let mut offset = 2;
    if payload_len == 126 {
        offset = 4;
    } else if payload_len == 127 {
        offset = 10;
    }
    
    if is_masked {
        offset += 4;
    }
    
    frame_data.len() >= offset + payload_len
}

/// Fast frame type detection
#[pyfunction]
pub fn get_frame_type(frame_data: &[u8]) -> Option<u8> {
    if frame_data.is_empty() {
        return None;
    }
    Some(frame_data[0] & 0x0F) // Return opcode
}

/// Check if WebSocket frame is final
#[pyfunction]
pub fn is_final_frame(frame_data: &[u8]) -> bool {
    if frame_data.is_empty() {
        return false;
    }
    (frame_data[0] & 0x80) != 0
}

/// Check if WebSocket frame is masked
#[pyfunction]
pub fn is_masked_frame(frame_data: &[u8]) -> bool {
    if frame_data.len() < 2 {
        return false;
    }
    (frame_data[1] & 0x80) != 0
}

/// Extract WebSocket payload length
#[pyfunction]
pub fn get_payload_length(frame_data: &[u8]) -> PyResult<usize> {
    if frame_data.len() < 2 {
        return Err(pyo3::exceptions::PyValueError::new_err("frame too short"));
    }
    
    let second_byte = frame_data[1];
    let mut payload_len = (second_byte & 0x7F) as usize;
    
    if payload_len == 126 {
        if frame_data.len() < 4 {
            return Err(pyo3::exceptions::PyValueError::new_err("invalid frame length"));
        }
        payload_len = ((frame_data[2] as usize) << 8) | (frame_data[3] as usize);
    } else if payload_len == 127 {
        if frame_data.len() < 10 {
            return Err(pyo3::exceptions::PyValueError::new_err("invalid frame length"));
        }
        payload_len = ((frame_data[6] as usize) << 24) 
            | ((frame_data[7] as usize) << 16) 
            | ((frame_data[8] as usize) << 8) 
            | (frame_data[9] as usize);
    }
    
    Ok(payload_len)
}