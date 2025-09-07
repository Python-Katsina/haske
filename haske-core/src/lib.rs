//! Haske core: Rust-first implementation
#![deny(clippy::all)]

pub mod json;
pub mod template;
pub mod router;
pub mod ws;
pub mod server;
pub mod cache;
pub mod crypto;
pub mod compress;
pub mod path;
pub mod orm;

#[cfg(feature = "python-handlers")]
pub mod python_bridge;