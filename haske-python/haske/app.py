# haske/app.py
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
            raise HTTPException(status_code=404)

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
              methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
    ])


# --------------------------------------------------------------------------
# Haske application
# --------------------------------------------------------------------------
class Haske:
    """
    Main Haske application class with integrated frontend support.
    """

    def __init__(self, name: str = "haske") -> None:
        self.name = name
        self.routes: List = []
        self.middleware_stack: List = []
        self.starlette_app: Optional[Starlette] = None
        self.start_time = time.time()
        self.registered_routes = []

        # Rust router (optional)
        self._rust_router = RustRouter() if HAS_RUST_ROUTER else None

        # Frontend integration state
        self._frontend_mode: str = "production"
        self._frontend_config: Dict[str, Any] = {}
        self._frontend_process: Optional[subprocess.Popen] = None
        self._frontend_dev_url: Optional[str] = None
        self._frontend_shutdown_cb = None

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

    def static(self, path: str = "/static", directory: str = "static", name: str = None):
        self.routes.append(Mount(path, app=StaticFiles(directory=directory), name=name))

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
    # STARLETTE APP
    # ---------------------------
    def build(self) -> Starlette:
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
    def run(self, host: str = "0.0.0.0", choosen_port: int = 8000, debug: bool = False, **kwargs):
        if self.starlette_app is None:
            self.build()

        os.environ["HASKE_DEBUG"] = str(debug)
        port = find_free_port_for_app(choosen_port)

        if choosen_port != port:
            print(f"""⚠️ Port {choosen_port} not available. Using port {port} instead.\n
            You can change this by adding your prefered port """)

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
                uvicorn.run(import_string, host=host, port=port, reload=True, log_level="debug", **kwargs)
            except Exception:
                uvicorn.run(self, host=host, port=port+1, reload=True, log_level="debug", **kwargs)
        else:
            try:
                uvicorn.run(self, host=host, port=port, reload=debug, **kwargs)
            except Exception:
                uvicorn.run(self, host=host, port=port+1, reload=debug, **kwargs)




