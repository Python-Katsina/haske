from haske.orm import AsyncORM, Column, String, Integer
from haske.app import Haske   # Haske is inside haske.app
from starlette.responses import JSONResponse  # JSONResponse is from Starlette

# Initialize ORM
db = AsyncORM()

# Define model
class User(db.Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Create Haske app
app = Haske(__name__)

# Startup event to init DB



@app.on_startup
async def init_db():
    # Create tables
    await db.init_engine("sqlite+aiosqlite:///test.db")
    await db.create_all()

    # Check if user with id=1 exists
    user = await db.get(User, id=1)
    if not user:
        await db.add(User(id=1, name="Test User"))

# Route to get a user
@app.route("/users/{user_id}", methods=["GET", "POST"])
async def get_user(request):
    user_id = int(request.path_params["user_id"])  # Extract param from request
    user = await db.get(User, id=user_id)
    if user:
        return {"id": user.id, "name": user.name}
    return JSONResponse({"error": "User not found"}, status_code=404)


if __name__=="__main__":
    app.run(choosen_port=8000)