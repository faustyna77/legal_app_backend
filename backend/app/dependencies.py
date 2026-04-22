import os
from fastapi import Depends, HTTPException, Header
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

# istniejąca autoryzacja x-internal-key — bez zmian
api_key_scheme = APIKeyHeader(name="x-internal-key", auto_error=True)

async def verify_internal_key(x_internal_key: str = Depends(api_key_scheme)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")

# nowa 
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

async def get_optional_user(authorization: str = Header(None)) -> dict | None:
    if not authorization:
        return None
    try:
        if not authorization.startswith("Bearer "):
            return None
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None