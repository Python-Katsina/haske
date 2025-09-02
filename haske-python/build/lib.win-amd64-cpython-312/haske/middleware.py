from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from typing import Callable, Any

class Middleware(StarletteMiddleware):
    """Haske Middleware wrapper around Starlette's Middleware."""

    def __init__(self, cls, **options):
        super().__init__(cls, **options)

class SessionMiddlewareFactory:
    """
    Factory for creating SessionMiddleware with options.
    Usage:
        Middleware(SessionMiddlewareFactory(secret_key="..."))
    """

    def __init__(self, secret_key: str, **options):
        self.secret_key = secret_key
        self.options = options

    def __call__(self):
        return SessionMiddleware, {"secret_key": self.secret_key, **self.options}

class CORSMiddlewareFactory:
    """Factory for CORS middleware"""
    
    def __init__(self, allow_origins=None, allow_methods=None, allow_headers=None, allow_credentials=False, max_age=600):
        from starlette.middleware.cors import CORSMiddleware
        
        self.middleware_cls = CORSMiddleware
        self.options = {
            "allow_origins": allow_origins or ["*"],
            "allow_methods": allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": allow_headers or ["*"],
            "allow_credentials": allow_credentials,
            "max_age": max_age,
        }
    
    def __call__(self):
        return self.middleware_cls, self.options

class CompressionMiddlewareFactory:
    """Factory for compression middleware"""
    
    def __init__(self, minimum_size=500, compression_level=6):
        self.middleware_cls = GZipMiddleware
        self.options = {
            "minimum_size": minimum_size,
            "compression_level": compression_level,
        }
    
    def __call__(self):
        return self.middleware_cls, self.options

class RateLimitMiddleware:
    """Custom rate limiting middleware"""
    
    def __init__(self, app, max_requests=100, time_window=60):
        self.app = app
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    async def __call__(self, scope, receive, send):
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
    """Factory for rate limiting middleware"""
    
    def __init__(self, max_requests=100, time_window=60):
        self.middleware_cls = RateLimitMiddleware
        self.options = {
            "max_requests": max_requests,
            "time_window": time_window,
        }
    
    def __call__(self):
        return self.middleware_cls, self.options