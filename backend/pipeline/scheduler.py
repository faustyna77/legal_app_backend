import logging
import os
from datetime import date,timedelta


from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.populate_db import (
    generate_jina_embeddings,
    get_conn,
    populate_from_nsa,
    populate_from_saos,
    backfill_references,
    backfill_saos_regulation_articles,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    return int(raw)


def _embed_full_for_next_judgments(judgment_limit: int, batch_size: int = 50) -> tuple[int, int]:
    if judgment_limit <= 0:
        return 0, 0

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, content FROM judgments WHERE embedding IS NULL ORDER BY id DESC LIMIT %s",
            (judgment_limit,),
        )
        judgment_rows = cur.fetchall()
        if not judgment_rows:
            return 0, 0

        judgment_ids = [row[0] for row in judgment_rows]
        judgment_texts = [row[1][:8000] for row in judgment_rows]
        judgment_embeddings = generate_jina_embeddings(judgment_texts)

        for judgment_id, embedding in zip(judgment_ids, judgment_embeddings):
            cur.execute("UPDATE judgments SET embedding = %s WHERE id = %s", (str(embedding), judgment_id))

        chunks_embedded = 0
        cur.execute(
            "SELECT id, content FROM judgment_chunks WHERE judgment_id = ANY(%s) AND embedding IS NULL ORDER BY id",
            (judgment_ids,),
        )
        chunk_rows = cur.fetchall()
        if chunk_rows:
            for start in range(0, len(chunk_rows), batch_size):
                batch_rows = chunk_rows[start : start + batch_size]
                chunk_ids = [row[0] for row in batch_rows]
                chunk_texts = [row[1][:8000] for row in batch_rows]
                chunk_embeddings = generate_jina_embeddings(chunk_texts)
                for chunk_id, embedding in zip(chunk_ids, chunk_embeddings):
                    cur.execute("UPDATE judgment_chunks SET embedding = %s WHERE id = %s", (str(embedding), chunk_id))
                chunks_embedded += len(batch_rows)

        conn.commit()
        return len(judgment_rows), chunks_embedded
    finally:
        cur.close()
        conn.close()


def run_saos_job() -> None:
    date_from = os.getenv(
        "INGEST_SAOS_DATE_FROM",
        (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    )
    date_to = str(date.today())
    fetch_limit = _int_env("INGEST_SAOS_LIMIT", 200)
    embed_judgment_limit = _int_env("INGEST_EMBED_JUDGMENTS_LIMIT", 100)
    embed_batch_size = _int_env("INGEST_EMBED_BATCH_SIZE", 100)
    court_type = os.getenv("INGEST_SAOS_COURT_TYPE") or None
    keyword = os.getenv("INGEST_SAOS_KEYWORD") or None

    logger.info("Starting SAOS ingestion job")
    stored = populate_from_saos(
        date_from=date_from,
        date_to=date_to,
        court_type=court_type,
        keyword=keyword,
        limit=fetch_limit,
    )
    backfill_references(limit=500)
    backfill_saos_regulation_articles(limit=500)
    embedded_judgments, embedded_chunks = _embed_full_for_next_judgments(embed_judgment_limit, embed_batch_size)
    logger.info(
        "SAOS job done: stored=%d embedded_judgments=%d embedded_chunks=%d",
        stored,
        embedded_judgments,
        embedded_chunks,
    )


def run_nsa_job() -> None:
    date_from = os.getenv(
        "INGEST_NSA_DATE_FROM",
        (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    )
    
    date_to = str(date.today())
    fetch_limit = _int_env("INGEST_NSA_LIMIT", 200)
    embed_judgment_limit = _int_env("INGEST_EMBED_JUDGMENTS_LIMIT", 100)
    embed_batch_size = _int_env("INGEST_EMBED_BATCH_SIZE", 100)

    logger.info("Starting NSA ingestion job")
    stored = populate_from_nsa(date_from=date_from, date_to=date_to, limit=fetch_limit)
    backfill_references(limit=500)
   
    embedded_judgments, embedded_chunks = _embed_full_for_next_judgments(embed_judgment_limit, embed_batch_size)
    logger.info(
        "NSA job done: stored=%d embedded_judgments=%d embedded_chunks=%d",
        stored,
        embedded_judgments,
        embedded_chunks,
    )


def _safe_run(name: str, fn) -> None:
    try:
        fn()
    except Exception:
        logger.exception("Job failed: %s", name)


def main() -> None:
    saos_hours = _int_env("INGEST_SAOS_INTERVAL_HOURS", 6)
    nsa_hours = _int_env("INGEST_NSA_INTERVAL_HOURS", 12)

    scheduler = BlockingScheduler(
        executors={"default": ThreadPoolExecutor(1)},
        job_defaults={"coalesce": True, "max_instances": 1},
    )

    scheduler.add_job(lambda: _safe_run("saos", run_saos_job), "interval", hours=saos_hours, id="saos")
    scheduler.add_job(lambda: _safe_run("nsa", run_nsa_job), "interval", hours=nsa_hours, id="nsa")

    logger.info(
        "Scheduler started: SAOS every %dh, NSA every %dh, full embedding for up to %d judgments/job",
        saos_hours,
        nsa_hours,
        _int_env("INGEST_EMBED_JUDGMENTS_LIMIT", 20),
    )

    _safe_run("saos_initial", run_saos_job)
    _safe_run("nsa_initial", run_nsa_job)

    scheduler.start()


if __name__ == "__main__":
    main()
