import os
import re
from datetime import date, datetime
from openai import AsyncOpenAI
from app.db import get_db_connection

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
CASE_NUMBER_QUERY_PATTERN = re.compile(r"\b[IVX]+\s+[A-ZĄĆĘŁŃÓŚŹŻ]{1,6}(?:/[A-ZĄĆĘŁŃÓŚŹŻa-z]{1,6})?\s+\d+[A-Z]?/\d{2,4}\b", re.IGNORECASE)


def _make_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _make_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _parse_filter_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _normalize_filter_values(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def _append_scalar_or_multi_filter(conditions: list[str], params: list, column_sql: str, value):
    values = _normalize_filter_values(value)
    if not values:
        return
    if len(values) == 1:
        params.append(values[0])
        conditions.append(f"{column_sql} = ${len(params)}")
    else:
        params.append(values)
        conditions.append(f"{column_sql} = ANY(${len(params)}::text[])")


class RAGService:
    def __init__(self):
        self.embed_client = _make_embed_client()
        self.llm_client = _make_llm_client()

    async def search(self, query: str, filters: dict) -> dict:
        semantic_result = await self.semantic_search(query, filters)
        judgments = semantic_result["judgments"]
        articles = semantic_result["articles"]

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
            "sources": semantic_result["sources"],
            "judgments": judgments,
            "articles": articles,
        }

    async def semantic_search(self, query: str, filters: dict) -> dict:
        case_number_hits = await self._search_by_case_number(query, filters)
        embedding = await self._embed(query)
        judgments = await self._search_judgment_chunks(embedding, filters, top_k=10)
        articles = await self._search_articles(embedding, filters, top_k=5)

        judgments = [d for d in judgments if (d.get("similarity") or 0) >= SIMILARITY_THRESHOLD]
        articles = [d for d in articles if (d.get("similarity") or 0) >= SIMILARITY_THRESHOLD]

        for hit in reversed(case_number_hits):
            if not any(j["id"] == hit["id"] for j in judgments):
                judgments.insert(0, hit)

        seen_counts = {}
        filtered_judgments = []
        for d in judgments:
            jid = d["id"]
            seen_counts[jid] = seen_counts.get(jid, 0) + 1
            if seen_counts[jid] <= 3:
                filtered_judgments.append(d)
        judgments = filtered_judgments
        judgments = await self._attach_judgment_references(judgments)

        seen_source_ids = set()
        unique_sources = []
        for d in judgments:
            if d["id"] not in seen_source_ids:
                seen_source_ids.add(d["id"])
                unique_sources.append(self._doc_to_source(d, "judgment"))

        return {
            "sources": unique_sources[:3] + [self._doc_to_source(d, "article") for d in articles[:2]],
            "judgments": judgments,
            "articles": articles,
        }

    async def _embed(self, text: str) -> list[float]:
        response = await self.embed_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=1024,
        )
        return response.data[0].embedding

    async def _search_by_case_number(self, query: str, filters: dict) -> list:
        query_case_numbers = [" ".join(m.split()) for m in CASE_NUMBER_QUERY_PATTERN.findall(query or "")]
        if not query_case_numbers:
            return []
        conn = await get_db_connection()
        try:
            conditions = []
            params: list = [query_case_numbers]
            conditions.append(f"j.case_number = ANY(${len(params)}::text[])")

            _append_scalar_or_multi_filter(conditions, params, "j.court", filters.get("court"))
            _append_scalar_or_multi_filter(conditions, params, "j.court_type", filters.get("court_type"))
            _append_scalar_or_multi_filter(conditions, params, "j.source", filters.get("source"))

            date_from = _parse_filter_date(filters.get("date_from"))
            
            if date_from:
                params.append(date_from)
                conditions.append(f"j.date >= ${len(params)}")
            date_to = _parse_filter_date(filters.get("date_to"))
            if date_to:
                params.append(date_to)
                conditions.append(f"j.date <= ${len(params)}")
            _append_scalar_or_multi_filter(conditions, params, "j.legal_area", filters.get("legal_area"))
            _append_scalar_or_multi_filter(conditions, params, "j.city", filters.get("city"))

            where_sql = "WHERE " + " AND ".join(conditions)


            rows = await conn.fetch(
                f"""
                SELECT j.id, j.case_number, j.court, j.date, j.thesis, j.source_url,
                       LEFT(COALESCE(j.content, ''), 1200) AS chunk_content,
                       1.0::float AS similarity
                FROM judgments j
                {where_sql}
                ORDER BY j.date DESC NULLS LAST
                LIMIT 5
                """,
                *params,
            )

            results = []
            for r in rows:
                d = dict(r)
                d["content"] = d.pop("chunk_content")
                results.append(d)
            return results
        finally:
            await conn.close()

    async def _search_judgment_chunks(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        try:
            conditions = ["jc.embedding IS NOT NULL"]
            params: list = [str(embedding), top_k]

            if filters.get("article"):
                article_values = _normalize_filter_values(filters["article"])
                if article_values:
                    article_conditions = []
                    for article in article_values:
                        params.append(f"%{article}%")
                        article_conditions.append(
                            f"EXISTS (SELECT 1 FROM judgment_regulations jr JOIN unnest(jr.articles) AS a ON TRUE WHERE jr.judgment_id = j.id AND a ILIKE ${len(params)})"
                        )
                    conditions.append("(" + " OR ".join(article_conditions) + ")")
            if filters.get("act_title"):
                act_title_values = _normalize_filter_values(filters["act_title"])
                if act_title_values:
                    act_title_conditions = []
                    for act_title in act_title_values:
                        params.append(f"%{act_title}%")
                        act_title_conditions.append(
                            f"EXISTS (SELECT 1 FROM judgment_regulations jr WHERE jr.judgment_id = j.id AND jr.act_title ILIKE ${len(params)})"
                        )
                    conditions.append("(" + " OR ".join(act_title_conditions) + ")")
            _append_scalar_or_multi_filter(conditions, params, "j.court", filters.get("court"))
            _append_scalar_or_multi_filter(conditions, params, "j.court_type", filters.get("court_type"))
            _append_scalar_or_multi_filter(conditions, params, "j.source", filters.get("source"))
            date_from = _parse_filter_date(filters.get("date_from"))
            if date_from:
                params.append(date_from)
                conditions.append(f"j.date >= ${len(params)}")
            date_to = _parse_filter_date(filters.get("date_to"))
            if date_to:
                params.append(date_to)
                conditions.append(f"j.date <= ${len(params)}")
            _append_scalar_or_multi_filter(conditions, params, "j.legal_area", filters.get("legal_area"))
            _append_scalar_or_multi_filter(conditions, params, "j.city", filters.get("city"))

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

    async def _attach_judgment_references(self, judgments: list[dict]) -> list[dict]:
        if not judgments:
            return judgments

        judgment_ids = list({j["id"] for j in judgments})
        conn = await get_db_connection()
        try:
            out_rows = await conn.fetch(
                """
                SELECT jr.judgment_id,
                       jr.referenced_case_number,
                       jr.referenced_judgment_id,
                       j.case_number,
                       j.court,
                       j.date,
                       j.source_url
                FROM judgment_references jr
                LEFT JOIN judgments j ON j.id = jr.referenced_judgment_id
                WHERE jr.judgment_id = ANY($1::int[])
                ORDER BY jr.judgment_id, jr.id
                """,
                judgment_ids,
            )
            in_rows = await conn.fetch(
                """
                SELECT jr.referenced_judgment_id,
                       jr.judgment_id,
                       s.case_number,
                       s.court,
                       s.date,
                       s.source_url
                FROM judgment_references jr
                JOIN judgments s ON s.id = jr.judgment_id
                WHERE jr.referenced_judgment_id = ANY($1::int[])
                ORDER BY jr.referenced_judgment_id, jr.id
                """,
                judgment_ids,
            )

            out_map: dict[int, list[dict]] = {jid: [] for jid in judgment_ids}
            for row in out_rows:
                d = dict(row)
                out_map[d["judgment_id"]].append(
                    {
                        "referenced_case_number": d["referenced_case_number"],
                        "referenced_judgment_id": d["referenced_judgment_id"],
                        "case_number": d.get("case_number"),
                        "court": d.get("court"),
                        "date": d.get("date"),
                        "source_url": d.get("source_url"),
                    }
                )

            in_map: dict[int, list[dict]] = {jid: [] for jid in judgment_ids}
            for row in in_rows:
                d = dict(row)
                in_map[d["referenced_judgment_id"]].append(
                    {
                        "judgment_id": d["judgment_id"],
                        "case_number": d["case_number"],
                        "court": d.get("court"),
                        "date": d.get("date"),
                        "source_url": d.get("source_url"),
                    }
                )

            for judgment in judgments:
                jid = judgment["id"]
                judgment["references_out"] = out_map.get(jid, [])
                judgment["references_in"] = in_map.get(jid, [])

            return judgments
        finally:
            await conn.close()

    async def _search_articles(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        try:
            conditions = ["a.embedding IS NOT NULL"]
            params: list = [str(embedding), top_k]

            if filters.get("article_number"):
                article_numbers = _normalize_filter_values(filters["article_number"])
                if article_numbers:
                    if len(article_numbers) == 1:
                        params.append(article_numbers[0])
                        conditions.append(f"a.article_number = ${len(params)}")
                    else:
                        params.append(article_numbers)
                        conditions.append(f"a.article_number = ANY(${len(params)}::text[])")
            if filters.get("legal_act_title"):
                legal_act_titles = _normalize_filter_values(filters["legal_act_title"])
                if legal_act_titles:
                    title_conditions = []
                    for legal_act_title in legal_act_titles:
                        params.append(f"%{legal_act_title}%")
                        title_conditions.append(f"la.title ILIKE ${len(params)}")
                    conditions.append("(" + " OR ".join(title_conditions) + ")")
            if filters.get("act_type"):
                act_types = _normalize_filter_values(filters["act_type"])
                if act_types:
                    if len(act_types) == 1:
                        params.append(act_types[0])
                        conditions.append(f"la.type = ${len(params)}")
                    else:
                        params.append(act_types)
                        conditions.append(f"la.type = ANY(${len(params)}::text[])")

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
        for judgment in judgments:
            thesis = judgment.get("thesis") or ""
            content = judgment.get("content") or ""
            if thesis:
                text = f"Teza: {thesis}\n\nTreść: {content}"
            else:
                text = content
            header = (
                f"[ORZECZENIE | Sygnatura: {judgment['case_number']} | "
                f"Sąd: {judgment['court']} | Data: {judgment['date']}]"
            )
            parts.append(f"{header}\n{text}")
        for art in articles:
            header = (
                f"[AKT PRAWNY | Tytuł: {art['act_title']} | "
                f"Artykuł: {art['article_number']}]"
            )
            parts.append(f"{header}\n{art['content']}")
        return "\n\n---\n\n".join(parts)

    async def _generate(self, query: str, context: str) -> str:
        print(f"MODEL: {LLM_MODEL}")
        print(f"CONTEXT FIRST 300: {context[:300]}")
        response = await self.llm_client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.0,
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś asystentem prawnym. "
                        "Odpowiadaj na pytania na podstawie dostarczonych fragmentów orzeczeń sądowych. "
                        "Każdy fragment zaczyna się od nagłówka [ORZECZENIE | Sygnatura: ... | Sąd: ... | Data: ...]. "
                        "Fragmenty mogą zaczynać się w połowie zdania — to normalne, analizuj dostępną treść. "
                        "Jeśli fragment zawiera pole 'Teza:' — użyj go jako głównej odpowiedzi. "
                        "Jeśli brak tezy — odpowiedz na podstawie treści fragmentu. "
                        "Nie korzystaj z własnej wiedzy — tylko z dostarczonych fragmentów. "
                        "Nie cytuj aktów prawnych ani sygnatur których nie ma w nagłówkach fragmentów. "
                        "Odpowiedź powinna być konkretna i zwięzła. "
                        "Podaj sygnaturę orzeczenia z nagłówka. "
                        "Jeśli żaden fragment nie dotyczy pytania, napisz: "
                        "\"Brak wystarczających danych w bazie do odpowiedzi na to pytanie.\""
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