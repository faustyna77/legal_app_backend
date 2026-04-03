import logging
import os
import psycopg2
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()


def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def embed_table(table: str, content_column: str = "content", batch_size: int = 50):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            f"SELECT id, {content_column} FROM {table} WHERE embedding IS NULL LIMIT %s",
            (batch_size,),
        )
        rows = cur.fetchall()

        if not rows:
            logger.info("No rows to embed in table '%s'", table)
            return 0

        for row_id, text in rows:
            if not text:
                continue
            try:
                embedding = generate_embedding(text)
                cur.execute(
                    f"UPDATE {table} SET embedding = %s WHERE id = %s",
                    (embedding, row_id),
                )
                logger.info("Embedded row %d in %s", row_id, table)
            except Exception as e:
                logger.error("Failed to embed row %d: %s", row_id, e)

        conn.commit()
        return len(rows)
    finally:
        cur.close()
        conn.close()
