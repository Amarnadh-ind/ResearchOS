-- ResearchOS PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ── Research Sessions ───────────────────────────────────
CREATE TABLE research_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt          TEXT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    plan            JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error           TEXT
);

CREATE INDEX idx_sessions_status ON research_sessions(status);
CREATE INDEX idx_sessions_created ON research_sessions(created_at DESC);

-- ── Sources ─────────────────────────────────────────────
CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    url             TEXT,
    title           TEXT,
    source_type     VARCHAR(32) NOT NULL, -- 'web', 'pdf', 'paper', 'book'
    content         TEXT,
    content_hash    VARCHAR(64),
    metadata        JSONB DEFAULT '{}',
    retrieved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_session ON sources(session_id);
CREATE INDEX idx_sources_hash ON sources(content_hash);

-- ── Claims ──────────────────────────────────────────────
CREATE TABLE claims (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_id       UUID REFERENCES sources(id) ON DELETE SET NULL,
    claim_text      TEXT NOT NULL,
    evidence        TEXT,
    confidence      REAL CHECK (confidence >= 0 AND confidence <= 1),
    verified        BOOLEAN DEFAULT FALSE,
    critique        TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claims_session ON claims(session_id);
CREATE INDEX idx_claims_verified ON claims(verified);

-- ── Citations ───────────────────────────────────────────
CREATE TABLE citations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_id       UUID REFERENCES sources(id) ON DELETE SET NULL,
    claim_id        UUID REFERENCES claims(id) ON DELETE SET NULL,
    citation_key    VARCHAR(64) NOT NULL,
    ieee_format     TEXT NOT NULL,
    authors         TEXT[],
    title           TEXT NOT NULL,
    publication     TEXT,
    year            INTEGER,
    doi             TEXT,
    url             TEXT,
    verified        BOOLEAN DEFAULT FALSE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_citations_session ON citations(session_id);
CREATE INDEX idx_citations_key ON citations(citation_key);

-- ── Papers ──────────────────────────────────────────────
CREATE TABLE papers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    abstract        TEXT,
    sections        JSONB NOT NULL DEFAULT '[]',
    "references"    JSONB NOT NULL DEFAULT '[]',
    format          VARCHAR(16) DEFAULT 'ieee',
    version         INTEGER DEFAULT 1,
    content_md      TEXT,
    content_latex   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_papers_session ON papers(session_id);

-- ── Agent Executions ────────────────────────────────────
CREATE TABLE agent_executions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    agent_name      VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    input_data      JSONB,
    output_data     JSONB,
    tokens_used     INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    error           TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_exec_session ON agent_executions(session_id);
CREATE INDEX idx_agent_exec_agent ON agent_executions(agent_name);

-- ── Updated_at trigger ──────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sessions_updated
    BEFORE UPDATE ON research_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_papers_updated
    BEFORE UPDATE ON papers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
