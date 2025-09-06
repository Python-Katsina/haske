use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;

#[pyfunction]
pub fn render_template<'py>(
    py: Python<'py>,
    template_src: &str,
    context: Bound<'py, PyDict>,
) -> PyResult<String> {
    // First try simple Rust-based template rendering for performance
    if let Ok(result) = render_simple_template(template_src, &context) {
        return Ok(result);
    }

    // Fall back to Python jinja2 for complex templates
    let jinja2 = py.import("jinja2").map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("jinja2 import error: {}", e))
    })?;
    let tmpl_cls = jinja2.getattr("Template").map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Template attr error: {}", e))
    })?;
    let tmpl = tmpl_cls.call1((template_src,)).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Template compile error: {}", e))
    })?;

    // Render with context as kwargs
    let rendered = tmpl
        .call_method("render", (), Some(&context))
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("render error: {}", e))
        })?;
    let s: String = rendered.extract().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "render result conversion error: {}",
            e
        ))
    })?;
    Ok(s)
}

/// Simple Rust-based template rendering for common cases
fn render_simple_template(template_src: &str, context: &Bound<'_, PyDict>) -> PyResult<String> {
    let mut result = template_src.to_string();

    // Handle simple {{ variable }} substitutions
    let re = Regex::new(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}").unwrap();

    for cap in re.captures_iter(template_src) {
        if let Some(var_name) = cap.get(1) {
            let var_name = var_name.as_str();
            if let Ok(Some(value)) = context.get_item(var_name) {
                let value_str = value.str()?.to_str()?.to_string();
                result = result.replace(&cap[0], &value_str);
            }
        }
    }

    Ok(result)
}

/// Pre-compile templates for better performance
#[pyfunction]
pub fn precompile_template(template_src: &str) -> PyResult<String> {
    // Simple template validation and optimization
    if template_src.contains("{%") || template_src.contains("{#") {
        // Complex template that needs Jinja2
        Ok(template_src.to_string())
    } else {
        // Simple template that can be optimized
        let re = Regex::new(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}").unwrap();
        let mut optimized = template_src.to_string();

        // Replace variables with placeholders for faster rendering
        for cap in re.captures_iter(template_src) {
            if let Some(var_name) = cap.get(1) {
                let placeholder = format!("__HASKE_VAR_{}__", var_name.as_str());
                optimized = optimized.replace(&cap[0], &placeholder);
            }
        }

        Ok(optimized)
    }
}
