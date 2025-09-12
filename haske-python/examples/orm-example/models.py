from haske.orm import Column, Integer, String, ForeignKey, relationship
from haske.orm import AsyncORM

db = AsyncORM()

class User(db.Model):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)

    posts = relationship("Post", back_populates="author")

    def __repr__(self):
        return f"<User {self.username}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    author = relationship("User", back_populates="posts")

    def __repr__(self):
        return f"<Post {self.title}>"
