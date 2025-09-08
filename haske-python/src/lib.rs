use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pymodule]
// #[pyo3(name = "_haske_core")]
fn haske(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    // Import the core module
    let core = PyModule::import(py, "_haske_core")?;

    // Re-export all classes
    m.add("HaskeApp", core.getattr("HaskeApp")?)?;
    m.add("HaskeCache", core.getattr("HaskeCache")?)?;
    m.add("WebSocketFrame", core.getattr("WebSocketFrame")?)?;

    // Re-export all functions with proper names
    let functions = [
        "compile_path", "match_path",
        "json_loads_bytes", "json_dumps_obj", "json_is_valid", "json_extract_field",
        "render_template", "precompile_template",
        "sign_cookie", "verify_cookie", "hash_password", "verify_password", "generate_random_bytes",
        "prepare_query", "prepare_queries",
        "create_cache",
        "gzip_compress", "gzip_decompress", "zstd_compress", "zstd_decompress", 
        "brotli_compress", "brotli_decompress",
        "websocket_accept_key"
    ];

    for func_name in functions.iter() {
        if let Ok(func) = core.getattr(*func_name) {
            m.add(*func_name, func)?;
        }
    }

    // Add build information
    m.add("HAS_RUST_EXTENSION", true)?;
    
    Ok(())
}