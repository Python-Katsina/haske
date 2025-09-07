use parking_lot::RwLock;
use tera::{Tera, Context};
use std::collections::HashMap;
use once_cell::sync::Lazy;
use anyhow::Result;

static TERA_REGISTRY: Lazy<RwLock<HashMap<String, Tera>>> = Lazy::new(|| RwLock::new(HashMap::new()));

/// Register templates from a glob (e.g., "templates/**/*") and precompile.
pub fn register_template_dir(name: &str, glob: &str) -> Result<()> {
    let mut tera = Tera::new(glob)?;
    tera.build_inheritance_chains()?;
    TERA_REGISTRY.write().insert(name.to_string(), tera);
    Ok(())
}

/// Render template using a registered registry name. Falls back to temporary engine if not registered.
pub fn render(name: &str, tpl: &str, ctx: &Context) -> Result<String> {
    if let Some(tera) = TERA_REGISTRY.read().get(name) {
        Ok(tera.render(tpl, ctx)?)
    } else {
        let mut t = Tera::default();
        t.add_raw_template(tpl, tpl)?;
        Ok(t.render(tpl, ctx)?)
    }
}

#[cfg(feature = "python-handlers")]
use pyo3::prelude::*;
#[cfg(feature = "python-handlers")]
use pyo3::types::PyDict;

#[cfg(feature = "python-handlers")]
fn py_dict_to_context(_py: Python, d: &PyDict) -> tera::Context {
    let mut ctx = Context::new();
    for (k, v) in d.items() {
        let key = k.extract::<String>().unwrap_or_else(|_| k.str().unwrap().to_str().unwrap().to_string());
        if v.is_instance_of::<pyo3::types::PyDict>().unwrap_or(false) {
            ctx.insert(&key, &v.str().unwrap().to_string());
        } else if let Ok(s) = v.extract::<String>() {
            ctx.insert(&key, &s);
        } else if let Ok(i) = v.extract::<i64>() {
            ctx.insert(&key, &i);
        } else if let Ok(f) = v.extract::<f64>() {
            ctx.insert(&key, &f);
        } else {
            ctx.insert(&key, &v.str().unwrap().to_string());
        }
    }
    ctx
}

#[cfg(feature = "python-handlers")]
#[pyfunction]
fn register_templates_py(_py: Python, name: &str, glob: &str) -> PyResult<()> {
    register_template_dir(name, glob).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[cfg(feature = "python-handlers")]
#[pyfunction]
fn render_py(_py: Python, name: &str, tpl: &str, ctx: &PyDict) -> PyResult<String> {
    let context = py_dict_to_context(_py, ctx);
    render(name, tpl, &context).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[cfg(feature = "python-handlers")]
#[pymodule]
fn haske_template(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(pyo3::wrap_pyfunction!(register_templates_py, m)?)?;
    m.add_function(pyo3::wrap_pyfunction!(render_py, m)?)?;
    Ok(())
}