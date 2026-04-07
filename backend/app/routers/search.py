import os
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.rag import RAGService
from app.dependencies import verify_internal_key

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    filters: dict = {}


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