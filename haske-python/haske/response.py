from typing import Any, Dict, Optional
from starlette.responses import (
    JSONResponse as StarletteJSONResponse, 
    HTMLResponse as StarletteHTMLResponse, 
    Response as StarletteResponse,
    RedirectResponse as StarletteRedirectResponse,
    StreamingResponse as StarletteStreamingResponse,
    FileResponse as StarletteFileResponse,
)
from _haske_core import gzip_compress, brotli_compress

class Response(StarletteResponse):
    """Base Haske Response (inherits Starlette's Response)."""
    
    def __init__(self, content: Any = None, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None,
                 compressed: bool = False):
        super().__init__(content, status_code, headers, media_type)
        self.compressed = compressed
    
    def compress(self, algorithm: str = "gzip"):
        """Compress response content"""
        if self.compressed or not self.body:
            return self
        
        if algorithm == "gzip":
            compressed = gzip_compress(self.body)
        elif algorithm == "brotli":
            compressed = brotli_compress(self.body)
        else:
            return self
        
        self.body = compressed
        self.headers["content-encoding"] = algorithm
        self.compressed = True
        return self

class JSONResponse(StarletteJSONResponse):
    """JSON Response wrapper for Haske."""
    
    def __init__(self, content: Any, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        super().__init__(content, status_code, headers, **kwargs)

class HTMLResponse(StarletteHTMLResponse):
    """HTML Response wrapper for Haske."""
    
    def __init__(self, content: str, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        super().__init__(content, status_code, headers, **kwargs)

class RedirectResponse(StarletteRedirectResponse):
    """Redirect Response wrapper for Haske."""
    
    def __init__(self, url: str, status_code: int = 307, 
                 headers: Dict[str, str] = None, **kwargs):
        super().__init__(url, status_code, headers, **kwargs)

class StreamingResponse(StarletteStreamingResponse):
    """Streaming Response wrapper for Haske."""
    
    def __init__(self, content: Any, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None, **kwargs):
        super().__init__(content, status_code, headers, media_type, **kwargs)

class FileResponse(StarletteFileResponse):
    """File Response wrapper for Haske."""
    
    def __init__(self, path: str, status_code: int = 200, 
                 headers: Dict[str, str] = None, media_type: str = None, 
                 filename: str = None, **kwargs):
        super().__init__(path, status_code, headers, media_type, filename, **kwargs)

class APIResponse(JSONResponse):
    """Standardized API response format"""
    
    def __init__(self, data: Any = None, status: str = "success", 
                 message: str = None, status_code: int = 200, 
                 headers: Dict[str, str] = None, **kwargs):
        
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
    """Convert Python data to a proper Starlette Response."""
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
    """Create a success response"""
    return APIResponse(data=data, message=message, status_code=200)

def created_response(data: Any = None, message: str = "Resource created") -> APIResponse:
    """Create a created response"""
    return APIResponse(data=data, message=message, status_code=201)

def error_response(message: str, status_code: int = 400, details: Any = None) -> APIResponse:
    """Create an error response"""
    return APIResponse(
        data=None, 
        status="error", 
        message=message, 
        status_code=status_code,
        details=details
    )

def not_found_response(message: str = "Resource not found") -> APIResponse:
    """Create a not found response"""
    return error_response(message, 404)

def validation_error_response(errors: Any) -> APIResponse:
    """Create a validation error response"""
    return error_response("Validation failed", 400, details=errors)