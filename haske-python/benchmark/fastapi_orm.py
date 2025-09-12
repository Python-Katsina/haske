from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from fastapi.responses import JSONResponse

DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    async with SessionLocal() as session:
        result = await session.get(User, user_id)
        if result:
            return {"id": result.id, "name": result.name}
        return JSONResponse({})
