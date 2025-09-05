use pyo3::prelude::*;
use pyo3::types::PyBytes;
use serde_json::Value;

#[cfg(feature = "simd")]
use simd_json;

#[pyfunction]
pub fn json_loads_bytes(py: Python<'_>, data: Py<PyBytes>) -> PyResult<Option<PyObject>> {
    // PyO3 0.26: bind before accessing bytes
    let buf = data.bind(py).as_bytes();

    // Try to parse using simd-json if enabled, otherwise serde_json
    #[cfg(feature = "simd")]
    let maybe_v = {
        let mut copied = buf.to_vec();
        simd_json::to_owned_value(&mut copied).ok()
    };

    #[cfg(not(feature = "simd"))]
    let maybe_v = serde_json::from_slice::<Value>(buf).ok();

    if let Some(v) = maybe_v {
        // Convert Value -> string -> Python object via json.loads
        match serde_json::to_string(&v) {
            Ok(s) => {
                let json_mod = py.import("json")?;
                let loads = json_mod.getattr("loads")?;
                let obj = loads.call1((s,))?;          // Bound<'py, PyAny>
                Ok(Some(obj.unbind()))                 // -> PyObject (Py<PyAny>)
            }
            Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "serialize error: {}",
                e
            ))),
        }
    } else {
        Ok(None)
    }
}

#[pyfunction]
pub fn json_dumps_obj(py: Python<'_>, obj: PyObject) -> PyResult<Option<String>> {
    // Use Python's json.dumps for generic PyObject -> JSON string
    let json_mod = py.import("json")?;
    let dumps = json_mod.getattr("dumps")?;
    let res = dumps.call1((obj.bind(py),))?; // bind PyObject for the call
    let s: String = res.extract()?;
    Ok(Some(s))
}

/// Fast JSON validation without full parsing
#[pyfunction]
pub fn json_is_valid(data: &[u8]) -> bool {
    #[cfg(feature = "simd")]
    {
        let mut copied = data.to_vec();
        simd_json::to_owned_value(&mut copied).is_ok()
    }

    #[cfg(not(feature = "simd"))]
    {
        serde_json::from_slice::<Value>(data).is_ok()
    }
}

/// Extract specific top-level field from JSON without full parsing result exposure
#[pyfunction]
pub fn json_extract_field(data: &[u8], field: &str) -> PyResult<Option<String>> {
    #[cfg(feature = "simd")]
    {
        let mut copied = data.to_vec();
        if let Ok(mut value) = simd_json::to_owned_value(&mut copied) {
            if let Some(field_value) = value.get_mut(field) {
                return Ok(Some(field_value.to_string()));
            }
        }
    }

    #[cfg(not(feature = "simd"))]
    {
        if let Ok(value) = serde_json::from_slice::<Value>(data) {
            if let Some(field_value) = value.get(field) {
                return Ok(Some(field_value.to_string()));
            }
        }
    }

    Ok(None)
}
