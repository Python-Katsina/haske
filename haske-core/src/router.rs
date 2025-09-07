use matchit::Router as MatchRouter;
use parking_lot::RwLock;
use std::sync::Arc;
use anyhow::Result;
use crate::server::{RequestContext, ResponseContext};

pub type Handler = Arc<dyn Fn(RequestContext) -> ResponseContext + Send + Sync + 'static>;

pub struct HaskeRouter {
    inner: RwLock<MatchRouter<Handler>>,
}

impl HaskeRouter {
    pub fn new() -> Self {
        Self { inner: RwLock::new(MatchRouter::new()) }
    }

    /// Insert a route; method is uppercase (GET, POST, ...), path supports matchit params.
    pub fn insert(&self, method: &str, path: &str, handler: Handler) -> Result<()> {
        let key = format!("{}:{}", method.to_uppercase(), path);
        self.inner.write().insert(&key, handler)?;
        Ok(())
    }

    /// Find a handler given method + path. Returns a cloned handler and params.
    pub fn find(&self, method: &str, path: &str) -> Option<(Handler, matchit::Params)> {
        let key = format!("{}:{}", method.to_uppercase(), path);
        if let Ok(m) = self.inner.read().match_with_params(&key) {
            Some((m.value.clone(), m.params))
        } else {
            None
        }
    }
}

impl Default for HaskeRouter {
    fn default() -> Self {
        Self::new()
    }
}