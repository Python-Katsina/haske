# haske/app.py
"""
Main application class for Haske web framework.

This module provides the core Haske application class that serves as the
entry point for creating web applications with Rust-accelerated performance.
"""

from typing import Any, Callable, Awaitable, Dict, List, Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware

from .static import FrontendManager, create_frontend_config
import os
import time
import uvicorn
import inspect
import sys

# Import Rust router if available
try:
    from _haske_core import HaskeApp as RustRouter
    HAS_RUST_ROUTER = True
except ImportError:
    HAS_RUST_ROUTER = False

class Haske:
    """
    Main Haske application class.
    
    This class represents a Haske web application and provides methods for
    routing, middleware, and application management.
    
    Attributes:
        name (str): Application name
        routes (list): Registered routes
        middleware_stack (list): Registered middleware
        starlette_app (Starlette): Internal Starlette application
        start_time (float): Application start time for uptime calculation
    """
    
    def __init__(self, name: str = "haske") -> None:
        """
        Initialize a new Haske application.
        
        Args:
            name: Application name, defaults to "haske"
        """
        self.name = name
        self.routes = []
        self.middleware_stack = []
        self.starlette_app: Optional[Starlette] = None
        self.start_time = time.time()
        
        # Initialize Rust router if available
        if HAS_RUST_ROUTER:
            self._rust_router = RustRouter()
        else:
            self._rust_router = None

        self.frontend_manager = None
        self.frontend_config = None
        
        # Default middleware
        self.middleware(GZipMiddleware, minimum_size=500)

    def route(self, path: str, methods: List[str] = None, name: str = None) -> Callable:
        """
        Decorator to register a route handler.
        
        Args:
            path: URL path pattern (supports path parameters)
            methods: HTTP methods to handle, defaults to ["GET"]
            name: Route name for reverse URL lookup
            
        Returns:
            Callable: Decorator function
            
        Example:
            @app.route("/users/:id", methods=["GET"])
            async def get_user(request: Request):
                return {"user": await get_user_by_id(request.path_params["id"])}
        """
        methods = methods or ["GET"]
        
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            async def endpoint(request):
                result = await func(request)
                return self._convert_to_response(result)
            
            # Add to both Starlette and Rust router (if available)
            self.routes.append(Route(path, endpoint, methods=methods, name=name))
            
            # Add to Rust router for faster matching
            if self._rust_router is not None:
                # Convert Starlette path format to regex
                from .routing import convert_path
                regex_path = convert_path(path.replace("<", ":").replace(">", ""))
                
                # Add to Rust router
                self._rust_router.add_route(
                    ",".join(methods), 
                    regex_path, 
                    func
                )
            
            return func
        return decorator
    
    def setup_frontend(self, 
                      framework: str = "react", 
                      mode: str = "production",
                      config: Optional[Dict] = None):
        """
        Setup frontend serving for React, Vue, Next.js, etc.
        
        Args:
            framework: Frontend framework ("react", "vue", "nextjs", etc.)
            mode: "production" or "development"
            config: Custom frontend configuration
            
        Example:
            app.setup_frontend("react", "production")
        """
        self.frontend_config = config or create_frontend_config(framework)
        self.frontend_manager = FrontendManager(self, self.frontend_config)
        self.frontend_manager.setup(mode)
    
    def serve_frontend(self, 
                      directory: str = "./frontend/build",
                      spa_mode: bool = True,
                      development_mode: bool = False):
        """
        Quick setup for frontend serving.
        
        Args:
            directory: Frontend build directory
            spa_mode: Enable SPA routing
            development_mode: Development mode
            
        Example:
            app.serve_frontend("./my-react-app/build")
        """
        from .static import FrontendServer
        frontend_server = FrontendServer(
            directory=directory,
            spa_mode=spa_mode,
            development_mode=development_mode
        )
        frontend_server.setup_middleware(self)

    def middleware(self, middleware_cls, **options):
        """
        Register middleware.
        
        Args:
            middleware_cls: Middleware class
            **options: Middleware configuration options
            
        Example:
            app.middleware(CORSMiddleware, allow_origins=["*"])
        """
        self.middleware_stack.append(StarletteMiddleware(middleware_cls, **options))

    def mount(self, path: str, app: Any, name: str = None):
        """
        Mount a sub-application.
        
        Args:
            path: Mount path
            app: Sub-application instance
            name: Mount name
        """
        self.routes.append(Mount(path, app=app, name=name))

    def static(self, path: str = "/static", directory: str = "static", name: str = None):
        """
        Serve static files from a directory.
        
        Args:
            path: URL path prefix
            directory: Directory path containing static files
            name: Static files mount name
        """
        self.routes.append(Mount(path, app=StaticFiles(directory=directory), name=name))

    def _convert_to_response(self, result: Any) -> Response:
        """
        Convert handler result into Starlette Response.
        
        Args:
            result: Handler return value
            
        Returns:
            Response: Appropriate Starlette response
            
        Converts:
            - dict/list -> JSONResponse
            - str -> HTMLResponse
            - Response -> unchanged
            - other -> plain text Response
        """
        if isinstance(result, Response):
            return result
        if isinstance(result, dict):
            return JSONResponse(result)
        if isinstance(result, str):
            return HTMLResponse(result)
        if isinstance(result, (list, tuple)):
            return JSONResponse(result)
        return Response(str(result))

    def match_request(self, method: str, path: str):
        """
        Match a request using Rust router if available.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            tuple: (handler, params) or (None, None)
        """
        if self._rust_router is not None:
            # Use Rust router for faster matching
            result = self._rust_router.match_request(method, path)
            if result:
                handler, params = result
                return handler, params
        
        # Fallback to Starlette routing
        return None, None

    def build(self) -> Starlette:
        """
        Build the internal Starlette app.
        
        Returns:
            Starlette: Configured Starlette application instance
        """
        self.starlette_app = Starlette(
            debug=os.getenv("HASKE_DEBUG", "False").lower() == "true",
            routes=self.routes,
            middleware=self.middleware_stack,
        )
        return self.starlette_app

    async def __call__(self, scope, receive, send) -> None:
        """
        ASGI application interface.
        
        Makes Haske ASGI-compatible so it can be used with any ASGI server.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if self.starlette_app is None:
            self.build()
        
        # Try Rust routing first if available
        if (scope["type"] == "http" and self._rust_router is not None):
            method = scope["method"]
            path = scope["path"]
            
            handler, params = self.match_request(method, path)
            if handler:
                # Create request object
                from .request import Request
                request = Request(scope, receive, send, params)
                
                # Execute handler
                try:
                    result = await handler(request)
                    response = self._convert_to_response(result)
                    await response(scope, receive, send)
                    return
                except Exception as e:
                    # Fall back to Starlette if Rust handler fails
                    pass
        
        # Fall back to Starlette
        await self.starlette_app(scope, receive, send)

    def get_uptime(self) -> float:
        """
        Get application uptime in seconds.
        
        Returns:
            float: Uptime in seconds
        """
        return time.time() - self.start_time

    def get_stats(self) -> Dict[str, Any]:
        """
        Get application statistics.
        
        Returns:
            dict: Application statistics including uptime, route count, etc.
        """
        rust_routes = self._rust_router.route_count() if self._rust_router else 0
        
        return {
            "uptime": self.get_uptime(),
            "routes": len(self.routes),
            "rust_routes": rust_routes,
            "middleware": len(self.middleware_stack),
        }

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False, **kwargs):
        """
        Run the application using uvicorn.
        
        Args:
            host: Host to bind to, defaults to "0.0.0.0"
            port: Port to listen on, defaults to 8000
            debug: Enable debug mode, defaults to False
            **kwargs: Additional arguments to pass to uvicorn
            
        Note:
            In debug mode, uvicorn will automatically reload on code changes.
        """
        if self.starlette_app is None:
            self.build()
        
        # Set debug mode
        os.environ["HASKE_DEBUG"] = str(debug)
        
        # Run with uvicorn
        if debug:
            # Uvicorn needs an import string when reload=True
            # Get the module name from the calling frame
            frame = inspect.currentframe()
            try:
                # Walk up the call stack to find the module that called run()
                while frame:
                    module = inspect.getmodule(frame)
                    if module and module.__name__ != "__main__" and module.__name__ != "haske.app":
                        module_name = module.__name__
                        # Check if the module has an 'app' attribute
                        if hasattr(module, 'app'):
                            import_string = f"{module_name}:app"
                            break
                    frame = frame.f_back
                else:
                    # Fallback: use the main module
                    import_string = "__main__:app"
            finally:
                del frame  # Avoid reference cycles
            
            uvicorn.run(
                import_string,   # import string
                host=host,
                port=port,
                reload=True,
                log_level="debug",
                **kwargs
            )
        else:
            uvicorn.run(
                self,  # Pass self as the ASGI application
                host=host,
                port=port,
                reload=debug,
                **kwargs
            )