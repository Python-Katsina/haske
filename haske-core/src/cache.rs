use moka::sync::Cache;
use pyo3::prelude::*;

#[pyclass]
pub struct HaskeCache {
    inner: Cache<String, String>,
}

#[pymethods]
impl HaskeCache {
    #[new]
    pub fn new(max_capacity: u64, time_to_live: u64) -> Self {
        let cache = Cache::builder()
            .max_capacity(max_capacity)
            .time_to_live(std::time::Duration::from_secs(time_to_live))
            .build();
        Self { inner: cache }
    }

    pub fn get(&self, key: &str) -> Option<String> {
        self.inner.get(key)
    }

    pub fn insert(&self, key: &str, value: &str) {
        self.inner.insert(key.to_string(), value.to_string());
    }

    pub fn remove(&self, key: &str) {
        self.inner.invalidate(key);
    }

    pub fn clear(&self) {
        self.inner.invalidate_all();
    }

    pub fn len(&self) -> usize {
        self.inner.entry_count() as usize
    }

    pub fn is_empty(&self) -> bool {
        self.inner.entry_count() == 0
    }
}

#[pyfunction]
pub fn create_cache(max_capacity: u64, time_to_live: u64) -> PyResult<HaskeCache> {
    Ok(HaskeCache::new(max_capacity, time_to_live))
}