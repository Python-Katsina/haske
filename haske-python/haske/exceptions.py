# haske/exceptions.py
"""
Custom exception classes and error handlers for Haske framework.

This module provides a hierarchy of custom exceptions for different error
scenarios and corresponding error handlers for consistent error responses.
"""

from starlette.exceptions import HTTPException
from typing import Any, Dict, Optional

class HaskeError(HTTPException):
    """
    Base Haske exception class.
    
    All custom Haske exceptions inherit from this class. Provides consistent
    error formatting with error codes and additional context.
    
    Attributes:
        detail (Any): Error message or details
        status_code (int): HTTP status code
        error_code (str): Machine-readable error code
        extra (dict): Additional error context
    """
    
    def __init__(self, detail: Any = None, status_code: int = 500, 
                 error_code: Optional[str] = None, **kwargs):
        """
        Initialize Haske error.
        
        Args:
            detail: Error message or details
            status_code: HTTP status code, defaults to 500
            error_code: Machine-readable error code, defaults to "ERR_{status_code}"
            **kwargs: Additional context to include in error response
        """
        super().__init__(status_code, detail)
        self.error_code = error_code or f"ERR_{status_code}"
        self.extra = kwargs

class ValidationError(HaskeError):
    """
    Validation error for invalid request data.
    
    Raised when request data fails validation against a schema.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            detail: Validation error details
            **kwargs: Additional validation context
        """
        super().__init__(detail or "Validation error", 400, "VALIDATION_ERROR", **kwargs)

class AuthenticationError(HaskeError):
    """
    Authentication error for unauthorized access.
    
    Raised when authentication is required but not provided or invalid.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize authentication error.
        
        Args:
            detail: Authentication error message
            **kwargs: Additional authentication context
        """
        super().__init__(detail or "Authentication required", 401, "AUTH_ERROR", **kwargs)

class PermissionError(HaskeError):
    """
    Permission error for insufficient privileges.
    
    Raised when a user doesn't have required permissions for an operation.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize permission error.
        
        Args:
            detail: Permission error message
            **kwargs: Additional permission context
        """
        super().__init__(detail or "Permission denied", 403, "PERMISSION_ERROR", **kwargs)

class NotFoundError(HaskeError):
    """
    Not found error for missing resources.
    
    Raised when a requested resource cannot be found.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize not found error.
        
        Args:
            detail: Not found error message
            **kwargs: Additional context about missing resource
        """
        super().__init__(detail or "Resource not found", 404, "NOT_FOUND", **kwargs)

class RateLimitError(HaskeError):
    """
    Rate limit error for excessive requests.
    
    Raised when a client exceeds rate limits.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize rate limit error.
        
        Args:
            detail: Rate limit error message
            **kwargs: Additional rate limiting context
        """
        super().__init__(detail or "Rate limit exceeded", 429, "RATE_LIMIT", **kwargs)

class ServerError(HaskeError):
    """
    Server error for internal server issues.
    
    Raised for unexpected server-side errors.
    """
    
    def __init__(self, detail: Any = None, **kwargs):
        """
        Initialize server error.
        
        Args:
            detail: Server error message
            **kwargs: Additional server error context
        """
        super().__init__(detail or "Internal server error", 500, "SERVER_ERROR", **kwargs)

def haske_error_handler(request, exc: HaskeError):
    """
    Custom error handler for Haske exceptions.
    
    Args:
        request: Request object
        exc: Haske exception instance
        
    Returns:
        JSONResponse: Formatted error response
        
    Example:
        >>> app.add_exception_handler(HaskeError, haske_error_handler)
    """
    from starlette.responses import JSONResponse
    
    response_data = {
        "error": {
            "code": exc.error_code,
            "message": exc.detail,
            "status": exc.status_code,
        }
    }
    
    if exc.extra:
        response_data["error"]["details"] = exc.extra
    
    return JSONResponse(response_data, status_code=exc.status_code)

def http_error_handler(request, exc: HTTPException):
    """
    Handler for standard HTTP exceptions.
    
    Args:
        request: Request object
        exc: HTTP exception instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    from starlette.responses import JSONResponse
    
    return JSONResponse({
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "status": exc.status_code,
        }
    }, status_code=exc.status_code)

def validation_error_handler(request, exc: ValidationError):
    """
    Handler for validation errors.
    
    Args:
        request: Request object
        exc: ValidationError instance
        
    Returns:
        JSONResponse: Formatted validation error response
    """
    return haske_error_handler(request, exc)

def install_error_handlers(app: 'Haske'):
    """
    Install all error handlers on the app.
    
    Args:
        app: Haske application instance
        
    Example:
        >>> install_error_handlers(app)
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    app.middleware_stack.append(
        Middleware(StarletteHTTPException, handlers={
            HaskeError: haske_error_handler,
            ValidationError: validation_error_handler,
            StarletteHTTPException: http_error_handler,
        })
    )