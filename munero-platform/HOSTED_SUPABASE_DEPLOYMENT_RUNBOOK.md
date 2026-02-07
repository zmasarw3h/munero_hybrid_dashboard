# Munero Hybrid Dashboard — Hosted Demo Deployment Runbook (Vercel + FastAPI + Supabase + LLM API)

This document is a **self‑contained, end‑to‑end implementation plan** to migrate and run Munero as a “production‑ish” hosted demo with **minimal moving parts**:

- **Frontend**: Next.js on **Vercel**
- **Backend**: FastAPI on **Render** (recommended) or **Koyeb**
- **Database**: Managed **Postgres on Supabase**
- **LLM**: Hosted **LLM API** (API key stored server‑side only; no local Ollama)

> Note: The repo previously assumed SQLite + local Ollama. Some parts of the backend are already Postgres‑ready, but there are still a few SQLite/Ollama assumptions to remove (listed below).

For the latest migration status + what to do next, see:
- `munero-platform/HOSTED_MIGRATION_HANDOFF_2026-02-07.md`

---

## TL;DR (happy path)

1. **Supabase**: get `DATABASE_URL` → load CSVs using `munero-platform/scripts/ingest_postgres.py` → add a few indexes.
2. **Backend**: deploy `munero-platform/backend` → set env vars (`DATABASE_URL` = **read-only app user** from §1.2, `CORS_ORIGINS`, `LLM_*`) → verify `GET /health`.
3. **Frontend**: Vercel **Root Directory** = `munero-platform/frontend` → set `NEXT_PUBLIC_API_URL` → verify dashboard + chat + CSV export.

---

## Architecture (hosted demo)

Browser (Vercel / Next.js)
→ FastAPI backend (Render/Koyeb)
→ Supabase Postgres

FastAPI backend
→ LLM API (OpenAI/Anthropic/etc.)

**Security principle**: the browser never sees `DATABASE_URL` or LLM API keys.

---

## 0) Prerequisites

- You already created a **Supabase project**.
- You have the Munero CSV dataset folder (e.g. `/Users/.../Munero_CSV_Data/`).
- Backend is deployed as a long‑running service (not Vercel serverless).

---

## 1) Supabase database setup

### 1.1 Get the Postgres connection string (`DATABASE_URL`)

In Supabase dashboard:
- **Project Settings → Database → Connection string → URI**

You’ll get a DSN that looks like:

```text
postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

Notes:
- Prefer the `postgresql://` scheme. (The backend already normalizes `postgres://` → `postgresql://`.)
- Ensure SSL is required (`sslmode=require`) if it isn’t already included.

Important:
- Treat the `postgres`/admin DSN as **high privilege**. Use it only for ingestion and schema maintenance.
- For the backend service, set `DATABASE_URL` to a **dedicated read-only login** (see §1.2).

### 1.2 Create a dedicated read‑only DB user (strongly recommended)

This reduces the blast radius if an LLM ever generates something unsafe.

Run in Supabase **SQL Editor** (as the admin user):

```sql
-- 1) Create a role with read-only permissions
create role munero_readonly;
grant usage on schema public to munero_readonly;
grant select on all tables in schema public to munero_readonly;
alter default privileges in schema public grant select on tables to munero_readonly;

-- 2) Create a login role for the app and attach read-only role
create role munero_app login password 'REPLACE_WITH_STRONG_PASSWORD';
grant munero_readonly to munero_app;
```

Then use a `DATABASE_URL` that authenticates as `munero_app` (not `postgres`) in your backend deploy.

Example backend DSN (direct connection):

```text
postgresql://munero_app:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

If you use Supabase’s pooler connection string, you may need to format the username as `<ROLE>.<PROJECT_REF>` (e.g., `munero_app.<PROJECT_REF>`).

### 1.3 Load CSVs into Supabase (one-time)

Use the ingestion script already in this repo:
- `munero-platform/scripts/ingest_postgres.py`

From the **repo root**:

```bash
# Use an admin DSN here because ingestion recreates tables.
# Do NOT reuse this URL for the backend service; the backend should use the read-only app user from §1.2.
export DATABASE_URL_ADMIN="postgresql://postgres.<PROJECT_REF>:[YOUR-PASSWORD]@<POOLER_HOST>:5432/postgres?sslmode=require"
export MUNERO_CSV_DIR="/Users/zmasarweh/Documents/Munero_CSV_Data"

python3 munero-platform/scripts/ingest_postgres.py \
  --db-url "$DATABASE_URL_ADMIN" \
  --csv-dir "$MUNERO_CSV_DIR"
```

What it does:
- Loads these CSVs into tables (replaces tables if they exist):
  - `dim_customer_rows.csv` → `dim_customer`
  - `dim_products_rows.csv` → `dim_products`
  - `dim_suppliers_rows.csv` → `dim_suppliers`
  - `fact_orders_rows_converted.csv` → `fact_orders`
- Prints row counts after load.

Important:
- It uses `if_exists="replace"` (it will drop/recreate tables). Don’t run this on a DB you need to preserve.
- Keep tables in the default `public` schema (the backend queries unqualified table names).

### 1.4 Add indexes (recommended)

Run in Supabase **SQL Editor**:

```sql
create index if not exists idx_fact_orders_order_date on fact_orders (order_date);
create index if not exists idx_fact_orders_order_number on fact_orders (order_number);

create index if not exists idx_fact_orders_client_country on fact_orders (client_country);
create index if not exists idx_fact_orders_client_name on fact_orders (client_name);
create index if not exists idx_fact_orders_product_brand on fact_orders (product_brand);
create index if not exists idx_fact_orders_order_type on fact_orders (order_type);
create index if not exists idx_fact_orders_supplier_name on fact_orders (supplier_name);
```

If you later change `order_date` to a real `DATE` type, recreate the date index accordingly.

---

## 2) Backend: remaining migration work (Postgres + LLM API)

Some Postgres compatibility has already been implemented (dialect-aware SQL in dashboard endpoints, SQLAlchemy usage for chat, `DATABASE_URL` support, etc.). The remaining work to fully support hosted Postgres + LLM API is:

### 2.1 Remove remaining SQLite assumptions (code TODOs)

- `munero-platform/backend/main.py`:
  - Remove `sqlite3` usage in startup logs and `/health`.
  - Health check should test the configured SQLAlchemy `engine` (e.g., `SELECT 1`) and should not depend on `DB_FILE`.
- `munero-platform/backend/app/core/database.py`:
  - Stop printing the full `DATABASE_URL` (it can include a password). Redact or remove.
- `munero-platform/backend/app/models.py`:
  - `MetaResponse.data_source` currently defaults to `munero.sqlite`; update to a dialect/provider-neutral value.
- Local helper scripts under `munero-platform/scripts/`:
  - `setup.sh` and `start_backend.sh` currently assume SQLite + Ollama; update or treat as “local-dev only”.

### 2.2 Replace Ollama with an LLM API (code TODOs)

Current state:
- `munero-platform/backend/app/services/llm_service.py` uses `langchain_ollama.ChatOllama`.
- `munero-platform/backend/app/api/chat.py` health messaging assumes Ollama.

Target state:
- Backend calls a hosted LLM API using a server-side API key.
- Prompts should be **schema-only by default** (avoid sending raw client rows to third parties).

Recommended interface (env vars):
- `LLM_PROVIDER` (e.g., `openai`, `anthropic`, `azure_openai`, `openrouter`, etc.)
- `LLM_API_KEY` (provider key; never exposed client-side)
- `LLM_MODEL` (provider model name)
- Optional: `LLM_BASE_URL` (for OpenAI-compatible gateways)
- Keep existing timeout knobs: `LLM_TIMEOUT`, `SQL_TIMEOUT`

Additional safety rails (recommended):
- Enforce read-only SQL at multiple layers:
  - App layer: only execute queries starting with `SELECT` / `WITH` (already validated in `LLMService.generate_sql`).
  - DB layer: use a read-only database user (see §1.2).
- Confirm `munero-platform/backend/app/services/llm_engine.py` is not used for hosted summaries (it includes code patterns that can send “first 5 rows” to the LLM).

### 2.3 CORS configuration for Vercel

Set `CORS_ORIGINS` on the backend service to your frontend origins.

Recommended format: JSON list (avoids comma parsing issues):

```text
["http://localhost:3000","https://YOUR_VERCEL_DOMAIN"]
```

If you need to support Vercel Preview deployments (many changing URLs), consider a small backend change to support an `allow_origin_regex` (instead of enumerating every preview URL).

---

## 3) Deploy the backend (Render recommended)

### 3.1 Render (recommended)

Why:
- Simple container deploys
- Great logs and environment management

Steps:
1. Create a new **Web Service** in Render.
2. Select “Deploy from GitHub”.
3. Configure the service:
   - Root directory: `munero-platform/backend`
   - Runtime: Docker (uses `munero-platform/backend/Dockerfile`)
   - Health check path: `/health`
4. Set environment variables:
   - `DATABASE_URL` (Supabase Postgres; **must** use the read-only app user from §1.2, not `postgres`)
   - `CORS_ORIGINS` (see §2.3)
   - `DEBUG=false`
   - `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` (once implemented)
5. Deploy and confirm:
   - `GET https://<render-service>/health`
   - `GET https://<render-service>/docs`

Operational notes:
- If you use a free tier that sleeps when idle, first request after sleep will be slower.

### 3.2 Koyeb (alternative)

High-level steps are the same:
- Deploy `munero-platform/backend` as a Docker app
- Set the same env vars
- Verify `/health` and `/docs`

---

## 4) Deploy the frontend (Vercel)

### 4.1 Fix the “NOT_FOUND” 404

Vercel must be pointed at the Next.js root:
- Vercel project setting **Root Directory** = `munero-platform/frontend`

### 4.2 Point frontend → backend

In Vercel environment variables (Production + Preview as needed):
- `NEXT_PUBLIC_API_URL = https://<your-backend-base-url>`

The frontend uses this in:
- `munero-platform/frontend/lib/api-client.ts`

---

## 5) Verification checklist (end-to-end)

Backend:
- `GET /health` returns `database_connected=true`
- `GET /docs` loads

Dashboard APIs:
- `POST /api/dashboard/headline` with `{}` returns KPIs
- `POST /api/dashboard/trend?granularity=month` with `{}` returns points
- `GET /api/dashboard/filter-options` returns lists

Chat:
- `POST /api/chat/` with `{ "message": "...", "filters": {} }` returns `sql_query` + data
- Confirm no raw table rows are being included in LLM prompts by default (unless explicitly enabled)

CSV export:
- Use the UI export or call `POST /api/chat/export-csv` and confirm a CSV download

Frontend:
- Load Vercel site → confirm no CORS errors in browser devtools

---

## 6) Rollback / recovery

- Backend rollback: redeploy the previous Render/Koyeb revision or revert config changes (env vars).
- DB rollback:
  - Keep a baseline `pg_dump` after the initial successful ingestion.
  - Re-ingest using `ingest_postgres.py` (it replaces tables) to restore baseline quickly.
