use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBool, PyDict, PyFloat, PyInt, PyString};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use once_cell::sync::Lazy;


/// Prepare a single SQL query with named parameters
#[pyfunction]
pub fn prepare_query(
    py: Python<'_>,
    sql: &str,
    params: Py<PyDict>,
) -> PyResult<(String, Vec<Py<PyAny>>)> {
    let mut out = String::new();
    let mut idx = 1usize;
    let bytes = sql.as_bytes();
    let mut i = 0usize;
    let mut vals: Vec<Py<PyAny>> = Vec::new();
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

    let dict = params.bind(py);
    for name in param_names {
        let val = match dict.get_item(name.as_str())? {
            Some(v) => v.into(),
            None => py.None(),
        };
        vals.push(val);
    }
    Ok((out, vals))
}

/// Batch prepare multiple queries
#[pyfunction]
pub fn prepare_queries(
    py: Python<'_>,
    queries: Vec<String>,
    params: Vec<Py<PyAny>>,
) -> PyResult<Vec<(String, Vec<Py<PyAny>>)>> {
    let mut results = Vec::with_capacity(queries.len());
    for (sql, param_dict_any) in queries.into_iter().zip(params.into_iter()) {
        let dict: Py<PyDict> = param_dict_any.extract(py)?;
        results.push(prepare_query(py, &sql, dict)?);
    }
    Ok(results)
}

/// Build SELECT query with clauses
#[pyfunction]
pub fn build_select_query(
    table: &str,
    columns: Vec<String>,
    where_clauses: Vec<String>,
    order_by: Option<String>,
    limit: Option<u32>,
    offset: Option<u32>,
) -> String {
    let mut query = String::with_capacity(256);
    query.push_str("SELECT ");
    if columns.is_empty() {
        query.push_str("*");
    } else {
        query.push_str(&columns.join(", "));
    }
    query.push_str(" FROM ");
    query.push_str(table);
    if !where_clauses.is_empty() {
        query.push_str(" WHERE ");
        query.push_str(&where_clauses.join(" AND "));
    }
    if let Some(order) = order_by {
        query.push_str(" ORDER BY ");
        query.push_str(&order);
    }
    if let Some(lim) = limit {
        query.push_str(&format!(" LIMIT {}", lim));
    }
    if let Some(off) = offset {
        query.push_str(&format!(" OFFSET {}", off));
    }
    query
}

/// Process a result set efficiently
#[pyfunction]
pub fn process_result_set(
    py: Python<'_>,
    results: Vec<Vec<Py<PyAny>>>,
    column_names: Vec<String>,
) -> PyResult<Vec<Py<PyAny>>> {
    let mut processed = Vec::with_capacity(results.len());
    for row in results {
        let dict = PyDict::new(py);
        for (i, value) in row.into_iter().enumerate() {
            if i < column_names.len() {
                dict.set_item(column_names[i].as_str(), value)?;
            }
        }
        processed.push(dict.into());
    }
    Ok(processed)
}

/// Connection pool
static CONNECTION_POOL: Lazy<Arc<Mutex<Vec<Py<PyAny>>>>> =
    Lazy::new(|| Arc::new(Mutex::new(Vec::with_capacity(10))));

#[pyfunction]
pub fn get_connection_from_pool(py: Python<'_>) -> PyResult<Py<PyAny>> {
    let mut pool = CONNECTION_POOL.lock().unwrap();
    if let Some(conn) = pool.pop() {
        Ok(conn)
    } else {
        Ok(py.None())
    }
}

#[pyfunction]
pub fn return_connection_to_pool(conn: Py<PyAny>) -> PyResult<()> {
    let mut pool = CONNECTION_POOL.lock().unwrap();
    pool.push(conn);
    Ok(())
}

/// Batch insert query builder
#[pyfunction]
pub fn batch_insert(
    table: &str,
    columns: Vec<String>,
    values: Vec<Vec<Py<PyAny>>>,
) -> PyResult<String> {
    if values.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("No values provided"));
    }
    if columns.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("No columns provided"));
    }

    let num_columns = columns.len();
    let mut query = String::with_capacity(1024);
    query.push_str("INSERT INTO ");
    query.push_str(table);
    query.push_str(" (");
    query.push_str(&columns.join(", "));
    query.push_str(") VALUES ");

    let mut placeholders = Vec::with_capacity(values.len());
    for (row_idx, row) in values.iter().enumerate() {
        if row.len() != num_columns {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Row {} has {} values, expected {}",
                row_idx + 1,
                row.len(),
                num_columns
            )));
        }
        let placeholder = format!(
            "({})",
            (0..num_columns)
                .map(|i| format!("${}", row_idx * num_columns + i + 1))
                .collect::<Vec<_>>()
                .join(", ")
        );
        placeholders.push(placeholder);
    }
    query.push_str(&placeholders.join(", "));
    Ok(query)
}

/// Optimize type conversion
#[pyfunction]
pub fn optimize_type_conversion(
    py: Python<'_>,
    values: Vec<Py<PyAny>>,
) -> PyResult<Vec<Py<PyAny>>> {
    let mut optimized = Vec::with_capacity(values.len());

    for value in values {
        let any = value.as_ref();

        if let Ok(s) = any.extract::<String>(py) {
            // Integer-like
            if let Ok(i) = s.parse::<i64>() {
                let int_obj = PyInt::new(py, i);
                optimized.push(int_obj.unbind().into());
                continue;
            }

            // Float-like
            if let Ok(f) = s.parse::<f64>() {
                let float_obj = PyFloat::new(py, f);
                optimized.push(float_obj.unbind().into());
                continue;
            }

            // Boolean-like
            if s.eq_ignore_ascii_case("true") {
                let bool_obj = PyBool::new(py, true);
                optimized.push(bool_obj.to_owned().unbind().into());
                continue;
            }
            if s.eq_ignore_ascii_case("false") {
                let bool_obj = PyBool::new(py, false);
                optimized.push(bool_obj.to_owned().unbind().into());
                continue;
            }
            // String fallback
            let string_obj = PyString::new(py, &s);
            optimized.push(string_obj.unbind().into());
        } else {
            optimized.push(value);
        }
    }

    Ok(optimized)
}

/// UPDATE query builder 
#[pyfunction]
pub fn build_update_query(
    table: &str,
    set_clauses: Vec<String>,
    where_clauses: Vec<String>,
) -> String {
    let mut query = String::with_capacity(128);
    query.push_str("UPDATE ");
    query.push_str(table);
    query.push_str(" SET ");
    query.push_str(&set_clauses.join(", "));
    if !where_clauses.is_empty() {
        query.push_str(" WHERE ");
        query.push_str(&where_clauses.join(" AND "));
    }
    query
}

/// DELETE query builder
#[pyfunction]
pub fn build_delete_query(table: &str, where_clauses: Vec<String>) -> String {
    let mut query = String::with_capacity(128);
    query.push_str("DELETE FROM ");
    query.push_str(table);
    if !where_clauses.is_empty() {
        query.push_str(" WHERE ");
        query.push_str(&where_clauses.join(" AND "));
    }
    query
}

/// Validate SQL query syntax
#[pyfunction]
pub fn validate_query_syntax(sql: &str) -> PyResult<bool> {
    let sql_upper = sql.to_uppercase();
    let dangerous_patterns = [
        "--", "/*", "*/", ";", "DROP", "DELETE", "UPDATE", "INSERT", "EXEC", "EXECUTE", "TRUNCATE",
        "ALTER", "CREATE",
    ];
    for pattern in dangerous_patterns.iter() {
        if sql_upper.contains(pattern) && !sql_upper.contains(&format!(" {} ", pattern)) {
            return Ok(false);
        }
    }
    let valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "WITH"];
    Ok(valid_starts.iter().any(|start| sql_upper.starts_with(start)))
}

/// Statement cache
static STATEMENT_CACHE: Lazy<Arc<Mutex<HashMap<String, Arc<Py<PyAny>>>>>> =
    Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

#[pyfunction]
pub fn cache_prepared_statement(statement: Py<PyAny>, sql: String) -> PyResult<()> {
    let mut cache = STATEMENT_CACHE.lock().unwrap();
    cache.insert(sql, Arc::new(statement));
    Ok(())
}

#[pyfunction]
pub fn get_cached_statement(py: Python<'_>, sql: &str) -> PyResult<Option<Py<PyAny>>> {
    let cache = STATEMENT_CACHE.lock().unwrap();
    Ok(cache.get(sql).map(|arc| arc.as_ref().clone_ref(py)))
}

#[pyfunction]
pub fn clear_statement_cache() -> PyResult<usize> {
    let mut cache = STATEMENT_CACHE.lock().unwrap();
    let size = cache.len();
    cache.clear();
    Ok(size)
}