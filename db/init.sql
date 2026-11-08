CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA IF NOT EXISTS ubs;

CREATE TABLE IF NOT EXISTS ubs.sources (
  source_id TEXT PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 50,
  published_at DATE,
  content_hash TEXT,
  last_checked_at TIMESTAMPTZ,
  last_success_at TIMESTAMPTZ,
  last_changed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'pending',
  last_error TEXT,
  chunk_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ubs.passages (
  id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES ubs.sources(source_id),
  revision_hash TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  body TEXT NOT NULL,
  embedding VECTOR(1536),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_id, revision_hash, chunk_index)
);
CREATE INDEX IF NOT EXISTS passages_active_source_idx ON ubs.passages(source_id) WHERE active;
CREATE INDEX IF NOT EXISTS passages_fts_idx ON ubs.passages USING GIN(to_tsvector('portuguese', body));
CREATE INDEX IF NOT EXISTS passages_trgm_idx ON ubs.passages USING GIN(body gin_trgm_ops);
CREATE INDEX IF NOT EXISTS passages_embedding_idx ON ubs.passages USING hnsw(embedding vector_cosine_ops) WHERE embedding IS NOT NULL;

CREATE TABLE IF NOT EXISTS ubs.ingestion_runs (
  id BIGSERIAL PRIMARY KEY,
  source_id TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  outcome TEXT NOT NULL,
  details TEXT
);
