# HTTPError, ValidationError
from starlette.exceptions import HTTPException
from typing import Any, Dict, Optional

class HaskeError(HTTPException):
    """Base Haske exception"""
    
    def __init__(self, detail: Any = None, status_code: int = 500, 
                 error_code: Optional[str] = None, **kwargs):
        super().__init__(status_code, detail)
        self.error_code = error_code or f"ERR_{status_code}"
        self.extra = kwargs

class ValidationError(HaskeError):
    """Validation error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Validation error", 400, "VALIDATION_ERROR", **kwargs)

class AuthenticationError(HaskeError):
    """Authentication error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Authentication required", 401, "AUTH_ERROR", **kwargs)

class PermissionError(HaskeError):
    """Permission error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Permission denied", 403, "PERMISSION_ERROR", **kwargs)

class NotFoundError(HaskeError):
    """Not found error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Resource not found", 404, "NOT_FOUND", **kwargs)

class RateLimitError(HaskeError):
    """Rate limit error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Rate limit exceeded", 429, "RATE_LIMIT", **kwargs)

class ServerError(HaskeError):
    """Server error"""
    
    def __init__(self, detail: Any = None, **kwargs):
        super().__init__(detail or "Internal server error", 500, "SERVER_ERROR", **kwargs)

def haske_error_handler(request, exc: HaskeError):
    """Custom error handler for Haske exceptions"""
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
    """Handler for standard HTTP exceptions"""
    from starlette.responses import JSONResponse
    
    return JSONResponse({
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "status": exc.status_code,
        }
    }, status_code=exc.status_code)

def validation_error_handler(request, exc: ValidationError):
    """Handler for validation errors"""
    return haske_error_handler(request, exc)

def install_error_handlers(app: 'Haske'):
    """Install all error handlers on the app"""
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    app.middleware_stack.append(
        Middleware(StarletteHTTPException, handlers={
            HaskeError: haske_error_handler,
            ValidationError: validation_error_handler,
            StarletteHTTPException: http_error_handler,
        })
    )