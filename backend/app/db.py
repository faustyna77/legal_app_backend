import os
import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://") if DATABASE_URL else None


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


async def get_db_connection() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


async def get_db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
