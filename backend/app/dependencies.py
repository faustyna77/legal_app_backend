import os
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

api_key_scheme = APIKeyHeader(name="x-internal-key", auto_error=True)

async def verify_internal_key(x_internal_key: str = Depends(api_key_scheme)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")