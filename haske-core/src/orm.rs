use pyo3::prelude::*;
use pyo3::types::PyDict;

/// prepare_query("SELECT * FROM users WHERE id = :id", {"id": 1})
/// -> ("SELECT * FROM users WHERE id = $1", [1])
#[pyfunction]
pub fn prepare_query(
    py: Python<'_>,
    sql: &str,
    params: Bound<'_, PyDict>,
) -> PyResult<(String, Vec<PyObject>)> {
    let mut out = String::new();
    let mut idx = 1usize;
    let bytes = sql.as_bytes();
    let mut i = 0usize;
    let mut vals: Vec<PyObject> = Vec::new();
    let mut param_names = Vec::new();

    while i < bytes.len() {
        let ch = bytes[i] as char;
        if ch == ':' {
            i += 1;
            let mut name = String::new();
            while i < bytes.len() {
                let c = bytes[i] as char;
                if c.is_alphanumeric() || c == '_' {
                    name.push(c);
                    i += 1;
                } else {
                    break;
                }
            }
            if name.is_empty() {
                return Err(pyo3::exceptions::PyValueError::new_err("empty param name"));
            }

            out.push_str(&format!("${}", idx));
            idx += 1;
            param_names.push(name);
        } else {
            out.push(ch);
            i += 1;
        }
    }

    // Get parameters in the order they appear in the query
    for name in param_names {
        match params.get_item(name.as_str()) {
            Ok(Some(val)) => vals.push(val.unbind()), // Bound -> PyObject
            Ok(None) => vals.push(py.None().into()),  // None -> PyObject
            Err(_) => {
                return Err(pyo3::exceptions::PyKeyError::new_err(format!(
                    "parameter '{}' not found",
                    name
                )))
            }
        }
    }

    Ok((out, vals))
}

/// Batch prepare multiple queries for better performance
#[pyfunction]
pub fn prepare_queries(
    py: Python<'_>,
    queries: Vec<String>,
    params: Vec<Bound<'_, PyDict>>,
) -> PyResult<Vec<(String, Vec<PyObject>)>> {
    let mut results = Vec::with_capacity(queries.len());
    for (sql, param_dict) in queries.into_iter().zip(params.into_iter()) {
        results.push(prepare_query(py, &sql, param_dict)?);
    }
    Ok(results)
}
