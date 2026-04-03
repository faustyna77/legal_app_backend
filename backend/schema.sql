CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    query_limit INTEGER DEFAULT 50,
    query_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS judgments (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(255) UNIQUE NOT NULL,
    court VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    date DATE NOT NULL,
    content TEXT NOT NULL,
    thesis TEXT,
    keywords TEXT[],
    doc_id VARCHAR(50) UNIQUE,
    embedding vector(1024),
    source_url TEXT,
    court_type VARCHAR(100),
    legal_area VARCHAR(100),
    source VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_judgments_embedding
    ON judgments USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_judgments_court ON judgments(court);
CREATE INDEX IF NOT EXISTS idx_judgments_date ON judgments(date DESC);
CREATE INDEX IF NOT EXISTS idx_judgments_city ON judgments(city);
CREATE INDEX IF NOT EXISTS idx_judgments_court_type ON judgments(court_type);
CREATE INDEX IF NOT EXISTS idx_judgments_legal_area ON judgments(legal_area);
CREATE INDEX IF NOT EXISTS idx_judgments_source ON judgments(source);

CREATE INDEX IF NOT EXISTS idx_articles_legal_act ON articles(legal_act_id);

CREATE TABLE IF NOT EXISTS legal_acts (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    year INTEGER,
    journal_number VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',
    embedding vector(1024),
    source_url TEXT,
    isap_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    legal_act_id INTEGER REFERENCES legal_acts(id) ON DELETE CASCADE,
    article_number VARCHAR(20) NOT NULL,
    paragraph VARCHAR(20),
    content TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS judgment_chunks (
    id SERIAL PRIMARY KEY,
    judgment_id INTEGER REFERENCES judgments(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (judgment_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_judgment_chunks_embedding
    ON judgment_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_judgment_chunks_judgment ON judgment_chunks(judgment_id);

CREATE INDEX IF NOT EXISTS idx_articles_embedding
    ON articles USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_legal_acts_embedding
    ON legal_acts USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS queries (
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

CREATE INDEX IF NOT EXISTS idx_queries_user ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_queries_sources ON queries USING gin(sources);
