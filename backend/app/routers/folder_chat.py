import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.db import get_db_connection
from fastapi.security import APIKeyHeader

router = APIRouter()
api_key_scheme = APIKeyHeader(name="x-internal-key", auto_error=True)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def verify_internal_key(x_internal_key: str = Depends(api_key_scheme)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


class FolderChatRequest(BaseModel):
    judgment_ids: list[int]
    question: str


@router.post("/folder-chat")
async def chat_with_folder(
    body: FolderChatRequest,
    _: None = Depends(verify_internal_key),
):
    if not body.judgment_ids:
        raise HTTPException(status_code=400, detail="judgment_ids is empty")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    embed_response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=body.question,
        dimensions=1024,
    )
    embedding = embed_response.data[0].embedding

    conn = await get_db_connection()
    try:
        meta_rows = await conn.fetch(
            "SELECT id, case_number, court, date, thesis FROM judgments WHERE id = ANY($1::int[])",
            body.judgment_ids,
        )
        if not meta_rows:
            raise HTTPException(status_code=404, detail="No judgments found")
        meta_map = {r["id"]: dict(r) for r in meta_rows}

        top_rows = await conn.fetch(
            """
            SELECT jc.judgment_id, jc.chunk_index, jc.content,
                   1 - (jc.embedding <=> $1) AS similarity
            FROM judgment_chunks jc
            WHERE jc.judgment_id = ANY($2::int[])
              AND jc.embedding IS NOT NULL
            ORDER BY jc.embedding <=> $1
            LIMIT 12
            """,
            str(embedding),
            body.judgment_ids,
        )
        top_chunks = [dict(r) for r in top_rows]

        if not top_chunks:
            raise HTTPException(status_code=422, detail="No chunks found for these judgments")

        chunks_with_context = []
        for chunk in top_chunks:
            jid = chunk["judgment_id"]
            idx = chunk["chunk_index"]
            expanded = await conn.fetch(
                """SELECT chunk_index, content FROM judgment_chunks
                   WHERE judgment_id = $1 AND chunk_index = ANY($2::int[])
                   ORDER BY chunk_index""",
                jid, [idx - 1, idx, idx + 1],
            )
            expanded_map = {r["chunk_index"]: r["content"] for r in expanded}
            merged = [expanded_map.get(i) for i in [idx - 1, idx, idx + 1] if expanded_map.get(i)]
            meta = meta_map.get(jid, {})
            chunks_with_context.append({
                "judgment_id": jid,
                "case_number": meta.get("case_number", ""),
                "court": meta.get("court", ""),
                "content": "\n\n".join(merged) if merged else chunk["content"],
                "similarity": chunk["similarity"],
            })
    finally:
        await conn.close()

    context_parts = []
    for chunk in chunks_with_context:
        header = f"[{chunk['case_number']} | {chunk['court']}]"
        context_parts.append(f"{header}\n{chunk['content']}")
    context = "\n\n---\n\n".join(context_parts)

    llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    llm_response = await llm.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.0,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś asystentem prawnym. "
                    "Odpowiadaj na pytania na podstawie fragmentów orzeczeń sądowych zawartych w kontekście. "
                    "Każdy fragment jest oznaczony sygnaturą sprawy i sądem w nawiasach kwadratowych. "
                    "W odpowiedzi możesz powoływać się na konkretne orzeczenia po ich sygnaturze. "
                    "Jeśli orzeczenia nie zawierają odpowiedzi, napisz: "
                    "'Katalog orzeczeń nie zawiera informacji na ten temat.'"
                ),
            },
            {
                "role": "user",
                "content": f"Fragmenty orzeczeń z katalogu:\n\n{context}\n\nPytanie: {body.question}",
            },
        ],
    )

    return {
        "answer": llm_response.choices[0].message.content,
        "question": body.question,
        "chunks_used": len(chunks_with_context),
        "judgment_ids": body.judgment_ids,
    }
