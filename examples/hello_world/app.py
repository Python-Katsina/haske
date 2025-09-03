# examples/hello_world/app.py
from haske import Haske, Request, Response

app = Haske(__name__)

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!", "version": "0.1.0"}

@app.route("/api/users", methods=["GET"])
async def get_users(request: Request):
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

@app.route("/api/users/:id", methods=["GET"])
async def get_user(request: Request):
    user_id = request.get_path_param("id")
    return {"id": user_id, "name": f"User {user_id}"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)