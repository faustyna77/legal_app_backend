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
import json
import argparse
import logging
import os
import re
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def generate_thesis_with_llm(content: str) -> str | None:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")
    prompt = (
        "Jestes ekspertem prawnym. Na podstawie ponizszej tresci orzeczenia napisz krotka teze "
        "(1-3 zdania) oddajaca glowna mysl prawna orzeczenia. Odpowiedz tylko teza, bez wstepow.\n\n"
        f"Tresc orzeczenia:\n{content[:4000]}"
    )
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": LLM_MODEL, "temperature": 0.1, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
def generate_summary_with_llm(case_number: str, court: str, date, thesis: str, content: str) -> dict | None:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": LLM_MODEL,
            "temperature": 0.0,
            "messages": [
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
                        f"Sygnatura: {case_number}\n"
                        f"Sad: {court}\n"
                        f"Data: {date}\n"
                        f"Teza: {thesis}\n\n"
                        f"Tresc orzeczenia:\n{content[:6000]}"
                    ),
                },
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"].strip()
    try:
        raw_clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_clean)
    except Exception:
        return {"teza": raw, "stan_faktyczny": "", "rozstrzygniecie": "", "podstawa_prawna": ""}



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

def backfill_summaries(limit: int = 100) -> int:
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """SELECT id, case_number, court, date, thesis, content
               FROM judgments
               WHERE summary IS NULL AND content IS NOT NULL AND content != ''
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments without summary", len(rows))
        for row in rows:
            judgment_id, case_number, court, j_date, thesis, content = row
            try:
                summary = generate_summary_with_llm(
                    case_number, court, j_date, thesis or "", content
                )
                if summary:
                    cur.execute(
                        "UPDATE judgments SET summary = %s WHERE id = %s",
                        (json.dumps(summary, ensure_ascii=False), judgment_id),
                    )
                    updated += 1
                    logger.info("Generated summary for id=%d", judgment_id)
            except Exception as e:
                logger.error("Summary generation failed for id=%d: %s", judgment_id, e)
            time.sleep(0.5)
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Generated summaries for %d judgments", updated)
    return updated


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
CASE_NUMBER_PATTERN = r"\b[IVX]+\s+[A-Za-z]+\s+\d+[a-z]?/\d{2,4}\b"
ARTICLE_MENTION_PATTERN = re.compile(
    r"\bart\.\s*\d+[a-z]?(?:\s*§\s*\d+[a-z]?)?(?:\s*ust\.\s*\d+[a-z]?)?(?:\s*pkt\s*\d+[a-z]?)?",
    re.IGNORECASE,
)


def _normalize_article_ref(article: str) -> str:
    normalized = " ".join((article or "").split())
    normalized = re.sub(r"^art\.?\s*", "art. ", normalized, flags=re.IGNORECASE)
    normalized = normalized.strip().rstrip(".,;:")
    return normalized.lower()


def _article_core(article: str) -> str:
    match = re.search(r"art\.\s*\d+[a-z]?", article, re.IGNORECASE)
    if not match:
        return article
    return " ".join(match.group(0).lower().split())


def extract_article_mentions(content: str) -> list[str]:
    if not content:
        return []
    mentions = ARTICLE_MENTION_PATTERN.findall(content)
    unique: list[str] = []
    seen = set()
    for mention in mentions:
        normalized = _normalize_article_ref(mention)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _load_isap_article_numbers_for_act(cur, act_title: str) -> set[str]:
    if not act_title:
        return set()

    cur.execute(
        """
        SELECT a.article_number
        FROM articles a
        JOIN legal_acts la ON la.id = a.legal_act_id
        WHERE la.title ILIKE %s
        """,
        (f"%{act_title}%",),
    )
    rows = cur.fetchall()

    if not rows:
        keyword = _keyword_from_act_title(act_title)
        if keyword:
            cur.execute(
                """
                SELECT a.article_number
                FROM articles a
                JOIN legal_acts la ON la.id = a.legal_act_id
                WHERE la.title ILIKE %s
                """,
                (f"%{keyword}%",),
            )
            rows = cur.fetchall()

    normalized = set()
    for (article_number,) in rows:
        value = _normalize_article_ref(article_number or "")
        if value:
            normalized.add(value)
    return normalized


def _match_article_mentions_to_act(cur, act_title: str, article_mentions: list[str]) -> list[str]:
    if not article_mentions:
        return []
    isap_article_numbers = _load_isap_article_numbers_for_act(cur, act_title)
    if not isap_article_numbers:
        return []
    isap_cores = {_article_core(article) for article in isap_article_numbers}

    matched: list[str] = []
    seen = set()
    for mention in article_mentions:
        core = _article_core(mention)
        if mention in isap_article_numbers or core in isap_cores:
            if mention not in seen:
                seen.add(mention)
                matched.append(mention)
    return matched


def enrich_regulations_articles(cur, regulations: list[dict], content: str | None) -> list[dict]:
    if not regulations:
        return []

    article_mentions = extract_article_mentions(content or "")
    enriched: list[dict] = []

    for reg in regulations:
        item = dict(reg)
        existing_articles = []
        for article in item.get("articles", []) or []:
            normalized = _normalize_article_ref(article)
            if normalized and normalized not in existing_articles:
                existing_articles.append(normalized)

        if existing_articles:
            item["articles"] = existing_articles
            enriched.append(item)
            continue

        mapped_articles = _match_article_mentions_to_act(cur, item.get("act_title", ""), article_mentions)
        if not mapped_articles:
            mapped_articles = article_mentions
        item["articles"] = mapped_articles
        enriched.append(item)

    return enriched


def extract_referenced_case_numbers(content: str) -> list[str]:
    if not content:
        return []
    case_numbers = re.findall(CASE_NUMBER_PATTERN, content)
    unique: list[str] = []
    seen = set()
    for case_number in case_numbers:
        normalized = " ".join(case_number.split())
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def store_judgment_references(cur, judgment_id: int, case_number: str, content: str):
    referenced_case_numbers = extract_referenced_case_numbers(content)
    for referenced_case_number in referenced_case_numbers:
        if referenced_case_number == case_number:
            continue
        cur.execute(
            "SELECT id FROM judgments WHERE case_number = %s",
            (referenced_case_number,),
        )
        row = cur.fetchone()
        referenced_judgment_id = row[0] if row else None
        cur.execute(
            """
            INSERT INTO judgment_references (judgment_id, referenced_case_number, referenced_judgment_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (judgment_id, referenced_case_number) DO UPDATE
            SET referenced_judgment_id = COALESCE(judgment_references.referenced_judgment_id, EXCLUDED.referenced_judgment_id)
            """,
            (judgment_id, referenced_case_number, referenced_judgment_id),
        )


def store_judgment_regulations(cur, judgment_id: int, regulations: list[dict]):
    for reg in regulations:
        cur.execute(
            """
            INSERT INTO judgment_regulations
            (judgment_id, act_title, act_year, journal_no, articles)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                judgment_id,
                reg["act_title"],
                reg.get("act_year"),
                reg.get("journal_no"),
                reg.get("articles", []),
            ),
        )


def link_references_to_existing_judgment(cur, referenced_case_number: str, referenced_judgment_id: int):
    cur.execute(
        """
        UPDATE judgment_references
        SET referenced_judgment_id = %s
        WHERE referenced_case_number = %s
          AND referenced_judgment_id IS NULL
        """,
        (referenced_judgment_id, referenced_case_number),
    )


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


def generate_openai_embeddings(texts: list[str]) -> list[list[float]]:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")
    attempts = 6
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": EMBEDDING_MODEL, "input": texts, "dimensions": 1024},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429 or attempt == attempts:
                raise
            retry_after = e.response.headers.get("retry-after")
            sleep_seconds = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
            logger.warning("Embedding rate limited (429), retrying in %.1fs (attempt %d/%d)", sleep_seconds, attempt, attempts)
            time.sleep(sleep_seconds)
    raise RuntimeError("Embedding request failed after retries")


def generate_jina_embeddings(texts: list[str]) -> list[list[float]]:
    return generate_openai_embeddings(texts)


def embed_pending_chunks(batch_size: int = 10):
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
                embeddings = generate_openai_embeddings(texts)
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


def embed_pending_judgments(batch_size: int = 10):
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
                embeddings = generate_openai_embeddings(texts)
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


def embed_pending_legal_acts(batch_size: int = 10):
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
                embeddings = generate_openai_embeddings(texts)
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
        isap_id = act.get("isap_id")
        title = act["title"]
        act_type = act.get("type", "ustawa")
        source_url = act.get("source_url")
        act_year = act.get("year")
        journal_number = act.get("journal_number")

        if isap_id:
            cur.execute(
                """
                INSERT INTO legal_acts (title, type, source_url, year, isap_id, journal_number)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (isap_id) DO UPDATE
                SET title = EXCLUDED.title,
                    type = EXCLUDED.type,
                    source_url = COALESCE(EXCLUDED.source_url, legal_acts.source_url),
                    year = COALESCE(EXCLUDED.year, legal_acts.year),
                    journal_number = COALESCE(EXCLUDED.journal_number, legal_acts.journal_number)
                RETURNING id
                """,
                (title, act_type, source_url, act_year, isap_id, journal_number),
            )
            row = cur.fetchone()
            act_id = row[0] if row else None
        else:
            cur.execute(
                """
                SELECT id FROM legal_acts
                WHERE lower(btrim(title)) = lower(btrim(%s))
                  AND COALESCE(year, -1) = COALESCE(%s, -1)
                  AND COALESCE(lower(btrim(journal_number)), '') = COALESCE(lower(btrim(%s)), '')
                LIMIT 1
                """,
                (title, act_year, journal_number),
            )
            row = cur.fetchone()
            if row:
                act_id = row[0]
            else:
                cur.execute(
                    """
                    INSERT INTO legal_acts (title, type, source_url, year, isap_id, journal_number)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (title, act_type, source_url, act_year, None, journal_number),
                )
                row = cur.fetchone()
                act_id = row[0] if row else None

        if not act_id:
            return None

        for article in act.get("articles", []):
            cur.execute(
                """
                INSERT INTO articles (legal_act_id, article_number, paragraph, content)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM articles
                    WHERE legal_act_id = %s
                      AND lower(btrim(article_number)) = lower(btrim(%s))
                      AND COALESCE(lower(btrim(paragraph)), '') = COALESCE(lower(btrim(%s)), '')
                      AND content = %s
                )
                """,
                (act_id, article["number"], article.get("paragraph"), article["content"], act_id, article["number"], article.get("paragraph"), article["content"]),
            )
        return act_id
    except Exception as e:
        logger.error("Failed to store act %s: %s", act.get("title"), e)
        return None


def embed_pending_articles(batch_size: int = 10):
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
                embeddings = generate_openai_embeddings(texts)
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


def _keyword_from_act_title(act_title: str) -> str:
    if not act_title:
        return ""
    title = act_title
    if " - " in title:
        title = title.split(" - ", 1)[1]
    title = re.sub(r"^Ustawa z dnia .*?\s+", "", title, flags=re.IGNORECASE).strip()
    return title[:120]


def ensure_isap_act_for_regulation(cur, isap: ISAPScraper, act_title: str, force_refresh: bool = False):
    if not act_title or act_title.startswith("Nieustalony akt"):
        return

    cur.execute("SELECT id FROM legal_acts WHERE title ILIKE %s LIMIT 1", (f"%{act_title}%",))
    existing = cur.fetchone()
    if existing and not force_refresh:
        return

    keyword = _keyword_from_act_title(act_title)
    if not keyword:
        return

    try:
        acts = isap.search_acts(keyword=keyword, limit=1)
    except Exception as e:
        logger.warning("ISAP lookup failed for '%s': %s", act_title, e)
        return

    if not acts:
        return

    store_legal_act(cur, acts[0])


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
                judgment_id = existing[0]
                cur.execute("SELECT 1 FROM judgment_chunks WHERE judgment_id = %s LIMIT 1", (judgment_id,))
                if not cur.fetchone() and j.get("content"):
                    store_judgment_chunks(cur, judgment_id, j["content"])
                if j.get("content"):
                    store_judgment_references(cur, judgment_id, j["case_number"], j["content"])
                if j.get("regulations"):
                    regulations = enrich_regulations_articles(cur, j.get("regulations", []), j.get("content"))
                    store_judgment_regulations(cur, judgment_id, regulations)
                    

                       
                    link_references_to_existing_judgment(cur, j["case_number"], judgment_id)
                stored += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Stored %d new NSA judgments (skipped %d duplicates)", stored, len(judgments) - stored)
    return stored



def _resolve_saos_detail_url(source_url: str | None, doc_id: str | None) -> str | None:
    if source_url and "/api/judgments/" in source_url:
        return source_url
    if source_url and "/judgments/" in source_url:
        return source_url.replace("/judgments/", "/api/judgments/")
    if doc_id:
        return f"https://www.saos.org.pl/api/judgments/{doc_id}"
    return None


def backfill_thesis_from_saos(limit: int = 100) -> int:
    scraper = SAOSScraper(delay=0.5)
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            "SELECT id, source_url, doc_id FROM judgments WHERE thesis IS NULL AND source = %s LIMIT %s",
            ("saos", limit),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments with NULL thesis to backfill", len(rows))
        for row_id, source_url, doc_id in rows:
            detail_url = _resolve_saos_detail_url(source_url, doc_id)
            if not detail_url:
                continue
            detail = scraper.fetch_judgment_detail(detail_url)
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


def backfill_regulations(limit: int = 200) -> int:
    scraper = SAOSScraper(delay=0.5)
    
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """
            SELECT j.id, j.source_url, j.doc_id, j.content
            FROM judgments j
            LEFT JOIN judgment_regulations jr ON jr.judgment_id = j.id
            WHERE j.source = %s AND jr.id IS NULL
            LIMIT %s
            """,
            ("saos", limit),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments without regulations", len(rows))
        for judgment_id, source_url, doc_id, content in rows:
            detail_url = _resolve_saos_detail_url(source_url, doc_id)
            if not detail_url:
                continue
            detail = scraper.fetch_judgment_detail(detail_url)
            if not detail:
                time.sleep(scraper.delay)
                continue
            regulations = scraper.extract_regulations(detail)
            regulations = enrich_regulations_articles(cur, regulations, content)
            if regulations:
                store_judgment_regulations(cur, judgment_id, regulations)
                
                updated += 1
                logger.info("Stored regulations for id=%d", judgment_id)
            time.sleep(scraper.delay)
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled regulations for %d judgments", updated)
    return updated


def backfill_references(limit: int = 200) -> int:
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """
            SELECT j.id, j.case_number, j.content
            FROM judgments j
            LEFT JOIN judgment_references jr ON jr.judgment_id = j.id
            WHERE jr.id IS NULL AND j.content IS NOT NULL AND j.content != ''
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        logger.info("Found %d judgments without references", len(rows))
        for judgment_id, case_number, content in rows:
            store_judgment_references(cur, judgment_id, case_number, content)
            link_references_to_existing_judgment(cur, case_number, judgment_id)
            updated += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled references for %d judgments", updated)
    return updated


def backfill_nsa_regulations(limit: int = 200) -> int:
    scraper = NSAScraper(delay=0.1)
    
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """
            SELECT j.id, j.content
            FROM judgments j
            LEFT JOIN judgment_regulations jr ON jr.judgment_id = j.id
            WHERE j.source = 'nsa' AND jr.id IS NULL
              AND j.content IS NOT NULL AND j.content != ''
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        logger.info("Found %d NSA judgments without regulations", len(rows))
        for judgment_id, content in rows:
            regulations = scraper.extract_regulations(content)
            if not regulations:
                continue
            store_judgment_regulations(cur, judgment_id, regulations)
            
            updated += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled NSA regulations for %d judgments", updated)
    return updated


def backfill_isap_acts_for_regulations(limit: int = 500) -> int:
    isap = ISAPScraper(delay=0.2)
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """
            SELECT DISTINCT jr.act_title
            FROM judgment_regulations jr
            JOIN judgments j ON j.id = jr.judgment_id
            WHERE j.source = 'saos'
              AND jr.act_title IS NOT NULL
              AND jr.act_title <> ''
            ORDER BY jr.act_title
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        logger.info("Found %d SAOS regulation acts to ensure in ISAP", len(rows))

        for (act_title,) in rows:
            cur.execute("SELECT id FROM legal_acts WHERE title ILIKE %s LIMIT 1", (f"%{act_title}%",))
            had_before = cur.fetchone() is not None
            
            cur.execute("SELECT id FROM legal_acts WHERE title ILIKE %s LIMIT 1", (f"%{act_title}%",))
            has_after = cur.fetchone() is not None
            if not had_before and has_after:
                updated += 1

        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info("Backfilled ISAP acts for %d SAOS regulation titles", updated)
    return updated


def backfill_saos_regulation_articles(limit: int = 200) -> int:
    conn = get_conn()
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute(
            """
            SELECT DISTINCT j.id, j.content
            FROM judgments j
            JOIN judgment_regulations jr ON jr.judgment_id = j.id
            WHERE j.source = 'saos'
              AND (jr.articles IS NULL OR array_length(jr.articles, 1) IS NULL)
              AND j.content IS NOT NULL AND j.content != ''
            LIMIT %s
            """,
            (limit,),
        )
        judgments = cur.fetchall()
        logger.info("Found %d SAOS judgments with empty regulation articles", len(judgments))

        for judgment_id, content in judgments:
            cur.execute(
                """
                SELECT id, act_title, act_year, journal_no, articles
                FROM judgment_regulations
                WHERE judgment_id = %s
                ORDER BY id
                """,
                (judgment_id,),
            )
            regs_rows = cur.fetchall()

            regulations = []
            reg_ids = []
            for reg_id, act_title, act_year, journal_no, articles in regs_rows:
                reg_ids.append(reg_id)
                regulations.append(
                    {
                        "act_title": act_title or "",
                        "act_year": act_year,
                        "journal_no": journal_no,
                        "articles": articles or [],
                    }
                )

            enriched_regs = enrich_regulations_articles(cur, regulations, content)
            for reg_id, reg in zip(reg_ids, enriched_regs):
                mapped_articles = reg.get("articles", []) or []
                if not mapped_articles:
                    continue
                cur.execute(
                    "UPDATE judgment_regulations SET articles = %s WHERE id = %s",
                    (mapped_articles, reg_id),
                )
                updated += 1

        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Backfilled SAOS regulation articles for %d rows", updated)
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
                judgment_id = existing[0]
                cur.execute("SELECT 1 FROM judgment_chunks WHERE judgment_id = %s LIMIT 1", (judgment_id,))
                if not cur.fetchone() and j.get("content"):
                    store_judgment_chunks(cur, judgment_id, j["content"])
                if j.get("content"):
                    store_judgment_references(cur, judgment_id, j["case_number"], j["content"])
                if j.get("regulations"):
                    store_judgment_regulations(cur, judgment_id, j.get("regulations", []))
                link_references_to_existing_judgment(cur, j["case_number"], judgment_id)
                continue
            if store_judgment(cur, j):
                cur.execute("SELECT id FROM judgments WHERE case_number = %s", (j["case_number"],))
                row = cur.fetchone()
                if row:
                    judgment_id = row[0]
                    store_judgment_chunks(cur, judgment_id, j["content"])
                    if j.get("content"):
                        store_judgment_references(cur, judgment_id, j["case_number"], j["content"])
                    if j.get("regulations"):
                        regulations = enrich_regulations_articles(cur, j.get("regulations", []), j.get("content"))
                        store_judgment_regulations(cur, judgment_id, regulations)
                       
                    link_references_to_existing_judgment(cur, j["case_number"], judgment_id)
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
    parser.add_argument("--embed", action="store_true", help="Generate OpenAI embeddings after storing")
    parser.add_argument("--backfill-thesis", action="store_true", help="Backfill NULL thesis from SAOS detail endpoint")
    parser.add_argument("--backfill-thesis-llm", action="store_true", help="Backfill NULL thesis using OpenAI LLM from content")
    parser.add_argument("--backfill-summaries", action="store_true", help="Generate summaries for judgments without summary")
    parser.add_argument("--backfill-regulations", action="store_true", help="Backfill missing regulations from SAOS detail endpoint")
    parser.add_argument("--backfill-references", action="store_true", help="Backfill missing judgment references from content")
    parser.add_argument("--backfill-nsa-regulations", action="store_true", help="Backfill NSA regulations from content regex + ISAP lookup")
    parser.add_argument("--backfill-isap-acts-for-regulations", action="store_true", help="Backfill missing legal_acts/articles from ISAP for SAOS regulation titles")
    parser.add_argument("--backfill-saos-regulation-articles", action="store_true", help="Backfill empty SAOS regulation articles from judgment content + ISAP article mapping")
    args = parser.parse_args()

    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)

    if args.backfill_thesis:
        logger.info("Backfilling thesis from SAOS detail endpoint...")
        backfill_thesis_from_saos(limit=args.limit)
        return

    if args.backfill_thesis_llm:
        logger.info("Backfilling thesis via OpenAI LLM...")
        backfill_thesis_with_llm(limit=args.limit)
        return
    if args.backfill_summaries:
        logger.info("Backfilling summaries via OpenAI LLM...")
        backfill_summaries(limit=args.limit)
        return

    if args.backfill_regulations:
        logger.info("Backfilling regulations from SAOS detail endpoint...")
        backfill_regulations(limit=args.limit)
        return

    if args.backfill_references:
        logger.info("Backfilling references from judgment content...")
        backfill_references(limit=args.limit)
        return

    if args.backfill_nsa_regulations:
        logger.info("Backfilling NSA regulations from judgment content...")
        backfill_nsa_regulations(limit=args.limit)
        return

    if args.backfill_isap_acts_for_regulations:
        logger.info("Backfilling ISAP legal acts for SAOS regulation titles...")
        backfill_isap_acts_for_regulations(limit=args.limit)
        return

    if args.backfill_saos_regulation_articles:
        logger.info("Backfilling SAOS regulation articles from judgment content + ISAP mapping...")
        backfill_saos_regulation_articles(limit=args.limit)
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
