# Struktura projektu — jak to działa?

---

## Mapa plików

```
backend/
│
├── main.py                          ← punkt startowy FastAPI (serwer)
├── schema.sql                       ← definicja tabel w bazie danych
├── requirements.txt                 ← lista bibliotek Python
├── .env / .env.example              ← klucze API i connection string do bazy
│
├── app/                             ← KOD SERWERA (FastAPI backend)
│   ├── db.py                        ← połączenie z bazą danych
│   ├── models.py                    ← definicje tabel jako klasy Python (ORM)
│   ├── routers/
│   │   ├── search.py                ← endpoint POST /search (wywołuje RAG)
│   │   ├── judgments.py             ← endpoint GET /judgments (lista orzeczeń)
│   │   └── embed.py                 ← endpoint POST /embed (generowanie embeddingów przez API)
│   └── services/
│       └── rag.py                   ← CAŁY KOD RAG (serce aplikacji)
│
└── pipeline/                        ← KOD DO ZASILANIA BAZY DANYCH
    ├── populate_db.py               ← główny skrypt do pobierania i zapisywania danych
    ├── embedder.py                  ← generowanie embeddingów przez OpenAI (stary kod)
    ├── tasks.py                     ← zadania Celery (automatyczne uruchamianie pipeline)
    └── scrapers/
        ├── saos.py                  ← pobieranie danych z SAOS API
        ├── isap.py                  ← pobieranie aktów prawnych z ISAP (scraping)
        └── nsa.py                   ← pobieranie orzeczeń NSA (scraping)
```

---

## 1. Gdzie są pobierane dane z SAOS?

**Plik:** `pipeline/scrapers/saos.py`

To jest jedyne źródło z gotowym REST API. Kod wysyła zapytania HTTP do:
```
https://www.saos.org.pl/api/search/judgments
```

Klasa `SAOSScraper` ma dwie główne metody:
- `fetch_judgments()` — pobiera listę orzeczeń (stronicowanie)
- `fetch_judgment_detail()` — pobiera szczegóły pojedynczego orzeczenia
- `scrape_range()` — łączy obie powyższe, zwraca listę słowników gotowych do zapisu

**Co zwraca dla każdego orzeczenia:**
```python
{
    "case_number": "I ACa 115/24",     # sygnatura
    "court": "Sąd Apelacyjny w ...",   # nazwa sądu
    "date": "2024-02-22",              # data
    "content": "Sygn. akt I ACa ...",  # pełna treść
    "thesis": None,                    # teza (SAOS nie zwraca przez API listy)
    "keywords": ["kredyt", ...],       # słowa kluczowe
    "source_url": "https://saos..."    # link do orzeczenia
}
```

---

## 2. Gdzie jest kod do wypełniania bazy danych?

**Główny skrypt:** `pipeline/populate_db.py`

To jest skrypt uruchamiany ręcznie z terminala. Robi trzy rzeczy:
1. Wywołuje scraper (SAOS / ISAP / NSA)
2. Zapisuje dane do bazy przez `psycopg2`
3. Opcjonalnie generuje embeddingi (flaga `--embed`)

```bash
python -m pipeline.populate_db --source saos --limit 200 --embed
```

Funkcje w tym pliku:
- `store_judgment()` — zapisuje orzeczenie do tabeli `judgments`
- `store_legal_act()` — zapisuje akt prawny do tabel `legal_acts` + `articles`
- `embed_pending_judgments()` — generuje embeddingi dla rekordów bez embeddingu
- `embed_pending_articles()` — to samo dla artykułów

**Pomocniczy plik:** `pipeline/tasks.py`

Zawiera te same operacje ale jako **zadania Celery** — służy do automatycznego uruchamiania pipeline w tle (np. co noc). Wymaga Redisa. Na razie nie jest używany — używamy `populate_db.py`.

---

## 3. Gdzie są tworzone embeddingi?

**W pipeline (ręcznie):** `pipeline/populate_db.py` — funkcja `embed_pending_judgments()`

Wywołuje Jina AI API:
```
POST https://api.jina.ai/v1/embeddings
model: jina-embeddings-v3
```

Wynik (lista 1024 liczb) zapisuje do kolumny `embedding` w tabeli `judgments` lub `articles`.

**W serwisie RAG (przy każdym zapytaniu):** `app/services/rag.py` — metoda `_embed()`

Kiedy użytkownik zadaje pytanie, RAG generuje embedding tego pytania (też przez Jina AI) i porównuje go z embeddingami w bazie metodą cosine similarity.

**Stary embedder:** `pipeline/embedder.py` — używa OpenAI zamiast Jina, nie jest aktualnie używany.

---

## 4. Gdzie są chunki?

**Tabela w bazie:** `judgment_chunks` (zdefiniowana w `schema.sql`)

**Aktualny stan:** tabela istnieje w bazie ale jest **pusta** — kod do podziału orzeczeń na chunki nie jest jeszcze napisany.

**Co to jest chunk i po co?**
Orzeczenie może mieć 10-20 stron tekstu. Zamiast robić jeden embedding dla całego dokumentu, dzielimy go na fragmenty po ~500 słów i robimy embedding każdego fragmentu osobno. Dzięki temu wyszukiwanie jest precyzyjniejsze — zamiast "ten dokument pasuje ogólnie", dostajemy "ten konkretny akapit pasuje".

Aktualnie wyszukiwanie działa na poziomie całego orzeczenia (jeden embedding na dokument).

---

## 5. Gdzie jest backend FastAPI?

**Punkt startowy:** `main.py`

Tutaj tworzona jest aplikacja FastAPI i rejestrowane są wszystkie endpointy.

**Połączenie z bazą:** `app/db.py`

Konfiguracja połączenia z PostgreSQL (Neon.tech). Zawiera dwie metody:
- `get_db()` — dla SQLAlchemy (synchroniczne)
- `get_db_connection()` — dla asyncpg (asynchroniczne, używane w RAG)

**Endpointy (routers):**

| Plik | Endpoint | Co robi |
|---|---|---|
| `app/routers/search.py` | `POST /search` | Przyjmuje pytanie, wywołuje RAG, zwraca odpowiedź |
| `app/routers/judgments.py` | `GET /judgments` | Lista orzeczeń z bazy |
| `app/routers/embed.py` | `POST /embed` | Generuje embeddingi przez Jina API |
| `main.py` | `GET /health` | Sprawdzenie czy serwer działa |

---

## 6. Gdzie jest kod RAG?

**Plik:** `app/services/rag.py`

To jest serce aplikacji. Klasa `RAGService` wykonuje cały pipeline RAG w 4 krokach:

```
Pytanie użytkownika
        ↓
[Krok 1] _embed()
Zamień pytanie na wektor 1024 liczb (Jina AI)
        ↓
[Krok 2] _search_judgments() + _search_articles()
Porównaj wektor pytania z wektorami w bazie (pgvector)
Zwróć top 5 najbardziej podobnych dokumentów
        ↓
[Krok 3] _build_context()
Złóż znalezione dokumenty w jeden tekst kontekstu
Odfiltruj dokumenty poniżej progu similarity (domyślnie 0.3)
        ↓
[Krok 4] _generate()
Wyślij pytanie + kontekst do LLM (Groq / llama-3.1-8b)
Otrzymaj odpowiedź w języku naturalnym z cytatami
        ↓
Zwróć: { answer, sources, judgments, articles }
```

---

## Przepływ danych — od zera do odpowiedzi

```
[ZASILANIE BAZY — jednorazowo]

pipeline/scrapers/saos.py
    pobiera orzeczenia z SAOS API
        ↓
pipeline/populate_db.py
    zapisuje do tabeli judgments w PostgreSQL
    generuje embeddingi przez Jina AI
    zapisuje embedding do kolumny embedding
        ↓
Baza danych (Neon.tech)
    tabela judgments: case_number, court, date, content, embedding


[ODPOWIADANIE NA PYTANIA — przy każdym zapytaniu]

Użytkownik → POST /search { "query": "...", "filters": {} }
        ↓
app/routers/search.py
    sprawdza klucz API (x-internal-key)
        ↓
app/services/rag.py — RAGService.search()
    1. embedding pytania (Jina AI)
    2. vector search w bazie (pgvector)
    3. filtrowanie po similarity threshold
    4. generowanie odpowiedzi (Groq LLM)
        ↓
Odpowiedź JSON: { answer, sources, judgments, articles }
```
