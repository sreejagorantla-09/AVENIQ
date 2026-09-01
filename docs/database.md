# AVENIQ Database Architecture

This document describes the Supabase PostgreSQL database architecture designed for AVENIQ.

---

## 1. Schema Diagram & Relationships

AVENIQ's entity relationship flow maps as follows:

```
merchants
 ├── products
 ├── merchant_policies
 ├── ai_agents
 ├── agent_requests
 │      ├── policy_decisions
 │      ├── approvals
 │      └── transactions
 └── audit_events
```

---

## 2. Table Specifications

### 1. `merchants`
Represents the core tenant (business) on AVENIQ.
*   `id` (UUID): Primary key.
*   `merchant_code` (TEXT): Unique human-readable identifier (e.g. `AVENIQ_MERCHANT_001`).
*   `business_name` (TEXT): Name of the business.
*   `trust_score` (NUMERIC): Quality score (0.0 to 100.0) calculated for the merchant.
*   `status` (TEXT): Active, inactive, or suspended.

### 2. `merchant_policies`
Merchant-defined policies enforced on agent transactions.
*   `id` (UUID): Primary key.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `policy_type` (TEXT): Category of policy (`spending_limit`, `return`, `refund`, `delivery`, `inventory`, `approval`, `payment`).
*   `rules` (JSONB): Dynamic policy parameters (e.g. max spend amount).
*   `priority` (INTEGER): Precedence ordering during policy checks.

### 3. `products`
The commerce inventory items available for agents to procure.
*   `id` (UUID): Primary key.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `sku` (TEXT): Unique stock keeping unit.
*   `price` (NUMERIC): Item price.
*   `stock_quantity` (INTEGER): Available inventory quantity.
*   `metadata` (JSONB): Flexible attribute catalog (size, color, brand).

### 4. `ai_agents`
The AI agent registry representing authorized bots.
*   `id` (UUID): Primary key.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `agent_code` (TEXT): Unique agent code (e.g. `DEMO_AGENT_001`).
*   `capabilities` (JSONB): Operational constraints directly mapped to the agent.

### 5. `agent_requests`
Main proposal table capturing agent requests.
*   `id` (UUID): Primary key.
*   `agent_id` (UUID): Foreign key referencing `ai_agents`.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `raw_request` (TEXT): Raw input string/intent from the agent.
*   `structured_intent` (JSONB): Parsed intent attributes (extracted by AI).
*   `requested_action` (JSONB): Target API invocation actions.
*   `status` (TEXT): Current lifecycle state (`received`, `parsed`, `policy_check`, `approved`, `denied`, `requires_approval`, `executed`, `failed`).

### 6. `policy_decisions`
Stores the results of the deterministic policy check phase.
*   `id` (UUID): Primary key.
*   `request_id` (UUID): Foreign key referencing `agent_requests`.
*   `decision` (TEXT): Deterministic decision (`ALLOW`, `DENY`, `REQUIRE_APPROVAL`).
*   `policy_results` (JSONB): Details of which policies were evaluated and their pass/fail results.

### 7. `approvals`
Human-in-the-loop approvals for flagged requests.
*   `id` (UUID): Primary key.
*   `request_id` (UUID): Foreign key referencing `agent_requests`.
*   `status` (TEXT): Pending, approved, rejected, expired.

### 8. `transactions`
Payment and commerce logs.
*   `id` (UUID): Primary key.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `request_id` (UUID): Foreign key referencing `agent_requests` (restrictive delete).
*   `product_id` (UUID): Foreign key referencing `products` (nullified on delete).

### 9. `audit_events`
The append-only ledger tracking all actions.
*   `id` (UUID): Primary key.
*   `merchant_id` (UUID): Foreign key referencing `merchants`.
*   `previous_event_hash` (TEXT): Cryptographic hash linking to the preceding audit log.
*   `event_hash` (TEXT): SHA-256 hash of the current event data + previous hash.

---

## 3. Database Indexes

To optimize lookup speeds, explicit database indexes have been created for:
*   `products`: `merchant_id`, `sku`, `category`, and `status`.
*   `merchant_policies`: `merchant_id`.
*   `ai_agents`: `merchant_id`.
*   `agent_requests`: `agent_id`, `merchant_id`.
*   `policy_decisions`: `request_id`, `merchant_id`.
*   `approvals`: `request_id`, `merchant_id`.
*   `transactions`: `merchant_id`, `request_id`, `product_id`.
*   `audit_events`: `merchant_id`, `agent_id`, `request_id`.

---

## 4. Row Level Security (RLS) Strategy

We have enabled RLS on all 9 application tables:
```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
```
By default, we **do not create any public policies** (`USING (true)`).
*   **Backend Client**: Authenticates using the Supabase `service_role` token. This token acts as an admin bypass, allowing the FastAPI application to write and read data securely.
*   **Public Access**: Direct client-side HTTP calls to Supabase REST endpoints will fail, blocking unauthorized data access or modifications.

---

## 5. Audit Chain Hashing & Appendix Hashing

The `audit_events` table operates as a tamper-evident audit log:
1.  **Hash Generation**: Every time a new audit log is generated, the system queries the most recent event's `event_hash` to use as `previous_event_hash` (defaulting to `"0"` for the first entry).
2.  **SHA-256 Calculation**: The current hash is computed deterministically by encoding:
    `SHA256(previous_event_hash | event_type | actor_type | actor_id | entity_type | entity_id | action | decision | details_json)`
3.  **Verification**: We provide an endpoint (`GET /api/v1/audit/verify`) which recalculates hashes sequentially from index 0. If any row's payload or sequence is modified, the computed hash chain fails validation, signaling tampering.

---

## 6. Why JSONB is Used

*   **Policies (`rules`)**: Business rules vary dramatically by category. A `spending_limit` policy requires threshold values and currencies, while a `delivery` policy checks SLA shipping days. Mapping these into standard tables would require sparse, non-normalized columns. JSONB allows for flexible schema-on-read validation.
*   **Intent Extraction (`structured_intent`, `requested_action`)**: Autonomous AI agents express requests dynamically (e.g. buying items, negotiating pricing, requesting refunds). Using JSONB ensures our parsed payload structure remains flexible as Gemini parser models improve.
