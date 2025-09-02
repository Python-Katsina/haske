use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pymodule]
fn haske(py: Python, m: &PyModule) -> PyResult<()> {
    // Import the compiled core module
    let core = PyModule::import(py, "_haske_core")?;

    // Re-export HaskeApp class
    m.add("HaskeApp", core.getattr("HaskeApp")?)?;

    // Re-export functions
    m.add("compile_path", core.getattr("compile_path")?)?;
    m.add("json_loads_bytes", core.getattr("json_loads_bytes")?)?;
    m.add("json_dumps_obj", core.getattr("json_dumps_obj")?)?;
    m.add("render_template", core.getattr("render_template")?)?;
    m.add("sign_cookie", core.getattr("sign_cookie")?)?;
    m.add("verify_cookie", core.getattr("verify_cookie")?)?;
    m.add("prepare_query", core.getattr("prepare_query")?)?;

    // Add documentation
    m.add("__doc__", "Haske framework Python bindings (built on _haske_core)")?;
    Ok(())
}
