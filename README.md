# AVENIQ

**Commerce Passport for AI Agents**

AVENIQ is a production-oriented platform designed to establish safe, policy-controlled AI-agent commerce. By implementing strict boundaries, cryptographic authorizations, and auditable pipelines, AVENIQ enables autonomous AI agents to engage in secure procurement, negotiation, and commerce operations.

---

## Core Architecture

AVENIQ enforces security through the following lifecycle flow:

```
AI PROPOSES
     ↓
AVENIQ POLICY DECIDES
     ↓
BACKEND AUTHORIZES
     ↓
BACKEND EXECUTES
     ↓
AUDIT RECORDS
```

### Stack
*   **Frontend**: React, Vite, TypeScript, Tailwind CSS
*   **Backend**: Python, FastAPI, Pydantic (using `pydantic-settings` for config validation)
*   **Database**: Supabase PostgreSQL (scaffolded migration layouts)

---

## Database & Service Layer

We have completed the database architecture setup:
*   SQL Migration schema definitions for all nine core tables under `supabase/migrations/`.
*   Active Row Level Security (RLS) configured on all tables.
*   Type-safe Pydantic v2 schemas mapping table inputs/outputs.
*   Cryptographic append-only SHA-256 hash chains for audit trails.
*   Decoupled backend service layers for products, policies, agents, requests, and audits.
*   Database seed scripts and unit testing integration.

---

## Environment Variables

An `.env.example` file is provided in the root directory. Copy `.env.example` to `.env` in the root:

```bash
cp .env.example .env
```

Define the following configuration variables inside `.env`:

```env
# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
SUPABASE_SECRET_KEY=your-supabase-secret-key

# Gemini API Configuration
GEMINI_API_KEY=your-gemini-api-key

# Razorpay Configuration
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret
RAZORPAY_WEBHOOK_SECRET=your-razorpay-webhook-secret
```

> [!WARNING]
> Keep `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, and `RAZORPAY_KEY_SECRET` strictly on the server-side. Never expose these to the React frontend.

---

## Database Migrations & Seeding

### 1. Execute SQL Migrations
Apply the initial schema to Supabase:
*   **Local Supabase CLI**:
    ```bash
    supabase db push
    ```
*   **Supabase Dashboard**: Copy the SQL contents of [20260827151600_init_schema.sql](file:///d:/AVENIQ/supabase/migrations/20260827151600_init_schema.sql) and paste them directly into the **SQL Editor** in the Supabase Dashboard, then run it.

### 2. Populate Development Seed Data
Ensure you have configured `SUPABASE_URL` and `SUPABASE_SECRET_KEY` inside `.env`, then run:
```bash
cd backend
.venv\Scripts\python app/db/seed.py
```
This inserts a default merchant (`AVENIQ_MERCHANT_001`), five commerce products, three merchant policies, and one demo AI agent.

---

## Backend Setup & Execution

### Setup Steps
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Initialize virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Execution
Run the FastAPI server:
```bash
python -m uvicorn app.main:app --port 8000 --reload
```

---

## API Routers Overview

*   **Health Check**: `GET /api/v1/health` (monitors backend and checks db connection status)
*   **Products**:
    *   `GET /api/v1/products` (list products)
    *   `GET /api/v1/products/{product_id}` (detail lookup)
*   **Policies**: `GET /api/v1/policies` (list active rulesets)
*   **Agents**: `GET /api/v1/agents` (list authorized agents)
*   **Requests**:
    *   `POST /api/v1/requests` (submit agent proposals)
    *   `GET /api/v1/requests/{request_id}` (check proposal status)
*   **Audit**:
    *   `GET /api/v1/audit/events` (get sequential ledger logs)
    *   `GET /api/v1/audit/verify` (verifies SHA-256 chain integrity)

---

## Testing

Run unit tests locally (without requiring production database credentials):
```bash
cd backend
.venv\Scripts\pytest -v
```
This runs validation suites verifying database configuration checks, product/policy/request routes, custom SHA-256 audit chaining, invalid UUID errors, missing properties, and secret leakage preventions.
