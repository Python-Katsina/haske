// PyO3 v0.26 compatible module bootstrap for the Haske core extension

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pyo3::types::PyModule;

mod path;
mod router;
mod json;
mod template;
mod crypto;
mod orm;
mod cache;
mod compress;
mod ws;

use router::HaskeApp;


// PyO3 module initializer for `_haske_core`.
// Make sure this name matches `lib.name` in Cargo.toml and `module-name` in pyproject.toml.
#[pymodule]
fn _haske_core(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    // Register classes (assumes router::HaskeApp, cache::HaskeCache, ws::WebSocketFrame are declared with #[pyclass])
    m.add_class::<HaskeApp>()?;
    m.add_class::<cache::HaskeCache>()?;
    m.add_class::<ws::WebSocketFrame>()?;

    // Register path functions (assumes #[pyfunction] on these functions)
    m.add_function(wrap_pyfunction!(path::compile_path, m)?)?;
    m.add_function(wrap_pyfunction!(path::match_path, m)?)?;

    // JSON helpers
    m.add_function(wrap_pyfunction!(json::json_loads_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_dumps_obj, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_extract_field, m)?)?;

    // Template helpers
    m.add_function(wrap_pyfunction!(template::render_template, m)?)?;
    m.add_function(wrap_pyfunction!(template::precompile_template, m)?)?;

    // Crypto helpers
    m.add_function(wrap_pyfunction!(crypto::sign_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::generate_random_bytes, m)?)?;

    // ORM helpers
    m.add_function(wrap_pyfunction!(orm::prepare_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::prepare_queries, m)?)?;

    // Cache helpers
    m.add_function(wrap_pyfunction!(cache::create_cache, m)?)?;

    // Compression helpers
    m.add_function(wrap_pyfunction!(compress::gzip_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::gzip_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_decompress, m)?)?;

    // WebSocket helpers
    m.add_function(wrap_pyfunction!(ws::websocket_accept_key, m)?)?;

    // Module metadata (docstring and a boolean flag)
    m.add("__doc__", "Haske core extension: fast routing, json, templates, crypto, orm helpers.")?;
    m.add("HAS_RUST_EXTENSION", true)?;

    Ok(())
}
