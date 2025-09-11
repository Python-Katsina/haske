"""
Main application class for Haske web framework.

Provides Haske application, plus integrated frontend dev/prod support:
- Production: serve static build output
- Development: spawn frontend dev server and proxy non-/api routes to it
"""

import os
import time
import uvicorn
import inspect
import subprocess
import shutil
import signal
import threading
import shlex
import socket
import sys
import asyncio
import importlib
from pathlib import Path
from typing import Any, Callable, Awaitable, Dict, List, Optional

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

# Import Rust router if available
try:
    from _haske_core import HaskeApp as RustRouter
    HAS_RUST_ROUTER = True
except Exception:
    HAS_RUST_ROUTER = False

<<<<<<< HEAD
# Import templates configuration so we can sync dirs
from . import templates as templates_module
=======
# Try to import watchdog for hot reload
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
>>>>>>> 99892b4cefc94f376578ef782d44acf5e3f0f4c8


# --------------------------------------------------------------------------
# Helper utilities
# --------------------------------------------------------------------------
def find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def find_free_port_for_app(start_port: int) -> int:
    """Find the next available port starting from start_port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port  # Found free port
            except OSError:
                port += 1


def wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    """Wait until TCP port is accepting connections or timeout; returns True if open."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def stream_subprocess_output(stream, prefix: str = "[frontend] "):
    """Read lines from subprocess stdout and print them (daemon thread)."""
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            print(f"{prefix}{line.rstrip()}")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Reverse proxy helper
# --------------------------------------------------------------------------
def create_reverse_proxy(
    target_host: str,
    target_port: int,
    excluded_endpoints: List[str] = [],
):
    """
    Create a Starlette app that forwards all requests to target_host:target_port
    except for excluded_endpoints (let Haske handle those).
    """
    import httpx
    target_url = f"http://{target_host}:{target_port}"

    async def proxy_endpoint(request):
        path = request.url.path
        # skip excluded endpoints → let Starlette/Haske handle them
        if any(path == ep or path.startswith(ep.rstrip("/") + "/") for ep in excluded_endpoints):
            return None

        upstream = f"{target_url}{path}"
        if request.url.query:
            upstream += "?" + request.url.query

        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "content-length", "accept-encoding")}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method=request.method,
                    url=upstream,
                    headers=headers,
                    content=await request.body(),
                    timeout=30.0,
                    follow_redirects=True,
                )
            response_headers = dict(resp.headers)
            response_headers.pop("content-encoding", None)
            return Response(resp.content, resp.status_code, headers=response_headers)
        except Exception as e:
            return Response(f"Proxy error: {e}", status_code=502)

    return Starlette(routes=[
        Route("/{path:path}", endpoint=proxy_endpoint,
              methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    ])


# --------------------------------------------------------------------------
# Hot reload handler class
# --------------------------------------------------------------------------
if HAS_WATCHDOG:
    class BackendFileChangeHandler(FileSystemEventHandler):
        """Handler for backend file changes to trigger hot reload"""
        
        def __init__(self, app_instance, patterns=None):
            self.app = app_instance
            self.patterns = patterns or ["*.py"]
            self.last_reload = time.time()
            self.reload_cooldown = 1.0  # seconds between reloads
            
        def on_modified(self, event):
            if not any(event.src_path.endswith(pattern) for pattern in self.patterns):
                return
                
            current_time = time.time()
            if current_time - self.last_reload < self.reload_cooldown:
                return
                
            self.last_reload = current_time
            print(f"\n🔄 [Haske] Detected change in {event.src_path}, triggering reload...")
            
            # Schedule reload in the event loop
            if hasattr(self.app, '_reload_task') and not self.app._reload_task.done():
                self.app._reload_task.cancel()
            
            self.app._reload_task = asyncio.create_task(self.app._trigger_reload())


# --------------------------------------------------------------------------
# Haske application
# --------------------------------------------------------------------------
class Haske:
    """
    Main Haske application class with integrated frontend support.
    """

    def __init__(
        self,
        name: str = "haske",
        template_dir: str = "templates",
        static_dir: str = "static",
    ) -> None:
        self.name = name
        self.routes: List = []
        self.middleware_stack: List = []
        self.starlette_app: Optional[Starlette] = None
        self.start_time = time.time()
        self.registered_routes: List[str] = []

        # Template/static directories (user-configurable)
        self.template_dir = template_dir or "templates"
        self.static_dir = static_dir or "static"

        # Ensure templates module knows about these directories
        templates_module.configure_templates(self.template_dir, self.static_dir)

        # Rust router (optional)
        self._rust_router = RustRouter() if HAS_RUST_ROUTER else None

        # Frontend integration state
        self._frontend_mode: str = "production"
        self._frontend_config: Dict[str, Any] = {}
        self._frontend_process: Optional[subprocess.Popen] = None
        self._frontend_dev_url: Optional[str] = None
        self._frontend_shutdown_cb = None

        # Hot reload state
        self._reload_observer = None
        self._reload_patterns = ["*.py"]
        self._reload_task = None
        self._reload_lock = asyncio.Lock()
        self._original_modules = set(sys.modules.keys())

        # DEFAULT MIDDLEWARE - CORS FIRST!
        self.middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
        # THEN add other middleware
        self.middleware(GZipMiddleware, minimum_size=500)

        # Auto-register default static mount (if directory exists)
        # Use absolute path to avoid WSGI/cwd issues
        try:
            self.static(path="/static", directory=self.static_dir, name="static")
        except Exception:
            # static() will print helpful message if directory missing
            pass

    def cors(self, **kwargs):
        self.middleware(CORSMiddleware, **kwargs)

    def allow_ips(self, ipaddrs):
        self.middleware(CORSMiddleware, allow_origins=ipaddrs)

    def allow_methods(self, methods):
        self.middleware(CORSMiddleware, allow_methods=methods)

    def _reorder_routes(self, new_mounts: List[Mount]) -> None:
        """
        Reorder routes to ensure API routes come before static/proxy mounts.
        """
        api_routes = []
        existing_mounts = []

        for route in self.routes:
            if isinstance(route, Mount):
                existing_mounts.append(route)
            else:
                api_routes.append(route)

        all_mounts = existing_mounts + new_mounts
        self.routes = api_routes + all_mounts
        print(f"[Haske] Route ordering: {len(api_routes)} API routes, {len(all_mounts)} mounts")

    # ---------------------------
    # ROUTING (decorator)
    # ---------------------------
    def route(self, path: str, methods: List[str] = None, name: str = None) -> Callable:
        methods = methods or ["GET"]
        self.registered_routes.append(path)

        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            async def endpoint(request):
                result = await func(request)
                return self._convert_to_response(result)

            self.routes.append(Route(path, endpoint, methods=methods, name=name))

            if self._rust_router is not None:
                from .routing import convert_path
                regex_path = convert_path(path.replace("<", ":").replace(">", ""))
                self._rust_router.add_route(",".join(methods), regex_path, func)
            return func

        return decorator

    # ---------------------------
    # FRONTEND (production & development)
    # ---------------------------
    def setup_frontend(self, config: Optional[Dict] = None, mode: Optional[str] = None):
        """
        Configure frontend serving (production static OR development proxy).
        """
        self._frontend_config = config or {}
        self._frontend_mode = (mode or self._frontend_config.get("mode") or "").lower() or None

        frontend_dir = Path(self._frontend_config.get("frontend_dir", "./frontend"))
        explicit_build_dir = self._frontend_config.get("build_dir")
        candidate_builds = [
            explicit_build_dir,
            str(frontend_dir / "out"),
            str(frontend_dir / "build"),
            str(frontend_dir / "dist"),
            str(frontend_dir / ".next"),
        ]
        found_build = next((Path(c) for c in candidate_builds if c and Path(c).exists()), None)

        force_dev = bool(self._frontend_config.get("force_dev", False))
        if self._frontend_mode is None:
            self._frontend_mode = "production" if found_build and not force_dev else "development"

        # ---------- PRODUCTION ----------
        if self._frontend_mode == "production":
            build_dir = Path(self._frontend_config.get("build_dir", found_build or (frontend_dir / "build")))
            if not build_dir.exists():
                raise RuntimeError(f"Frontend build directory not found: {build_dir}")

            static_mounts = [Mount("/", app=StaticFiles(directory=str(build_dir), html=True), name="frontend")]
            extras = {
                "_next": build_dir / "_next",
                "static": build_dir / "static",
                "public": build_dir / "public",
                "dist": build_dir / "dist",
            }
            for mount_name, path_obj in extras.items():
                if path_obj.exists():
                    url_path = f"/{path_obj.name}" if path_obj.name != "_next" else "/_next"
                    static_mounts.append(
                        Mount(url_path, app=StaticFiles(directory=str(path_obj)), name=f"frontend_{path_obj.name}")
                    )

            self._reorder_routes(static_mounts)
            print(f"[Haske] Serving frontend from {build_dir}")
            return

        # ---------- DEVELOPMENT ----------
        if os.getenv("HASKE_SKIP_FRONTEND") == "1":
            print("[Haske] Skipping frontend dev server (already running?)")
            return
        os.environ["HASKE_SKIP_FRONTEND"] = "1"

        dev_port = int(self._frontend_config.get("dev_port", find_free_port()))
        raw_cmd = self._frontend_config.get("dev_command")
        if raw_cmd:
            cmd_list = shlex.split(raw_cmd) if isinstance(raw_cmd, str) else list(raw_cmd)
        else:
            npm_exec = shutil.which("npm.cmd") or shutil.which("npm") or shutil.which("npx") or shutil.which("yarn") or shutil.which("pnpm")
            if not npm_exec:
                raise RuntimeError("npm/yarn/pnpm not found in PATH; install Node.js")
            cmd_list = [npm_exec, "run", "dev"]

        resolved_first = shutil.which(cmd_list[0]) or shutil.which(cmd_list[0] + ".cmd")
        if resolved_first:
            cmd_list[0] = resolved_first

        env = dict(os.environ)
        env.update(self._frontend_config.get("env", {}))
        env["PORT"] = str(dev_port)

        self._frontend_process = subprocess.Popen(
            cmd_list,
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        if self._frontend_process.stdout:
            threading.Thread(target=stream_subprocess_output, args=(self._frontend_process.stdout,), daemon=True).start()

        host = "127.0.0.1"
        if not wait_for_port(host, dev_port, timeout=20):
            print(f"[Haske] Warning: frontend dev server did not start on port {dev_port}")

        self._frontend_dev_url = f"http://{host}:{dev_port}"
        print(f"[Haske] Frontend dev server URL: {self._frontend_dev_url}")

        proxy_app = create_reverse_proxy(host, dev_port, excluded_endpoints=self.registered_routes)
        self._reorder_routes([Mount("/", app=proxy_app, name="frontend_proxy")])

        async def _shutdown_cb():
            if self._frontend_process:
                try:
                    print("[Haske] Stopping frontend dev server...")
                    self._frontend_process.send_signal(signal.SIGINT)
                    try:
                        self._frontend_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._frontend_process.terminate()
                        try:
                            self._frontend_process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            self._frontend_process.kill()
                except Exception as e:
                    print(f"[Haske] Error stopping frontend: {e}")

        self._frontend_shutdown_cb = _shutdown_cb
        if self.starlette_app:
            self.starlette_app.add_event_handler("shutdown", _shutdown_cb)

    def get_frontend_url(self, path: str = "") -> str:
        if self._frontend_mode == "production":
            return f"/{path.lstrip('/')}"
        else:
            if not self._frontend_dev_url:
                return "/"
            return f"{self._frontend_dev_url.rstrip('/')}/{path.lstrip('/')}"

    # ---------------------------
    # MIDDLEWARE & MOUNT
    # ---------------------------
    def middleware(self, middleware_cls, **options):
        self.middleware_stack.append(StarletteMiddleware(middleware_cls, **options))

    def mount(self, path: str, app: Any, name: str = None):
        self.routes.append(Mount(path, app=app, name=name))

    def static(self, path: str = "/static", directory: str = None, name: str = None):
        """
        Mount static files directory. Defaults to the app's configured static_dir.
        directory may be relative or absolute. We resolve to absolute path.
        If the directory does not exist we print a warning and skip mounting.
        """
        directory = directory or self.static_dir
        # If directory is inside the package (e.g. "static"), make it absolute relative to project root
        # Allow user to pass absolute path as well.
        abs_path = os.path.abspath(directory)

        if not os.path.isdir(abs_path):
            print(f"[Haske] Static directory not found: {abs_path}. Skipping static mount.")
            return

        # Update configured static_dir to resolved absolute path
        self.static_dir = abs_path
        # Keep template module in sync
        templates_module.configure_templates(self.template_dir, self.static_dir)

        # Append mount and keep mounts ordered to end
        self.routes.append(Mount(path, app=StaticFiles(directory=abs_path), name=name or "static"))
        print(f"[Haske] ✅ Serving static from: {abs_path} at {path}")

    # ---------------------------
    # RESPONSE HANDLING
    # ---------------------------
    def _convert_to_response(self, result: Any) -> Response:
        if isinstance(result, Response):
            response = result
        elif isinstance(result, dict):
            response = JSONResponse(result)
        elif isinstance(result, str):
            response = HTMLResponse(result)
        elif isinstance(result, (list, tuple)):
            response = JSONResponse(result)
        else:
            response = Response(str(result))
        self._add_cors_headers(response)
        return response

    def _add_cors_headers(self, response: Response) -> None:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"

    # ---------------------------
    # ROUTER MATCH
    # ---------------------------
    def match_request(self, method: str, path: str):
        if self._rust_router:
            result = self._rust_router.match_request(method, path)
            if result:
                handler, params = result
                return handler, params
        return None, None

    # ---------------------------
    # HOT RELOAD FUNCTIONALITY
    # ---------------------------
    async def _trigger_reload(self):
        """Trigger application reload after a short delay"""
        await asyncio.sleep(0.5)  # Small delay to avoid rapid successive reloads
        
        async with self._reload_lock:
            try:
                print("🔄 [Haske] Reloading application...")
                
                # Clear routes and middleware
                self.routes.clear()
                self.middleware_stack.clear()
                self.registered_routes.clear()
                
                # Reload all project modules
                self._reload_project_modules()
                
                # Rebuild the application
                if self.starlette_app:
                    self.starlette_app = None
                self.build()
                
                print("✅ [Haske] Application reloaded successfully")
                
            except Exception as e:
                print(f"❌ [Haske] Reload failed: {e}")
                import traceback
                traceback.print_exc()
    
    def _reload_project_modules(self):
        """Reload all project modules except standard library and third-party packages"""
        current_modules = set(sys.modules.keys())
        new_modules = current_modules - self._original_modules
        
        for module_name in list(new_modules):
            if (module_name.startswith('__') or 
                module_name.startswith('_') or
                any(module_name.startswith(lib) for lib in ['uvicorn', 'starlette', 'asyncio', 'os', 'sys', 'time'])):
                continue
                
            try:
                module = sys.modules[module_name]
                importlib.reload(module)
                print(f"   ↳ Reloaded module: {module_name}")
            except Exception as e:
                print(f"   ↳ Failed to reload {module_name}: {e}")
    
    def _setup_hot_reload(self, watch_patterns=None, watch_directories=None):
        """Set up file watching for hot reload"""
        if self._reload_observer or not HAS_WATCHDOG:
            return
            
        patterns = watch_patterns or self._reload_patterns
        directories = watch_directories or ['.']
        
        self._reload_observer = Observer()
        event_handler = BackendFileChangeHandler(self, patterns)
        
        for directory in directories:
            if Path(directory).exists():
                self._reload_observer.schedule(event_handler, directory, recursive=True)
                print(f"[Haske] Watching {directory} for changes")
        
        self._reload_observer.start()
        print("[Haske] Hot reload enabled - watching for backend changes")
    
    def _stop_hot_reload(self):
        """Stop the file watcher"""
        if self._reload_observer:
            self._reload_observer.stop()
            self._reload_observer.join()
            self._reload_observer = None

    # ---------------------------
    # STARLETTE APP
    # ---------------------------
    def build(self) -> Starlette:
        # Re-order mounts to ensure API routes first, then mounts
        # (This will not duplicate mounts if build is called multiple times.)
        # Create Starlette app with the current routes & middleware
        self.starlette_app = Starlette(
            debug=os.getenv("HASKE_DEBUG", "False").lower() == "true",
            routes=self.routes,
            middleware=self.middleware_stack,
        )
        if self._frontend_shutdown_cb:
            self.starlette_app.add_event_handler("shutdown", self._frontend_shutdown_cb)
        return self.starlette_app

    async def __call__(self, scope, receive, send) -> None:
        if self.starlette_app is None:
            self.build()

        if scope["type"] == "http" and self._rust_router:
            method = scope["method"]
            path = scope["path"]
            handler, params = self.match_request(method, path)
            if handler:
                from .request import Request
                request = Request(scope, receive, send, params)
                try:
                    result = await handler(request)
                    response = self._convert_to_response(result)
                    await response(scope, receive, send)
                    return
                except Exception:
                    pass

        await self.starlette_app(scope, receive, send)

    # ---------------------------
    # APP INFO
    # ---------------------------
    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def get_stats(self) -> Dict[str, Any]:
        rust_routes = self._rust_router.route_count() if self._rust_router else 0
        return {
            "uptime": self.get_uptime(),
            "routes": len(self.routes),
            "rust_routes": rust_routes,
            "middleware": len(self.middleware_stack),
        }

    # ---------------------------
    # RUN
    # ---------------------------
    def run(self, host: str = "0.0.0.0", choosen_port: int = 8000, debug: bool = False, 
            hot_reload: bool = True, watch_dirs: List[str] = None, **kwargs):
        """
        Run the Haske application with optional hot reload.
        
        Args:
            host: Host to bind to
            choosen_port: Preferred port (will find next available if taken)
            debug: Enable debug mode
            hot_reload: Enable hot reload for backend changes
            watch_dirs: Directories to watch for changes (default: current directory)
            **kwargs: Additional arguments for uvicorn
        """
        if self.starlette_app is None:
            self.build()

        os.environ["HASKE_DEBUG"] = str(debug)
        port = find_free_port_for_app(choosen_port)

        if choosen_port != port:
            print(f"""Port {choosen_port} not available. Using port {port} instead.\n
            You can change this by adding your preferred port """)

        # Setup hot reload if enabled and in debug mode
        if debug and hot_reload:
            try:
                self._setup_hot_reload(watch_directories=watch_dirs)
                # Add shutdown handler to stop the observer
                original_shutdown = getattr(self.starlette_app, 'shutdown', None)
                
                async def shutdown_with_cleanup():
                    self._stop_hot_reload()
                    if original_shutdown:
                        await original_shutdown()
                
                self.starlette_app.shutdown = shutdown_with_cleanup
                
            except ImportError:
                print("[Haske] watchdog not installed. Hot reload disabled.")
                print("   Install with: pip install watchdog")
            except Exception as e:
                print(f"[Haske] Failed to setup hot reload: {e}")

        if debug:
            frame = inspect.currentframe()
            try:
                while frame:
                    module = inspect.getmodule(frame)
                    if module and module.__name__ not in ("__main__", "haske.app"):
                        module_name = module.__name__
                        if hasattr(module, "app"):
                            import_string = f"{module_name}:app"
                            break
                    frame = frame.f_back
                else:
                    import_string = "__main__:app"
            finally:
                del frame
            try:
                uvicorn.run(import_string, host=host, port=port, reload=hot_reload, log_level="debug", **kwargs)
            except Exception:
                uvicorn.run(self, host=host, port=port+1, reload=hot_reload, log_level="debug", **kwargs)
        else:
            try:
                uvicorn.run(self, host=host, port=port, reload=False, **kwargs)
            except Exception:
                uvicorn.run(self, host=host, port=port+1, reload=debug, **kwargs)
