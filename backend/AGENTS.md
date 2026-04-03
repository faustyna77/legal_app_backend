# AGENTS.md

## Kontekst projektu

**Taxenbach Backend** — aplikacja RAG (Retrieval-Augmented Generation) do badań prawnych.

- **Framework:** FastAPI
- **Baza danych:** PostgreSQL (Neon.tech) + pgvector
- **Embeddingi:** Jina AI (`jina-embeddings-v3`, 1024 dim)
- **LLM:** Groq (`llama-3.1-8b-instant`)
- **Pipeline:** Celery + Redis (opcjonalnie)

## Struktura projektu

```
backend/
├── main.py
├── schema.sql
├── requirements.txt
├── .env.example
├── app/
│   ├── db.py
│   ├── models.py
│   └── routers/
│       ├── search.py
│       ├── judgments.py
│       └── embed.py
└── pipeline/
    ├── embedder.py
    ├── tasks.py
    ├── populate_db.py          # skrypt do zasilania DB z SAOS API
    └── scrapers/
        ├── saos.py             # SAOS REST API — gotowe API
        ├── isap.py             # ISAP — scraping HTML
        └── nsa.py              # NSA — scraping HTML
```

## Zmienne środowiskowe (.env)

```
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require
INTERNAL_API_KEY=...
JINA_API_KEY=jina_...
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=jina-embeddings-v3
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000
```

## Uwagi techniczne

- `schema.sql` deklaruje `vector(1024)` (Jina) — autorytatywne
- `models.py` wyrównany do `Vector(1024)` (Judgment, LegalAct, Article)
- `embedder.py` używa OpenAI client — do wymiany na Jina jeśli potrzeba pełnego pipeline przez Celery
- RAG endpoint: `POST /search` z headerem `x-internal-key`
- NSA i ISAP używają scrapingu HTML — mogą być zawodne, SAOS REST API jest najbardziej niezawodne

## Pełny flow uruchomienia

```bash
# 1. Utwórz tabele
python -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute(open('schema.sql').read())
conn.commit(); cur.close(); conn.close()
print('Schema OK')
"

# 2. Pobierz dane
python -m pipeline.populate_db --source saos --limit 50 --embed
python -m pipeline.populate_db --source nsa --date-from 2024-01-01 --date-to 2024-03-01 --limit 20 --embed
python -m pipeline.populate_db --source isap --keyword "kodeks pracy" --limit 10 --embed

# 3. Uruchom API
uvicorn main:app --reload --port 8000

# 4. Testuj RAG
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "x-internal-key: TWOJ_INTERNAL_API_KEY" \
  -d '{"query": "wypowiedzenie umowy o pracę", "filters": {}}'
```

---
