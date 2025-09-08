use pyo3::prelude::*;
use regex::Regex;
use parking_lot::RwLock;
use std::sync::Arc;
use std::collections::HashMap;

#[derive(Clone)]
struct RouteEntry {
    method: String,
    regex_src: String,
    regex: Regex,
    param_names: Vec<String>,
    handler: Arc<Py<PyAny>>, // ✅ Arc for cheap clone
}

#[pyclass]
pub struct HaskeApp {
    routes: Arc<RwLock<Vec<RouteEntry>>>,
    route_cache: Arc<RwLock<HashMap<(String, String), (Arc<Py<PyAny>>, PyObject)>>>,
}

#[pymethods]
impl HaskeApp {
    #[new]
    pub fn new() -> Self {
        HaskeApp {
            routes: Arc::new(RwLock::new(Vec::new())),
            route_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Add route: method (GET/POST/ANY), regex src, python handler callback
    pub fn add_route(&self, method: &str, path_regex: &str, handler: Py<PyAny>) -> PyResult<()> {
        let regex = Regex::new(path_regex)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("invalid regex: {}", e)))?;
        let param_names: Vec<String> = regex
            .capture_names()
            .flatten()
            .map(|s| s.to_string())
            .collect();
        let entry = RouteEntry {
            method: method.to_uppercase(),
            regex_src: path_regex.to_string(),
            regex,
            param_names,
            handler: Arc::new(handler), // ✅ store in Arc
        };
        self.routes.write().push(entry);
        self.route_cache.write().clear(); // Clear cache when routes change
        Ok(())
    }

    /// match_request returns (handler, dict-of-params) or None
pub fn match_request<'py>(
    &self,
    py: Python<'py>,
    method: &str,
    path: &str,
) -> PyResult<Option<(PyObject, PyObject)>> {
    // Check cache first
    let cache_key = (method.to_uppercase(), path.to_string());
    {
        let cache = self.route_cache.read();
        if let Some(result) = cache.get(&cache_key) {
            return Ok(Some((
                result.0.as_ref().clone_ref(py),
                result.1.clone_ref(py), // ✅ fixed
            )));
        }
    }

    let routes = self.routes.read();
    for r in routes.iter() {
        if r.method != "ANY" && r.method != method.to_uppercase() {
            continue;
        }
        if let Some(caps) = r.regex.captures(path) {
            let dict = pyo3::types::PyDict::new(py);
            for name in &r.param_names {
                if let Some(m) = caps.name(name) {
                    dict.set_item(name, m.as_str())?;
                }
            }

            let handler = r.handler.as_ref().clone_ref(py);
            let dict_obj: PyObject = dict.into();

            // Cache the result
            let mut cache = self.route_cache.write();
            cache.insert(cache_key, (r.handler.clone(), dict_obj.clone_ref(py))); // ✅ fixed

            return Ok(Some((handler, dict_obj)));
        }
    }
    Ok(None)
}

    /// Get number of registered routes
    pub fn route_count(&self) -> usize {
        self.routes.read().len()
    }

    /// Clear all routes and cache
    pub fn clear_routes(&self) {
        self.routes.write().clear();
        self.route_cache.write().clear();
    }
}
