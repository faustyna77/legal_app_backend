import os
import time
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from app.services.rag import RAGService

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    filters: dict = {}


def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/search")
async def search(
    body: SearchRequest,
    _: None = Depends(verify_internal_key),
):
    start = time.time()
    rag = RAGService()
    result = await rag.search(body.query, body.filters)
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result
