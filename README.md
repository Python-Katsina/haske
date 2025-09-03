# 🌟 Haske Web Framework

Haske is a **modern Python web framework** that combines the simplicity of Flask, the power of FastAPI, and the performance of Rust extensions. It is designed for developers who want to build **fast, scalable, and maintainable web applications** without unnecessary complexity.

---

## 📖 Table of Contents

1. [Introduction](#-introduction)  
2. [Installation](#-installation)  
3. [Quickstart](#-quickstart)  
4. [Routing](#-routing)  
5. [Requests & Responses](#-requests--responses)  
6. [Middleware](#-middleware)  
7. [Sessions](#-sessions)  
8. [Templates](#-templates)  
9. [ORM & Database](#-orm--database)  
10. [Authentication](#-authentication)  
11. [CLI](#-cli)  
12. [WebSockets](#-websockets)  
13. [Error Handling](#-error-handling)  
14. [Testing](#-testing)  
15. [Deployment](#-deployment)  
16. [Contributing](#-contributing)  
17. [License](#-license)  

---

## 📌 Introduction

Haske was built to solve a common problem in Python web development:

- **Flask** is simple, but too minimal for large apps.  
- **Django** is powerful, but heavy and opinionated.  
- **FastAPI** is fast, but focused mostly on APIs.  

Haske combines the best of all worlds:

- 🌀 **Simple API** — inspired by Flask.  
- ⚡ **Fast** — powered by Rust extensions.  
- 🔧 **Flexible** — lets you add only what you need.  
- 🌍 **Full-stack ready** — supports templates, ORM, sessions, and WebSockets.  

---

## ⚙️ Installation

### Requirements
- Python 3.8+
- Rust (for building extensions)
- pip / virtualenv

### Install Haske

```bash
pip install haske
```

Or, from source:

```bash
git clone https://github.com/Python-Katsina/haske.git
cd haske
pip install -e .
```

---

## 🚀 Quickstart

Create a file `app.py`:

```python
from haske import Haske, Request, Response

app = Haske(__name__)

@app.route("/")
async def home(request: Request) -> Response:
    return {"message": "Hello, Haske!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
```

Run the app:

```bash
python app.py
```

Visit: [http://localhost:8000](http://localhost:8000) 🎉

---

## 🔀 Routing

Routing is how Haske connects **URLs** to **functions**.

### Basic Route
```python
@app.route("/hello")
async def say_hello(request: Request):
    return {"message": "Hello World"}
```

### Path Parameters
```python
@app.route("/user/{username}")
async def greet_user(request: Request, username: str):
    return {"message": f"Hello {username}"}
```

### Query Parameters
```python
@app.route("/search")
async def search(request: Request):
    query = request.query.get("q", "none")
    return {"search_for": query}
```

### HTTP Methods
```python
@app.route("/submit", methods=["POST"])
async def submit(request: Request):
    data = await request.json()
    return {"received": data}
```

---

## 📥 Requests & Responses

Haske provides easy access to HTTP requests and responses.

### Request Object
```python
@app.route("/headers")
async def headers(request: Request):
    return {"user_agent": request.headers.get("User-Agent")}
```

### JSON Response
```python
@app.route("/json")
async def json_response(request: Request):
    return {"framework": "Haske", "type": "JSON"}
```

### Redirect
```python
from haske.responses import RedirectResponse

@app.route("/go")
async def go(request: Request):
    return RedirectResponse(url="/hello")
```

---

## 🧩 Middleware

### What is Middleware?
Middleware is code that runs **before or after each request**.  
Uses include: logging, authentication, CORS, compression, etc.

### Example: Logging Middleware
```python
from haske.middleware import Middleware

class LoggingMiddleware(Middleware):
    async def before_request(self, request):
        print(f"➡️ Incoming request: {request.url}")

    async def after_response(self, request, response):
        print(f"⬅️ Response status: {response.status_code}")

app.add_middleware(LoggingMiddleware)
```

---

## 🔑 Sessions

### What are Sessions?
HTTP is **stateless** — it doesn’t remember users between requests.  
Sessions allow you to **store user data** (like logins or cart items) across multiple requests.

### Why Sessions Matter
- 🔐 Authentication (keep users logged in)  
- 🛒 Shopping carts  
- 🎛 Preferences & personalization  

### Example: Using Sessions
```python
@app.route("/login", methods=["POST"])
async def login(request: Request):
    data = await request.json()
    username = data.get("username")

    # Save to session
    request.session["user"] = username
    return {"message": f"Welcome {username}"}

@app.route("/profile")
async def profile(request: Request):
    user = request.session.get("user")
    if not user:
        return {"error": "Not logged in"}
    return {"profile": f"User profile for {user}"}
```

---

## 🎨 Templates

Haske supports rendering HTML templates (Jinja2 or similar).

### Example
```python
@app.route("/welcome")
async def welcome(request: Request):
    return app.template("welcome.html", {"name": "Haske User"})
```

**`templates/welcome.html`:**
```html
<html>
  <body>
    <h1>Welcome {{ name }}!</h1>
  </body>
</html>
```

---

## 🗄️ ORM & Database

Haske can integrate with SQLAlchemy or other ORMs.

### Example: SQLAlchemy
```python
from haske.orm import Model, Column, Integer, String

class User(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Create
new_user = User(name="Alice")
db.session.add(new_user)
db.session.commit()

# Query
user = User.query.filter_by(name="Alice").first()
```

---

## 🔐 Authentication

Authentication is usually built on top of **sessions**.

### Example
```python
@app.route("/auth/login", methods=["POST"])
async def auth_login(request: Request):
    data = await request.json()
    if data["username"] == "admin" and data["password"] == "123":
        request.session["user"] = "admin"
        return {"status": "logged_in"}
    return {"error": "Invalid credentials"}

@app.route("/auth/protected")
async def protected(request: Request):
    if request.session.get("user") != "admin":
        return {"error": "Unauthorized"}
    return {"message": "Welcome, admin!"}
```

---

## 🖥️ CLI

Haske comes with a command-line interface.

### Create New Project
```bash
haske new myproject
```

### Run Server
```bash
haske run
```

---

## 📡 WebSockets

Haske supports **real-time apps** with WebSockets.

### Example: Chat
```python
@app.websocket("/ws")
async def websocket_endpoint(socket):
    await socket.send("Welcome to Haske Chat!")
    async for message in socket:
        await socket.send(f"You said: {message}")
```

---

## ⚠️ Error Handling

### Custom Error Handler
```python
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return {"error": "Page not found"}
```

---

## 🧪 Testing

Haske makes testing simple.

### Example: Using pytest
```python
from haske.testing import TestClient

def test_homepage():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello, Haske!"
```

---

## 🚀 Deployment

### Run with Uvicorn
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Run with Gunicorn
```bash
gunicorn -k uvicorn.workers.UvicornWorker app:app
```

---

## 🤝 Contributing

1. Fork the repo.  
2. Create a feature branch.  
3. Submit a pull request.  

We welcome contributions in:
- Bug fixes
- New features
- Docs improvements

---

## 📜 License

MIT License © 2025 Python Katsina Community
