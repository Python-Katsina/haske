use pyo3::prelude::*;

mod path;
mod router;
mod json;
mod template;
mod crypto;
mod orm;
mod cache;
mod compress;
mod ws;

#[pymodule]
fn _haske_core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // Register classes
    m.add_class::<router::HaskeApp>()?;
    m.add_class::<cache::HaskeCache>()?;
    m.add_class::<ws::WebSocketFrame>()?;

    // Path functions
    m.add_function(wrap_pyfunction!(path::compile_path, m)?)?;
    m.add_function(wrap_pyfunction!(path::match_path, m)?)?;

    // JSON functions
    m.add_function(wrap_pyfunction!(json::json_loads_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_dumps_obj, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_extract_field, m)?)?;

    // Template functions
    m.add_function(wrap_pyfunction!(template::render_template, m)?)?;
    m.add_function(wrap_pyfunction!(template::precompile_template, m)?)?;

    // Crypto functions
    m.add_function(wrap_pyfunction!(crypto::sign_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::generate_random_bytes, m)?)?;

    // ORM functions
    m.add_function(wrap_pyfunction!(orm::prepare_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::prepare_queries, m)?)?;

    // Cache functions
    m.add_function(wrap_pyfunction!(cache::create_cache, m)?)?;

    // Compression functions
    m.add_function(wrap_pyfunction!(compress::gzip_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::gzip_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_decompress, m)?)?;

    // WebSocket functions
    m.add_function(wrap_pyfunction!(ws::websocket_accept_key, m)?)?;

    m.add("__doc__", "Haske core extension: fast routing, json, templates, crypto, orm helpers.")?;
    Ok(())
}