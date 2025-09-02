# haske/app.py
from typing import Any, Callable, Awaitable, Dict, List, Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import os
import time

try:
    from _haske_core import HaskeApp as RustHaskeApp, compile_path, match_path
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    print("Warning: Rust extensions not available. Using Python fallback.")

class Haske:
    def __init__(self, name: str = "haske") -> None:
        self.name = name
        self.routes = []
        self.middleware_stack = []
        self.starlette_app: Optional[Starlette] = None
        self.rust_router = RustHaskeApp() if HAS_RUST else None
        self.start_time = time.time()
        
        # Default middleware
        self.middleware(Middleware(GZipMiddleware, minimum_size=500))

    def route(self, path: str, methods: List[str] = None, name: str = None) -> Callable:
        """
        Decorator to register a route handler.
        Example:
            @app.route("/", methods=["GET"])
            async def homepage(request):
                return {"message": "Hello"}
        """
        methods = methods or ["GET"]
        
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            async def endpoint(request):
                result = await func(request)
                return self._convert_to_response(result)
            
            # Add to Starlette routes
            self.routes.append(Route(path, endpoint, methods=methods, name=name))
            
            # Add to Rust router for faster matching if available
            if HAS_RUST and self.rust_router:
                try:
                    # Compile path to regex if it contains parameters
                    if ':' in path:
                        regex_path = compile_path(path)
                        self.rust_router.add_route(
                            methods[0] if len(methods) == 1 else "ANY",
                            regex_path,
                            func
                        )
                    else:
                        # Simple path without parameters
                        self.rust_router.add_route(
                            methods[0] if len(methods) == 1 else "ANY",
                            f"^{path}$",
                            func
                        )
                except Exception as e:
                    print(f"Warning: Could not add route to Rust router: {e}")
            
            return func
        return decorator

    def middleware(self, middleware_cls, **options):
        """
        Register middleware. Example:
            app.middleware(CORSMiddleware, allow_origins=["*"])
        """
        self.middleware_stack.append(Middleware(middleware_cls, **options))

    def mount(self, path: str, app: Any, name: str = None):
        """Mount a sub-application"""
        self.routes.append(Mount(path, app=app, name=name))

    def static(self, path: str, directory: str, name: str = None):
        """Serve static files from a directory"""
        self.routes.append(Mount(path, app=StaticFiles(directory=directory), name=name))

    def _convert_to_response(self, result: Any) -> Response:
        """Convert handler result into Starlette Response"""
        if isinstance(result, Response):
            return result
        if isinstance(result, dict):
            return JSONResponse(result)
        if isinstance(result, str):
            return HTMLResponse(result)
        if isinstance(result, (list, tuple)):
            return JSONResponse(result)
        return Response(str(result))

    def build(self) -> Starlette:
        """Build the internal Starlette app"""
        self.starlette_app = Starlette(
            debug=os.getenv("HASKE_DEBUG", "False").lower() == "true",
            routes=self.routes,
            middleware=self.middleware_stack,
        )
        return self.starlette_app

    async def __call__(self, scope, receive, send) -> None:
        """
        Make Haske ASGI-compatible so `uvicorn.run(app)` works directly.
        """
        if self.starlette_app is None:
            self.build()
        
        # Try Rust router first for faster matching
        if (HAS_RUST and 
            scope["type"] == "http" and 
            self.rust_router and 
            "path" in scope and 
            "method" in scope):
            
            try:
                result = self.rust_router.match_request(
                    scope["method"], 
                    scope["path"]
                )
                if result:
                    handler, params = result
                    # Create a custom request with path parameters
                    from .request import Request
                    custom_request = Request(
                        scope, receive, send, 
                        path_params=params,
                        body_bytes=await self._get_body(scope, receive)
                    )
                    response = await handler(custom_request)
                    return await response(scope, receive, send)
            except Exception as e:
                print(f"Rust router error: {e}")
                # Fall back to Starlette
        
        await self.starlette_app(scope, receive, send)
    
    async def _get_body(self, scope, receive):
        """Extract body from request"""
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        return body

    def get_uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time

    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics"""
        return {
            "uptime": self.get_uptime(),
            "routes": len(self.routes),
            "middleware": len(self.middleware_stack),
            "rust_available": HAS_RUST,
            "rust_routes": self.rust_router.route_count() if HAS_RUST and self.rust_router else 0,
        }