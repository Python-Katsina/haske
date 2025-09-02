# benchmarks/fastapi_app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import time
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Simple GET endpoint
@app.get("/")
async def homepage():
    return {"message": "Hello, FastAPI!"}

# JSON response
@app.get("/json")
async def json_response():
    return {
        "status": "success",
        "message": "JSON response",
        "timestamp": time.time(),
        "data": {"items": [1, 2, 3, 4, 5]}
    }

# Path parameters
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}

# POST request with JSON
@app.post("/users")
async def create_user(user: dict):
    if not user:
        raise HTTPException(status_code=400, detail="Empty user data")
    return {
        "status": "created",
        "user": user,
        "id": 123,
        "created_at": time.time()
    }

# POST request with form data
@app.post("/users/form")
async def create_user_form(name: str, email: str, age: int = None):
    user_data = {"name": name, "email": email}
    if age:
        user_data["age"] = age
    return {
        "status": "created",
        "user": user_data,
        "id": 124,
        "created_at": time.time()
    }

# Template rendering
@app.get("/template", response_class=HTMLResponse)
async def template_test():
    return templates.TemplateResponse(
        "test_template.html",
        {
            "request": None,
            "title": "FastAPI Benchmark",
            "items": [f"Item {i}" for i in range(10)],
            "timestamp": time.time()
        }
    )

# CPU intensive task (Fibonacci)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

@app.get("/fib/{n}")
async def fib_endpoint(n: int):
    if n < 0 or n > 35:  # Limit for safety
        raise HTTPException(status_code=400, detail="n must be between 0 and 35")
    result = fibonacci(n)
    return {"n": n, "result": result}