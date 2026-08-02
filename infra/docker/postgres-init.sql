-- ForgeOps PostgreSQL initialisation
-- Runs once on first container start.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- for BM25-style text search
