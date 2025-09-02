use pyo3::prelude::*;
use flate2::{Compression, write::GzEncoder, read::GzDecoder};
use std::io::{Write, Read};

/// Compress data using gzip
#[pyfunction]
pub fn gzip_compress(data: &[u8], level: Option<u32>) -> PyResult<Vec<u8>> {
    let compression_level = level.map(Compression::new).unwrap_or(Compression::default());
    let mut encoder = GzEncoder::new(Vec::new(), compression_level);
    encoder.write_all(data)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("gzip compression error: {}", e)))?;
    encoder.finish()
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("gzip compression error: {}", e)))
}

/// Decompress gzip data
#[pyfunction]
pub fn gzip_decompress(data: &[u8]) -> PyResult<Vec<u8>> {
    let mut decoder = GzDecoder::new(data);
    let mut result = Vec::new();
    decoder.read_to_end(&mut result)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("gzip decompression error: {}", e)))?;
    Ok(result)
}

/// Compress data using zstd
#[pyfunction]
pub fn zstd_compress(data: &[u8], level: Option<i32>) -> PyResult<Vec<u8>> {
    let compression_level = level.unwrap_or(3);
    zstd::encode_all(data, compression_level)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("zstd compression error: {}", e)))
}

/// Decompress zstd data
#[pyfunction]
pub fn zstd_decompress(data: &[u8]) -> PyResult<Vec<u8>> {
    zstd::decode_all(data)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("zstd decompression error: {}", e)))
}

/// Compress data using brotli - fixed implementation
#[pyfunction]
pub fn brotli_compress(data: &[u8], level: Option<u32>) -> PyResult<Vec<u8>> {
    let compression_level = level.unwrap_or(5);
    let mut result = Vec::new();
    
    {
        let mut writer = brotli::CompressorWriter::new(&mut result, 4096, compression_level, 22);
        writer.write_all(data)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("brotli compression error: {}", e)))?;
        writer.flush()
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("brotli compression error: {}", e)))?;
    } // writer is dropped here, so we can use result
    
    Ok(result)
}

/// Decompress brotli data
#[pyfunction]
pub fn brotli_decompress(data: &[u8]) -> PyResult<Vec<u8>> {
    let mut result = Vec::new();
    let mut reader = brotli::Decompressor::new(data, 4096);
    reader.read_to_end(&mut result)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("brotli decompression error: {}", e)))?;
    Ok(result)
}