import os
import json
from fastapi import APIRouter, HTTPException, Header, Depends
from openai import AsyncOpenAI
from app.db import get_db_connection
from fastapi.security import APIKeyHeader

router = APIRouter()
api_key_scheme = APIKeyHeader(name="x-internal-key", auto_error=True)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


def verify_internal_key(x_internal_key: str = Depends(api_key_scheme)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")


def _make_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


async def _generate_summary(judgment: dict) -> dict:
    content = judgment.get("content") or ""
    thesis = judgment.get("thesis") or ""

    llm = _make_llm_client()
    response = await llm.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.0,
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jestes asystentem prawnym. Na podstawie tresci orzeczenia sadowego "
                    "wygeneruj ustrukturyzowane podsumowanie w jezyku polskim. "
                    "Odpowiedz wylacznie w formacie JSON z polami: "
                    "teza, stan_faktyczny, rozstrzygniecie, podstawa_prawna. "
                    "Kazde pole to string. Nie dodawaj zadnych innych kluczy ani komentarzy."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Sygnatura: {judgment['case_number']}\n"
                    f"Sad: {judgment['court']}\n"
                    f"Data: {judgment['date']}\n"
                    f"Teza: {thesis}\n\n"
                    f"Tresc orzeczenia:\n{content[:6000]}"
                ),
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    try:
        raw_clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_clean)
    except Exception:
        return {
            "teza": raw,
            "stan_faktyczny": "",
            "rozstrzygniecie": "",
            "podstawa_prawna": "",
        }


@router.get("/{judgment_id}/summary")
async def get_judgment_summary(
    judgment_id: int,
    _: None = Depends(verify_internal_key),
):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            """SELECT id, case_number, court, date, thesis, content, summary
               FROM judgments WHERE id = $1""",
            judgment_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Judgment not found")

        judgment = dict(row)

        # zwróć z cache jeśli już jest
        if judgment.get("summary"):
            return {
                "id": judgment["id"],
                "case_number": judgment["case_number"],
                "court": judgment["court"],
                "date": str(judgment["date"]),
                "summary": judgment["summary"],
                "cached": True,
            }

        if not judgment.get("content"):
            raise HTTPException(status_code=422, detail="Judgment has no content")

    finally:
        await conn.close()

    # generuj przez LLM
    summary = await _generate_summary(judgment)

    # zapisz do bazy
    conn2 = await get_db_connection()
    try:
        await conn2.execute(
            "UPDATE judgments SET summary = $1 WHERE id = $2",
            json.dumps(summary, ensure_ascii=False),
            judgment_id,
        )
    finally:
        await conn2.close()

    return {
        "id": judgment["id"],
        "case_number": judgment["case_number"],
        "court": judgment["court"],
        "date": str(judgment["date"]),
        "summary": summary,
        "cached": False,
    }