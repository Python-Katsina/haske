use anyhow::Result;
use serde_json::Value;

#[cfg(feature = "python-handlers")]
use pyo3::prelude::*;
#[cfg(feature = "python-handlers")]
use pyo3::types::{PyDict, PyList};

/// Parse JSON bytes into serde_json::Value.
pub fn parse_json_bytes(data: &[u8]) -> Result<Value> {
    Ok(serde_json::from_slice(data)?)
}

/// Convert serde_json::Value -> PyObject WITHOUT serializing to string.
#[cfg(feature = "python-handlers")]
pub fn serde_value_to_py(py: Python, v: &Value) -> PyObject {
    match v {
        Value::Null => py.None(),
        Value::Bool(b) => b.into_py(py),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_py(py)
            } else if let Some(u) = n.as_u64() {
                u.into_py(py)
            } else {
                n.as_f64().unwrap().into_py(py)
            }
        }
        Value::String(s) => s.into_py(py),
        Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(serde_value_to_py(py, item)).unwrap();
            }
            list.into_py(py)
        }
        Value::Object(map) => {
            let dict = PyDict::new(py);
            for (k, val) in map {
                dict.set_item(k, serde_value_to_py(py, val)).unwrap();
            }
            dict.into_py(py)
        }
    }
}

/// Convert Python object into serde_json::Value (basic conversion).
#[cfg(feature = "python-handlers")]
pub fn py_to_serde_value(py: Python, obj: &pyo3::PyAny) -> Result<Value, pyo3::PyErr> {
    if obj.is_none() {
        return Ok(Value::Null);
    }

    if let Ok(b) = obj.extract::<bool>() {
        return Ok(Value::Bool(b));
    }
    if let Ok(i) = obj.extract::<i64>() {
        return Ok(Value::Number(i.into()));
    }
    if let Ok(f) = obj.extract::<f64>() {
        return Ok(serde_json::Number::from_f64(f)
            .map(Value::Number)
            .unwrap_or(Value::Null));
    }
    if let Ok(s) = obj.extract::<String>() {
        return Ok(Value::String(s));
    }
    if let Ok(bytes) = obj.extract::<Vec<u8>>() {
        return Ok(Value::String(base64::engine::general_purpose::STANDARD.encode(bytes)));
    }
    if let Ok(seq) = obj.downcast::<PyList>() {
        let mut arr = Vec::with_capacity(seq.len());
        for item in seq.iter() {
            arr.push(py_to_serde_value(py, item)?);
        }
        return Ok(Value::Array(arr));
    }
    if let Ok(dict) = obj.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in dict.items() {
            let key = k.extract::<String>()?;
            map.insert(key, py_to_serde_value(py, v)?);
        }
        return Ok(Value::Object(map));
    }

    Ok(Value::String(obj.str()?.to_str()?.to_string()))
}

#[cfg(feature = "python-handlers")]
#[pyfunction]
fn loads(py: Python, data: &[u8]) -> PyResult<PyObject> {
    let v: Value = parse_json_bytes(data).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(serde_value_to_py(py, &v))
}

#[cfg(feature = "python-handlers")]
#[pymodule]
fn haske_json(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(pyo3::wrap_pyfunction!(loads, m)?)?;
    Ok(())
}