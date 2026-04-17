import os
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

router = APIRouter()


def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


class EmbedRequest(BaseModel):
    texts: list[str]
    model: str = "text-embedding-3-small"


def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def embed(
    body: EmbedRequest,
    _: None = Depends(verify_internal_key),
):
    client = _make_client()
    response = await client.embeddings.create(
        model=body.model,
        input=body.texts,
        dimensions=1024,
    )
    return {"embeddings": [item.embedding for item in response.data]}
