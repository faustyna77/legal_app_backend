import os
from openai import AsyncOpenAI
from app.db import get_db_connection

LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jina-embeddings-v3")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))


def _make_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("JINA_API_KEY"),
        base_url="https://api.jina.ai/v1",
    )


def _make_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


class RAGService:
    def __init__(self):
        self.embed_client = _make_embed_client()
        self.llm_client = _make_llm_client()

    async def search(self, query: str, filters: dict) -> dict:
        embedding = await self._embed(query)
        judgments = await self._search_judgment_chunks(embedding, filters, top_k=10)
        articles = await self._search_articles(embedding, filters, top_k=5)

        judgments = [d for d in judgments if (d.get("similarity") or 0) >= SIMILARITY_THRESHOLD]
        articles = [d for d in articles if (d.get("similarity") or 0) >= SIMILARITY_THRESHOLD]

        seen_counts = {}
        filtered_judgments = []
        for d in judgments:
            jid = d["id"]
            seen_counts[jid] = seen_counts.get(jid, 0) + 1
            if seen_counts[jid] <= 3:
                filtered_judgments.append(d)
        judgments = filtered_judgments

        if not judgments and not articles:
            return {
                "answer": "Nie znaleziono dokumentów wystarczająco powiązanych z zadanym pytaniem. Spróbuj przeformułować zapytanie lub załaduj więcej danych do bazy.",
                "sources": [],
                "judgments": [],
                "articles": [],
            }

        context = self._build_context(judgments, articles)
        answer = await self._generate(query, context)

        return {
            "answer": answer,
            "sources": [self._doc_to_source(d, "judgment") for d in judgments[:3]]
                     + [self._doc_to_source(d, "article") for d in articles[:2]],
            "judgments": judgments,
            "articles": articles,
        }

    async def _embed(self, text: str) -> list[float]:
        response = await self.embed_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    async def _search_judgment_chunks(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        try:
            conditions = ["jc.embedding IS NOT NULL"]
            params: list = [str(embedding), top_k]

            if filters.get("court"):
                params.append(filters["court"])
                conditions.append(f"j.court = ${len(params)}")
            if filters.get("source"):
                params.append(filters["source"])
                conditions.append(f"j.source = ${len(params)}")
            if filters.get("date_from"):
                params.append(filters["date_from"])
                conditions.append(f"j.date >= ${len(params)}")
            if filters.get("date_to"):
                params.append(filters["date_to"])
                conditions.append(f"j.date <= ${len(params)}")

            where_sql = "WHERE " + " AND ".join(conditions)

            rows = await conn.fetch(
                f"""
                SELECT j.id, j.case_number, j.court, j.date, j.thesis, j.source_url,
                       jc.content AS chunk_content,
                       1 - (jc.embedding <=> $1) AS similarity
                FROM judgment_chunks jc
                JOIN judgments j ON j.id = jc.judgment_id
                {where_sql}
                ORDER BY jc.embedding <=> $1
                LIMIT $2
                """,
                *params,
            )

            results = []
            for r in rows:
                d = dict(r)
                d["content"] = d.pop("chunk_content")
                results.append(d)
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results
        finally:
            await conn.close()

    async def _search_judgments(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        try:
            conditions = ["embedding IS NOT NULL"]
            params: list = [str(embedding), top_k]

            if filters.get("court"):
                params.append(filters["court"])
                conditions.append(f"court = ${len(params)}")
            if filters.get("source"):
                params.append(filters["source"])
                conditions.append(f"source = ${len(params)}")
            if filters.get("date_from"):
                params.append(filters["date_from"])
                conditions.append(f"date >= ${len(params)}")
            if filters.get("date_to"):
                params.append(filters["date_to"])
                conditions.append(f"date <= ${len(params)}")

            where_sql = "WHERE " + " AND ".join(conditions)

            rows = await conn.fetch(
                f"""
                SELECT id, case_number, court, date, thesis, content, source_url,
                       1 - (embedding <=> $1) AS similarity
                FROM judgments
                {where_sql}
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                *params,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def _search_articles(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        try:
            conditions = ["a.embedding IS NOT NULL"]
            params: list = [str(embedding), top_k]

            if filters.get("article_number"):
                params.append(filters["article_number"])
                conditions.append(f"a.article_number = ${len(params)}")
            if filters.get("legal_act_title"):
                params.append(f"%{filters['legal_act_title']}%")
                conditions.append(f"la.title ILIKE ${len(params)}")
            if filters.get("act_type"):
                params.append(filters["act_type"])
                conditions.append(f"la.type = ${len(params)}")

            where_sql = "WHERE " + " AND ".join(conditions)

            rows = await conn.fetch(
                f"""
                SELECT a.id, a.article_number, a.paragraph, a.content,
                       la.title AS act_title, la.type AS act_type, la.source_url,
                       1 - (a.embedding <=> $1) AS similarity
                FROM articles a
                JOIN legal_acts la ON la.id = a.legal_act_id
                {where_sql}
                ORDER BY a.embedding <=> $1
                LIMIT $2
                """,
                *params,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    def _build_context(self, judgments: list, articles: list) -> str:
        parts = []
        for doc in judgments:
            text = doc.get("thesis") or doc.get("content") or ""
            header = (
                f"[ORZECZENIE | Sygnatura: {doc['case_number']} | "
                f"Sąd: {doc['court']} | Data: {doc['date']}]"
            )
            parts.append(f"{header}\n{text[:2000]}")
        for art in articles:
            header = (
                f"[AKT PRAWNY | Tytuł: {art['act_title']} | "
                f"Artykuł: {art['article_number']}]"
            )
            parts.append(f"{header}\n{art['content'][:800]}")
        return "\n\n---\n\n".join(parts)

    async def _generate(self, query: str, context: str) -> str:
        print("=== CONTEXT ===")
        print(context[:800])
        print("===============")
        response = await self.llm_client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.0,
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś asystentem prawnym. "
                        "Odpowiadaj WYŁĄCZNIE na podstawie fragmentów dokumentów podanych poniżej. "
                        "ZAKAZ korzystania z własnej wiedzy, pamięci ani żadnych zewnętrznych źródeł. "
                        "ZAKAZ cytowania aktów prawnych, sygnatur, dat ani numerów Dz.U. "
                        "które nie są dosłownie wymienione w dostarczonych fragmentach. "
                        "Jeśli fragment jest obcięty lub niekompletny, opieraj się wyłącznie na tym co widać. "
                        "Pytanie może dotyczyć wielu aspektów — odpowiedz na tyle ile fragmenty pozwalają. "
                        "Nie musisz odpowiedzieć na każdy aspekt pytania jeśli nie ma go w fragmentach. "
                        "Jeśli dostarczone fragmenty nie zawierają odpowiedzi na pytanie, "
                        "napisz dokładnie: \"Brak wystarczających danych w bazie do odpowiedzi na to pytanie.\" "
                        "Podaj sygnaturę lub tytuł aktu tylko jeśli jest wprost w nagłówku fragmentu."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Pytanie: {query}\n\n"
                        f"Fragmenty dokumentów z bazy:\n\n{context}\n\n"
                        "Odpowiedz na pytanie opierając się wyłącznie na powyższych fragmentach."
                    ),
                },
            ],
        )
        return response.choices[0].message.content

    def _doc_to_source(self, doc: dict, doc_type: str) -> dict:
        if doc_type == "article":
            return {
                "type": "article",
                "id": doc["id"],
                "title": f"{doc['act_title']} art. {doc['article_number']}",
                "excerpt": doc.get("content", "")[:200],
                "url": doc.get("source_url", ""),
            }
        return {
            "type": "judgment",
            "id": doc["id"],
            "title": f"{doc['court']} {doc['case_number']}",
            "excerpt": (doc.get("thesis") or doc.get("content") or "")[:200],
            "url": doc.get("source_url", ""),
        }
