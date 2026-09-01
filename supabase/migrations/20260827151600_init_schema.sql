-- Database Migration: Initialize AVENIQ Core Schema
-- Created at: 2026-08-27 15:16:00

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------
-- Helper Trigger Function for updated_at Column
-- ----------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------
-- 1. Table: merchants
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_code TEXT UNIQUE NOT NULL,
    business_name TEXT NOT NULL,
    business_type TEXT,
    description TEXT,
    website_url TEXT,
    country TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    trust_score NUMERIC CHECK (trust_score >= 0.0 AND trust_score <= 100.0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trigger_update_merchants_updated_at
BEFORE UPDATE ON merchants
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------
-- 2. Table: merchant_policies
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS merchant_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    policy_type TEXT NOT NULL CHECK (policy_type IN ('spending_limit', 'return', 'refund', 'delivery', 'inventory', 'approval', 'payment')),
    policy_name TEXT NOT NULL,
    description TEXT,
    rules JSONB NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trigger_update_merchant_policies_updated_at
BEFORE UPDATE ON merchant_policies
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_merchant_policies_merchant_id ON merchant_policies(merchant_id);

-- ----------------------------------------------------
-- 3. Table: products
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    price NUMERIC NOT NULL CHECK (price >= 0.0),
    currency TEXT NOT NULL DEFAULT 'INR',
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'draft', 'archived')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trigger_update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_products_merchant_id ON products(merchant_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);

-- ----------------------------------------------------
-- 4. Table: ai_agents
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    agent_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    agent_type TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'revoked')),
    capabilities JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trigger_update_ai_agents_updated_at
BEFORE UPDATE ON ai_agents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_ai_agents_merchant_id ON ai_agents(merchant_id);

-- ----------------------------------------------------
-- 5. Table: agent_requests
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES ai_agents(id) ON DELETE RESTRICT,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    raw_request TEXT NOT NULL,
    structured_intent JSONB NOT NULL,
    requested_action JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'parsed', 'policy_check', 'approved', 'denied', 'requires_approval', 'executed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_requests_agent_id ON agent_requests(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_requests_merchant_id ON agent_requests(merchant_id);

-- ----------------------------------------------------
-- 6. Table: policy_decisions
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS policy_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES agent_requests(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'REQUIRE_APPROVAL')),
    policy_results JSONB NOT NULL,
    reason TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_request_id ON policy_decisions(request_id);
CREATE INDEX IF NOT EXISTS idx_policy_decisions_merchant_id ON policy_decisions(merchant_id);

-- ----------------------------------------------------
-- 7. Table: approvals
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES agent_requests(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    approval_type TEXT,
    requested_by TEXT,
    approved_by TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approvals_request_id ON approvals(request_id);
CREATE INDEX IF NOT EXISTS idx_approvals_merchant_id ON approvals(merchant_id);

-- ----------------------------------------------------
-- 8. Table: transactions
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES agent_requests(id) ON DELETE RESTRICT,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    amount NUMERIC NOT NULL CHECK (amount >= 0.0),
    currency TEXT NOT NULL DEFAULT 'INR',
    payment_provider TEXT NOT NULL,
    provider_transaction_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trigger_update_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_transactions_merchant_id ON transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_request_id ON transactions(request_id);
CREATE INDEX IF NOT EXISTS idx_transactions_product_id ON transactions(product_id);

-- ----------------------------------------------------
-- 9. Table: audit_events
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES ai_agents(id) ON DELETE SET NULL,
    request_id UUID REFERENCES agent_requests(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('agent', 'merchant', 'system', 'admin')),
    actor_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    decision TEXT,
    details JSONB,
    previous_event_hash TEXT,
    event_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_merchant_id ON audit_events(merchant_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_agent_id ON audit_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_request_id ON audit_events(request_id);

-- ----------------------------------------------------
-- Row Level Security (RLS) Enablement
-- ----------------------------------------------------
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
