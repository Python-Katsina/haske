# haske/app.py - Updated run method
from typing import Any, Callable, Awaitable, Dict, List, Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
import os
import time
import uvicorn
import inspect
import sys

class Haske:
    def __init__(self, name: str = "haske") -> None:
        self.name = name
        self.routes = []
        self.middleware_stack = []
        self.starlette_app: Optional[Starlette] = None
        self.start_time = time.time()
        
        # Default middleware
        self.middleware(GZipMiddleware, minimum_size=500)

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
            
            return func
        return decorator

    def middleware(self, middleware_cls, **options):
        """
        Register middleware. Example:
            app.middleware(CORSMiddleware, allow_origins=["*"])
        """
        self.middleware_stack.append(StarletteMiddleware(middleware_cls, **options))

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
        
        await self.starlette_app(scope, receive, send)

    def get_uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time

    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics"""
        return {
            "uptime": self.get_uptime(),
            "routes": len(self.routes),
            "middleware": len(self.middleware_stack),
        }

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False, **kwargs):
        """
        Run the application using uvicorn.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
            **kwargs: Additional arguments to pass to uvicorn
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