# examples/fullstack_app.py
"""
Full-stack Haske application serving both backend API and React frontend.
"""

from haske import Haske, Request, JSONResponse
from haske.static import FrontendManager
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class User:
    id: int
    name: str
    email: str
    created_at: datetime

# Create Haske application
app = Haske(__name__)

# Setup frontend serving (React in this example)
app.setup_frontend(
    framework="react",
    mode="production",  # Use "development" for dev server proxy
    config={
        "build_dir": "./my-react-app/build",
        "dev_server": "http://localhost:3000",
        "index": "index.html",
        "static_dir": "./my-react-app/build/static"
    }
)

# API Routes
@app.route("/api/users", methods=["GET"])
async def get_users(request: Request):
    """Get all users - API endpoint that frontend can call"""
    users = [
        User(1, "John Doe", "john@example.com", datetime.now()),
        User(2, "Jane Smith", "jane@example.com", datetime.now()),
    ]
    return users

@app.route("/api/users/:id", methods=["GET"])
async def get_user(request: Request):
    """Get specific user"""
    user_id = int(request.get_path_param("id"))
    user = User(user_id, f"User {user_id}", f"user{user_id}@example.com", datetime.now())
    return user

@app.route("/api/users", methods=["POST"])
async def create_user(request: Request):
    """Create new user"""
    user_data = await request.json()
    new_user = User(
        id=3,  # In real app, this would come from database
        name=user_data.get("name"),
        email=user_data.get("email"),
        created_at=datetime.now()
    )
    return JSONResponse(new_user, status_code=201)

@app.route("/api/health", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Frontend-specific routes (optional)
@app.route("/", methods=["GET"])
async def serve_homepage(request: Request):
    """Serve homepage - this will be handled by frontend SPA"""
    # In production, FrontendServer will serve index.html
    # In development, it will proxy to the dev server
    return await app.frontend_manager.production_server.serve("")

if __name__ == "__main__":
    # Start the full-stack server
    print("Starting Haske full-stack server...")
    print("Backend API: http://localhost:8000/api/")
    print("Frontend: http://localhost:8000/")
    print("Health check: http://localhost:8000/api/health")
    
    app.run(host="0.0.0.0", port=8000, debug=True)