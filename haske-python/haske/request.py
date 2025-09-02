import json
from typing import Dict, Any, Optional
from starlette.requests import Request as StarletteReq
from _haske_core import json_loads_bytes, json_is_valid, json_extract_field

class Request:
    def __init__(self, scope, receive, send, path_params: Dict[str, Any] = None, body_bytes: bytes = None):
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
        return self.scope["method"]

    @property
    def path(self) -> str:
        return self.scope["path"]

    def get_path_param(self, key: str, default: Any = None) -> Any:
        return self.path_params.get(key, default)

    async def body(self) -> bytes:
        if self._body is None:
            self._body = b""
            more_body = True
            while more_body:
                message = await self.receive()
                self._body += message.get("body", b"")
                more_body = message.get("more_body", False)
        return self._body

    async def json(self) -> Any:
        if self._json is None:
            body = await self.body()
            
            # Try Rust-accelerated JSON parsing first
            if body:
                parsed = json_loads_bytes(body)
                if parsed is not None:
                    self._json = parsed
                else:
                    # Fall back to Python JSON
                    try:
                        self._json = json.loads(body.decode("utf-8") or "null")
                    except json.JSONDecodeError:
                        self._json = {}
            else:
                self._json = {}
        
        return self._json

    async def text(self) -> str:
        body = await self.body()
        return body.decode("utf-8", errors="replace")

    async def form(self) -> Dict[str, Any]:
        if self._form is None:
            body = await self.text()
            if "application/x-www-form-urlencoded" in self.headers.get("content-type", ""):
                from urllib.parse import parse_qs
                self._form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body).items()}
            else:
                self._form = {}
        return self._form

    @property
    def headers(self) -> Dict[str, str]:
        return {k.decode(): v.decode() for k, v in self.scope.get("headers", [])}

    @property
    def cookies(self) -> Dict[str, str]:
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
        return self.scope.get("query_string", b"").decode()

    def get_query_param(self, key: str, default: Any = None) -> Any:
        from urllib.parse import parse_qs
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        return params.get(key, [default])[0] if params.get(key) else default

    def is_json(self) -> bool:
        content_type = self.headers.get("content-type", "")
        return "application/json" in content_type

    def is_form(self) -> bool:
        content_type = self.headers.get("content-type", "")
        return "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type

    async def validate_json(self, schema: Any = None) -> Any:
        """Validate JSON against a schema (e.g., Pydantic, Marshmallow)"""
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
        """Get client IP address, considering proxies"""
        if "x-forwarded-for" in self.headers:
            # Get the first IP in the list
            return self.headers["x-forwarded-for"].split(",")[0].strip()
        return self.scope.get("client", ["unknown"])[0]