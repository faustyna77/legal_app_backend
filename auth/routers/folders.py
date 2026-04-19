from fastapi import APIRouter, HTTPException, Depends, Header
from database import get_db_connection
from schemas import FolderCreate, FolderUpdate, FolderJudgmentAdd
from utils.jwt import verify_token

router = APIRouter()

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Nieprawidłowy nagłówek")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token nieprawidłowy")
    return payload

@router.post("/folders")
async def create_folder(
    data: FolderCreate,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        folder = await conn.fetchrow(
            """INSERT INTO user_folders (user_id, name, description)
               VALUES ($1, $2, $3)
               RETURNING id, name, description, created_at""",
            current_user["user_id"], data.name, data.description
        )
        return dict(folder)
    finally:
        await conn.close()

@router.get("/folders")
async def list_folders(current_user: dict = Depends(get_current_user)):
    conn = await get_db_connection()
    try:
        folders = await conn.fetch(
            """SELECT f.id, f.name, f.description, f.created_at,
               COUNT(fj.id) as judgment_count
               FROM user_folders f
               LEFT JOIN user_folder_judgments fj ON fj.folder_id = f.id
               WHERE f.user_id = $1
               GROUP BY f.id
               ORDER BY f.created_at DESC""",
            current_user["user_id"]
        )
        return {"folders": [dict(f) for f in folders]}
    finally:
        await conn.close()

@router.get("/folders/{folder_id}")
async def get_folder(
    folder_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        folder = await conn.fetchrow(
            "SELECT * FROM user_folders WHERE id = $1 AND user_id = $2",
            folder_id, current_user["user_id"]
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Katalog nie znaleziony")
        return dict(folder)
    finally:
        await conn.close()

@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: int,
    data: FolderUpdate,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        folder = await conn.fetchrow(
            """UPDATE user_folders
               SET name = COALESCE($1, name),
                   description = COALESCE($2, description),
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = $3 AND user_id = $4
               RETURNING id, name, description""",
            data.name, data.description, folder_id, current_user["user_id"]
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Katalog nie znaleziony")
        return dict(folder)
    finally:
        await conn.close()

@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        result = await conn.execute(
            "DELETE FROM user_folders WHERE id = $1 AND user_id = $2",
            folder_id, current_user["user_id"]
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Katalog nie znaleziony")
        return {"message": "Katalog usunięty"}
    finally:
        await conn.close()

@router.post("/folders/{folder_id}/judgments")
async def add_judgment_to_folder(
    folder_id: int,
    data: FolderJudgmentAdd,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        folder = await conn.fetchrow(
            "SELECT id FROM user_folders WHERE id = $1 AND user_id = $2",
            folder_id, current_user["user_id"]
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Katalog nie znaleziony")
        
        try:
            judgment = await conn.fetchrow(
                """INSERT INTO user_folder_judgments
                   (folder_id, user_id, judgment_id, case_number, court, date, note)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING id, judgment_id, case_number""",
                folder_id, current_user["user_id"], data.judgment_id,
                data.case_number, data.court, data.date, data.note
            )
            return dict(judgment)
        except Exception:
            raise HTTPException(status_code=400, detail="Orzeczenie już w katalogu")
    finally:
        await conn.close()

@router.delete("/folders/{folder_id}/judgments/{judgment_id}")
async def remove_judgment_from_folder(
    folder_id: int,
    judgment_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        result = await conn.execute(
            """DELETE FROM user_folder_judgments
               WHERE folder_id = $1 AND judgment_id = $2 AND user_id = $3""",
            folder_id, judgment_id, current_user["user_id"]
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Orzeczenie nie znalezione")
        return {"message": "Orzeczenie usunięte z katalogu"}
    finally:
        await conn.close()

@router.get("/folders/{folder_id}/judgments")
async def list_folder_judgments(
    folder_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = await get_db_connection()
    try:
        folder = await conn.fetchrow(
            "SELECT id FROM user_folders WHERE id = $1 AND user_id = $2",
            folder_id, current_user["user_id"]
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Katalog nie znaleziony")
        
        judgments = await conn.fetch(
            """SELECT judgment_id, case_number, court, date, note, created_at
               FROM user_folder_judgments
               WHERE folder_id = $1
               ORDER BY created_at DESC""",
            folder_id
        )
        return {"judgments": [dict(j) for j in judgments]}
    finally:
        await conn.close()