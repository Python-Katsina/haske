# haske/request.py
"""
Enhanced request handling for Haske framework.

This module provides a custom Request class with Rust-accelerated
JSON parsing, form handling, and convenient access to request data.
"""

import json
from typing import Dict, Any, Optional
from starlette.requests import Request as StarletteReq

# Import Rust JSON functions if available
try:
    from _haske_core import json_loads_bytes, json_is_valid, json_extract_field
    HAS_RUST_JSON = True
except ImportError:
    HAS_RUST_JSON = False

class Request:
    """
    Enhanced request class with Rust acceleration.
    
    Extends Starlette's Request with improved performance and
    additional convenience methods for common request operations.
    
    Attributes:
        scope: ASGI scope
        receive: ASGI receive function
        send: ASGI send function
        path_params: Path parameters dictionary
        _body: Cached request body
        _json: Cached JSON data
        _form: Cached form data
        _cookies: Cached cookies
    """
    
    def __init__(self, scope, receive, send, path_params: Dict[str, Any] = None, body_bytes: bytes = None):
        """
        Initialize request.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
            path_params: Path parameters, defaults to empty dict
            body_bytes: Pre-loaded body bytes, defaults to None
        """
        self.scope = scope
        self.receive = receive
        self.send = send
        self.path_params = path_params or {}
        self._body = body_bytes
        self._json = None
        self._form = None
        self._cookies = None

    @property
    def method(self) -> str:
        """
        Get HTTP method.
        
        Returns:
            str: HTTP method (GET, POST, etc.)
        """
        return self.scope["method"]

    @property
    def path(self) -> str:
        """
        Get request path.
        
        Returns:
            str: Request path
        """
        return self.scope["path"]

    def get_path_param(self, key: str, default: Any = None) -> Any:
        """
        Get path parameter by key.
        
        Args:
            key: Path parameter name
            default: Default value if parameter not found
            
        Returns:
            Any: Path parameter value or default
            
        Example:
            >>> user_id = request.get_path_param("user_id")
        """
        return self.path_params.get(key, default)

    async def body(self) -> bytes:
        """
        Get raw request body as bytes.
        
        Returns:
            bytes: Request body bytes
            
        Note:
            Caches the body for subsequent calls
        """
        if self._body is None:
            self._body = b""
            more_body = True
            while more_body:
                message = await self.receive()
                self._body += message.get("body", b"")
                more_body = message.get("more_body", False)
        return self._body

    async def json(self) -> Any:
        """
        Parse request body as JSON.
        
        Returns:
            Any: Parsed JSON data
            
        Note:
            Uses Rust-accelerated parsing when available
            Falls back to Python JSON if Rust fails
        """
        if self._json is None:
            body = await self.body()
            
            # Try Rust-accelerated JSON parsing first
            if body and HAS_RUST_JSON:
                try:
                    parsed = json_loads_bytes(body)
                    if parsed is not None:
                        self._json = parsed
                        return self._json
                except Exception:
                    # Fall back to Python JSON if Rust parsing fails
                    pass
            
            # Fall back to Python JSON
            try:
                self._json = json.loads(body.decode("utf-8") or "null")
            except json.JSONDecodeError:
                self._json = {}
        
        return self._json

    async def text(self) -> str:
        """
        Get request body as text.
        
        Returns:
            str: Request body as UTF-8 text
        """
        body = await self.body()
        return body.decode("utf-8", errors="replace")

    async def form(self) -> Dict[str, Any]:
        """
        Parse request body as form data.
        
        Returns:
            Dict[str, Any]: Parsed form data
            
        Note:
            Only works for application/x-www-form-urlencoded content type
        """
        if self._form is None:
            body = await self.text()
            if "application/x-www-form-urlencoded" in self.headers.get("content-type", ""):
                from urllib.parse import parse_qs
                self._form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body).items()}
            else:
                self._form = {}
        # self._form = dict(self._form)
        return self._form

    @property
    def headers(self) -> Dict[str, str]:
        """
        Get request headers.
        
        Returns:
            Dict[str, str]: Headers dictionary
        """
        return {k.decode(): v.decode() for k, v in self.scope.get("headers", [])}

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Get request cookies.
        
        Returns:
            Dict[str, str]: Cookies dictionary
        """
        if self._cookies is None:
            self._cookies = {}
            cookie_header = self.headers.get("cookie", "")
            if cookie_header:
                from http.cookies import SimpleCookie
                c = SimpleCookie()
                c.load(cookie_header)
                self._cookies = {k: v.value for k, v in c.items()}
        return self._cookies

    @property
    def query_params(self) -> Dict[str, Any]:
        """
        Get query parameters as string.
        
        Returns:
            str: Raw query string
        """
        return self.scope.get("query_string", b"").decode()

    def get_query_param(self, key: str, default: Any = None) -> Any:
        """
        Get query parameter by key.
        
        Args:
            key: Query parameter name
            default: Default value if parameter not found
            
        Returns:
            Any: Query parameter value or default
            
        Example:
            >>> page = request.get_query_param("page", 1)
        """
        from urllib.parse import parse_qs
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        return params.get(key, [default])[0] if params.get(key) else default

    def is_json(self) -> bool:
        """
        Check if request contains JSON data.
        
        Returns:
            bool: True if content-type indicates JSON
        """
        content_type = self.headers.get("content-type", "")
        return "application/json" in content_type

    def is_form(self) -> bool:
        """
        Check if request contains form data.
        
        Returns:
            bool: True if content-type indicates form data
        """
        content_type = self.headers.get("content-type", "")
        return "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type

    def is_valid_json(self) -> bool:
        """
        Check if request contains valid JSON using Rust acceleration.
        
        Returns:
            bool: True if content is valid JSON
        """
        if not self.is_json():
            return False
            
        if HAS_RUST_JSON:
            body = self._body or b""
            return json_is_valid(body)
        else:
            # Fallback implementation
            try:
                self.json()
                return True
            except json.JSONDecodeError:
                return False

    def extract_json_field(self, field: str) -> Optional[str]:
        """
        Extract specific field from JSON using Rust acceleration.
        
        Args:
            field: Field name to extract
            
        Returns:
            Optional[str]: Field value or None
        """
        if not self.is_json():
            return None
            
        if HAS_RUST_JSON:
            body = self._body or b""
            return json_extract_field(body, field)
        else:
            # Fallback implementation
            try:
                data = self.json()
                return str(data.get(field, None))
            except Exception:
                return None

    async def validate_json(self, schema: Any = None) -> Any:
        """
        Validate JSON against a schema.
        
        Args:
            schema: Validation schema (Pydantic, Marshmallow, etc.)
            
        Returns:
            Any: Validated data
            
        Raises:
            ValidationError: If validation fails
            
        Example:
            >>> data = await request.validate_json(UserSchema)
        """
        data = await self.json()
        
        if schema is not None:
            if hasattr(schema, "validate"):
                # Marshmallow-like schema
                errors = schema.validate(data)
                if errors:
                    from .exceptions import ValidationError
                    raise ValidationError("Validation failed", details=errors)
            elif hasattr(schema, "parse_obj"):
                # Pydantic-like schema
                try:
                    data = schema.parse_obj(data)
                except Exception as e:
                    from .exceptions import ValidationError
                    raise ValidationError("Validation failed", details=str(e))
        
        return data

    def get_client_ip(self) -> str:
        """
        Get client IP address, considering proxies.
        
        Returns:
            str: Client IP address
            
        Note:
            Checks X-Forwarded-For header for proxy scenarios
        """
        if "x-forwarded-for" in self.headers:
            # Get the first IP in the list
            return self.headers["x-forwarded-for"].split(",")[0].strip()
        return self.scope.get("client", ["unknown"])[0]