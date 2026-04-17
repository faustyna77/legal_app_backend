from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from app.db import get_db_connection

router = APIRouter()


@router.get("")
async def list_judgments(
    court: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    conn = await get_db_connection()
    try:
        conditions = []
        params = []

        if court:
            params.append(court)
            conditions.append(f"court = ${len(params)}")
        if date_from:
            params.append(date_from)
            conditions.append(f"date >= ${len(params)}")
        if date_to:
            params.append(date_to)
            conditions.append(f"date <= ${len(params)}")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params += [limit, offset]

        rows = await conn.fetch(
            f"""
            SELECT id, case_number, court, date, thesis, source_url, created_at
            FROM judgments
            {where}
            ORDER BY date DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@router.get("/{judgment_id}")
async def get_judgment(judgment_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM judgments WHERE id = $1", judgment_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Judgment not found")
        return dict(row)
    finally:
        await conn.close()


@router.get("/{judgment_id}/similar")
async def similar_judgments(judgment_id: int, limit: int = Query(5, le=20)):
    conn = await get_db_connection()
    try:
        source = await conn.fetchrow(
            "SELECT embedding FROM judgments WHERE id = $1", judgment_id
        )
        if not source or source["embedding"] is None:
            raise HTTPException(status_code=404, detail="Judgment or embedding not found")

        rows = await conn.fetch(
            """
            SELECT id, case_number, court, date, thesis, source_url,
                   1 - (embedding <=> $1) AS similarity
            FROM judgments
            WHERE id != $2
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            source["embedding"],
            judgment_id,
            limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@router.get("/{judgment_id}/regulations")
async def get_judgment_regulations(judgment_id: int):
    conn = await get_db_connection()
    try:
        exists = await conn.fetchrow("SELECT 1 FROM judgments WHERE id = $1", judgment_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Judgment not found")

        rows = await conn.fetch(
            """
            SELECT act_title, act_year, articles
            FROM judgment_regulations
            WHERE judgment_id = $1
            ORDER BY id
            """,
            judgment_id,
        )

        grouped: dict[tuple[str, int | None], dict] = {}
        for row in rows:
            act_title = row["act_title"]
            act_year = row["act_year"]
            key = (act_title, act_year)
            if key not in grouped:
                grouped[key] = {
                    "act_title": act_title,
                    "act_year": act_year,
                    "articles": [],
                }
            articles = row["articles"] or []
            for article in articles:
                if article and article not in grouped[key]["articles"]:
                    grouped[key]["articles"].append(article)

        return {
            "judgment_id": judgment_id,
            "regulations": list(grouped.values()),
        }
    finally:
        await conn.close()


@router.get("/{judgment_id}/references")
async def get_judgment_references(judgment_id: int):
    conn = await get_db_connection()
    try:
        exists = await conn.fetchrow("SELECT 1 FROM judgments WHERE id = $1", judgment_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Judgment not found")

        rows_out = await conn.fetch(
            """
            SELECT jr.referenced_case_number,
                   jr.referenced_judgment_id,
                   j.court,
                   j.date,
                   j.source_url
            FROM judgment_references jr
            LEFT JOIN judgments j ON j.id = jr.referenced_judgment_id
            WHERE jr.judgment_id = $1
            ORDER BY jr.id
            """,
            judgment_id,
        )

        rows_in = await conn.fetch(
            """
            SELECT s.id AS judgment_id,
                   s.case_number,
                   s.court,
                   s.date,
                   s.source_url
            FROM judgment_references jr
            JOIN judgments s ON s.id = jr.judgment_id
            WHERE jr.referenced_judgment_id = $1
            ORDER BY jr.id
            """,
            judgment_id,
        )

        return {
            "judgment_id": judgment_id,
            "references_out": [
                {
                    "case_number": r["referenced_case_number"],
                    "court": r["court"],
                    "date": r["date"],
                    "source_url": r["source_url"],
                    "in_database": r["referenced_judgment_id"] is not None,
                }
                for r in rows_out
            ],
            "references_in": [
                {
                    "judgment_id": r["judgment_id"],
                    "case_number": r["case_number"],
                    "court": r["court"],
                    "date": r["date"],
                    "source_url": r["source_url"],
                }
                for r in rows_in
            ],
        }
    finally:
        await conn.close()
