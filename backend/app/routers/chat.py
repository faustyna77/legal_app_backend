import os
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.db import get_db_connection

router = APIRouter()

LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jina-embeddings-v3")


def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


def _make_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("JINA_API_KEY"),
        base_url="https://api.jina.ai/v1",
    )


def _make_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


class ChatRequest(BaseModel):
    question: str


@router.post("/{judgment_id}/chat")
async def chat_with_judgment(
    judgment_id: int,
    body: ChatRequest,
    _: None = Depends(verify_internal_key),
):
    # sprawdź czy orzeczenie istnieje
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT id, case_number, court, date, thesis FROM judgments WHERE id = $1",
            judgment_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Judgment not found")
        judgment_meta = dict(row)
    finally:
        await conn.close()

    # wygeneruj embedding pytania
    embed_client = _make_embed_client()
    response = await embed_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=body.question,
        extra_body={"task": "retrieval.query"},
    )
    embedding = response.data[0].embedding

    # szukaj chunków tylko dla tego orzeczenia
    conn2 = await get_db_connection()
    try:
        rows = await conn2.fetch(
            """
            SELECT jc.content,
                   1 - (jc.embedding <=> $1) AS similarity
            FROM judgment_chunks jc
            WHERE jc.judgment_id = $2
              AND jc.embedding IS NOT NULL
            ORDER BY jc.embedding <=> $1
            LIMIT 5
            """,
            str(embedding),
            judgment_id,
        )
        chunks = [dict(r) for r in rows]
    finally:
        await conn2.close()

    if not chunks:
        raise HTTPException(status_code=422, detail="No chunks found for this judgment")

    # zbuduj kontekst
    thesis = judgment_meta.get("thesis") or ""
    context_parts = []
    if thesis:
        context_parts.append(f"Teza: {thesis}")
    for chunk in chunks:
        context_parts.append(chunk["content"])
    context = "\n\n---\n\n".join(context_parts)

    header = (
        f"[ORZECZENIE | Sygnatura: {judgment_meta['case_number']} | "
        f"Sąd: {judgment_meta['court']} | Data: {judgment_meta['date']}]"
    )

    # generuj odpowiedź
    llm = _make_llm_client()
    response = await llm.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.0,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś asystentem prawnym. "
                    "Odpowiadaj na pytania wyłącznie na podstawie dostarczonego orzeczenia sądowego. "
                    "Fragmenty mogą zaczynać się w połowie zdania — to normalne, analizuj dostępną treść. "
                    "Jeśli fragment zawiera pole 'Teza:' — użyj go jako głównej odpowiedzi. "
                    "Odpowiedź powinna być konkretna i zwięzła. "
                    "Jeśli orzeczenie nie zawiera odpowiedzi na pytanie, napisz: "
                    "'Orzeczenie nie zawiera informacji na ten temat.'"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{header}\n\n"
                    f"Fragmenty orzeczenia:\n\n{context}\n\n"
                    f"Pytanie: {body.question}"
                ),
            },
        ],
    )

    return {
        "judgment_id": judgment_id,
        "case_number": judgment_meta["case_number"],
        "court": judgment_meta["court"],
        "question": body.question,
        "answer": response.choices[0].message.content,
        "chunks_used": len(chunks),
       
        "chunks": [
        {
            "content": chunk["content"],
            "similarity": round(chunk["similarity"], 4),
        }
        for chunk in chunks
        ],
}
    