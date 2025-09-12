from haske.orm import AsyncORM, Base, Column, Integer, String, ForeignKey, OneToMany

db = AsyncORM()                    # not yet initialized
# init engine (sync-friendly)
db.init_engine("sqlite+aiosqlite:///./test.db")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    posts = OneToMany("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

# create tables (sync-friendly)
db.create_all()

# add and query (sync-friendly)
u = User(username="alice")
db.add(u)
# get one user
user = db.get(User, id=1)

# get all users
users = db.all(User)

# paginate
page = db.paginate(User, page=2, per_page=10)
print(page.items, page.total, page.next_page)
