use dashmap::DashMap;
use std::time::{Instant, Duration};
use std::sync::Arc;
use tokio::task;

#[derive(Clone)]
pub struct CacheValue {
    pub expires: Option<Instant>,
    pub bytes: Vec<u8>,
}

#[derive(Clone)]
pub struct SimpleCache {
    map: Arc<DashMap<String, CacheValue>>,
}

impl SimpleCache {
    pub fn new() -> Self {
        let c = Self { map: Arc::new(DashMap::new()) };
        let m = c.map.clone();
        task::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            loop {
                interval.tick().await;
                let now = Instant::now();
                let expired: Vec<String> = m
                    .iter()
                    .filter_map(|kv| {
                        if let Some(ex) = kv.value().expires {
                            if ex <= now {
                                Some(kv.key().clone())
                            } else {
                                None
                            }
                        } else {
                            None
                        }
                    })
                    .collect();

                for k in expired {
                    m.remove(&k);
                }
            }
        });
        c
    }

    pub fn set(&self, key: String, bytes: Vec<u8>, ttl: Option<Duration>) {
        let expires = ttl.map(|t| Instant::now() + t);
        self.map.insert(key, CacheValue { expires, bytes });
    }

    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.map.get(key).map(|v| v.bytes.clone())
    }

    pub fn remove(&self, key: &str) {
        self.map.remove(key);
    }

    pub fn clear(&self) {
        self.map.clear();
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}