from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from datetime import date as DateType
from app.db import get_db_connection


def _normalize_multi(value: Optional[list[str]]) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for item in value:
        if not item:
            continue
        parts = [p.strip() for p in item.split(",") if p.strip()]
        out.extend(parts)
    return out


router = APIRouter()

@router.get("")
async def list_judgments(
    court: Optional[list[str]] = Query(None),
    court_type: Optional[list[str]] = Query(None),
    legal_area: Optional[list[str]] = Query(None),
    source: Optional[list[str]] = Query(None),
    city: Optional[list[str]] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    article: Optional[list[str]] = Query(None),
    act_title: Optional[list[str]] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    conn = await get_db_connection()
    try:
        conditions = []
        params = []

        courts = _normalize_multi(court)
        if courts:
            params.append(courts)
            conditions.append(f"j.court = ANY(${len(params)}::text[])")

        court_types = _normalize_multi(court_type)
        if court_types:
            params.append(court_types)
            conditions.append(f"j.court_type = ANY(${len(params)}::text[])")

        legal_areas = _normalize_multi(legal_area)
        if legal_areas:
            params.append(legal_areas)
            conditions.append(f"j.legal_area = ANY(${len(params)}::text[])")

        sources = _normalize_multi(source)
        if sources:
            params.append(sources)
            conditions.append(f"j.source = ANY(${len(params)}::text[])")

        cities = _normalize_multi(city)
        if cities:
            params.append(cities)
            conditions.append(f"j.city = ANY(${len(params)}::text[])")
        if date_from:
            params.append(DateType.fromisoformat(date_from))  # ← konwersja
            conditions.append(f"j.date >= ${len(params)}")
        if date_to:
            params.append(DateType.fromisoformat(date_to))    # ← konwersja
            conditions.append(f"j.date <= ${len(params)}")
        articles = _normalize_multi(article)
        if articles:
            article_conditions = []
            for single_article in articles:
                params.append(f"%{single_article}%")
                article_conditions.append(
                    f"EXISTS (SELECT 1 FROM judgment_regulations jr "
                    f"JOIN unnest(jr.articles) AS a ON TRUE "
                    f"WHERE jr.judgment_id = j.id AND a ILIKE ${len(params)})"
                )
            conditions.append("(" + " OR ".join(article_conditions) + ")")

        act_titles = _normalize_multi(act_title)
        if act_titles:
            act_title_conditions = []
            for single_act_title in act_titles:
                params.append(f"%{single_act_title}%")
                act_title_conditions.append(
                    f"EXISTS (SELECT 1 FROM judgment_regulations jr "
                    f"WHERE jr.judgment_id = j.id AND jr.act_title ILIKE ${len(params)})"
                )
            conditions.append("(" + " OR ".join(act_title_conditions) + ")")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_row = await conn.fetchrow(
            f"SELECT COUNT(*) as total FROM judgments j {where}",
            *params
        )
        total = count_row["total"]

        params += [limit, offset]
        rows = await conn.fetch(
            f"""
            SELECT j.id, j.case_number, j.court, j.court_type, j.city,
                   j.date, j.thesis, j.source_url, j.legal_area, j.source,
                   j.created_at
            FROM judgments j
            {where}
            ORDER BY j.date DESC NULLS LAST
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        return {
            "judgments": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset
        }
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
