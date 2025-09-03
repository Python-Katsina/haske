# haske/middleware.py
"""
Middleware factories and utilities for Haske framework.

This module provides middleware factories for common middleware patterns
and custom middleware implementations for enhanced functionality.
"""

import time
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from typing import Callable, Any

class Middleware(StarletteMiddleware):
    """
    Haske Middleware wrapper around Starlette's Middleware.
    
    Provides a consistent interface for middleware configuration.
    """

    def __init__(self, cls, **options):
        """
        Initialize middleware.
        
        Args:
            cls: Middleware class
            **options: Middleware configuration options
        """
        super().__init__(cls, **options)

class SessionMiddlewareFactory:
    """
    Factory for creating SessionMiddleware with options.
    
    Simplifies session middleware configuration with sensible defaults.
    
    Example:
        Middleware(SessionMiddlewareFactory(secret_key="..."))
    """

    def __init__(self, secret_key: str, **options):
        """
        Initialize session middleware factory.
        
        Args:
            secret_key: Secret key for session encryption
            **options: Additional session middleware options
        """
        self.secret_key = secret_key
        self.options = options

    def __call__(self):
        """
        Create session middleware instance.
        
        Returns:
            tuple: (Middleware class, options dictionary)
        """
        return SessionMiddleware, {"secret_key": self.secret_key, **self.options}

class CORSMiddlewareFactory:
    """
    Factory for CORS middleware configuration.
    
    Provides convenient defaults for Cross-Origin Resource Sharing.
    """
    
    def __init__(self, allow_origins=None, allow_methods=None, allow_headers=None, 
                 allow_credentials=False, max_age=600):
        """
        Initialize CORS middleware factory.
        
        Args:
            allow_origins: List of allowed origins, defaults to ["*"]
            allow_methods: List of allowed HTTP methods, defaults to common methods
            allow_headers: List of allowed headers, defaults to ["*"]
            allow_credentials: Allow credentials, defaults to False
            max_age: Max age for preflight requests, defaults to 600
        """
        self.middleware_cls = CORSMiddleware
        self.options = {
            "allow_origins": allow_origins or ["*"],
            "allow_methods": allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": allow_headers or ["*"],
            "allow_credentials": allow_credentials,
            "max_age": max_age,
        }
    
    def __call__(self):
        """
        Create CORS middleware instance.
        
        Returns:
            tuple: (Middleware class, options dictionary)
        """
        return self.middleware_cls, self.options

class CompressionMiddlewareFactory:
    """
    Factory for compression middleware configuration.
    
    Configures response compression with GZip or other algorithms.
    """
    
    def __init__(self, minimum_size=500, compression_level=6):
        """
        Initialize compression middleware factory.
        
        Args:
            minimum_size: Minimum response size to compress, defaults to 500 bytes
            compression_level: Compression level (1-9), defaults to 6
        """
        self.middleware_cls = GZipMiddleware
        self.options = {
            "minimum_size": minimum_size,
            "compression_level": compression_level,
        }
    
    def __call__(self):
        """
        Create compression middleware instance.
        
        Returns:
            tuple: (Middleware class, options dictionary)
        """
        return self.middleware_cls, self.options

class RateLimitMiddleware:
    """
    Custom rate limiting middleware.
    
    Implements request rate limiting based on client IP address.
    
    Attributes:
        app: ASGI application
        max_requests: Maximum requests per time window
        time_window: Time window in seconds
        requests: Request tracking dictionary
    """
    
    def __init__(self, app, max_requests=100, time_window=60):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: ASGI application to wrap
            max_requests: Maximum requests per time window, defaults to 100
            time_window: Time window in seconds, defaults to 60
        """
        self.app = app
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    async def __call__(self, scope, receive, send) -> None:
        """
        ASGI middleware implementation.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
            
        Returns:
            None: Processes request or returns rate limit error
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        client_ip = scope["client"][0] if scope.get("client") else "unknown"
        current_time = time.time()
        
        # Clean up old entries
        self.requests[client_ip] = [
            t for t in self.requests.get(client_ip, []) 
            if current_time - t < self.time_window
        ]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            from starlette.responses import JSONResponse
            response = JSONResponse(
                {"error": "Rate limit exceeded"}, 
                status_code=429
            )
            return await response(scope, receive, send)
        
        self.requests[client_ip].append(current_time)
        return await self.app(scope, receive, send)

class RateLimitMiddlewareFactory:
    """
    Factory for rate limiting middleware configuration.
    
    Simplifies rate limiting middleware setup.
    """
    
    def __init__(self, max_requests=100, time_window=60):
        """
        Initialize rate limit middleware factory.
        
        Args:
            max_requests: Maximum requests per time window, defaults to 100
            time_window: Time window in seconds, defaults to 60
        """
        self.middleware_cls = RateLimitMiddleware
        self.options = {
            "max_requests": max_requests,
            "time_window": time_window,
        }
    
    def __call__(self):
        """
        Create rate limit middleware instance.
        
        Returns:
            tuple: (Middleware class, options dictionary)
        """
        return self.middleware_cls, self.options