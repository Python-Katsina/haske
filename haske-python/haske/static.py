# haske/static.py
"""
Frontend static file serving for Haske framework.

This module provides utilities to serve React, Vue, Next.js, and other
frontend frameworks from the same Haske server.
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, HTMLResponse, Response
from starlette.background import BackgroundTask

class FrontendServer:
    """
    Serve frontend static files with SPA (Single Page Application) support.
    
    This class handles serving frontend builds with proper routing,
    fallback to index.html for SPA routing, and development/production modes.
    """
    
    def __init__(self, 
                 directory: str = "./frontend/build",
                 index: str = "index.html",
                 spa_mode: bool = True,
                 development_mode: bool = False):
        """
        Initialize frontend server.
        
        Args:
            directory: Frontend build directory
            index: Main index file name
            spa_mode: Enable SPA routing (fallback to index.html)
            development_mode: Development mode (disable caching, etc.)
        """
        self.directory = Path(directory)
        self.index = index
        self.spa_mode = spa_mode
        self.development_mode = development_mode
        self.static_files = StaticFiles(directory=str(self.directory))
        
        # Common frontend framework build directories
        self.common_paths = [
            self.directory,
            self.directory / "build",
            self.directory / "dist",
            self.directory / "out",
            self.directory / "public",
            self.directory / "out/_next/static",
        ]
    
    async def serve(self, path: str = "") -> Response:
        """
        Serve frontend static files.
        
        Args:
            path: Request path
            
        Returns:
            Response: File response or HTML response for SPA
        """
        # Clean path to prevent directory traversal
        clean_path = path.lstrip('/')
        if '..' in clean_path:
            return Response("Invalid path", status_code=400)
        
        # Try to serve static file
        file_path = self.directory / clean_path
        
        # Check if file exists and is a file (not directory)
        if file_path.is_file() and file_path.exists():
            return await self._serve_file(file_path)
        
        # For SPA mode, fallback to index.html for all routes
        if self.spa_mode:
            index_path = self.directory / self.index
            if index_path.exists():
                return await self._serve_file(index_path)
        
        # File not found
        return Response("Not found", status_code=404)
    
    async def _serve_file(self, file_path: Path) -> Response:
        """Serve a single file with proper headers."""
        headers = {}
        
        # Set content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type:
            headers["Content-Type"] = content_type
        
        # Cache control for production
        if not self.development_mode:
            headers["Cache-Control"] = "public, max-age=3600"
        else:
            headers["Cache-Control"] = "no-cache, no-store"
        
        return FileResponse(
            str(file_path),
            headers=headers,
            background=BackgroundTask(self._log_serve, file_path)
        )
    
    async def _log_serve(self, file_path: Path):
        """Log file serving (for debugging)."""
        if self.development_mode:
            print(f"Serving frontend file: {file_path}")
    
    def detect_frontend_framework(self) -> Optional[str]:
        """
        Detect which frontend framework is being used.
        
        Returns:
            Optional[str]: Framework name or None
        """
        framework_indicators = {
            "react": ["static/js", "asset-manifest.json", "react"],
            "vue": ["vue", "dist/vue"],
            "nextjs": ["_next", ".next"],
            "angular": ["angular", "main.js"],
            "svelte": ["svelte", "build/svelte"],
        }
        
        for framework, indicators in framework_indicators.items():
            for indicator in indicators:
                if (self.directory / indicator).exists():
                    return framework
        
        return None
    
    # def setup_middleware(self, app):
    #     """
    #     Setup frontend serving middleware for the app.
        
    #     Args:
    #         app: Haske application instance
    #     """
    #     # Mount static filesgi
    #     app.mount("/static", self.static_files, name="static")
        
    #     # Add catch-all route for SPA
    #     if self.spa_mode:
    #         @app.route("/{path:path}")
    #         async def catch_all(request):
    #             path = request.path_params.get("path", "")
    #             return await self.serve(path)

    def setup_middleware(self, app):
        """
        Setup frontend serving middleware for the app.
        
        Args:
            app: Haske application instance
        """

        # Always mount the main build directory
        if self.directory.exists():
            app.mount("/", StaticFiles(directory=str(self.directory), html=True), name="frontend")

        # Also check for common frontend subfolders
        extra_static_paths = [
            ("_next/static", str(self.directory / "_next" / "static")),  # Next.js
            ("static", str(self.directory / "static")),                  # CRA/Vite
            ("public", str(self.directory / "public")),                  # Next.js public
            ("dist", str(self.directory / "dist")),                      # Vue/Angular builds
            ("_next/static/css", str(self.directory / "_next" / "static" / "css")),                        # Svelte builds
        ]

        for mount_path, static_dir in extra_static_paths:
            if Path(static_dir).exists():
                app.mount(f"/{mount_path}", StaticFiles(directory=static_dir), name=mount_path)

        # Add catch-all route for SPA fallback
        if self.spa_mode:
            @app.route("/{path:path}")
            async def catch_all(request):
                return await self.serve(request.path_params.get("path", ""))

            @app.route("/")
            async def index(request):
                return await self.serve("")


class FrontendDevelopmentServer:
    """
    Development server proxy for frontend frameworks.
    
    Proxies requests to frontend dev servers (Vite, Create React App, etc.)
    during development.
    """
    
    def __init__(self, 
                 dev_server_url: str = "http://localhost:3000",
                 enabled: bool = True):
        """
        Initialize development server proxy.
        
        Args:
            dev_server_url: Frontend development server URL
            enabled: Whether dev server proxy is enabled
        """
        self.dev_server_url = dev_server_url.rstrip('/')
        self.enabled = enabled
        self.http_client = None
    
    async def proxy_request(self, request) -> Response:
        """
        Proxy request to frontend development server.
        
        Args:
            request: Original request
            
        Returns:
            Response: Proxied response
        """
        if not self.enabled:
            return Response("Development server not enabled", status_code=503)
        
        try:
            import httpx
            
            if self.http_client is None:
                self.http_client = httpx.AsyncClient()
            
            # Build target URL
            target_url = f"{self.dev_server_url}{request.url.path}"
            if request.url.query:
                target_url += f"?{request.url.query}"
            
            # Forward headers (filter out some that shouldn't be forwarded)
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ['host', 'content-length']
            }
            
            # Make the request to dev server
            response = await self.http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body(),
                timeout=30.0
            )
            
            # Return the response from dev server
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except Exception as e:
            return Response(f"Dev server error: {str(e)}", status_code=502)

def create_frontend_config(framework: str = "react") -> Dict[str, Any]:
    """
    Create default configuration for different frontend frameworks.
    
    Args:
        framework: Frontend framework name
        
    Returns:
        Dict: Configuration dictionary
    """
    configs = {
        "react": {
            "build_dir": "./frontend/build",
            "dev_server": "http://localhost:3000",
            "index": "index.html",
            "static_dir": "./frontend/build/static"
        },
        "vue": {
            "build_dir": "./frontend/dist",
            "dev_server": "http://localhost:5173",
            "index": "index.html",
            "static_dir": "./frontend/dist"
        },
        "nextjs": {
            "build_dir": "./frontend/.next",
            "dev_server": "http://localhost:3000",
            "index": "index.html",
            "static_dir": "./frontend/.next/static"
        },
        "angular": {
            "build_dir": "./frontend/dist",
            "dev_server": "http://localhost:4200",
            "index": "index.html",
            "static_dir": "./frontend/dist"
        },
        "svelte": {
            "build_dir": "./frontend/build",
            "dev_server": "http://localhost:5173",
            "index": "index.html",
            "static_dir": "./frontend/build"
        }
    }
    
    return configs.get(framework, configs["react"])

# class FrontendManager:
#     """
#     Comprehensive frontend management for Haske.
    
#     Handles both production builds and development servers.
#     """
    
#     def __init__(self, app, config: Optional[Dict] = None):
#         """
#         Initialize frontend manager.
        
#         Args:
#             app: Haske application
#             config: Frontend configuration
#         """
#         self.app = app
#         self.config = config or create_frontend_config()
#         self.production_server = None
#         self.development_server = None
#         self.mode = "production"  # or "development"
    
#     def setup(self, mode: str = "production"):
#         """
#         Setup frontend serving based on mode.
        
#         Args:
#             mode: "production" or "development"
#         """
#         self.mode = mode
        
#         if mode == "production":
#             self._setup_production()
#         else:
#             self._setup_development()
    
#     def _setup_production(self):
#         """Setup production frontend serving."""
#         build_dir = self.config.get("build_dir", "./frontend/build")
#         self.production_server = FrontendServer(
#             directory=build_dir,
#             index=self.config.get("index", "index.html"),
#             spa_mode=True,
#             development_mode=False
#         )
        
#         # Setup static file serving
#         static_dir = self.config.get("static_dir")
#         if static_dir and Path(static_dir).exists():
#             self.app.static("/static", static_dir)
        
#         # Setup SPA catch-all
#         self.production_server.setup_middleware(self.app)
    
#     def _setup_development(self):
#         """Setup development frontend proxy."""
#         dev_server_url = self.config.get("dev_server", "http://localhost:3000")
#         self.development_server = FrontendDevelopmentServer(
#             dev_server_url=dev_server_url,
#             enabled=True
#         )
        
#         # Setup dev server proxy for all frontend routes
#         @self.app.route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
#         async def dev_proxy(request):
#             path = request.get_path_param("path", "")
            
#             # Don't proxy API routes to frontend dev server
#             if path.startswith("api/") or path == "api":
#                 # Let Haske handle API routes
#                 return Response("API route not found", status_code=404)
            
#             # Proxy all other routes to frontend dev server
#             return await self.development_server.proxy_request(request)
    
#     def get_frontend_url(self, path: str = "") -> str:
#         """
#         Get frontend URL for redirects or links.
        
#         Args:
#             path: Frontend path
            
#         Returns:
#             str: Full frontend URL
#         """
#         if self.mode == "production":
#             return f"/{path.lstrip('/')}"
#         else:
#             dev_url = self.config.get("dev_server", "http://localhost:3000")
#             return f"{dev_url}/{path.lstrip('/')}"


import subprocess
import signal
import socket
import os
from pathlib import Path
from typing import Dict, Optional
from starlette.responses import Response

# Helper: find free port
def find_free_port():
    """Find an available TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FrontendManager:
    """
    Comprehensive frontend management for Haske.
    
    Handles both production builds and development servers
    across any JS-based framework (React, Vue, Next.js, Svelte, etc.).
    """

    def __init__(self, app, config: Optional[Dict] = None):
        """
        Initialize frontend manager.

        Args:
            app: Haske application
            config: Frontend configuration
        """
        self.app = app
        self.config = config or {}
        self.production_server = None
        self.development_server = None
        self.frontend_process = None
        self.mode = "production"  # default
        self.port = None
        self.dev_server_url = None

    def setup(self, mode: Optional[str] = None):
        """
        Setup frontend serving based on mode.

        Args:
            mode: "production" or "development" (auto-detected if None)
        """
        # Mode detection
        if mode:
            self.mode = mode
        else:
            build_dir = os.path.join(
                self.config.get("frontend_dir", "./frontend"),
                self.config.get("build_subdir", "build"),
            )
            self.mode = "production" if Path(build_dir).exists() else "development"

        # Assign a port for dev mode
        if self.mode == "development":
            self.port = find_free_port()
            self.dev_server_url = f"http://localhost:{self.port}"

        # Setup frontend
        if self.mode == "production":
            self._setup_production()
        else:
            self._setup_development()

    def _setup_production(self):
        """Setup production frontend serving."""
        build_dir = self.config.get("build_dir", "./frontend/build")
        index_file = self.config.get("index", "index.html")

        # Serve static frontend files
        self.production_server = FrontendServer(
            directory=build_dir,
            index=index_file,
            spa_mode=True,
            development_mode=False,
        )

        static_dir = self.config.get("static_dir")
        if static_dir and Path(static_dir).exists():
            self.app.static("/static", static_dir)

        # SPA catch-all middleware
        self.production_server.setup_middleware(self.app)


import platform
import shlex
import shutil

def _setup_development(self):
    """Setup development frontend proxy with process spawning."""
    cwd = self.config.get("frontend_dir", "./frontend")
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    dev_cmd = [npm_cmd, "run", "dev"]
    proc = subprocess.Popen(
    "where npm",
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
    out, err = proc.communicate()

    # Framework-specific commands
    if self.config.get("dev_command"):
        start_cmd = self.config["dev_command"] + ["--", "-p", str(self.port)]
    else:
        start_cmd = [npm_cmd, "run", "dev", "--", "-p", str(self.port)]

    print(f"🚀 Starting frontend dev server: {' '.join(start_cmd)} in {cwd}")

    # Detect OS
    is_windows = platform.system().lower().startswith("win")

    if is_windows:
        # Use npm.cmd if available
        npm_path = out.strip()
        if npm_path is None:
            raise RuntimeError("❌ npm not found. Make sure Node.js is installed and npm is in PATH.")

        # Convert command list into string for shell=True
        cmd = f'"{npm_path}" run dev -- -p {self.port}'
        shell_flag = True
    else:
        # On Linux/macOS, pass list directly
        cmd = start_cmd
        shell_flag = False

    self.frontend_process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env={**os.environ, **self.config.get("env", {})},
        shell=shell_flag,
    )
