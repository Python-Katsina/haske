// haske-core/src/lib.rs
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
use ws::{WebSocketFrame, WebSocketManager, WebSocketReceiver};

// PyO3 module initializer for `_haske_core`.
#[pymodule]
fn _haske_core(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    // Register classes
    m.add_class::<HaskeApp>()?;
    m.add_class::<cache::HaskeCache>()?;
    
    // WebSocket classes
    m.add_class::<WebSocketFrame>()?;
    m.add_class::<WebSocketManager>()?;
    m.add_class::<WebSocketReceiver>()?;

    // Register path functions
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
    m.add_function(wrap_pyfunction!(orm::build_select_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::process_result_set, m)?)?;
    m.add_function(wrap_pyfunction!(orm::get_connection_from_pool, m)?)?;
    m.add_function(wrap_pyfunction!(orm::return_connection_to_pool, m)?)?;
    m.add_function(wrap_pyfunction!(orm::batch_insert, m)?)?;
    m.add_function(wrap_pyfunction!(orm::optimize_type_conversion, m)?)?;
    m.add_function(wrap_pyfunction!(orm::build_update_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::build_delete_query, m)?)?;
    m.add_function(wrap_pyfunction!(orm::validate_query_syntax, m)?)?;
    m.add_function(wrap_pyfunction!(orm::cache_prepared_statement, m)?)?;
    m.add_function(wrap_pyfunction!(orm::get_cached_statement, m)?)?;
    m.add_function(wrap_pyfunction!(orm::clear_statement_cache, m)?)?;

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
    m.add_function(wrap_pyfunction!(ws::validate_websocket_frame, m)?)?;
    m.add_function(wrap_pyfunction!(ws::get_frame_type, m)?)?;
    m.add_function(wrap_pyfunction!(ws::is_final_frame, m)?)?;
    m.add_function(wrap_pyfunction!(ws::is_masked_frame, m)?)?;
    m.add_function(wrap_pyfunction!(ws::get_payload_length, m)?)?;

    // Module metadata
    m.add("__doc__", "Haske core extension: fast routing, json, templates, crypto, orm, websocket helpers.")?;
    m.add("HAS_RUST_EXTENSION", true)?;

    Ok(())
}