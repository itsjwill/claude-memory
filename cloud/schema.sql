-- Claude Memory Cloud Schema
-- Supabase (Postgres + pgvector) - NEVER DELETES
--
-- Run this against your Supabase project to set up tables.
-- All memories are preserved forever in the cloud.

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- Main memories table (mirrors local SQLite, NEVER deletes)
-- =============================================================
CREATE TABLE IF NOT EXISTS memories (
  id BIGSERIAL PRIMARY KEY,
  content_hash TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  tags TEXT,                              -- Comma-separated tags
  memory_type TEXT,                       -- decision, pattern, learning, etc.
  metadata JSONB DEFAULT '{}',            -- Flexible metadata
  created_at DOUBLE PRECISION,            -- Unix timestamp (matches SQLite)
  updated_at DOUBLE PRECISION,
  embedding vector(384),                  -- pgvector for all-MiniLM-L6-v2

  -- Cloud-specific fields
  source_device TEXT NOT NULL DEFAULT 'unknown',
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  local_deleted BOOLEAN DEFAULT FALSE,    -- Marked when deleted locally
  is_summary BOOLEAN DEFAULT FALSE,       -- Summary memories (non-destructive)
  summarized_from TEXT[]                  -- Hashes this memory summarizes
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories (memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_synced ON memories (synced_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_device ON memories (source_device);
CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories (local_deleted);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories
  USING gin (to_tsvector('english', COALESCE(tags, '')));

-- Vector similarity index (IVFFlat - good for Supabase free tier)
-- NOTE: This requires at least ~100 rows to work. Create after initial sync.
-- CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
--   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- =============================================================
-- Memory associations graph
-- =============================================================
CREATE TABLE IF NOT EXISTS memory_graph (
  id BIGSERIAL PRIMARY KEY,
  source_hash TEXT NOT NULL,
  target_hash TEXT NOT NULL,
  similarity DOUBLE PRECISION,
  relationship_type TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (source_hash, target_hash)
);

CREATE INDEX IF NOT EXISTS idx_graph_source ON memory_graph (source_hash);
CREATE INDEX IF NOT EXISTS idx_graph_target ON memory_graph (target_hash);

-- =============================================================
-- Sync state tracking (per device)
-- =============================================================
CREATE TABLE IF NOT EXISTS sync_state (
  device_name TEXT PRIMARY KEY,
  last_sync_at TIMESTAMPTZ DEFAULT NOW(),
  last_sync_updated_at DOUBLE PRECISION DEFAULT 0,  -- Unix timestamp of last synced memory
  memories_synced INTEGER DEFAULT 0,
  status TEXT DEFAULT 'idle'
);

-- =============================================================
-- Deletion audit log (preserves everything forever)
-- =============================================================
CREATE TABLE IF NOT EXISTS deletion_log (
  id BIGSERIAL PRIMARY KEY,
  content_hash TEXT NOT NULL,
  original_content TEXT NOT NULL,    -- Full content preserved forever
  original_tags TEXT,
  original_type TEXT,
  original_metadata JSONB,
  reason TEXT,
  device_name TEXT,
  deleted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deletion_hash ON deletion_log (content_hash);

-- =============================================================
-- Row-Level Security (allow service_role full access)
-- =============================================================
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE deletion_log ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS, but create policies for completeness
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'memories_full_access') THEN
    CREATE POLICY memories_full_access ON memories FOR ALL USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'graph_full_access') THEN
    CREATE POLICY graph_full_access ON memory_graph FOR ALL USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'sync_full_access') THEN
    CREATE POLICY sync_full_access ON sync_state FOR ALL USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'deletion_full_access') THEN
    CREATE POLICY deletion_full_access ON deletion_log FOR ALL USING (true);
  END IF;
END $$;

-- =============================================================
-- Helper function: semantic search via pgvector
-- =============================================================
CREATE OR REPLACE FUNCTION search_memories(
  query_embedding vector(384),
  match_count INT DEFAULT 10,
  include_deleted BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
  content_hash TEXT,
  content TEXT,
  tags TEXT,
  memory_type TEXT,
  metadata JSONB,
  created_at DOUBLE PRECISION,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.content_hash,
    m.content,
    m.tags,
    m.memory_type,
    m.metadata,
    m.created_at,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM memories m
  WHERE (include_deleted OR m.local_deleted = FALSE)
    AND m.embedding IS NOT NULL
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
