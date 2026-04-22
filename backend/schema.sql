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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary JSONB,
    judgment_type VARCHAR(50),
    is_final VARCHAR(50),
    content_updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_judgments_embedding
    ON judgments USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_judgments_court ON judgments(court);
CREATE INDEX IF NOT EXISTS idx_judgments_date ON judgments(date DESC);
CREATE INDEX IF NOT EXISTS idx_judgments_city ON judgments(city);
CREATE INDEX IF NOT EXISTS idx_judgments_court_type ON judgments(court_type);
CREATE INDEX IF NOT EXISTS idx_judgments_legal_area ON judgments(legal_area);
CREATE INDEX IF NOT EXISTS idx_judgments_source ON judgments(source);
CREATE INDEX IF NOT EXISTS idx_judgments_judgment_type ON judgments(judgment_type);
CREATE INDEX IF NOT EXISTS idx_judgments_is_final ON judgments(is_final);
CREATE INDEX IF NOT EXISTS idx_judgments_content_updated_at ON judgments(content_updated_at DESC) WHERE content_updated_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS judgment_references (
    id SERIAL PRIMARY KEY,
    judgment_id INTEGER NOT NULL REFERENCES judgments(id) ON DELETE CASCADE,
    referenced_case_number VARCHAR(100) NOT NULL,
    referenced_judgment_id INTEGER REFERENCES judgments(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (judgment_id, referenced_case_number)
);

CREATE INDEX IF NOT EXISTS idx_judgment_references_judgment
    ON judgment_references(judgment_id);
CREATE INDEX IF NOT EXISTS idx_judgment_references_referenced
    ON judgment_references(referenced_judgment_id);
CREATE INDEX IF NOT EXISTS idx_judgment_references_case_number
    ON judgment_references(referenced_case_number);

CREATE TABLE IF NOT EXISTS judgment_regulations (
    id SERIAL PRIMARY KEY,
    judgment_id INTEGER REFERENCES judgments(id) ON DELETE CASCADE,
    act_title TEXT NOT NULL,
    act_year INTEGER,
    journal_no VARCHAR(50),
    articles TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_judgment_regulations_judgment
    ON judgment_regulations(judgment_id);

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

CREATE INDEX IF NOT EXISTS idx_articles_legal_act ON articles(legal_act_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_acts_isap_id
    ON legal_acts(isap_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_acts_title_year_journal
    ON legal_acts(lower(btrim(title)), COALESCE(year, -1), COALESCE(lower(btrim(journal_number)), ''));

CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_dedup
    ON articles(legal_act_id, lower(btrim(article_number)), COALESCE(lower(btrim(paragraph)), ''), md5(content));

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
