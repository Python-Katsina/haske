# haske/__init__.py
"""
Haske - High-performance Python web framework with Rust acceleration.

This package provides a modern, async-first web framework built on Starlette
with Rust-powered performance optimizations for critical paths.
"""

from .app import Haske
from .request import Request
from .response import Response, JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse, FileResponse, APIResponse
from .response import ok_response, created_response, error_response, not_found_response, validation_error_response
from .templates import render_template, render_template_async, template_response, TemplateEngine
from .orm import Database, Model
from .auth import create_session_token, verify_session_token, create_password_hash, verify_password_hash
from .auth import generate_csrf_token, validate_csrf_token, AuthManager
from .exceptions import HaskeError, ValidationError, AuthenticationError, PermissionError, NotFoundError, RateLimitError, ServerError
from .exceptions import haske_error_handler, http_error_handler, validation_error_handler, install_error_handlers
from .middleware import Middleware, SessionMiddlewareFactory, CORSMiddlewareFactory, CompressionMiddlewareFactory, RateLimitMiddlewareFactory
from .admin import generate_admin_index, generate_admin_api
from .routing import Route, PathConverter, IntConverter, FloatConverter, UUIDConverter, PathConverterRegistry, convert_path
from .cli import cli
from .cache import Cache, get_default_cache
from .static import FrontendServer, FrontendDevelopmentServer, FrontendManager, create_frontend_config

# Import Rust extensions
try:
    from _haske_core import (
        HaskeApp as RustRouter, 
        HaskeCache as RustCache,
        compile_path, match_path,
        json_loads_bytes, json_dumps_obj, json_is_valid, json_extract_field,
        sign_cookie, verify_cookie, hash_password, verify_password, generate_random_bytes,
        gzip_compress, gzip_decompress, zstd_compress, zstd_decompress, brotli_compress, brotli_decompress,
        prepare_query, prepare_queries,
        websocket_accept_key, WebSocketFrame,
        render_template as rust_render_template, precompile_template
    )
    HAS_RUST_EXTENSION = True
except ImportError:
    HAS_RUST_EXTENSION = False
    # Fallback implementations
    def compile_path(path: str) -> str:
        from .routing import default_converter_registry
        return default_converter_registry.convert_path(path)
    
    def match_path(pattern: str, path: str):
        import re
        regex = re.compile(pattern)
        if match := regex.match(path):
            return match.groupdict()
        return None

__version__ = "0.2.0"
__all__ = [
    "Haske", "Request", "Response", "JSONResponse", "HTMLResponse", "RedirectResponse", 
    "StreamingResponse", "FileResponse", "APIResponse", "ok_response", "created_response", 
    "error_response", "not_found_response", "validation_error_response", "render_template", 
    "render_template_async", "template_response", "TemplateEngine", "Database", "Model",
    "create_session_token", "verify_session_token", "create_password_hash", "verify_password_hash",
    "generate_csrf_token", "validate_csrf_token", "AuthManager", "HaskeError", "ValidationError",
    "AuthenticationError", "PermissionError", "NotFoundError", "RateLimitError", "ServerError",
    "haske_error_handler", "http_error_handler", "validation_error_handler", "install_error_handlers",
    "Middleware", "SessionMiddlewareFactory", "CORSMiddlewareFactory", "CompressionMiddlewareFactory",
    "RateLimitMiddlewareFactory", "generate_admin_index", "generate_admin_api", "Route", "PathConverter",
    "IntConverter", "FloatConverter", "UUIDConverter", "PathConverterRegistry", "convert_path", "cli",
    "Cache", "get_default_cache", "FrontendServer", "FrontendDevelopmentServer", "FrontendManager", 
    "create_frontend_config", "HAS_RUST_EXTENSION"
]