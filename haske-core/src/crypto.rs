use pyo3::prelude::*;
use hmac::{Hmac, Mac};
use sha2::{Sha256, Sha512};
use pbkdf2::pbkdf2;
use base64::{engine::general_purpose, Engine as _};
use rand::RngCore;

type HmacSha256 = Hmac<Sha256>;
type HmacSha512 = Hmac<Sha512>;

#[pyfunction]
pub fn sign_cookie(secret: &str, payload: &str) -> PyResult<String> {
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("{}", e)))?;
    mac.update(payload.as_bytes());
    let code = mac.finalize().into_bytes();
    let pb64 = general_purpose::URL_SAFE_NO_PAD.encode(payload.as_bytes());
    let hb64 = general_purpose::URL_SAFE_NO_PAD.encode(&code);
    Ok(format!("{}.{}", pb64, hb64))
}

#[pyfunction]
pub fn verify_cookie(secret: &str, token: &str) -> PyResult<Option<String>> {
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 2 {
        return Ok(None);
    }
    let payload_b = match general_purpose::URL_SAFE_NO_PAD.decode(parts[0]) {
        Ok(b) => b,
        Err(_) => return Ok(None),
    };
    let sig_b = match general_purpose::URL_SAFE_NO_PAD.decode(parts[1]) {
        Ok(b) => b,
        Err(_) => return Ok(None),
    };
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("{}", e)))?;
    mac.update(&payload_b);
    if mac.verify_slice(&sig_b).is_ok() {
        match String::from_utf8(payload_b) {
            Ok(s) => Ok(Some(s)),
            Err(_) => Ok(None),
        }
    } else {
        Ok(None)
    }
}

/// Hash password using PBKDF2 with SHA256
#[pyfunction]
pub fn hash_password(password: &str, salt: Option<Vec<u8>>) -> PyResult<(Vec<u8>, Vec<u8>)> {
    let mut rng = rand::thread_rng();
    let salt = salt.unwrap_or_else(|| {
        let mut salt = [0u8; 16];
        rng.fill_bytes(&mut salt);
        salt.to_vec()
    });
    
    let mut output = [0u8; 32];
    pbkdf2::<Hmac<Sha256>>(password.as_bytes(), &salt, 100_000, &mut output);
    
    Ok((output.to_vec(), salt))
}

/// Verify password against hash
#[pyfunction]
pub fn verify_password(password: &str, hash: &[u8], salt: &[u8]) -> PyResult<bool> {
    let mut test_hash = [0u8; 32];
    pbkdf2::<Hmac<Sha256>>(password.as_bytes(), salt, 100_000, &mut test_hash);
    
    Ok(constant_time_eq::constant_time_eq(hash, &test_hash))
}

/// Generate cryptographically secure random bytes
#[pyfunction]
pub fn generate_random_bytes(length: usize) -> PyResult<Vec<u8>> {
    let mut rng = rand::thread_rng();
    let mut bytes = vec![0u8; length];
    rng.fill_bytes(&mut bytes);
    Ok(bytes)
}