-- Database Migration: Create agent_keys table for authentication
-- Created at: 2026-08-27 18:56:00

CREATE TABLE IF NOT EXISTS agent_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    key_hash TEXT UNIQUE NOT NULL,
    key_preview TEXT NOT NULL,
    name TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{read:passport,read:products}'::text[],
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE agent_keys ENABLE ROW LEVEL SECURITY;

-- Create index for fast hash lookup
CREATE INDEX IF NOT EXISTS idx_agent_keys_hash ON agent_keys(key_hash);
