import os
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

router = APIRouter()

client = AsyncOpenAI(
    api_key=os.getenv("JINA_API_KEY"),
    base_url="https://api.jina.ai/v1",
)


class EmbedRequest(BaseModel):
    texts: list[str]
    model: str = "jina-embeddings-v3"


def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def embed(
    body: EmbedRequest,
    _: None = Depends(verify_internal_key),
):
    response = await client.embeddings.create(
        model=body.model,
        input=body.texts,
    )
    return {"embeddings": [item.embedding for item in response.data]}
