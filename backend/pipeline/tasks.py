import os
import logging
import psycopg2
from celery import Celery
from pipeline.scrapers.nsa import NSAScraper
from pipeline.scrapers.isap import ISAPScraper
from pipeline.embedder import embed_table

logger = logging.getLogger(__name__)

app = Celery("legal_pipeline", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def store_judgment(judgment: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO judgments (case_number, court, date, content, thesis, source_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (case_number) DO NOTHING
            """,
            (
                judgment["case_number"],
                judgment["court"],
                judgment.get("date"),
                judgment["content"],
                judgment.get("thesis"),
                judgment.get("source_url"),
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def store_legal_act(act: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO legal_acts (title, type, source_url)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (act["title"], act["type"], act.get("source_url")),
        )
        act_id = cur.fetchone()[0]

        for article in act.get("articles", []):
            cur.execute(
                """
                INSERT INTO articles (legal_act_id, article_number, content)
                VALUES (%s, %s, %s)
                """,
                (act_id, article["number"], article["content"]),
            )

        conn.commit()
    finally:
        cur.close()
        conn.close()


@app.task
def scrape_nsa(date_from: str, date_to: str, limit: int = 500):
    scraper = NSAScraper()
    judgments = scraper.scrape_range(date_from, date_to, limit=limit)
    for j in judgments:
        store_judgment(j)
    logger.info("Stored %d NSA judgments", len(judgments))
    embed_judgments.delay()


@app.task
def scrape_isap(keyword: str, limit: int = 50):
    scraper = ISAPScraper()
    acts = scraper.search_acts(keyword, limit=limit)
    for act in acts:
        store_legal_act(act)
    logger.info("Stored %d ISAP acts", len(acts))
    embed_articles.delay()


@app.task
def embed_judgments(batch_size: int = 50):
    total = 0
    while True:
        embedded = embed_table("judgments", batch_size=batch_size)
        total += embedded
        if embedded < batch_size:
            break
    logger.info("Embedded %d judgments", total)


@app.task
def embed_articles(batch_size: int = 50):
    total = 0
    while True:
        embedded = embed_table("articles", batch_size=batch_size)
        total += embedded
        if embedded < batch_size:
            break
    logger.info("Embedded %d articles", total)
