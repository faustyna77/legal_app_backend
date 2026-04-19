import os
from fastapi import APIRouter, HTTPException, Depends, Header
from database import get_db_connection
from schemas import SearchHistorySave, ChatHistorySave
from utils.jwt import verify_token

router = APIRouter()
INTERNAL_KEY = os.getenv("INTERNAL_KEY")

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Nieprawidłowy nagłówek")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token nieprawidłowy")
    return payload

async def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != INTERNAL_KEY:
        raise HTTPException(status_code=403, detail="Brak dostępu")

@router.get("/history/search")
async def get_search_history(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        offset = (page - 1) * limit
        rows = await conn.fetch(
            """SELECT id, query, filters, answer, case_numbers, created_at
               FROM user_search_history
               WHERE user_id = $1
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            current_user["user_id"], limit, offset
        )
        return {"history": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.delete("/history/search/{history_id}")
async def delete_search_history(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        result = await conn.execute(
            "DELETE FROM user_search_history WHERE id = $1 AND user_id = $2",
            history_id, current_user["user_id"]
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Wpis nie znaleziony")
        return {"message": "Wpis usunięty"}
    finally:
        await conn.close()

@router.get("/history/chat")
async def get_chat_history(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        offset = (page - 1) * limit
        rows = await conn.fetch(
            """SELECT id, judgment_id, case_number, court, question, answer, created_at
               FROM user_chat_history
               WHERE user_id = $1
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            current_user["user_id"], limit, offset
        )
        return {"history": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.get("/history/chat/{judgment_id}")
async def get_chat_history_for_judgment(
    judgment_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        rows = await conn.fetch(
            """SELECT id, question, answer, created_at
               FROM user_chat_history
               WHERE user_id = $1 AND judgment_id = $2
               ORDER BY created_at ASC""",
            current_user["user_id"], judgment_id
        )
        return {"history": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.delete("/history/chat/{history_id}")
async def delete_chat_history(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        result = await conn.execute(
            "DELETE FROM user_chat_history WHERE id = $1 AND user_id = $2",
            history_id, current_user["user_id"]
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Wpis nie znaleziony")
        return {"message": "Wpis usunięty"}
    finally:
        await conn.close()

@router.post("/internal/search-history")
async def save_search_history(
    data: SearchHistorySave,
    _: None = Depends(verify_internal_key)
):
    conn = await get_db_connection()
    try:
        import json
        await conn.execute(
            """INSERT INTO user_search_history
               (user_id, query, filters, answer, case_numbers)
               VALUES ($1, $2, $3, $4, $5)""",
            data.user_id,
            data.query,
            json.dumps(data.filters) if data.filters else None,
            data.answer,
            data.case_numbers or []
        )
        return {"message": "Zapisano"}
    finally:
        await conn.close()

@router.post("/internal/chat-history")
async def save_chat_history(
    data: ChatHistorySave,
    _: None = Depends(verify_internal_key)
):
    conn = await get_db_connection()
    try:
        await conn.execute(
            """INSERT INTO user_chat_history
               (user_id, judgment_id, case_number, court, question, answer)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            data.user_id, data.judgment_id, data.case_number,
            data.court, data.question, data.answer
        )
        return {"message": "Zapisano"}
    finally:
        await conn.close()