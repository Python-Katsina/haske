# haske/__init__.py
"""
Haske - High-performance Python web framework with Rust acceleration.

This package provides a modern, async-first web framework built on Starlette
with Rust-powered performance optimizations for critical paths.

Modules:
    app: Main application class and core functionality
    request: Enhanced request handling with Rust acceleration
    response: Comprehensive response types and utilities
    templates: Template rendering with Jinja2 and Rust optimizations
    orm: Database ORM with async support
    auth: Authentication and authorization utilities
    exceptions: Custom exception types and error handling
    middleware: Middleware factories and utilities
    admin: Admin interface generation
    routing: Route handling and path parameter conversion
    cli: Command-line interface for development and deployment

Key Features:
    - Rust-accelerated JSON parsing, routing, and templating
    - Async/await support throughout
    - Type annotations and validation
    - Comprehensive authentication system
    - Database ORM with multiple backend support
    - Admin interface generation
    - Built-in CLI tools
    - Production-ready deployment options
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


__version__ = "0.1.0"
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
    "IntConverter", "FloatConverter", "UUIDConverter", "PathConverterRegistry", "convert_path", "cli"
]