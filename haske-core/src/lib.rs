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

/// Python module `_haske_core`
/// Register functions and classes from submodules.
#[pymodule]
fn _haske_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Classes
    m.add_class::<router::HaskeApp>()?;
    m.add_class::<cache::HaskeCache>()?;
    m.add_class::<ws::WebSocketFrame>()?;

    // path
    m.add_function(wrap_pyfunction!(path::compile_path, m)?)?;
    m.add_function(wrap_pyfunction!(path::match_path, m)?)?;

    // json
    m.add_function(wrap_pyfunction!(json::json_loads_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_dumps_obj, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(json::json_extract_field, m)?)?;

    // template
    m.add_function(wrap_pyfunction!(template::render_template, m)?)?;
    m.add_function(wrap_pyfunction!(template::precompile_template, m)?)?;

    // crypto
    m.add_function(wrap_pyfunction!(crypto::sign_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_cookie, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(crypto::generate_random_bytes, m)?)?;

    // orm
    m.add_function(wrap_pyfunction!(orm::prepare_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::prepare_queries, m)?)?;

    // cache
    m.add_function(wrap_pyfunction!(cache::create_cache, m)?)?;

    // compression
    m.add_function(wrap_pyfunction!(compress::gzip_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::gzip_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::zstd_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress::brotli_decompress, m)?)?;

    // websocket
    m.add_function(wrap_pyfunction!(ws::websocket_accept_key, m)?)?;

    m.add("__doc__", "Haske core extension: fast routing, json, templates, crypto, orm helpers.")?;
    Ok(())
}