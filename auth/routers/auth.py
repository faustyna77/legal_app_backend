import os
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Depends
from database import get_db_connection
from schemas import UserRegister, UserLogin, UserUpdate, TokenResponse, RefreshRequest
from utils.security import hash_password, verify_password
from utils.jwt import create_access_token, create_refresh_token, verify_token

router = APIRouter()

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Nieprawidłowy nagłówek autoryzacji")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token nieprawidłowy lub wygasły")
    return payload

@router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    conn = await get_db_connection()
    try:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", data.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email już zajęty")
        
        password_hash = hash_password(data.password)
        user = await conn.fetchrow(
            """INSERT INTO users (email, password_hash, name)
               VALUES ($1, $2, $3) RETURNING id, email""",
            data.email, password_hash, data.name
        )
        
        access_token = create_access_token(user["id"], user["email"])
        refresh_token = create_refresh_token(user["id"])
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        await conn.execute(
            """INSERT INTO refresh_tokens (user_id, token, expires_at)
               VALUES ($1, $2, $3)""",
            user["id"], refresh_token, expires_at
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
    finally:
        await conn.close()

@router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash, is_active FROM users WHERE email = $1",
            data.email
        )
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Nieprawidłowy email lub hasło")
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Konto nieaktywne")
        
        access_token = create_access_token(user["id"], user["email"])
        refresh_token = create_refresh_token(user["id"])
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        await conn.execute(
            """INSERT INTO refresh_tokens (user_id, token, expires_at)
               VALUES ($1, $2, $3)""",
            user["id"], refresh_token, expires_at
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
    finally:
        await conn.close()

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    conn = await get_db_connection()
    try:
        payload = verify_token(data.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token")
        
        token_row = await conn.fetchrow(
            """SELECT id, user_id, expires_at FROM refresh_tokens
               WHERE token = $1""",
            data.refresh_token
        )
        if not token_row:
            raise HTTPException(status_code=401, detail="Token nieważny")
        if token_row["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token wygasły")
        
        await conn.execute(
            "DELETE FROM refresh_tokens WHERE id = $1", token_row["id"]
        )
        
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE id = $1", token_row["user_id"]
        )
        
        new_access_token = create_access_token(user["id"], user["email"])
        new_refresh_token = create_refresh_token(user["id"])
        new_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        await conn.execute(
            """INSERT INTO refresh_tokens (user_id, token, expires_at)
               VALUES ($1, $2, $3)""",
            user["id"], new_refresh_token, new_expires_at
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
    finally:
        await conn.close()

@router.post("/auth/logout")
async def logout(
    data: RefreshRequest,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        await conn.execute(
            "DELETE FROM refresh_tokens WHERE token = $1", data.refresh_token
        )
        return {"message": "Wylogowano pomyślnie"}
    finally:
        await conn.close()

@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            "SELECT id, email, name, is_active, created_at FROM users WHERE id = $1",
            current_user["user_id"]
        )
        if not user:
            raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
        return dict(user)
    finally:
        await conn.close()

@router.put("/auth/me")
async def update_me(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            """UPDATE users SET name = COALESCE($1, name),
               updated_at = CURRENT_TIMESTAMP
               WHERE id = $2
               RETURNING id, email, name, is_active""",
            data.name, current_user["user_id"]
        )
        return dict(user)
    finally:
        await conn.close()