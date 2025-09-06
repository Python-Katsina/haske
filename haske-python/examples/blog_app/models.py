# examples/blog_app/models.py
from datetime import datetime
from typing import Optional, List

# In-memory database for demonstration
posts_db = []
users_db = []

class User:
    def __init__(self, id: int, username: str, email: str, password_hash: str):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.now()

    @classmethod
    def get(cls, user_id: int) -> Optional['User']:
        return next((user for user in users_db if user.id == user_id), None)

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        return next((user for user in users_db if user.username == username), None)

    @classmethod
    def create(cls, username: str, email: str, password_hash: str) -> 'User':
        user_id = len(users_db) + 1
        user = User(user_id, username, email, password_hash)
        users_db.append(user)
        return user

class Post:
    def __init__(self, id: int, title: str, content: str, author_id: int):
        self.id = id
        self.title = title
        self.content = content
        self.author_id = author_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @classmethod
    def all(cls) -> List['Post']:
        return posts_db

    @classmethod
    def get(cls, post_id: int) -> Optional['Post']:
        return next((post for post in posts_db if post.id == post_id), None)

    @classmethod
    def create(cls, title: str, content: str, author_id: int) -> 'Post':
        post_id = len(posts_db) + 1
        post = Post(post_id, title, content, author_id)
        posts_db.append(post)
        return post

    @classmethod
    def update(cls, post_id: int, title: str, content: str) -> Optional['Post']:
        post = cls.get(post_id)
        if post:
            post.title = title
            post.content = content
            post.updated_at = datetime.now()
        return post

    @classmethod
    def delete(cls, post_id: int) -> bool:
        global posts_db
        post = cls.get(post_id)
        if post:
            posts_db = [p for p in posts_db if p.id != post_id]
            return True
        return False

# Create sample data synchronously
def init_sample_data():
    # Create sample user
    if not users_db:
        user = User.create("admin", "admin@example.com", "hashed_password")
        users_db.append(user)
    
    # Create sample posts
    if not posts_db:
        posts = [
            ("Welcome to Haske Blog", "This is the first post on our amazing blog platform built with Haske!"),
            ("Getting Started with Haske", "Learn how to build web applications with the Haske framework."),
            ("Building REST APIs", "A guide to creating RESTful APIs with Haske and Python.")
        ]
        
        for title, content in posts:
            post = Post.create(title, content, 1)
            posts_db.append(post)

# Initialize sample data
init_sample_data()