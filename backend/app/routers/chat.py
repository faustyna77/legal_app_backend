import os
import re
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.db import get_db_connection
from fastapi.security import APIKeyHeader

router = APIRouter()
api_key_scheme = APIKeyHeader(name="x-internal-key", auto_error=True)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EVIDENCE_QUESTION_PATTERN = re.compile(r"(roszcz|żąd|kwot|ile|odsetk|zapłat|nieważn)", re.IGNORECASE)
EVIDENCE_SENTENCE_PATTERN = re.compile(r"[^.!?\n]*[^.!?\n]*[^.!?\n]*[.!?]")


def verify_internal_key(x_internal_key: str = Depends(api_key_scheme)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


def _make_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _make_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _build_evidence_quotes(question: str, chunks: list[dict], max_quotes: int = 3) -> list[str]:
    if not EVIDENCE_QUESTION_PATTERN.search(question or ""):
        return []
    quotes: list[str] = []
    seen = set()
    for chunk in chunks:
        for sentence in EVIDENCE_SENTENCE_PATTERN.findall(chunk.get("content") or ""):
            s = " ".join(sentence.split())
            sl = s.lower()
            if not s:
                continue
            if not any(k in sl for k in ["powod", "żąda", "żąd", "kwot", "odset", "nieważ", "zapłat"]):
                continue
            if s in seen:
                continue
            seen.add(s)
            quotes.append(s)
            if len(quotes) >= max_quotes:
                return quotes
    return quotes


def _to_display_chunk(text: str, max_sentences: int = 3, max_chars: int = 900) -> str:
    normalized = " ".join((text or "").split())
    if not normalized:
        return ""
    if normalized and normalized[0].islower():
        m = re.search(r"[.!?]\s+", normalized)
        if m and len(normalized[m.end():]) > 80:
            normalized = normalized[m.end():]
    sentences = [" ".join(s.split()) for s in EVIDENCE_SENTENCE_PATTERN.findall(normalized)]
    if sentences:
        selected = []
        size = 0
        for sentence in sentences[:max_sentences + 2]:
            if size + len(sentence) > max_chars and selected:
                break
            selected.append(sentence)
            size += len(sentence)
            if len(selected) >= max_sentences:
                break
        if selected:
            return " ".join(selected)
    if len(normalized) <= max_chars:
        return normalized
    trimmed = normalized[:max_chars]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return trimmed


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
        dimensions=1024,
    )
    embedding = response.data[0].embedding

    # szukaj chunków tylko dla tego orzeczenia
    conn2 = await get_db_connection()
    try:
        rows = await conn2.fetch(
            """
            SELECT jc.chunk_index, jc.content,
                   1 - (jc.embedding <=> $1) AS similarity
            FROM judgment_chunks jc
            WHERE jc.judgment_id = $2
              AND jc.embedding IS NOT NULL
            ORDER BY jc.embedding <=> $1
            LIMIT 8
            """,
            str(embedding),
            judgment_id,
        )
        top_chunks = [dict(r) for r in rows]

        neighbor_indexes = set()
        for chunk in top_chunks:
            idx = chunk["chunk_index"]
            neighbor_indexes.update([idx - 1, idx, idx + 1])
        neighbor_indexes = sorted(i for i in neighbor_indexes if i >= 0)

        expanded_rows = await conn2.fetch(
            """
            SELECT jc.chunk_index, jc.content
            FROM judgment_chunks jc
            WHERE jc.judgment_id = $1
              AND jc.chunk_index = ANY($2::int[])
            ORDER BY jc.chunk_index
            """,
            judgment_id,
            neighbor_indexes,
        )
        expanded_map = {r["chunk_index"]: r["content"] for r in expanded_rows}

        chunks = []
        for chunk in top_chunks:
            idx = chunk["chunk_index"]
            merged = [expanded_map.get(i) for i in [idx - 1, idx, idx + 1] if expanded_map.get(i)]
            chunks.append(
                {
                    "content": "\n\n".join(merged) if merged else chunk["content"],
                    "similarity": chunk["similarity"],
                }
            )
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
                    "Jeśli pytanie dotyczy roszczenia, wskaż wyłącznie roszczenie strony powodowej. "
                    "Nie mieszaj roszczeń powodów z kwotami podawanymi przez pozwanego ani z zarzutem zatrzymania. "
                    "Jeżeli podajesz kwotę, podaj też krótkie dosłowne uzasadnienie z fragmentu w cudzysłowie. "
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

    evidence_quotes = _build_evidence_quotes(body.question, chunks)

    return {
        "judgment_id": judgment_id,
        "case_number": judgment_meta["case_number"],
        "court": judgment_meta["court"],
        "question": body.question,
        "answer": response.choices[0].message.content,
        "chunks_used": len(chunks),
        "evidence_quotes": evidence_quotes,
       
        "chunks": [
        {
            "content": _to_display_chunk(chunk["content"]),
            "similarity": round(chunk["similarity"], 4),
        }
        for chunk in chunks
        ],
}
    