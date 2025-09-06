# haske/response.py
"""
Enhanced response classes and utilities for Haske framework.

This module provides custom response classes with compression support
and convenient response factory functions for common scenarios.
"""

from typing import Any, Dict, Optional
from starlette.responses import (
    JSONResponse as StarletteJSONResponse, 
    HTMLResponse as StarletteHTMLResponse, 
    Response as StarletteResponse,
    RedirectResponse as StarletteRedirectResponse,
    StreamingResponse as StarletteStreamingResponse,
    FileResponse as StarletteFileResponse,
)

# Import Rust compression functions if available
try:
    from _haske_core import gzip_compress, brotli_compress
    HAS_RUST_COMPRESSION = True
except ImportError:
    HAS_RUST_COMPRESSION = False

class Response(StarletteResponse):
    """
    Base Haske Response with compression support.
    
    Extends Starlette's Response with built-in compression capabilities.
    
    Attributes:
        content: Response content
        status_code: HTTP status code
        headers: Response headers
        media_type: Content media type
        compressed: Whether response is compressed
    """
    
    def __init__(self, content: Any = None, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None,
                 compressed: bool = False):
        """
        Initialize response.
        
        Args:
            content: Response content
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            media_type: Content media type, defaults to None
            compressed: Whether response is compressed, defaults to False
        """
        super().__init__(content, status_code, headers, media_type)
        self.compressed = compressed
    
    def compress(self, algorithm: str = "gzip"):
        """
        Compress response content.
        
        Args:
            algorithm: Compression algorithm ("gzip" or "brotli"), defaults to "gzip"
            
        Returns:
            Response: Self for method chaining
            
        Example:
            >>> response = Response("content").compress("gzip")
        """
        if self.compressed or not self.body:
            return self
        
        if HAS_RUST_COMPRESSION:
            if algorithm == "gzip":
                compressed = gzip_compress(self.body)
            elif algorithm == "brotli":
                compressed = brotli_compress(self.body)
            else:
                return self
        else:
            # Fallback Python implementation
            import gzip
            import brotli
            
            if algorithm == "gzip":
                compressed = gzip.compress(self.body)
            elif algorithm == "brotli":
                compressed = brotli.compress(self.body)
            else:
                return self
        
        self.body = compressed
        self.headers["content-encoding"] = algorithm
        self.compressed = True
        return self

class JSONResponse(StarletteJSONResponse):
    """
    JSON Response wrapper for Haske.
    
    Provides JSON response with consistent formatting.
    """

    def __init__(self, content: Any, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        """
        Initialize JSON response.
        
        Args:
            content: JSON-serializable content
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            **kwargs: Additional JSON response options
        """
        super().__init__(content, status_code, headers, **kwargs)

class HTMLResponse(StarletteHTMLResponse):
    """
    HTML Response wrapper for Haske.
    
    Provides HTML response with proper content type.
    """

    def __init__(self, content: str, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        """
        Initialize HTML response.
        
        Args:
            content: HTML content
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            **kwargs: Additional HTML response options
        """
        super().__init__(content, status_code, headers, **kwargs)

class RedirectResponse(StarletteRedirectResponse):
    """
    Redirect Response wrapper for Haske.
    
    Provides HTTP redirect responses.
    """

    def __init__(self, url: str, status_code: int = 307, 
                 headers: Dict[str, str] = None, **kwargs):
        """
        Initialize redirect response.
        
        Args:
            url: Redirect target URL
            status_code: HTTP status code, defaults to 307 (Temporary Redirect)
            headers: Response headers, defaults to None
            **kwargs: Additional redirect response options
        """
        super().__init__(url, status_code, headers, **kwargs)

class StreamingResponse(StarletteStreamingResponse):
    """
    Streaming Response wrapper for Haske.
    
    Provides streaming response for large content.
    """

    def __init__(self, content: Any, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None, **kwargs):
        """
        Initialize streaming response.
        
        Args:
            content: Streaming content
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            media_type: Content media type, defaults to None
            **kwargs: Additional streaming response options
        """
        super().__init__(content, status_code, headers, media_type, **kwargs)

class FileResponse(StarletteFileResponse):
    """
    File Response wrapper for Haske.
    
    Provides file download responses.
    """

    def __init__(self, path: str, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None, 
                 filename: str = None, **kwargs):
        """
        Initialize file response.
        
        Args:
            path: File path
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            media_type: Content media type, defaults to None
            filename: Download filename, defaults to None
            **kwargs: Additional file response options
        """
        super().__init__(path, status_code, headers, media_type, filename, **kwargs)

class APIResponse(JSONResponse):
    """
    Standardized API response format.
    
    Provides consistent JSON response structure for APIs.
    """
    
    def __init__(self, data: Any = None, status: str = "success", 
                 message: str = None, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        """
        Initialize API response.
        
        Args:
            data: Response data
            status: Response status ("success" or "error"), defaults to "success"
            message: Optional message, defaults to None
            status_code: HTTP status code, defaults to 200
            headers: Response headers, defaults to None
            **kwargs: Additional response data
        """
        
        response_data = {
            "status": status,
            "data": data,
        }
        
        if message:
            response_data["message"] = message
        
        if kwargs:
            response_data.update(kwargs)
        
        super().__init__(response_data, status_code, headers)

def to_starlette_response(data: Any) -> StarletteResponse:
    """
    Convert Python data to a proper Starlette Response.
    
    Args:
        data: Data to convert
        
    Returns:
        StarletteResponse: Appropriate response type
        
    Converts:
        - dict/list -> JSONResponse
        - str -> HTMLResponse
        - bytes -> Response with octet-stream
        - other -> plain text Response
    """
    if isinstance(data, StarletteResponse):
        return data
    elif isinstance(data, dict) or isinstance(data, list):
        return JSONResponse(data)
    elif isinstance(data, str):
        return HTMLResponse(data)
    elif isinstance(data, bytes):
        return Response(content=data, media_type="application/octet-stream")
    else:
        return Response(content=str(data))

def ok_response(data: Any = None, message: str = None) -> APIResponse:
    """
    Create a success response.
    
    Args:
        data: Response data, defaults to None
        message: Optional message, defaults to None
        
    Returns:
        APIResponse: Success response with 200 status
        
    Example:
        >>> return ok_response({"user": user}, "Operation successful")
    """
    return APIResponse(data=data, message=message, status_code=200)

def created_response(data: Any = None, message: str = "Resource created") -> APIResponse:
    """
    Create a created response.
    
    Args:
        data: Response data, defaults to None
        message: Optional message, defaults to "Resource created"
        
    Returns:
        APIResponse: Created response with 201 status
    """
    return APIResponse(data=data, message=message, status_code=201)

def error_response(message: str, status_code: int = 400, details: Any = None) -> APIResponse:
    """
    Create an error response.
    
    Args:
        message: Error message
        status_code: HTTP status code, defaults to 400
        details: Additional error details, defaults to None
        
    Returns:
        APIResponse: Error response with specified status
    """
    return APIResponse(
        data=None, 
        status="error", 
        message=message, 
        status_code=status_code,
        details=details
    )

def not_found_response(message: str = "Resource not found") -> APIResponse:
    """
    Create a not found response.
    
    Args:
        message: Error message, defaults to "Resource not found"
        
    Returns:
        APIResponse: Not found response with 404 status
    """
    return error_response(message, 404)

def validation_error_response(errors: Any) -> APIResponse:
    """
    Create a validation error response.
    
    Args:
        errors: Validation errors
        
    Returns:
        APIResponse: Validation error response with 400 status
    """
    return error_response("Validation failed", 400, details=errors)