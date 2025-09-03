# Haske Developer Guide

> Draft v0.1 — generated from the current repository structure and README. Please leave comments wherever the API differs from the code so we can align the docs.

---

## 1) What is Haske?

Haske is an async-first Python web framework with a Rust-accelerated core for routing, JSON, templating, compression and other hot paths. It aims to be as *easy as Flask*, as *complete as Django* for full‑stack work, while reaching *FastAPI‑class performance* (or better) thanks to Rust.

**Key traits**
- ASGI-native (works with Uvicorn/Hypercorn)
- Type-friendly (Pydantic integration planned)
- Modular architecture (Python façade + Rust core)
- CLI for development and deployment

---

## 2) Framework layout

```
haske/
├─ haske-core/         # Rust acceleration crate (PyO3)
├─ haske-python/       # Python framework layer (ASGI app, routing, etc.)
├─ benchmark/          # Bench tools & scenarios
└─ tests/              # Unit/async tests
```

### 2.1 haske-core (Rust)
- Exposes `_haske_core` via PyO3.
- Optimizes: route matching, JSON encode/decode, compression, hashing/crypto hooks, (optionally) template rendering.

### 2.2 haske-python (Python)
Suggested modules (align with code as it evolves):
- `haske.app` — main application class `Haske`
- `haske.routing` — router, route decorators, path params
- `haske.requests` / `haske.responses` — request/response types
- `haske.middleware` — middleware contracts + factories
- `haske.templates` — Jinja2 (or Rust-backed) rendering helpers
- `haske.auth` — session/JWT helpers
- `haske.orm` — thin wrapper over SQLAlchemy async engine
- `haske.cli` — `haske` command (dev server, new, build, routes)

> If a module name differs in code, prefer the code. Update this doc with the exact import paths.

---

## 3) Installation

### 3.1 Quick start
```bash
python -m venv .venv && source .venv/bin/activate  # (PowerShell: .venv\Scripts\Activate.ps1)
pip install --upgrade pip setuptools wheel
pip install haske
```

### 3.2 From source (development)
```bash
git clone https://github.com/Python-Katsina/haske.git
cd haske
pip install -e .
```

### 3.3 Platform notes
- **Windows**: Install Rust via `winget install -e --id Rustlang.Rust` first when doing editable builds.
- **Linux/macOS**: Install Rust via `curl https://sh.rustup.rs | sh` and `source ~/.cargo/env`.
- **Android Termux**:
  ```bash
  pkg update && pkg upgrade
  pkg install python rust clang libffi-dev python-dev
  pip install --upgrade pip setuptools wheel
  # For editable installs that fail isolation
  pip install --no-build-isolation -e .
  ```
- **Docker**: See §13 for a minimal image.

> If Rust is not available or fails, use `HASKE_NO_RUST=1` to force Python‑only paths.

---

## 4) Your First Haske App

```python
from haske import Haske, Request, JSONResponse

app = Haske(__name__)

@app.route("/")
async def root(request: Request):
    return {"message": "Hello, Haske!"}

# Path parameter (style A)
@app.route("/users/{name}")
async def hello_user(request: Request):
    name = request.path_params("name")
    return {"greeting": f"Hello, {name}!"}

# Alternatively, if the router supports angle brackets
# @app.route("/users/<name>")
# async def hello_user(request: Request):
#     name = request.get_path_param("name")
#     return {"greeting": f"Hello, {name}!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

**Run**
```bash
haske dev --module your_app:app --host 0.0.0.0 --port 8000
# or
python your_app.py
```

> If your current code uses the `":name"` placeholder (e.g. `/users/:name`), confirm the router’s matcher. If 404 occurs, switch to `{name}`.

---

## 5) Routing

### 5.1 Defining routes
```python
@app.route("/items")                 # GET by default; see methods below
@app.route("/items", methods=["POST"])  # Explicit methods
```

### 5.2 Path parameters
```python
@app.route("/items/{item_id}")
async def get_item(request: Request):
    item_id = request.get_path_param("item_id")
    return {"id": int(item_id)}
```

### 5.3 Query parameters
```python
@app.route("/search")
async def search(request: Request):
    q = request.query.get("q", "")
    page = int(request.query.get("page", 1))
    return {"q": q, "page": page}
```

### 5.4 Request body (JSON/form)
```python
@app.route("/echo", methods=["POST"])
async def echo(request: Request):
    data = await request.json()  # or await request.form()
    return JSONResponse({"received": data})
```

### 5.5 Responses
- Return `dict` → auto JSON response
- Or return explicit `JSONResponse`, `HTMLResponse`, `PlainTextResponse`, `StreamingResponse` (as provided by `haske.responses`).

### 5.6 Status, headers, cookies
```python
return JSONResponse({"ok": True}, status_code=201, headers={"X-Trace": "abc"})
```

---

## 6) Middleware

```python
from haske.middleware import CORSMiddlewareFactory, RateLimitMiddlewareFactory

app.middleware(CORSMiddlewareFactory(allow_origins=["*"]))
app.middleware(RateLimitMiddlewareFactory(max_requests=100, time_window=60))
```

**Custom middleware**
```python
@app.middleware
async def metrics_middleware(request, call_next):
    # pre
    response = await call_next(request)
    # post
    return response
```

---

## 7) Dependency Injection (optional pattern)
If the codebase exposes a DI helper, use it; otherwise, a simple pattern:
```python
def with_db(handler):
    async def wrapper(request: Request, *args, **kwargs):
        request.state.db = make_db()
        try:
            return await handler(request, *args, **kwargs)
        finally:
            await request.state.db.dispose()
    return wrapper

@app.route("/users")
@with_db
async def list_users(request: Request):
    return await request.state.db.fetch_users()
```

---

## 8) Templating

```python
from haske.templates import render_template, render_template_async

@app.route("/dashboard")
async def dashboard(request: Request):
    user = {"name": "Yusee"}
    return render_template("dashboard.html", user=user)

@app.route("/profile")
async def profile(request: Request):
    content = await render_template_async("profile.html", user={"name": "Yusee"})
    return HTMLResponse(content)
```

> If Rust-backed templates are enabled in `haske-core`, rendering may be significantly faster.

---

## 9) Database & ORM

```python
from haske.orm import Database, Model
from sqlalchemy import Column, Integer, String

db = Database("sqlite+aiosqlite:///./app.db")

class User(Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)

@app.route("/users")
async def users(request: Request):
    return {"users": await User.all()}
```

**Supported drivers** (planned/typical): PostgreSQL (asyncpg), MySQL (aiomysql), SQLite (aiosqlite).

---

## 10) Authentication

```python
from haske.auth import AuthManager
from haske.responses import JSONResponse

auth = AuthManager(secret_key="your-secret-key")

@app.route("/login", methods=["POST"])
async def login(request: Request):
    user = await validate_credentials(request)
    resp = JSONResponse({"status": "ok"})
    auth.create_session(resp, user.id, user.data)  # sets cookie / headers
    return resp

@app.route("/protected")
@auth.login_required
async def protected(request: Request):
    return {"user": request.user}
```

> JWT helpers and role decorators (`@auth.roles_required`) may also be available as the code matures.

---

## 11) WebSockets & Background Tasks

```python
from haske import WebSocket, BackgroundTask, JSONResponse

@app.websocket_route("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    while True:
        msg = await websocket.receive_text()
        await websocket.send_text(f"Echo: {msg}")

@app.route("/process", methods=["POST"])
async def process(request: Request):
    data = await request.json()
    task = BackgroundTask(process_data_async, data)
    return JSONResponse({"status": "processing"}, background=task)

async def process_data_async(data):
    # long running work
    ...
```

---

## 12) CLI

```bash
# Dev server
haske dev --module app.main:app --host 0.0.0.0 --port 8000

# Create project scaffold\phaske new my-project

# Build (optimize / compile extensions)
haske build

# Run tests
haske test

# Show routes\phaske routes

# Health check
haske check
```

---

## 13) Configuration

Environment variables:
```
HASKE_DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///./app.db
SECRET_KEY=change-me
HASKE_NO_RUST=1     # fallback to Python
```

---

## 14) Deployment

### 14.1 Uvicorn (production)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 14.2 Dockerfile (minimal)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["haske", "dev", "--module", "app.main:app", "--host", "0.0.0.0"]
```

---

## 15) Testing

Use `pytest` and `httpx.AsyncClient` (or Starlette’s test client) to test routes and middleware.
```python
import pytest
from httpx import AsyncClient
from haske import Haske

@pytest.mark.asyncio
async def test_root():
    app = Haske(__name__)

    @app.route("/")
    async def root(request):
        return {"ok": True}

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/")
        assert res.status_code == 200
        assert res.json()["ok"] is True
```

---

## 16) Performance Notes

- Ensure Rust toolchain is available to unlock accelerations.
- Enable gzip/brotli/zstd compression middleware when serving large JSON.
- Use DB connection pooling for async backends.
- Offload heavy CPU tasks with background tasks or external workers.

---

## 17) Troubleshooting

**Editable install fails on Termux**
```bash
pip install --upgrade pip setuptools wheel
pip install --no-build-isolation -e .
```

**`BackendUnavailable: Cannot import 'setuptools.build_meta'`**
- Reinstall `setuptools`, then retry with `--no-build-isolation`.

**404 for `/users/:name`**
- Do not put `:` in the browser URL. Use `/users/Yusee`.
- Prefer route pattern `/users/{name}` in code.

**Port already in use**
```bash
haske dev --module app.main:app --port 8001
```

---

## 18) Roadmap (proposed)
- Pydantic v2 integration for request/response models
- Auto‑OpenAPI generation & interactive docs
- First‑class DI container
- Built-in session/JWT strategies with refresh tokens
- Built-in CSRF + CORS hardening presets
- Static files & templating CLI scaffolds
- `maturin`/`setuptools-rust` build targets for `haske-core`

---

## 19) Reference (Index)

- `Haske` — app initialization, `.route`, `.middleware`, `.run`
- `Request` — `.query`, `.headers`, `.cookies`, `.json()`, `.form()`, `.get_path_param()`
- `Responses` — `JSONResponse`, `HTMLResponse`, `PlainTextResponse`, `StreamingResponse`
- `Middleware` — function middleware or factory-based
- `Templates` — `render_template`, `render_template_async`
- `ORM` — `Database`, `Model`
- `Auth` — `AuthManager`, decorators
- `CLI` — `haske dev|new|build|routes|test|check`

---

### Appendix A — Example Project Structure
```
my-project/
├── app/
│   ├── main.py          # Main application
│   ├── models.py        # Database models
│   └── routes.py        # Route definitions
├── static/              # Static files
├── templates/           # Jinja2 templates
├── migrations/          # Database migrations
├── tests/               # Test files
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```

---

**Maintainers**: update import paths and examples as APIs stabilize.

