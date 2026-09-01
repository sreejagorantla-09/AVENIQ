-- Database Migration: Create negotiation_sessions table for AI bargaining
-- Created at: 2026-08-28 06:00:00

CREATE TABLE IF NOT EXISTS negotiation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES agent_requests(id) ON DELETE CASCADE,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES ai_agents(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('active', 'accepted', 'declined')),
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    original_price NUMERIC NOT NULL,
    counter_offer_price NUMERIC NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE negotiation_sessions ENABLE ROW LEVEL SECURITY;

-- Disable RLS restrictions for local system or simplify to wide open for active merchant control plane
CREATE POLICY "Allow all operations on negotiation_sessions"
    ON negotiation_sessions FOR ALL
    USING (true)
    WITH CHECK (true);
