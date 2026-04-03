# Legal Research Platform - Platforma Badań Prawnych

> **Zaawansowana platforma do wyszukiwania i analizy orzeczeń sądowych oraz aktów prawnych z wykorzystaniem AI (RAG + LLM)**

Inspirowana: [Lexedit.pl](https://lexedit.pl)

---

## 📋 Spis Treści

1. [Opis Projektu](#-opis-projektu)
2. [Architektura Techniczna](#-architektura-techniczna)
3. [Stack Technologiczny](#-stack-technologiczny)
4. [Źródła Danych](#-źródła-danych)
5. [Schemat Bazy Danych](#-schemat-bazy-danych)
6. [Komponenty Systemu](#-komponenty-systemu)
7. [RAG Pipeline - Szczegółowo](#-rag-pipeline---szczegółowo)
8. [Funkcjonalności](#-funkcjonalności)
9. [Plan Implementacji](#-plan-implementacji)
10. [Instrukcje dla Deweloperów](#-instrukcje-dla-deweloperów)

---

## 🎯 Opis Projektu

### Cel

Stworzenie inteligentnej platformy prawniczej wykorzystującej najnowsze technologie AI (RAG + LLM) do:
- Szybkiego wyszukiwania orzeczeń sądowych i aktów prawnych
- Generowania szczegółowych notatek badawczych z cytatami
- Analizy precedensów prawnych
- Wyszukiwania na podstawie konkretnych artykułów i przepisów

### Główne Funkcjonalności

1. **Wyszukiwanie AI z RAG**
   - Semantyczne wyszukiwanie w bazie orzeczeń i aktów prawnych
   - Generowanie notatek badawczych (research notes) z automatycznymi cytatami
   - Odpowiedzi w języku naturalnym z pełną traceability do źródeł

2. **Baza Danych Prawnych**
   - Orzeczenia sądowe (NSA, SN, sądy powszechne)
   - Akty prawne (ustawy, rozporządzenia, dyrektywy)
   - Komentarze i doktryna prawnicza

3. **Zaawansowane Wyszukiwanie**
   - Wyszukiwanie po konkretnych artykułach (np. "art. 15 ust. 1 RODO")
   - Filtrowanie po dacie, sądzie, typie dokumentu
   - Wyszukiwanie podobnych orzeczeń (case law similarity)

4. **System Użytkownika**
   - Autentykacja i autoryzacja (NextAuth.js)
   - Historia zapytań i zapisanych dokumentów
   - Limity zapytań API (rate limiting)

### Inspiracja: Lexedit.pl

Lexedit oferuje AI-powered legal research. Nasza platforma idzie dalej poprzez:
- Open-source approach z możliwością self-hosting
- Pełna kontrola nad danymi i procesem RAG
- Integracja z publicznymi źródłami polskiego prawa
- Customizowalne modele LLM (OpenAI, Anthropic, local models)

---

## 🏗️ Architektura Techniczna

### Podział na Serwisy

Aplikacja składa się z **trzech niezależnych serwisów**:

| Serwis | Technologia | Odpowiedzialność | Hosting |
|--------|-------------|-----------------|---------|
| **Frontend + Auth** | Next.js 14 | UI, SSR, autentykacja | Vercel |
| **RAG API** | FastAPI (Python) | Embeddingi, vector search, LLM | Render / Hugging Face |
| **Data Pipeline** | Python + Celery | Scrapowanie, przetwarzanie danych | Render / Fly.io |

### Wysokopoziomowa Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                    (Next.js 14 + React + TailwindCSS)           │
│                                                                  │
│   /app/api/auth/   ──── NextAuth.js (sesja, JWT)                │
│   /app/api/user/   ──── Historia zapytań (proxy do FastAPI)     │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST API (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI - RAG SERVICE                       │
│                    (Python 3.11+, Uvicorn)                      │
│                                                                  │
│  POST /search        ──── Główny endpoint RAG                   │
│  POST /embed         ──── Generowanie embeddingów               │
│  GET  /judgments     ──── CRUD dla orzeczeń                     │
│  GET  /similar/{id}  ──── Podobne orzeczenia                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  PostgreSQL │  │   pgvector  │  │  LLM API    │
    │   Database  │  │   (Vector   │  │  (OpenAI/   │
    │  (Neon.tech)│  │    Store)   │  │  Anthropic) │
    └─────────────┘  └─────────────┘  └─────────────┘
                             ▲
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Data Pipeline  │           │  Embedding      │
    │  (Celery+Redis) │──────────▶│   Service       │
    │  Scrapery NSA,  │           │  (text-embed-3) │
    │  ISAP, SN       │           │                 │
    └─────────────────┘           └─────────────────┘
```

### Przepływ Żądania (Request Flow)

```
Użytkownik wpisuje pytanie w przeglądarce
        │
        ▼
Next.js (Frontend)
  1. Sprawdza sesję NextAuth (czy użytkownik zalogowany)
  2. Wysyła POST /api/search → proxy do FastAPI
        │
        │  REST: { query, userId, filters }
        ▼
FastAPI (RAG Service)
  3. Generuje embedding pytania (OpenAI)
  4. Szuka podobnych dokumentów (pgvector)
  5. Buduje prompt z kontekstem
  6. Wywołuje LLM API (OpenAI/Anthropic)
  7. Zwraca odpowiedź z cytatami
        │
        │  JSON: { answer, sources, latency }
        ▼
Next.js (API Route /api/search)
  8. Zapisuje zapytanie do historii (DB)
  9. Zwraca odpowiedź do frontendu
        │
        ▼
React UI renderuje odpowiedź
```

### Dlaczego taki podział?

**Next.js odpowiada za:**
- ✅ SSR/SSG → lepsze SEO dla stron orzeczeń
- ✅ Auth (NextAuth.js) → sesje, JWT, OAuth
- ✅ Routing i UI

**FastAPI odpowiada za:**
- ✅ Cały RAG pipeline (Python ma najlepszy ekosystem: LangChain, sentence-transformers)
- ✅ Operacje długotrwałe bez limitu 30s (Vercel timeout)
- ✅ Async/await z pełną kontrolą nad streamingiem
- ✅ Łatwe skalowanie niezależnie od frontendu

---

## 🛠️ Stack Technologiczny

### Frontend (Next.js)

```json
{
  "framework": "Next.js 14+ (App Router)",
  "ui-library": "React 18+",
  "styling": "TailwindCSS 3+",
  "components": "shadcn/ui + Radix UI",
  "state": "Zustand / React Query (TanStack Query)",
  "forms": "React Hook Form + Zod",
  "markdown": "react-markdown + remark",
  "auth": "NextAuth.js v5",
  "hosting": "Vercel"
}
```

**Next.js API Routes (tylko te, nie przenosić do FastAPI):**
- `/api/auth/[...nextauth]` — logowanie, rejestracja, sesja
- `/api/user/queries` — historia zapytań użytkownika (proxy lub bezpośrednio z DB)

### Backend RAG (FastAPI)

```toml
# requirements.txt
fastapi = ">=0.110"
uvicorn = ">=0.29"
pydantic = ">=2.0"
openai = ">=1.0"
anthropic = ">=0.20"
langchain = ">=0.1"
langchain-openai = ">=0.1"
psycopg2-binary = ">=2.9"
pgvector = ">=0.2"
sqlalchemy = ">=2.0"
python-jose = ">=3.3"     # JWT weryfikacja tokenów z Next.js
httpx = ">=0.27"
```

**Endpoints FastAPI:**

```
POST /search              ← Główny RAG endpoint
POST /embed               ← Generowanie embeddingów (dla pipeline)
GET  /judgments           ← Lista orzeczeń z filtrowaniem
GET  /judgments/{id}      ← Szczegóły orzeczenia
GET  /judgments/{id}/similar ← Podobne orzeczenia
GET  /articles            ← Wyszukiwanie artykułów prawnych
GET  /health              ← Health check (dla Render/HF Spaces)
```

**Hosting FastAPI:**
- **Render** (rekomendowane): darmowy tier, auto-deploy z GitHub, Docker support
- **Hugging Face Spaces**: darmowe, idealne jeśli używasz HF models dla embeddingów

### Baza Danych

**PostgreSQL 15+ z pgvector (Neon.tech)**

```sql
-- Instalacja pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Przykład kolumny z embeddings
CREATE TABLE judgments (
  id SERIAL PRIMARY KEY,
  content TEXT,
  embedding vector(1536)  -- OpenAI embeddings
);

-- Index dla szybkiego vector search
CREATE INDEX ON judgments 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Dlaczego pgvector?**
- ✅ Jedna baza (PostgreSQL) zamiast dwóch systemów
- ✅ ACID transactions
- ✅ Łatwiejsze backupy i maintenance
- ✅ Koszt-efektywność (vs Pinecone)

**Rekomendowany hosting bazy:** [Neon.tech](https://neon.tech) — darmowy tier, serverless PostgreSQL z pgvector, auto-pause.

### LLM API

1. **OpenAI** (GPT-4o, GPT-4o-mini)
   - ✅ Najlepsza jakość odpowiedzi
   - ✅ Świetne API i dokumentacja
   - ⚠️ Koszt ($0.01-0.03/1k tokens)

2. **Anthropic** (Claude 3.5 Sonnet)
   - ✅ Długi context window (200k tokens — idealny dla długich orzeczeń)
   - ✅ Bezpieczne i dokładne odpowiedzi
   - ⚠️ Koszt podobny do OpenAI

3. **Local Models** (LLaMA 3, Mixtral) — v2, po MVP
   - ✅ Brak kosztów API
   - ⚠️ Wymaga GPU

**Rekomendacja:** Start z `gpt-4o-mini` (tanie, szybkie), upgrade do `gpt-4o` lub `claude-sonnet` dla lepszej jakości.

### Embedding Models

```python
# OpenAI Embeddings
"text-embedding-3-small"  # 1536 dim, $0.02/1M tokens ← rekomendowane dla MVP
"text-embedding-3-large"  # 3072 dim, $0.13/1M tokens

# Open Source (v2, po MVP)
"intfloat/multilingual-e5-large"  # Polish support, FREE
"sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
```

### Data Scraping & Processing

**Python Stack:**
```python
requests         # HTTP requests
beautifulsoup4   # HTML parsing
scrapy           # Advanced scraping framework
pdfplumber       # PDF extraction
spacy            # NLP (Polish model: pl_core_news_lg)
langchain        # RAG utilities, text splitting
celery           # Task queue
redis            # Celery broker
```

---

## 📊 Źródła Danych

### 1. NSA - Naczelny Sąd Administracyjny

**URL:** https://orzeczenia.nsa.gov.pl/cbo/query

```python
def scrape_nsa_judgment(case_number: str):
    url = f"https://orzeczenia.nsa.gov.pl/doc/{case_number}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    return {
        'case_number': case_number,
        'date': soup.find('span', {'class': 'date'}).text,
        'court': 'NSA',
        'content': soup.find('div', {'class': 'content'}).text,
        'thesis': soup.find('div', {'class': 'thesis'}).text,
    }
```

**Rate Limiting:** 1 request/second

### 2. ISAP - Internetowy System Aktów Prawnych

**URL:** https://isap.sejm.gov.pl/

**Co zawiera:** Ustawy, Rozporządzenia, Akty prawa miejscowego, Dzienniki Ustaw

```python
def scrape_isap_act(act_url: str):
    response = requests.get(act_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    articles = []
    for article in soup.find_all('div', {'class': 'article'}):
        articles.append({
            'number': article.find('span', {'class': 'art-num'}).text,
            'content': article.find('div', {'class': 'art-content'}).text
        })
    
    return {
        'title': soup.find('h1').text,
        'type': 'ustawa',
        'articles': articles,
        'source_url': act_url
    }
```

### 3. Inne Źródła

| Źródło | URL | Opis |
|--------|-----|------|
| **Sąd Najwyższy** | https://www.sn.pl/orzecznictwo | Orzeczenia SN |
| **Trybunał Konstytucyjny** | https://trybunal.gov.pl | Wyroki TK |
| **Saos** | https://saos.org.pl | Agregator orzeczeń |

### Data Ingestion Pipeline

```
┌─────────────┐
│  Scraper    │  ─────▶  Pobiera HTML/PDF
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parser    │  ─────▶  Ekstrahuje strukturę (artykuły, tezy)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Chunker    │  ─────▶  Dzieli na fragmenty (chunk_size=1000, overlap=200)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embedder   │  ─────▶  Generuje embeddings (OpenAI text-embedding-3-small)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Database   │  ─────▶  Zapisuje do PostgreSQL + pgvector
└─────────────┘
```

---

## 🗄️ Schemat Bazy Danych

### ERD

```
┌─────────────────────┐
│       users         │
├─────────────────────┤
│ id (PK)             │
│ email               │
│ password_hash       │
│ plan                │──────┐
│ created_at          │      │
└─────────────────────┘      │ 1:N
                             ▼
┌─────────────────────┐   ┌──────────────────┐
│     judgments       │   │     queries      │
├─────────────────────┤   ├──────────────────┤
│ id (PK)             │   │ id (PK)          │
│ case_number         │   │ user_id (FK)     │
│ court               │   │ query_text       │
│ date                │   │ response         │
│ content             │   │ sources (JSONB)  │
│ thesis              │   │ latency_ms       │
│ embedding (vector)  │   │ created_at       │
│ source_url          │   └──────────────────┘
└─────────────────────┘
         │ N:M
         ▼
┌─────────────────────┐
│    legal_acts       │
├─────────────────────┤
│ id (PK)             │
│ title               │
│ type                │
│ year                │
│ journal_number      │
│ embedding (vector)  │
│ source_url          │
└─────────────────────┘
         │ 1:N
         ▼
┌─────────────────────┐
│      articles       │
├─────────────────────┤
│ id (PK)             │
│ legal_act_id (FK)   │
│ article_number      │
│ paragraph           │
│ content             │
│ embedding (vector)  │
└─────────────────────┘
```

### Szczegółowe Tabele SQL

```sql
-- 1. Użytkownicy
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  plan VARCHAR(50) DEFAULT 'free',
  query_limit INTEGER DEFAULT 50,
  query_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Orzeczenia
CREATE TABLE judgments (
  id SERIAL PRIMARY KEY,
  case_number VARCHAR(255) UNIQUE NOT NULL,
  court VARCHAR(100) NOT NULL,
  date DATE NOT NULL,
  content TEXT NOT NULL,
  thesis TEXT,
  keywords TEXT[],
  embedding vector(1536),
  source_url TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_judgments_embedding ON judgments 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_judgments_court ON judgments(court);
CREATE INDEX idx_judgments_date ON judgments(date DESC);

-- 3. Akty prawne
CREATE TABLE legal_acts (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  type VARCHAR(50) NOT NULL,
  year INTEGER,
  journal_number VARCHAR(50),
  status VARCHAR(50) DEFAULT 'active',
  embedding vector(1536),
  source_url TEXT,
  isap_id VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Artykuły aktów prawnych
CREATE TABLE articles (
  id SERIAL PRIMARY KEY,
  legal_act_id INTEGER REFERENCES legal_acts(id) ON DELETE CASCADE,
  article_number VARCHAR(20) NOT NULL,
  paragraph VARCHAR(20),
  content TEXT NOT NULL,
  embedding vector(1536),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Historia zapytań
CREATE TABLE queries (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  query_text TEXT NOT NULL,
  response TEXT,
  sources JSONB,
  model VARCHAR(50),
  tokens_used INTEGER,
  latency_ms INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queries_user ON queries(user_id);
CREATE INDEX idx_queries_created ON queries(created_at DESC);
```

---

## 🧩 Komponenty Systemu

### 1. Frontend - Next.js

#### A. Search Page

```tsx
// app/search/page.tsx
'use client';

import { useState } from 'react';
import { SearchBar } from '@/components/SearchBar';
import { ResearchNote } from '@/components/ResearchNote';
import { ResultsList } from '@/components/ResultsList';

export default function SearchPage() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    // Next.js API Route → proxy do FastAPI
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    setResults(data);
    setLoading(false);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <SearchBar onSearch={handleSearch} />
      {loading && <LoadingSpinner />}
      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <ResearchNote content={results.answer} sources={results.sources} />
          <ResultsList judgments={results.judgments} />
        </div>
      )}
    </div>
  );
}
```

#### B. Next.js API Route — proxy do FastAPI

```typescript
// app/api/search/route.ts
// Ten route NIE zawiera logiki RAG — tylko proxy + zapis historii
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/db';

const FASTAPI_URL = process.env.FASTAPI_URL; // np. https://legal-rag.onrender.com

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { query, filters } = await request.json();

  // Wywołaj FastAPI
  const ragResponse = await fetch(`${FASTAPI_URL}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Key': process.env.INTERNAL_API_KEY!, // prosty secret
    },
    body: JSON.stringify({ query, filters })
  });

  const result = await ragResponse.json();

  // Zapisz do historii (opcjonalnie tutaj lub w FastAPI)
  await db.query(
    `INSERT INTO queries (user_id, query_text, response, sources, latency_ms)
     VALUES ($1, $2, $3, $4, $5)`,
    [session.user.id, query, result.answer, JSON.stringify(result.sources), result.latency_ms]
  );

  return NextResponse.json(result);
}
```

#### C. Auth (zostaje w Next.js)

```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      credentials: { email: {}, password: {} },
      async authorize(credentials) {
        const user = await findUserByEmail(credentials.email);
        if (!user) return null;
        const isValid = await verifyPassword(credentials.password, user.password_hash);
        if (!isValid) return null;
        return { id: user.id, email: user.email, plan: user.plan };
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) token.plan = user.plan;
      return token;
    },
    async session({ session, token }) {
      session.user.plan = token.plan;
      return session;
    }
  }
});

export { handler as GET, handler as POST };
```

### 2. Backend RAG — FastAPI

#### A. Główny endpoint `/search`

```python
# app/routers/search.py
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from app.services.rag import RAGService
import time, os

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    filters: dict = {}

def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/search")
async def search(
    body: SearchRequest,
    _: None = Depends(verify_internal_key)
):
    start = time.time()
    rag = RAGService()
    result = await rag.search(body.query, body.filters)
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result
```

#### B. RAG Service

```python
# app/services/rag.py
from openai import AsyncOpenAI
from app.db import get_db_connection
import json

class RAGService:
    def __init__(self):
        self.client = AsyncOpenAI()
    
    async def search(self, query: str, filters: dict) -> dict:
        # Krok 1: Embedding pytania
        embedding = await self._embed(query)
        
        # Krok 2: Vector similarity search
        documents = await self._vector_search(embedding, filters, top_k=10)
        
        # Krok 3: Zbuduj kontekst
        context = self._build_context(documents)
        
        # Krok 4: Wygeneruj odpowiedź LLM
        answer = await self._generate(query, context)
        
        return {
            "answer": answer,
            "sources": [self._doc_to_source(d) for d in documents[:5]],
            "judgments": documents
        }
    
    async def _embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    async def _vector_search(self, embedding: list, filters: dict, top_k: int) -> list:
        conn = await get_db_connection()
        
        where_clauses = []
        params = [embedding, top_k]
        
        if filters.get("court"):
            params.append(filters["court"])
            where_clauses.append(f"court = ${len(params)}")
        
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        
        rows = await conn.fetch(f"""
            SELECT id, case_number, court, date, thesis, source_url,
                   1 - (embedding <=> $1) AS similarity
            FROM judgments
            {where_sql}
            ORDER BY embedding <=> $1
            LIMIT $2
        """, *params)
        
        return [dict(r) for r in rows]
    
    def _build_context(self, documents: list) -> str:
        parts = []
        for doc in documents[:5]:
            parts.append(
                f"[{doc['court']} {doc['case_number']} z {doc['date']}]:\n{doc.get('thesis', '')}"
            )
        return "\n\n".join(parts)
    
    async def _generate(self, query: str, context: str) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś ekspertem prawnym specjalizującym się w polskim prawie. "
                        "Odpowiadaj na pytania wyłącznie na podstawie dostarczonych orzeczeń i aktów prawnych. "
                        "Zawsze cytuj źródła podając sygnaturę i datę orzeczenia."
                    )
                },
                {
                    "role": "user",
                    "content": f"Pytanie: {query}\n\nDostępne dokumenty:\n{context}"
                }
            ]
        )
        return response.choices[0].message.content
    
    def _doc_to_source(self, doc: dict) -> dict:
        return {
            "type": "judgment",
            "id": doc["id"],
            "title": f"{doc['court']} {doc['case_number']}",
            "excerpt": doc.get("thesis", "")[:200],
            "url": doc.get("source_url", "")
        }
```

#### C. Główny plik FastAPI

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search, judgments, embed

app = FastAPI(title="Legal RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "http://localhost:3000"  # development
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["search"])
app.include_router(judgments.router, prefix="/judgments", tags=["judgments"])
app.include_router(embed.router, prefix="/embed", tags=["embed"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 3. Data Pipeline (Python + Celery)

```python
# pipeline/tasks.py
from celery import Celery
from .scrapers.nsa import NSAScraper
from .scrapers.isap import ISAPScraper
from .embedder import generate_and_store_embeddings

app = Celery('legal_pipeline', broker='redis://localhost:6379/0')

@app.task
def scrape_nsa(date_from: str, date_to: str, limit: int = 500):
    scraper = NSAScraper()
    judgments = scraper.scrape_range(date_from, date_to, limit=limit)
    for j in judgments:
        store_judgment(j)
    generate_and_store_embeddings.delay('judgments')

@app.task
def generate_and_store_embeddings(table: str):
    """Generuje embeddingi dla dokumentów bez embeddingów"""
    conn = get_db_connection()
    rows = conn.execute(
        f"SELECT id, content FROM {table} WHERE embedding IS NULL LIMIT 100"
    ).fetchall()
    
    for row in rows:
        embedding = openai_embed(row['content'])
        conn.execute(
            f"UPDATE {table} SET embedding = %s WHERE id = %s",
            (embedding, row['id'])
        )
    
    conn.commit()
```

---

## 🔄 RAG Pipeline - Szczegółowo

```
┌─────────────────────────────────────────────────────────────────┐
│                    UŻYTKOWNIK ZADAJE PYTANIE                     │
│  "Jakie są przesłanki odwołania od decyzji NSA?"                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼  [FastAPI /search]
┌─────────────────────────────────────────────────────────────────┐
│  KROK 1: EMBEDDING PYTANIA                                       │
│  - POST do OpenAI text-embedding-3-small                        │
│  - Wynik: wektor 1536 wymiarów                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  KROK 2: VECTOR SIMILARITY SEARCH (pgvector)                    │
│  - SQL: ORDER BY embedding <=> $query_vector LIMIT 10           │
│  - Opcjonalne filtry: court, date_range                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  KROK 3: CONTEXT ASSEMBLY                                        │
│  - Top 5 dokumentów jako kontekst                               │
│  - Format: [NSA I OSK 1234/20 z 2023-03-15]: "teza..."         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  KROK 4: LLM GENERATION (OpenAI/Anthropic)                      │
│  - System prompt: ekspert prawny, cytuj źródła                 │
│  - User prompt: pytanie + kontekst                              │
│  - Temperature: 0.1 (dla faktów prawnych)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  KROK 5: ZWROT DO NEXT.JS                                        │
│  JSON: { answer, sources, judgments, latency_ms }               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  KROK 6: ZAPIS HISTORII (Next.js API Route)                     │
│  - INSERT INTO queries (user_id, query_text, response, ...)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 Plan Implementacji (4 tygodnie MVP)

### Tydzień 1: Setup infrastruktury

**Cele:**
- Działający projekt Next.js z auth
- Działające FastAPI z endpointem `/health`
- Baza danych PostgreSQL + pgvector online (Neon.tech)
- Komunikacja Next.js ↔ FastAPI działa lokalnie

```bash
# 1. Next.js
npx create-next-app@latest frontend --typescript --tailwind --app
cd frontend
npm install next-auth @neondatabase/serverless pg react-query

# 2. FastAPI
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn openai pgvector psycopg2-binary sqlalchemy python-dotenv

# 3. Baza (Neon.tech — darmowe konto)
# Uruchom schema.sql

# 4. Lokalny docker dla developmentu
docker run -d --name legal-db \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 ankane/pgvector
```

**Deliverables:**
- ✅ Next.js na `localhost:3000` z logowaniem (NextAuth)
- ✅ FastAPI na `localhost:8000` z `/health` i `/search` (mock)
- ✅ Baza PostgreSQL + pgvector (Neon.tech lub lokalnie)

### Tydzień 2: Data Pipeline

**Cele:**
- Scraper NSA działa i pobiera dane
- Embeddingi generowane i zapisane w DB
- ~1000 orzeczeń w bazie

```bash
# Setup pipeline
cd backend/pipeline
pip install requests beautifulsoup4 celery redis

# Uruchom scraper (start small)
python scrape_nsa.py --date-from 2024-01-01 --limit 200

# Generuj embeddingi
python generate_embeddings.py --table judgments --batch-size 50
```

**Deliverables:**
- ✅ Działający scraper NSA (min. 500 orzeczeń)
- ✅ Embeddingi dla wszystkich dokumentów w DB
- ✅ Działające vector similarity search (przetestowane w SQL)

### Tydzień 3: RAG Pipeline + FastAPI

**Cele:**
- Endpoint `/search` zwraca realne odpowiedzi
- LLM generuje odpowiedzi z cytatami
- Komunikacja Next.js → FastAPI → odpowiedź działa end-to-end

```bash
# Test FastAPI lokalnie
uvicorn main:app --reload --port 8000

# Test endpointu
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: dev-secret" \
  -d '{"query": "przesłanki odwołania NSA"}'
```

**Deliverables:**
- ✅ `/search` endpoint z prawdziwymi odpowiedziami RAG
- ✅ Next.js proxy działa, odpowiedzi widoczne w UI
- ✅ Historia zapytań zapisuje się do DB

### Tydzień 4: Deploy + Finalizacja

**Cele:**
- FastAPI na Render lub Hugging Face Spaces
- Next.js na Vercel
- Podstawowe UI gotowe

**Deploy FastAPI na Render:**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# render.yaml
services:
  - type: web
    name: legal-rag-api
    env: docker
    dockerfilePath: ./backend/Dockerfile
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: INTERNAL_API_KEY
        sync: false
```

**Deploy Next.js na Vercel:**

```bash
npm i -g vercel
vercel --prod
# Dodaj env vars: FASTAPI_URL, NEXTAUTH_SECRET, DATABASE_URL
```

**Deliverables:**
- ✅ FastAPI live na Render/HF Spaces
- ✅ Next.js live na Vercel
- ✅ End-to-end flow działa na produkcji
- ✅ Podstawowy UI do wyszukiwania

---

## 🚀 Instrukcje dla Deweloperów

### Wymagania Systemowe

- Node.js 18+
- Python 3.11+
- Docker (opcjonalnie dla lokalnej bazy)
- Konta: Neon.tech, Vercel, Render (wszystkie mają darmowe tiery)

### Struktura Projektu

```
legal-research-app/
├── frontend/                    # Next.js 14
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── api/
│   │   │   ├── auth/[...nextauth]/   ← Auth, zostaje tu
│   │   │   ├── search/               ← Proxy do FastAPI
│   │   │   └── user/queries/         ← Historia
│   │   ├── search/
│   │   ├── judgment/[id]/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── ResearchNote.tsx
│   │   └── JudgmentCard.tsx
│   ├── lib/
│   │   ├── auth.ts              ← NextAuth config
│   │   └── db.ts                ← DB client (dla historii)
│   ├── .env.local
│   └── package.json
│
├── backend/                     # FastAPI + Python
│   ├── main.py                  ← FastAPI app
│   ├── app/
│   │   ├── routers/
│   │   │   ├── search.py        ← POST /search (RAG)
│   │   │   ├── judgments.py     ← GET /judgments
│   │   │   └── embed.py         ← POST /embed
│   │   ├── services/
│   │   │   ├── rag.py           ← RAG pipeline
│   │   │   └── embedder.py      ← Embedding service
│   │   └── db.py                ← DB connection
│   ├── pipeline/
│   │   ├── scrapers/
│   │   │   ├── nsa_scraper.py
│   │   │   └── isap_scraper.py
│   │   ├── embedder.py
│   │   ├── tasks.py             ← Celery tasks
│   │   └── requirements.txt
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
└── sql/
    ├── schema.sql
    └── seed.sql
```

### Zmienne Środowiskowe

**frontend/.env.local:**
```bash
# Auth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="generuj: openssl rand -base64 32"

# Baza (dla historii zapytań)
DATABASE_URL="postgresql://user:pass@localhost:5432/legal_research"

# FastAPI URL
FASTAPI_URL="http://localhost:8000"          # development
# FASTAPI_URL="https://legal-rag.onrender.com"  # production

# Klucz wewnętrzny (Next.js → FastAPI)
INTERNAL_API_KEY="wygeneruj-losowy-string"
```

**backend/.env:**
```bash
# OpenAI
OPENAI_API_KEY="sk-..."

# Baza danych
DATABASE_URL="postgresql://user:pass@localhost:5432/legal_research"

# Klucz wewnętrzny (weryfikacja requestów z Next.js)
INTERNAL_API_KEY="ten-sam-co-w-frontend"

# Celery (opcjonalnie)
CELERY_BROKER_URL="redis://localhost:6379/0"
```

### Lokalny Setup

```bash
# 1. Baza danych (Docker)
docker run -d --name legal-db \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=legal_research \
  -p 5432:5432 ankane/pgvector

psql postgresql://postgres:secret@localhost:5432/legal_research < sql/schema.sql

# 2. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000

# 3. FastAPI
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# → http://localhost:8000/docs

# 4. (Opcjonalnie) Celery
cd backend/pipeline
celery -A tasks worker --loglevel=info
```

---

## 💰 Koszty Operacyjne (Szacunki miesięczne dla MVP)

| Serwis | Plan | Koszt | Uwagi |
|--------|------|-------|-------|
| **Vercel** | Hobby | $0 | Frontend + Next.js API |
| **Render** | Free | $0 | FastAPI (zasypia po 15min bezczynności) |
| **Neon.tech** | Free | $0 | PostgreSQL + pgvector, 0.5GB |
| **Upstash Redis** | Free | $0 | Rate limiting (10k requests/dzień) |
| **OpenAI API** | Pay-as-you-go | $20-80 | ~5k zapytań + embeddingi |
| **RAZEM** | | **$20-80** | Dla MVP |

> **Uwaga Render Free tier:** FastAPI zasypia po 15 minutach braku ruchu i budzi się ~30 sekund. Na MVP to akceptowalne. Upgrade do paid ($7/mies.) usuwa ten problem.

---

## 📝 Notatki Końcowe

### Optymalizacje Kosztów

1. Cache'owanie odpowiedzi (identyczne pytania → cache hit, oszczędność 30-50% kosztów LLM)
2. `gpt-4o-mini` zamiast `gpt-4o` ($0.15 vs $5 per 1M tokens) — wystarczy dla MVP
3. Local embeddings po MVP (sentence-transformers — FREE vs $0.02/1M tokens OpenAI)

### Roadmap po MVP

- [ ] Streaming odpowiedzi LLM (SSE)
- [ ] Re-ranking dokumentów (cross-encoder)
- [ ] Więcej źródeł danych (SN, TK, Saos)
- [ ] PDF export notatek badawczych
- [ ] Local embeddings (sentence-transformers, multilingual)
- [ ] Graph database dla relacji między orzeczeniami
- [ ] Mobile app (React Native)

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### License

MIT License — see [LICENSE](LICENSE) for details.

---

**Powodzenia z projektem! 🚀⚖️**

*Dokument zaktualizowany: Marzec 2026*  
*Wersja: 2.0.0 — Architektura: Next.js (Frontend+Auth) + FastAPI (RAG)*

