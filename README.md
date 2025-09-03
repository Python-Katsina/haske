# Haske - High-Performance Python Web Framework

Haske is a modern, high-performance web framework for Python that combines the simplicity of Python with the speed of Rust. Built on top of Starlette and powered by Rust extensions, Haske delivers exceptional performance for web applications and APIs.

## 🚀 Features

- **Blazing Fast**: Rust-powered core for maximum performance
- **Async First**: Built on ASGI with full async/await support
- **Type Safe**: Comprehensive type annotations and Pydantic integration
- **Developer Friendly**: Intuitive API with excellent documentation
- **Extensible**: Modular architecture with plugin support
- **Production Ready**: Built-in security, monitoring, and deployment tools

## 📦 Installation

### Prerequisites

- Python 3.8+
- Rust toolchain (will be installed automatically if missing)

### Quick Install

```bash
pip install haske

From Source
bash

# Clone the repository
git clone https://github.com/your-org/haske.git
cd haske

# Install with Rust extensions (automatic)
pip install .

# Or install in development mode
pip install -e .

Manual Rust Installation (Optional)
```

# If you prefer to install Rust manually:

```bash

# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add Rust to your PATH
source ~/.cargo/env

🎯 Quick Start
Basic Application
python

from haske import Haske, Request

app = Haske(__name__)

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!"}

@app.route("/users/:name")
async def greet_user(request: Request):
    name = request.get_path_param("name")
    return {"greeting": f"Hello, {name}!"}

if __name__ == "__main__":
    app.run(debug=True)
```
# Run Your Application

```bash

# Using the built-in CLI
haske dev --module your_app:app --host 0.0.0.0 --port 8000

# Or using Python directly
python your_app.py

🛠️ CLI Commands

Haske includes a powerful CLI for development and deployment:
bash

# Start development server
haske dev --module app.main:app

# Create a new project
haske new my-project

# Build for production
haske build

# Run tests
haske test

# Show routes
haske routes

# Check application health
haske check
```

# 🔧 Configuration
Environment Variables
```bash

# Debug mode
HASKE_DEBUG=True

# Database URL
DATABASE_URL=sqlite+aiosqlite:///./app.db

# Secret key for sessions
SECRET_KEY=your-secret-key-here

# Disable Rust extensions (fallback to Python)
HASKE_NO_RUST=1
```
# Project Structure
```text

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
# ⚡ Performance Features
Rust-Powered Optimizations

Haske uses Rust extensions for critical performance paths:

    JSON Parsing: 3-5x faster than pure Python

    Template Rendering: 2-4x speed improvement

    Routing: Ultra-fast request matching

    Cryptography: Secure and fast crypto operations

    Compression: Efficient gzip/brotli/zstd support

# Benchmark Comparison
Operation	Haske (Rust)	Pure Python	Improvement
JSON Parse	0.5ms	2.1ms	4.2x
Template Render	1.2ms	4.8ms	4.0x
Route Matching	0.1ms	0.8ms	8.0x
🗄️ Database Support

# Haske includes built-in ORM support with SQLAlchemy:
```bash
python

from haske.orm import Database, Model

# Initialize database
db = Database("sqlite+aiosqlite:///./app.db")

# Define models
class User(Model):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)

# Use in routes
@app.route("/users")
async def list_users(request: Request):
    users = await User.all()
    return {"users": users}

Supported databases:

    PostgreSQL (asyncpg)

    MySQL (aiomysql)

    SQLite (aiosqlite)
```
# 🔐 Authentication & Security
```bash
python

from haske.auth import AuthManager

auth = AuthManager(secret_key="your-secret-key")

@app.route("/login")
async def login(request: Request):
    # Validate credentials
    user = await validate_credentials(request)
    
    # Create session
    response = JSONResponse({"status": "success"})
    auth.create_session(response, user.id, user.data)
    return response

@app.route("/protected")
@auth.login_required
async def protected_route(request: Request):
    return {"user": request.user}
```
# 📊 Monitoring & Metrics
```bash
python

from prometheus_client import Counter

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')

@app.middleware
async def metrics_middleware(request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response
```
# 🚀 Deployment
Docker Deployment
```bash
dockerfile

FROM python:3.11-slim

# Install Rust for building extensions
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["haske", "dev", "--module", "app.main:app", "--host", "0.0.0.0"]
```
# Production Deployment

```bash

# Build optimized version
haske build

# Use production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
# 🤝 Contributing

We welcome contributions! Please see our Contributing Guide for details.
Development Setup
bash

# Clone and setup
```bash
git clone https://github.com/your-org/haske.git
cd haske

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Build Rust extensions
maturin develop
```
# 📄 License

Haske is licensed under the MIT License. See LICENSE for details.
# 🆘 Support

    📖 Documentation

    🐛 Issue Tracker

    💬 Discussions

    📧 Email Support

# 🏆 Acknowledgments

    Built on Starlette and Uvicorn

    Rust extensions powered by Pyo3

    Inspired by FastAPI and Django

# 🔧 Advanced Usage
Custom Middleware
```bash
python

from haske.middleware import Middleware, RateLimitMiddlewareFactory

# Add rate limiting middleware
app.middleware(RateLimitMiddlewareFactory(max_requests=100, time_window=60))

# Add CORS middleware
app.middleware(CORSMiddlewareFactory(allow_origins=["*"]))

Template Rendering
python

from haske.templates import render_template, TemplateEngine

@app.route("/dashboard")
async def dashboard(request: Request):
    user_data = await get_user_data(request)
    return render_template("dashboard.html", user=user_data)

# Or use async rendering
@app.route("/profile")
async def profile(request: Request):
    user_data = await get_user_data(request)
    content = await render_template_async("profile.html", user=user_data)
    return HTMLResponse(content)
```

# Error Handling
```bash
python

from haske.exceptions import ValidationError, NotFoundError
from haske.response import error_response, not_found_response

@app.route("/api/users/:id")
async def get_user(request: Request):
    user_id = request.get_path_param("id")
    user = await User.get(user_id)
    
    if not user:
        raise NotFoundError("User not found")
    
    return {"user": user}

# Custom error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return error_response("Validation failed", 400, exc.details)

@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return not_found_response(exc.detail)
```

# WebSocket Support
```bash
python

from haske import WebSocket

@app.websocket_route("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")

Background Tasks
python

from haske import BackgroundTask

@app.route("/process")
async def process_data(request: Request):
    data = await request.json()
    
    # Run task in background
    background_task = BackgroundTask(process_data_async, data)
    
    return JSONResponse(
        {"status": "processing"}, 
        background=background_task
    )

async def process_data_async(data):
    # Long-running processing
    await asyncio.sleep(5)
    print(f"Processed: {data}")
```

# 📚 API Reference
Core Classes

    Haske: Main application class

    Request: HTTP request object with enhanced functionality

    Response: Response classes (JSONResponse, HTMLResponse, etc.)

    Database: Database connection and ORM

    AuthManager: Authentication and session management

Decorators

    @app.route(): Register HTTP routes

    @app.websocket_route(): Register WebSocket routes

    @auth.login_required: Require authentication

    @auth.roles_required: Require specific roles

Utilities

    render_template(): Template rendering

    create_session_token(): JWT token creation

    validate_json(): Request validation

    generate_csrf_token(): CSRF protection

# 🔍 Debugging

Enable debug mode for detailed error messages and automatic reloading:
```bash

export HASKE_DEBUG=True
haske dev --module app.main:app
```

# 📊 Performance Tips

    Use Rust Extensions: Ensure Rust is installed for maximum performance

    Enable Compression: Use built-in compression middleware

    Database Pooling: Configure connection pooling for database operations

    Caching: Implement caching for frequently accessed data

    Background Processing: Use background tasks for long-running operations

# 🚨 Common Issues
Rust Installation Fails

If automatic Rust installation fails:
```bash

# Install manually
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Or use Python-only mode
export HASKE_NO_RUST=1
pip install haske
```
# Dependency Conflicts

If you encounter dependency conflicts:
bash

# Create virtual environment
```bash
python -m venv venv
source venv/bin/activate

# Install with dependency resolution
pip install --upgrade pip
pip install haske
```

# Port Already in Use

If port 8000 is already in use:
```bash

haske dev --module app.main:app --port 8001
```

## Haske - Where Python simplicity meets Rust performance. 🚀

# Start building high-performance web applications today!