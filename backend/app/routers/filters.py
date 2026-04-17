from fastapi import APIRouter, Query
from app.db import get_db_connection

router = APIRouter()


@router.get("/filters")
async def get_all_filters():
    """Zwraca wszystkie filtry naraz – jeden request zamiast pięciu."""
    conn = await get_db_connection()
    try:
        # ── 1. ŹRÓDŁO ──────────────────────────────────────────
        source_rows = await conn.fetch("""
            SELECT
                COALESCE(source,
                    CASE
                        WHEN source_url ILIKE '%nsa.gov.pl%'      THEN 'nsa'
                        WHEN source_url ILIKE '%saos.org.pl%'     THEN 'saos'
                        WHEN source_url ILIKE '%sn.pl%'           THEN 'sn'
                        WHEN source_url ILIKE '%curia.europa.eu%' THEN 'cjeu'
                        ELSE 'inne'
                    END
                ) AS value,
                COUNT(*) AS count
            FROM judgments
            GROUP BY value
            ORDER BY count DESC
        """)

        # ── 2. OBSZAR PRAWA ────────────────────────────────────
        try:
            area_rows = await conn.fetch("""
                SELECT legal_area AS value, COUNT(*) AS count
                FROM judgments
                WHERE legal_area IS NOT NULL AND legal_area != ''
                GROUP BY legal_area
                ORDER BY count DESC
            """)
        except Exception:
            area_rows = []  # kolumna jeszcze nie istnieje

        # ── 3. PRAWOMOCNOŚĆ ────────────────────────────────────
        # Sądy II instancji (apelacyjne, NSA, SN) = prawomocne
        finality_rows = await conn.fetch("""
            SELECT
                CASE
                    WHEN court ILIKE '%apelacyj%'
                      OR court ILIKE '%najwyższy%'
                      OR court ILIKE '%NSA%'
                      OR court_type ILIKE '%SUPREME%'
                    THEN 'Prawomocne'
                    ELSE 'Nieprawomocne'
                END      AS value,
                COUNT(*) AS count
            FROM judgments
            GROUP BY value
            ORDER BY count DESC
        """)

        # ── 4. MIASTO ──────────────────────────────────────────
        city_rows = await conn.fetch("""
            SELECT city AS value, COUNT(*) AS count
            FROM judgments
            WHERE city IS NOT NULL AND city != ''
            GROUP BY city
            ORDER BY count DESC
            LIMIT 30
        """)

        # ── 5. LATA (dla filtra Okres) ─────────────────────────
        year_rows = await conn.fetch("""
            SELECT
                EXTRACT(YEAR FROM date)::INTEGER AS value,
                COUNT(*)                          AS count
            FROM judgments
            WHERE date IS NOT NULL
            GROUP BY value
            ORDER BY value DESC
        """)

        return {
            "sources":      [{"value": r["value"], "count": r["count"]} for r in source_rows],
            "legal_areas":  [{"value": r["value"], "count": r["count"]} for r in area_rows],
            "finality":     [{"value": r["value"], "count": r["count"]} for r in finality_rows],
            "cities":       [{"value": r["value"], "count": r["count"]} for r in city_rows],
            "years":        [{"value": r["value"], "count": r["count"]} for r in year_rows],
        }

    finally:
        await conn.close()


# ── Osobne endpointy (kompatybilność z istniejącym kodem) ─────

@router.get("/filters/courts")
async def get_courts():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT court AS value, COUNT(*) AS count
            FROM judgments
            WHERE court IS NOT NULL AND court != ''
            GROUP BY court
            ORDER BY count DESC
            LIMIT 50
        """)
        return {"courts": [{"value": r["value"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()


@router.get("/filters/court-types")
async def get_court_types():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT court_type AS value, COUNT(*) AS count
            FROM judgments
            WHERE court_type IS NOT NULL AND court_type != ''
            GROUP BY court_type
            ORDER BY count DESC
        """)
        return {"court_types": [{"value": r["value"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()


@router.get("/filters/sources")
async def get_sources():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT
                COALESCE(source,
                    CASE
                        WHEN source_url ILIKE '%nsa.gov.pl%'      THEN 'nsa'
                        WHEN source_url ILIKE '%saos.org.pl%'     THEN 'saos'
                        WHEN source_url ILIKE '%sn.pl%'           THEN 'sn'
                        WHEN source_url ILIKE '%curia.europa.eu%' THEN 'cjeu'
                        ELSE 'inne'
                    END
                ) AS value,
                COUNT(*) AS count
            FROM judgments
            GROUP BY value
            ORDER BY count DESC
        """)
        return {"sources": [{"value": r["value"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()


@router.get("/filters/cities")
async def get_cities():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT city AS value, COUNT(*) AS count
            FROM judgments
            WHERE city IS NOT NULL AND city != ''
            GROUP BY city
            ORDER BY count DESC
            LIMIT 30
        """)
        return {"cities": [{"value": r["value"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()


@router.get("/filters/legal-areas")
async def get_legal_areas():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT legal_area AS value, COUNT(*) AS count
            FROM judgments
            WHERE legal_area IS NOT NULL AND legal_area != ''
            GROUP BY legal_area
            ORDER BY count DESC
        """)
        return {"legal_areas": [{"value": r["value"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()


@router.get("/filters/articles")
async def get_articles(act_title: str = Query(None)):
    conn = await get_db_connection()
    try:
        if act_title:
            rows = await conn.fetch("""
                SELECT DISTINCT unnest(jr.articles) AS article
                FROM judgment_regulations jr
                WHERE jr.act_title ILIKE $1
                  AND jr.articles IS NOT NULL
                  AND array_length(jr.articles, 1) > 0
                ORDER BY article
            """, f"%{act_title}%")
        else:
            rows = await conn.fetch("""
                SELECT DISTINCT unnest(jr.articles) AS article
                FROM judgment_regulations jr
                WHERE jr.articles IS NOT NULL
                  AND array_length(jr.articles, 1) > 0
                ORDER BY article
                LIMIT 200
            """)
        return {"articles": [r["article"] for r in rows]}
    finally:
        await conn.close()

@router.get("/filters/act-titles")
async def get_act_titles():
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT act_title, COUNT(*) as count
            FROM judgment_regulations
            WHERE act_title IS NOT NULL AND act_title != ''
            GROUP BY act_title
            ORDER BY count DESC
            LIMIT 100
        """)
        return {"act_titles": [{"value": r["act_title"], "count": r["count"]} for r in rows]}
    finally:
        await conn.close()