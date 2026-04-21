import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_host = os.getenv("DB_USERS_HOST", "localhost")
    db_port = os.getenv("DB_USERS_PORT", "5433")
    db_user = os.getenv("DB_USERS_USER", "postgres")
    db_password = os.getenv("DB_USERS_PASSWORD", "postgres")
    db_name = os.getenv("DB_USERS_NAME", "users")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


async def get_db_connection():
    return await asyncpg.connect(_resolve_database_url())
