# haske/cache.py
"""
Cache utilities for Haske framework with Rust acceleration.

This module provides high-performance caching using Rust-accelerated
cache implementation with automatic fallback to Python.
"""

from typing import Any, Optional, Union
import time

# Import Rust cache if available
try:
    from _haske_core import HaskeCache as RustCache
    HAS_RUST_CACHE = True
except ImportError:
    HAS_RUST_CACHE = False

class Cache:
    """
    High-performance cache with Rust acceleration.
    
    Provides a unified interface for caching with automatic fallback
    to Python implementation if Rust extensions are not available.
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live in seconds for cache items
        """
        if HAS_RUST_CACHE:
            self._rust_cache = RustCache(max_size, ttl)
            self._fallback_cache = None
        else:
            self._rust_cache = None
            self._fallback_cache = {}
            self._max_size = max_size
            self._ttl = ttl
            self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found/expired
        """
        if self._rust_cache is not None:
            return self._rust_cache.get(key)
        else:
            # Fallback Python implementation
            if key not in self._fallback_cache:
                return None
                
            # Check if expired
            if time.time() - self._timestamps[key] > self._ttl:
                self.delete(key)
                return None
                
            return self._fallback_cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if self._rust_cache is not None:
            self._rust_cache.set(key, value)
        else:
            # Fallback Python implementation
            # Check if we need to evict due to size
            if len(self._fallback_cache) >= self._max_size:
                # Remove oldest item
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                self.delete(oldest_key)
            
            self._fallback_cache[key] = value
            self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """
        Delete item from cache.
        
        Args:
            key: Cache key to delete
        """
        if self._rust_cache is not None:
            self._rust_cache.delete(key)
        else:
            # Fallback Python implementation
            if key in self._fallback_cache:
                del self._fallback_cache[key]
                del self._timestamps[key]
    
    def clear(self) -> None:
        """
        Clear all items from cache.
        """
        if self._rust_cache is not None:
            self._rust_cache.clear()
        else:
            # Fallback Python implementation
            self._fallback_cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        """
        Get current cache size.
        
        Returns:
            int: Number of items in cache
        """
        if self._rust_cache is not None:
            return self._rust_cache.size()
        else:
            return len(self._fallback_cache)

# Global cache instance
_default_cache = None

def get_default_cache() -> Cache:
    """
    Get the default global cache instance.
    
    Returns:
        Cache: Default cache instance
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = Cache()
    return _default_cache