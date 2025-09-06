# examples/hello_world/app.py
from haske import Haske, Request

app = Haske(__name__)

data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!", "version": "0.1.0"}

@app.route("/api/users", methods=["GET"])
async def get_users(request: Request):
    return data

@app.route("/api/user/{id}", methods=["GET"])
async def get_user(request: Request):
    user_id = request.path_params.get("id")
    user = next((user for user in data if user["id"] == int(user_id)), None)
    return user

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)