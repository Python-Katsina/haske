from haske import Haske, render_template_async, RedirectResponse, url_for, request
from haske.auth import AuthManager
from haske.orm import AsyncORM
import bcrypt

from models import User, Post, Comment

app = Haske(__name__)

orm = AsyncORM()

# ==== Auth Manager ====
auth = AuthManager(secret_key="abc")  # Manual session handling

# ====== initialize and create all database tables
@app.on_startup
async def create_db():
    await orm.init_engine("sqlite+aiosqlite:///blog.db", echo=True)
    await orm.create_all()

# ========= Index =========
@app.route("/", methods=["GET"])
async def index(request):
    posts = await orm.all(Post)
    for post in posts:
        post.user = await orm.get(User, id=post.user_id)
    posts.sort(key=lambda p: p.id, reverse=True)

    recent_posts = posts[:5]
    user = auth.get_session(request)
    return await render_template_async(
        "index.html", posts=posts, recent_posts=recent_posts, user=user
    )

# ========= Register =========
@app.route("/register", methods=["GET", "POST"])
async def register(request):
    if request.method == "POST":
        form = await request.form()
        username = form.get("username")
        password = bcrypt.hashpw(form.get("password").encode(), bcrypt.gensalt()).decode()
        user = User(username=username, password=password, role="author")
        await orm.add(user)
        await orm.commit()
        return RedirectResponse(url_for("login"), status_code=303)
    return await render_template_async("auth/register.html", user=auth.get_session(request))

# ========= Login =========
@app.route("/login", methods=["GET", "POST"])
async def login(request):
    if request.method == "POST":
        form = await request.form()
        user = await orm.get(User, username=form.get("username"))
        if user and bcrypt.checkpw(form.get("password").encode(), user.password.encode()):
            response = RedirectResponse(url_for("index"), status_code=303)
            auth.create_session(response, user.id, {"username": user.username, "roles": [user.role]})
            return response
        return await render_template_async("auth/login.html", error="Invalid credentials", user=None)
    return await render_template_async("auth/login.html", user=auth.get_session(request))

# ========= Logout =========
@app.route("/logout")
async def logout(request):
    response = RedirectResponse(url_for("index"), status_code=303)
    auth.clear_session(response)
    return response

# ========= New Post =========
@app.route("/new", methods=["GET", "POST"])
async def new_post(request):
    session = auth.get_session(request)
    if not session:
        return RedirectResponse(url_for("login"), status_code=303)

    if request.method == "POST":
        form = await request.form()
        post = Post(
            title=form.get("title"),
            content=form.get("content"),
            user_id=session["user_id"]
        )
        await orm.add(post)
        await orm.commit()
        return RedirectResponse(url_for("index"), status_code=303)

    return await render_template_async("new.html", user=session)

# ========= View Post & Comments =========
@app.route("/post/{post_id}", methods=["GET", "POST"])
async def view_post(request):
    post_id = int(request.path_params.get("post_id"))
    post = await orm.get(Post, id=post_id)
    post.user = await orm.get(User, id=post.user_id)

    comments = await orm.filter(Comment, post_id==post_id)
    for comment in comments:
        comment.user = await orm.get(User, id=comment.user_id)

    session = auth.get_session(request)
    recent_posts = (await orm.all(Post))[:5]
    for recent in recent_posts:
        recent.user = await orm.get(User, id=recent.user_id)

    if request.method == "POST" and session:
        form = await request.form()
        comment = Comment(
            content=form.get("content"),
            post_id=post.id,
            user_id=session["user_id"]
        )
        await orm.add(comment)
        await orm.commit()
        return RedirectResponse(url_for("view_post", post_id=post.id), status_code=303)

    return await render_template_async(
        "post.html", post=post, comments=comments, user=session, recent_posts=recent_posts
    )

# ========= Edit Post =========
@app.route("/edit/{post_id}", methods=["GET", "POST"])
async def edit_post(request):
    session = auth.get_session(request)
    if not session:
        return RedirectResponse(url_for("login"), status_code=303)

    post_id = int(request.path_params.get("post_id"))
    post = await orm.get(Post, id=post_id)

    if post.user_id != session["user_id"]:
        return RedirectResponse(url_for("index"), status_code=303)

    if request.method == "POST":
        form = await request.form()
        await orm.update(post, title=form.get("title"), content=form.get("content"))
        await orm.commit()
        return RedirectResponse(url_for("index"), status_code=303)

    post.user = await orm.get(User, id=post.user_id)
    return await render_template_async("edit.html", post=post, user=session)

# ========= Delete Post =========
@app.route("/delete/{post_id}")
async def delete_post(request):
    session = auth.get_session(request)
    if not session:
        return RedirectResponse(url_for("login"), status_code=303)

    post_id = int(request.path_params.get("post_id"))
    post = await orm.get(Post, id=post_id)

    if post and post.user_id == session["user_id"]:
        await orm.delete(post)
        await orm.commit()

    return RedirectResponse(url_for("index"), status_code=303)

# ========= Delete Comment =========
@app.route("/delete_comment/{comment_id}")
async def delete_comment(request):
    session = auth.get_session(request)
    if not session:
        return RedirectResponse(url_for("login"), status_code=303)

    comment_id = int(request.path_params.get("comment_id"))
    comment = await orm.get(Comment, id=comment_id)

    if comment and comment.user_id == session["user_id"]:
        await orm.delete(comment)
        await orm.commit()

    return RedirectResponse(url_for("view_post", post_id=comment.post_id), status_code=303)


if __name__ == "__main__":
    app.run(debug=True)
