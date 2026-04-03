"""
Populate database from SAOS API, ISAP scraper or NSA scraper.

Usage:
    python -m pipeline.populate_db [options]

Options:
    --source       saos | isap | nsa  (default: saos)
    --date-from    YYYY-MM-DD (default: 2024-01-01)  [saos, nsa]
    --date-to      YYYY-MM-DD (default: today)        [saos, nsa]
    --court-type   SUPREME_COURT | COMMON_COURT | ADMINISTRATIVE_COURT | ...  [saos]
    --keyword      keyword filter  [saos, isap]
    --limit        max records to fetch (default: 200)
    --embed        also generate Jina embeddings after storing
"""

import argparse
import logging
import os
import sys
import time
import psycopg2
import httpx
from datetime import date
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.scrapers.saos import SAOSScraper
from pipeline.scrapers.isap import ISAPScraper
from pipeline.scrapers.nsa import NSAScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
JINA_API_KEY = os.getenv("JINA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jina-embeddings-v3")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def generate_thesis_with_llm(content: str) -> str | None:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")
    prompt = (
        "Jestes ekspertem prawnym. Na podstawie ponizszej tresci orzeczenia napisz krotka teze "
        "(1-3 zdania) oddajaca glowna mysl prawna orzeczenia. Odpowiedz tylko teza, bez wstepow.\n\n"
        f"Tresc orzeczenia:\n{content[:4000]}"
    )
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": LLM_MODEL, "temperature": 0.1, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def backfill_thesis_with_llm(limit: int = 100) -> int:
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            "SELECT id, content FROM judgments WHERE thesis IS NULL AND content IS NOT NULL AND content != '' LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments with NULL thesis to backfill via LLM", len(rows))
        for row_id, content in rows:
            try:
                thesis = generate_thesis_with_llm(content)
                if thesis:
                    cur.execute("UPDATE judgments SET thesis = %s WHERE id = %s", (thesis, row_id))
                    updated += 1
                    logger.info("Generated thesis for id=%d", row_id)
            except Exception as e:
                logger.error("LLM thesis generation failed for id=%d: %s", row_id, e)
            time.sleep(0.3)
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled thesis for %d judgments via LLM", updated)
    return updated


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def store_judgment_chunks(cur, judgment_id: int, content: str):
    chunks = split_into_chunks(content)
    for idx, chunk in enumerate(chunks):
        cur.execute(
            """
            INSERT INTO judgment_chunks (judgment_id, chunk_index, content)
            VALUES (%s, %s, %s)
            """,
            (judgment_id, idx, chunk),
        )


def store_judgment(cur, judgment: dict) -> bool:
    try:
        cur.execute(
            """
            INSERT INTO judgments (case_number, court, court_type, city, date, content, thesis, keywords, doc_id, source_url, source, legal_area)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (case_number) DO NOTHING
    RETURNING id
    """,
    (
        judgment["case_number"],
        judgment["court"],
        judgment.get("court_type"),
        judgment.get("city"),
        judgment.get("date"),
        judgment["content"],
        judgment.get("thesis"),
        judgment.get("keywords") or [],
        judgment.get("doc_id"),
        judgment.get("source_url"),
        judgment.get("source"),
        judgment.get("legal_area"),
    ),
        )
        return cur.fetchone() is not None
    except Exception as e:
        logger.error("Failed to store %s: %s", judgment.get("case_number"), e)
        return False


def generate_jina_embeddings(texts: list[str]) -> list[list[float]]:
    if not JINA_API_KEY:
        raise ValueError("JINA_API_KEY not set in .env")
    response = httpx.post(
        "https://api.jina.ai/v1/embeddings",
        headers={"Authorization": f"Bearer {JINA_API_KEY}", "Content-Type": "application/json"},
        json={"model": EMBEDDING_MODEL, "input": texts, "task": "retrieval.passage"},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def embed_pending_chunks(batch_size: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    total = 0
    try:
        while True:
            cur.execute(
                "SELECT id, content FROM judgment_chunks WHERE embedding IS NULL LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                break
            ids = [r[0] for r in rows]
            texts = [r[1][:8000] for r in rows]
            try:
                embeddings = generate_jina_embeddings(texts)
            except Exception as e:
                logger.error("Embedding batch failed: %s", e)
                break
            for row_id, embedding in zip(ids, embeddings):
                cur.execute(
                    "UPDATE judgment_chunks SET embedding = %s WHERE id = %s",
                    (str(embedding), row_id),
                )
                total += 1
            conn.commit()
            logger.info("Embedded %d judgment chunks so far", total)
            if len(rows) < batch_size:
                break
    finally:
        cur.close()
        conn.close()
    return total


def embed_pending_judgments(batch_size: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    total = 0
    try:
        while True:
            cur.execute(
                "SELECT id, content FROM judgments WHERE embedding IS NULL LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                break

            ids = [r[0] for r in rows]
            texts = [r[1][:8000] for r in rows]

            try:
                embeddings = generate_jina_embeddings(texts)
            except Exception as e:
                logger.error("Embedding batch failed: %s", e)
                break

            for row_id, embedding in zip(ids, embeddings):
                cur.execute(
                    "UPDATE judgments SET embedding = %s WHERE id = %s",
                    (str(embedding), row_id),
                )
                total += 1

            conn.commit()
            logger.info("Embedded %d judgments so far", total)

            if len(rows) < batch_size:
                break
    finally:
        cur.close()
        conn.close()
    return total


def embed_pending_legal_acts(batch_size: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    total = 0
    try:
        while True:
            cur.execute(
                "SELECT id, title FROM legal_acts WHERE embedding IS NULL LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                break
            ids = [r[0] for r in rows]
            texts = [r[1][:8000] for r in rows]
            try:
                embeddings = generate_jina_embeddings(texts)
            except Exception as e:
                logger.error("Embedding batch failed: %s", e)
                break
            for row_id, embedding in zip(ids, embeddings):
                cur.execute(
                    "UPDATE legal_acts SET embedding = %s WHERE id = %s",
                    (str(embedding), row_id),
                )
                total += 1
            conn.commit()
            logger.info("Embedded %d legal_acts so far", total)
            if len(rows) < batch_size:
                break
    finally:
        cur.close()
        conn.close()
    return total


def store_legal_act(cur, act: dict) -> int | None:
    try:
        cur.execute(
            """
            INSERT INTO legal_acts (title, type, source_url, year, isap_id, journal_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                act["title"],
                act.get("type", "ustawa"),
                act.get("source_url"),
                act.get("year"),
                act.get("isap_id"),
                act.get("journal_number"),
            ),
        )
        row = cur.fetchone()
        if not row:
            return None
        act_id = row[0]
        for article in act.get("articles", []):
            cur.execute(
                """
                INSERT INTO articles (legal_act_id, article_number, paragraph, content)
                VALUES (%s, %s, %s, %s)
                """,
                (act_id, article["number"], article.get("paragraph"), article["content"]),
            )
        return act_id
    except Exception as e:
        logger.error("Failed to store act %s: %s", act.get("title"), e)
        return None


def embed_pending_articles(batch_size: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    total = 0
    try:
        while True:
            cur.execute(
                "SELECT id, content FROM articles WHERE embedding IS NULL LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                break
            ids = [r[0] for r in rows]
            texts = [r[1][:8000] for r in rows]
            try:
                embeddings = generate_jina_embeddings(texts)
            except Exception as e:
                logger.error("Embedding batch failed: %s", e)
                break
            for row_id, embedding in zip(ids, embeddings):
                cur.execute(
                    "UPDATE articles SET embedding = %s WHERE id = %s",
                    (str(embedding), row_id),
                )
                total += 1
            conn.commit()
            logger.info("Embedded %d articles so far", total)
            if len(rows) < batch_size:
                break
    finally:
        cur.close()
        conn.close()
    return total


def populate_from_isap(keyword: str, limit: int) -> int:
    scraper = ISAPScraper()
    logger.info("Fetching from ISAP: keyword=%s limit=%d", keyword, limit)
    acts = scraper.search_acts(keyword, limit=limit)
    logger.info("Fetched %d acts from ISAP", len(acts))
    conn = get_conn()
    cur = conn.cursor()
    stored = 0
    try:
        for act in acts:
            if store_legal_act(cur, act) is not None:
                stored += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Stored %d acts from ISAP", stored)
    return stored


def populate_from_nsa(date_from: str, date_to: str, limit: int) -> int:
    scraper = NSAScraper(delay=1.0)
    logger.info("Fetching from NSA: date_from=%s date_to=%s limit=%d", date_from, date_to, limit)
    judgments = scraper.scrape_range(date_from, date_to, limit=limit)
    logger.info("Fetched %d judgments from NSA", len(judgments))
    conn = get_conn()
    cur = conn.cursor()
    stored = 0
    try:
        for j in judgments:
            cur.execute("SELECT id FROM judgments WHERE case_number = %s", (j["case_number"],))
            existing = cur.fetchone()
            if existing:
                continue
            if store_judgment(cur, j):
                cur.execute("SELECT id FROM judgments WHERE case_number = %s", (j["case_number"],))
                row = cur.fetchone()
                if row:
                    store_judgment_chunks(cur, row[0], j["content"])
                stored += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Stored %d new NSA judgments (skipped %d duplicates)", stored, len(judgments) - stored)
    return stored


def backfill_thesis_from_saos(limit: int = 100) -> int:
    scraper = SAOSScraper(delay=0.5)
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            "SELECT id, source_url FROM judgments WHERE thesis IS NULL AND source_url LIKE %s LIMIT %s",
            ("%saos.org.pl%", limit),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments with NULL thesis to backfill", len(rows))
        for row_id, source_url in rows:
            detail = scraper.fetch_judgment_detail(source_url)
            if not detail:
                time.sleep(scraper.delay)
                continue
            thesis = scraper.extract_thesis(detail)
            if thesis:
                cur.execute("UPDATE judgments SET thesis = %s WHERE id = %s", (thesis, row_id))
                updated += 1
                logger.info("Updated thesis for id=%d", row_id)
            time.sleep(scraper.delay)
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled thesis for %d judgments", updated)
    return updated


def populate_from_saos(
    date_from: str,
    date_to: str,
    court_type: str | None,
    keyword: str | None,
    limit: int,
) -> int:
    scraper = SAOSScraper(delay=0.5)
    logger.info(
        "Fetching from SAOS: date_from=%s date_to=%s court_type=%s keyword=%s limit=%d",
        date_from, date_to, court_type, keyword, limit,
    )
    judgments = scraper.scrape_range(
        date_from=date_from,
        date_to=date_to,
        court_type=court_type,
        keyword=keyword,
        limit=limit,
    )
    logger.info("Fetched %d judgments from SAOS", len(judgments))

    conn = get_conn()
    cur = conn.cursor()
    stored = 0
    try:
        for j in judgments:
            cur.execute("SELECT id FROM judgments WHERE case_number = %s", (j["case_number"],))
            existing = cur.fetchone()
            if existing:
                continue
            if store_judgment(cur, j):
                cur.execute("SELECT id FROM judgments WHERE case_number = %s", (j["case_number"],))
                row = cur.fetchone()
                if row:
                    store_judgment_chunks(cur, row[0], j["content"])
                stored += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info("Stored %d new judgments (skipped %d duplicates)", stored, len(judgments) - stored)
    return stored


def main():
    parser = argparse.ArgumentParser(description="Populate DB from legal APIs")
    parser.add_argument("--source", default="saos", choices=["saos", "isap", "nsa"])
    parser.add_argument("--date-from", default="2024-01-01", help="[saos, nsa]")
    parser.add_argument("--date-to", default=str(date.today()), help="[saos, nsa]")
    parser.add_argument("--court-type", default=None, help="[saos] SUPREME_COURT | COMMON_COURT | ADMINISTRATIVE_COURT")
    parser.add_argument("--keyword", default=None, help="[saos, isap] keyword filter")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--embed", action="store_true", help="Generate Jina embeddings after storing")
    parser.add_argument("--backfill-thesis", action="store_true", help="Backfill NULL thesis from SAOS detail endpoint")
    parser.add_argument("--backfill-thesis-llm", action="store_true", help="Backfill NULL thesis using Groq LLM from content")
    args = parser.parse_args()

    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)

    if args.backfill_thesis:
        logger.info("Backfilling thesis from SAOS detail endpoint...")
        backfill_thesis_from_saos(limit=args.limit)
        return

    if args.backfill_thesis_llm:
        logger.info("Backfilling thesis via Groq LLM...")
        backfill_thesis_with_llm(limit=args.limit)
        return

    if args.source == "saos":
        populate_from_saos(
            date_from=args.date_from,
            date_to=args.date_to,
            court_type=args.court_type,
            keyword=args.keyword,
            limit=args.limit,
        )
    elif args.source == "isap":
        if not args.keyword:
            logger.error("--keyword is required for ISAP source")
            sys.exit(1)
        populate_from_isap(keyword=args.keyword, limit=args.limit)
    elif args.source == "nsa":
        populate_from_nsa(
            date_from=args.date_from,
            date_to=args.date_to,
            limit=args.limit,
        )

    if args.embed:
        logger.info("Generating embeddings for pending judgments...")
        j_total = embed_pending_judgments()
        logger.info("Embedded %d judgments", j_total)
        logger.info("Generating embeddings for pending judgment chunks...")
        c_total = embed_pending_chunks()
        logger.info("Embedded %d chunks", c_total)
        if args.source == "isap":
            logger.info("Generating embeddings for pending articles...")
            a_total = embed_pending_articles()
            logger.info("Embedded %d articles", a_total)
            logger.info("Generating embeddings for pending legal acts...")
            la_total = embed_pending_legal_acts()
            logger.info("Embedded %d legal acts", la_total)


if __name__ == "__main__":
    main()
