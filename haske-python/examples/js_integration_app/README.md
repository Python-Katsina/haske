# Haske Full-Stack Framework Documentation

## Complete Guide to Building Full-Stack Applications with Haske

**Version 1.0**  
*Serving React, Vue, Next.js, and more on a single server*

---

## Table of Contents

1. [Introduction](#introduction)
2. [Why Full-Stack Haske?](#why-full-stack-haske)
3. [Architecture Overview](#architecture-overview)
4. [Quick Start Guide](#quick-start-guide)
5. [Frontend Framework Integration](#frontend-framework-integration)
6. [Production Deployment](#production-deployment)
7. [Development Workflow](#development-workflow)
8. [API Design Best Practices](#api-design-best-practices)
9. [Advanced Configuration](#advanced-configuration)
10. [Troubleshooting](#troubleshooting)
11. [Examples](#examples)
12. [API Reference](#api-reference)

---

## Introduction

Haske is now a complete full-stack web framework that allows you to serve both your backend API and frontend application from a single server. This eliminates the need for separate servers, complex proxy configurations, and CORS issues during development and production.

### Key Benefits

- **Unified Deployment**: Single server for both frontend and backend
- **Simplified Development**: No CORS issues during development
- **Production Ready**: Optimized static file serving with caching
- **Framework Agnostic**: Supports React, Vue, Next.js, Angular, Svelte
- **Type Safety**: Automatic TypeScript interface generation
- **Developer Experience**: Hot reloading in development mode

---

## Why Full-Stack Haske?

### The Problem with Traditional Setup

Traditional web development often requires:

1. **Separate Servers**: Backend API server and frontend development server
2. **CORS Configuration**: Complex setup for cross-origin requests
3. **Deployment Complexity**: Multiple services to deploy and manage
4. **Development Overhead**: Different tools and processes for frontend/backend

### The Haske Solution

Haske solves these problems by:

1. **Single Server**: One server handles both API and frontend
2. **Built-in Proxy**: Development mode proxies to frontend dev servers
3. **Zero CORS**: Same origin eliminates CORS issues
4. **Unified Tooling**: Consistent development experience
5. **Simplified Deployment**: One service to deploy

---

---

## Quick Start Guide

### Installation

```bash
# Install Haske with frontend capabilities
pip install haske[fullstack]

# Or from source
git clone https://github.com/your-org/haske.git
cd haske
pip install -e ".[fullstack]"
```

### Create Your First Full-Stack App
```python
# app.py
from haske import Haske, Request
from datetime import datetime

app = Haske(__name__)

# Setup React frontend (production mode)
app.setup_frontend("react", "production")

# API Routes
@app.route("/api/users")
async def get_users(request: Request):
    return [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
    ]

@app.route("/api/health")
async def health_check(request: Request):
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### Create React Frontend
```bash
# Create React app
npx create-react-app my-frontend
cd my-frontend

# Build for production
npm run build
```

### Folder Structure
```text
my-app/
├── app.py                 # Haske backend
├── requirements.txt       # Python dependencies
├── my-frontend/          # React application
│   ├── src/
│   ├── public/
│   └── package.json
└── haske.config.json     # Configuration (optional)
```

### Run the Application
```bash
# Production mode (serves built files)
python app.py

# Development mode (proxies to React dev server)
# Update app.py: app.setup_frontend("react", "development")
# Then run: python app.py
```

---

## Frontend Framework Integration

### React Setup
```python
# For Create React App
app.setup_frontend(
    framework="react",
    mode="production",
    config={
        "build_dir": "./my-react-app/build",
        "dev_server": "http://localhost:3000"
    }
)
```

### Vue Setup
```python
# For Vue.js with Vite
app.setup_frontend(
    framework="vue", 
    mode="production",
    config={
        "build_dir": "./my-vue-app/dist",
        "dev_server": "http://localhost:5173"
    }
)
```

### Next.js Setup
```python
# For Next.js
app.setup_frontend(
    framework="nextjs",
    mode="production", 
    config={
        "build_dir": "./my-next-app/.next",
        "dev_server": "http://localhost:3000"
    }
)
```

### Angular Setup
```python
# For Angular
app.setup_frontend(
    framework="angular",
    mode="production",
    config={
        "build_dir": "./my-angular-app/dist",
        "dev_server": "http://localhost:4200"
    }
)
```

### Svelte Setup
```python
# For Svelte
app.setup_frontend(
    framework="svelte",
    mode="production",
    config={
        "build_dir": "./my-svelte-app/build",
        "dev_server": "http://localhost:5173"
    }
)
```

---

## Production Deployment

### Building for Production
```bash
# Build your frontend
cd my-frontend
npm run build

# Install production dependencies
pip install gunicorn

# Run with Gunicorn (recommended for production)
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy frontend and build
COPY my-frontend/ ./my-frontend/
WORKDIR /app/my-frontend
RUN npm install && npm run build
WORKDIR /app

# Copy backend code
COPY . .

# Expose port
EXPOSE 8000

# Start application
CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### Environment Configuration
```python
# Environment-based configuration
import os

frontend_mode = os.getenv("FRONTEND_MODE", "production")
framework = os.getenv("FRONTEND_FRAMEWORK", "react")

app.setup_frontend(
    framework=framework,
    mode=frontend_mode,
    config={
        "build_dir": os.getenv("FRONTEND_BUILD_DIR", "./frontend/build"),
        "dev_server": os.getenv("FRONTEND_DEV_SERVER", "http://localhost:3000")
    }
)
```

---

## Development Workflow

### Development Mode Setup
```python
# app.py (development configuration)
app.setup_frontend("react", "development")

# API routes work as usual
@app.route("/api/data")
async def get_data(request: Request):
    return {"data": [1, 2, 3, 4, 5]}
```

### Running in Development
```bash
# Terminal 1: Start frontend dev server
cd my-frontend
npm start

# Terminal 2: Start Haske backend (will proxy to frontend)
python app.py
```

### Development Benefits

- Hot Reloading: Frontend changes reflect immediately
- No CORS: API calls work without CORS configuration
- Debugging: Full access to both frontend and backend logs
- Consistent URLs: Same origin for all requests

### Development Console Output
```text
Haske server running on http://0.0.0.0:8000
✓ Backend API: http://localhost:8000/api/
✓ Frontend: http://localhost:8000/
✓ Development mode: Proxying to http://localhost:3000
```

---

## API Design Best Practices

### RESTful API Structure
```python
# users.py - Example RESTful resource
@app.route("/api/users", methods=["GET"])
async def get_users(request: Request):
    """Get all users"""
    users = await database.fetch_users()
    return users

@app.route("/api/users/:id", methods=["GET"])
async def get_user(request: Request):
    """Get specific user"""
    user_id = request.get_path_param("id")
    user = await database.fetch_user(user_id)
    return user

@app.route("/api/users", methods=["POST"])
async def create_user(request: Request):
    """Create new user"""
    user_data = await request.json()
    user = await database.create_user(user_data)
    return JSONResponse(user, status_code=201)

@app.route("/api/users/:id", methods=["PUT"])
async def update_user(request: Request):
    """Update user"""
    user_id = request.get_path_param("id")
    user_data = await request.json()
    user = await database.update_user(user_id, user_data)
    return user

@app.route("/api/users/:id", methods=["DELETE"])
async def delete_user(request: Request):
    """Delete user"""
    user_id = request.get_path_param("id")
    await database.delete_user(user_id)
    return {"message": "User deleted"}, 204
```

### Response Formatting
```python
from haske.frontend import APIResponse

@app.route("/api/data")
async def get_data(request: Request):
    try:
        data = await fetch_data()
        return APIResponse.success(data=data, message="Data fetched successfully")
    except Exception as e:
        return APIResponse.error(message="Failed to fetch data", error=str(e))
```

### Error Handling
```python
from haske.exceptions import NotFoundError, ValidationError

@app.route("/api/users/:id")
async def get_user(request: Request):
    user_id = request.get_path_param("id")
    user = await database.fetch_user(user_id)
    
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    
    return user

@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return APIResponse.error(
        message=exc.detail,
        error="NOT_FOUND",
        status_code=404
    )
```

---

## Advanced Configuration

### Custom Frontend Configuration
```python
# Custom configuration for unusual setups
app.setup_frontend(
    framework="react",
    mode="production",
    config={
        "build_dir": "./custom-build/output",
        "dev_server": "http://localhost:8080",
        "index": "main.html",
        "static_dir": "./custom-build/assets",
        "spa_mode": False  # Disable SPA routing
    }
)
```

### Multiple Frontend Applications
```python
# Serve multiple frontend apps from different paths
react_server = FrontendServer(directory="./react-app/build")
vue_server = FrontendServer(directory="./vue-app/dist")

@app.route("/react/{path:path}")
async def serve_react(request: Request):
    path = request.get_path_param("path", "")
    return await react_server.serve(path)

@app.route("/vue/{path:path}")  
async def serve_vue(request: Request):
    path = request.get_path_param("path", "")
    return await vue_server.serve(path)
```

### Custom Middleware
```python
# Add custom middleware for frontend routes
@app.middleware
async def frontend_middleware(request, call_next):
    # Add security headers for frontend routes
    if not request.url.path.startswith("/api/"):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    
    return await call_next(request)
```

### Static File Optimization
```python
# Custom static file serving with caching
app.static(
    "/static",
    "./frontend/build/static",
    cache_control="public, max-age=31536000",  # 1 year cache
    gzip=True,
    brotli=True
)
```

---

## Troubleshooting

### Common Issues and Solutions

- **Issue: Frontend not loading in production**  
  **Solution:** Check build directory path and ensure build was successful

- **Issue: API routes returning 404 in development**  
  **Solution:** Ensure API routes are defined before the catch-all route

- **Issue: Static files not serving**  
  **Solution:** Check file permissions and directory structure

- **Issue: Dev server proxy not working**  
  **Solution:** Verify frontend dev server is running on correct port

### Debug Mode
```python
# Enable detailed logging
app.setup_frontend(
    framework="react",
    mode="development",
    config={
        "build_dir": "./frontend/build",
        "dev_server": "http://localhost:3000",
        "debug": True  # Enable verbose logging
    }
)
```

### Health Check Endpoints
```python
@app.route("/api/debug/frontend")
async def debug_frontend(request: Request):
    """Debug endpoint for frontend configuration"""
    return {
        "mode": app.frontend_manager.mode,
        "config": app.frontend_manager.config,
        "build_dir_exists": Path(app.frontend_manager.config["build_dir"]).exists()
    }
```

---

## Examples

### Complete React + Haske Example
```python
# Complete full-stack example
from haske import Haske, Request, JSONResponse
from haske.frontend import APIResponse
from haske.orm import Database, Model
from datetime import datetime
from typing import List, Optional
import json

app = Haske(__name__)

# Setup React frontend
app.setup_frontend("react", "production")

# Database model
class User(Model):
    id: int
    name: str
    email: str
    created_at: datetime

# API Routes
@app.route("/api/users", methods=["GET"])
async def get_users(request: Request):
    users = await User.all()
    return APIResponse.success(data=users)

@app.route("/api/users/:id", methods=["GET"])
async def get_user(request: Request):
    user_id = request.get_path_param("id")
    user = await User.get(user_id)
    if not user:
        return APIResponse.error("User not found", status_code=404)
    return APIResponse.success(data=user)

@app.route("/api/users", methods=["POST"])
async def create_user(request: Request):
    try:
        user_data = await request.json()
        user = User(
            name=user_data["name"],
            email=user_data["email"],
            created_at=datetime.now()
        )
        await user.save()
        return APIResponse.success(data=user, status_code=201)
    except Exception as e:
        return APIResponse.error(str(e), status_code=400)

# Health check
@app.route("/api/health")
async def health_check(request: Request):
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### React Frontend Example
```javascript
// React component using Haske API
import React, { useState, useEffect } from 'react';

function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users');
      const result = await response.json();
      
      if (result.success) {
        setUsers(result.data);
      } else {
        console.error('Error:', result.error);
      }
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Users</h1>
      {users.map(user => (
        <div key={user.id}>
          <h3>{user.name}</h3>
          <p>{user.email}</p>
        </div>
      ))}
    </div>
  );
}

export default UserList;
```

---

## API Reference

### FrontendManager Class
```python
class FrontendManager:
    def __init__(self, app, config: Optional[Dict] = None):
        """Initialize frontend manager"""
    
    def setup(self, mode: str = "production"):
        """Setup frontend serving based on mode"""
    
    def get_frontend_url(self, path: str = "") -> str:
        """Get frontend URL for redirects or links"""
```

### FrontendServer Class
```python
class FrontendServer:
    def __init__(self, directory: str, index: str = "index.html", 
                 spa_mode: bool = True, development_mode: bool = False):
        """Initialize frontend server"""
    
    async def serve(self, path: str = "") -> Response:
        """Serve frontend static files"""
    
    def detect_frontend_framework(self) -> Optional[str]:
        """Detect which frontend framework is being used"""
    
    def setup_middleware(self, app):
        """Setup frontend serving middleware for the app"""
```

### FrontendDevelopmentServer Class
```python
class FrontendDevelopmentServer:
    def __init__(self, dev_server_url: str = "http://localhost:3000", enabled: bool = True):
        """Initialize development server proxy"""
    
    async def proxy_request(self, request) -> Response:
        """Proxy request to frontend development server"""
```

### Utility Functions
```python
def create_frontend_config(framework: str = "react") -> Dict[str, Any]:
    """Create default configuration for different frontend frameworks"""

def generate_typescript_interfaces(models: List[Any], output_path: str = None) -> str:
    """Generate TypeScript interfaces from Python models"""

def to_frontend_dict(obj: Any) -> Union[Dict, List]:
    """Convert Python object to frontend-compatible dictionary"""
```

---

## Conclusion

Haske's full-stack capabilities provide a revolutionary approach to web development by combining backend API serving with frontend application hosting in a single, cohesive framework. This eliminates traditional pain points like CORS configuration, deployment complexity, and development environment setup.

### Key Takeaways

- Simplified Development: No more separate servers or complex proxy setups
- Production Ready: Optimized static file serving with proper caching
- Framework Support: Works with React, Vue, Next.js, Angular, Svelte
- Type Safety: Automatic TypeScript interface generation from Python models
- Developer Experience: Hot reloading, unified logging, and consistent URLs

### Getting Help

- Documentation: https://haske.readthedocs.io
- GitHub: https://github.com/your-org/haske
- Discord: Join our community
- Email: support@haske.org
