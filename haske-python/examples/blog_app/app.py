# examples/blog_app/app.py
from haske import Haske, Request, Response, RedirectResponse
from haske.auth import AuthManager
from haske.templates import render_template_async
from models import Post, User

app = Haske(__name__)
auth = AuthManager("your-secret-key-here", session_expiry=3600)

# Create a sample user for demonstration
def create_sample_user():
    if not User.get_by_username("admin"):
        User.create("admin", "admin@example.com", "hashed_password")

# Helper function to check authentication
def check_auth(request: Request):
    session = auth.get_session(request)
    if not session:
        return False, RedirectResponse('/login')
    return True, session

# Routes
@app.route("/")
async def homepage(request: Request):
    posts = Post.all()
    return await render_template_async("index.html", posts=posts)

@app.route("/login", methods=["GET", "POST"])
async def login(request: Request):
    if request.method == "GET":
        return await render_template_async("login.html")
    
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    # Simple authentication for demo
    if username == "admin" and password == "password":
        user = User.get_by_username(username)
        if user:
            response = RedirectResponse("/")
            auth.create_session(response, user.id, {"username": user.username})
            return response
    
    return await render_template_async("login.html", error="Invalid credentials")

@app.route("/logout")
async def logout(request: Request):
    response = RedirectResponse("/")
    auth.clear_session(response)
    return response

# MOVE SPECIFIC ROUTES BEFORE PARAMETERIZED ROUTES
@app.route("/posts/create", methods=["GET","POST"])
async def create_post_form(request: Request):
    # Check authentication
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return response_or_session
    return await render_template_async("create.html")

@app.route("/posts", methods=["POST"])
async def create_post(request: Request):
    # Check authentication
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return response_or_session
    
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")
    
    if not title or not content:
        return await render_template_async("create.html", error="Title and content are required")
    
    # For demo, use author_id=1 (admin)
    post = Post.create(title, content, 1)
    
    # Use status code 303 (See Other) for POST redirects
    return RedirectResponse(f"/posts/{post.id}", status_code=303)

# Parameterized routes should come after specific routes
@app.route("/posts/{post_id}", methods=["GET"])
async def get_post(request: Request):
    post_id = int(request.path_params.get("post_id"))
    post = Post.get(post_id)
    if not post:
        return Response("Post not found", status_code=404)
    return await render_template_async("post.html", post=post)

@app.route("/posts/{post_id}/edit", methods=["GET"])
async def edit_post_form(request: Request):
    # Check authentication
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return response_or_session
    
    post_id = int(request.path_params.get("post_id"))
    post = Post.get(post_id)
    if not post:
        return Response("Post not found", status_code=404)
    return await render_template_async("edit.html", post=post)

@app.route("/posts/{post_id}/update", methods=["POST"])
async def update_post(request: Request):
    # Check authentication
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return response_or_session
    
    post_id = int(request.path_params.get("post_id"))
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")
    
    post = Post.update(post_id, title, content)
    if not post:
        return Response("Post not found", status_code=404)
    return RedirectResponse(f"/posts/{post.id}")

@app.route("/posts/{post_id}/delete", methods=["POST"])
async def delete_post(request: Request):
    # Check authentication
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return response_or_session
    
    post_id = int(request.path_params.get("post_id"))
    success = Post.delete(post_id)
    if not success:
        return Response("Post not found", status_code=404)
    return RedirectResponse("/")

# API endpoints
@app.route("/api/posts", methods=["GET"])
async def api_get_posts(request: Request):
    posts = Post.all()
    return Response.json([{
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat()
    } for post in posts])

@app.route("/api/posts/{post_id}", methods=["GET"])
async def api_get_post(request: Request):
    post_id = int(request.path_params.get("post_id"))
    post = Post.get(post_id)
    if not post:
        return Response.json({"error": "Post not found"}, status_code=404)
    return Response.json({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat()
    })

@app.route("/api/posts", methods=["POST"])
async def api_create_post(request: Request):
    # Check authentication for API
    is_authenticated, response_or_session = check_auth(request)
    if not is_authenticated:
        return Response.json({"error": "Authentication required"}, status_code=401)
    
    data = await request.json()
    post = Post.create(data["title"], data["content"], 1)  # author_id=1 for demo
    return Response.json({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id
    }, status_code=201)

if __name__ == "__main__":
    # Create sample user
    create_sample_user()
    
    app.run(
        host="0.0.0.0", 
        port=8000, 
        debug=True
    )