# benchmarks/haske_app.py
from haske import Haske, Request, Response
from haske.templates import render_template_async
import time
import json

app = Haske(__name__)

# Simple GET endpoint
@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!"}

# JSON response
@app.route("/json")
async def json_response(request: Request):
    return {
        "status": "success",
        "message": "JSON response",
        "timestamp": time.time(),
        "data": {"items": [1, 2, 3, 4, 5]}
    }

# Path parameters
@app.route("/users/{user_id}")
async def get_user(request: Request):
    user_id = request.path_params.get("user_id")
    return {"user_id": user_id, "name": f"User {user_id}"}

# POST request with JSON - with error handling
@app.route("/users", methods=["POST"])
async def create_user(request: Request):
    try:
        # Try to parse JSON, but handle empty/invalid cases
        body = await request.body()
        if not body:
            return Response.json({"error": "Empty request body"}, status_code=400)
        
        data = await request.json()
        if not data:
            return Response.json({"error": "Invalid JSON"}, status_code=400)
            
        return {
            "status": "created",
            "user": data,
            "id": 123,
            "created_at": time.time()
        }
    except json.JSONDecodeError:
        return Response.json({"error": "Invalid JSON format"}, status_code=400)
    except Exception as e:
        return Response.json({"error": str(e)}, status_code=500)

# POST request with form data
@app.route("/users/form", methods=["POST"])
async def create_user_form(request: Request):
    try:
        form_data = await request.form()
        return {
            "status": "created",
            "user": dict(form_data),
            "id": 124,
            "created_at": time.time()
        }
    except Exception as e:
        return Response.json({"error": str(e)}, status_code=500)

# Template rendering
@app.route("/template")
async def template_test(request: Request):
    return await render_template_async(
        "test_template.html",
        title="Haske Benchmark",
        items=[f"Item {i}" for i in range(10)],
        timestamp=time.time()
    )

# CPU intensive task (Fibonacci)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

@app.route("/fib/{n}")
async def fib_endpoint(request: Request):
    try:
        n = int(request.path_params.get("n"))
        result = fibonacci(n)
        return {"n": n, "result": result}
    except ValueError:
        return Response.json({"error": "Invalid number"}, status_code=400)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)