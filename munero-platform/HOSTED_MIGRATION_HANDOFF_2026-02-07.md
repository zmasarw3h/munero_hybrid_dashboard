# Munero Hybrid Dashboard — Hosted Migration Handoff (Feb 7, 2026)

Target stack: **Vercel (Next.js frontend)** + **Render (FastAPI backend)** + **Supabase Postgres** + **Gemini 2.5 Flash**.

Security principle: **no secrets in the frontend**. The only Vercel env var should be `NEXT_PUBLIC_API_URL`. All DB + LLM secrets live in Render env vars.

---

## Current state (source of truth)

- Latest backend fix is in commit `e868c73` (“Fix Postgres bind params in pandas”).
- Backend routes:
  - `GET /health` — checks DB connectivity; **only** checks “LLM key configured” (no external call).
  - `GET /api/chat/health` — performs a real Gemini connectivity check.
  - Dashboard APIs under `POST /api/dashboard/...`

---

## Frontend (Vercel)

### Vercel install/build fixes

- Fixed Vercel install issue (React 19 vs `react-simple-maps`) via `munero-platform/frontend/.npmrc`:
  - `legacy-peer-deps=true`
- Fixed `@/` path alias build failures on Vercel:
  - `munero-platform/frontend/next.config.ts` adds an explicit `@` alias for both Turbopack and Webpack.
  - `munero-platform/frontend/tsconfig.json` sets `baseUrl` to `"."` and keeps `paths` for `@/*`.

### Vercel configuration reminder

- Vercel project root directory must be `munero-platform/frontend`.
- Vercel env var (only):
  - `NEXT_PUBLIC_API_URL=https://<your-render-backend>`

---

## Backend (Render)

### Hosted Gemini integration (no LangChain)

- Added hosted Gemini provider support in `munero-platform/backend/app/core/config.py`:
  - `LLM_PROVIDER` (default `gemini`)
  - `LLM_API_KEY` (aliases: `GEMINI_API_KEY`, `GOOGLE_API_KEY`)
  - `LLM_MODEL` (default `gemini-2.5-flash`)
  - `LLM_BASE_URL` (default `https://generativelanguage.googleapis.com/v1beta`)
  - `LLM_MAX_OUTPUT_TOKENS`, `LLM_RETRIES`, `LLM_TIMEOUT`, `SQL_TIMEOUT`
  - `LLM_SQL_REPAIR_MAX_ATTEMPTS` (default `1`) — on SQL execution errors, asks the LLM to repair the SQL once and retries
- Implemented minimal Gemini HTTP client (httpx) in `munero-platform/backend/app/services/gemini_client.py`.
- Removed LangChain deps from `munero-platform/backend/requirements.txt` (hosted path uses `httpx`).

**Model selection note**: If you still see frequent bad SQL after the Postgres-proofing fixes + auto-repair retry, try switching to a stronger model (if available in your Google project), e.g. `LLM_MODEL=gemini-2.5-pro`. Keep `gemini-2.5-flash` if reliability is good; it’s typically cheaper/faster.

### DB connection hardening

- Psycopg v3 is used (`psycopg[binary]`), and the backend normalizes DSNs:
  - `postgres://` → `postgresql://`
  - `postgresql://` → `postgresql+psycopg://` when psycopg is installed
  - See `munero-platform/backend/app/core/config.py`.
- Statement timeout support:
  - `DB_STATEMENT_TIMEOUT_MS` (default 30000) applied via Postgres connection options in `munero-platform/backend/app/core/database.py`.

### Supabase connectivity specifics (what actually worked on Render)

- Use the **Supabase pooler** from Render (direct connections caused IPv4 issues).
- Pooler hostname shard matters: the wrong shard can produce “Tenant or user not found”.
  - Example of a working pattern: `aws-1-ap-south-1.pooler.supabase.com` (your project may differ).
- Use a **read-only** login role for the backend (recommended):
  - Create role `munero_ro` (read-only grants).
  - When using the pooler, Supabase expects username format: `munero_ro.<PROJECT_REF>`.
- `.env.example` was updated to reflect the psycopg driver scheme:
  - `munero-platform/backend/.env.example`

---

## Postgres-proofing (dashboard endpoints)

After DB connectivity succeeded, some dashboard queries failed due to strict Postgres typing and SQL portability issues (e.g., numeric/date columns stored as `TEXT`, alias usage in `HAVING`/`GROUP BY`).

Fixes implemented in `munero-platform/backend/app/api/dashboard.py`:

- `_sql_numeric_expr()` — coerces numeric-like `TEXT` safely (tolerates blanks/formatting).
- `_sql_date_cast_expr()` — casts date-like values safely (tolerates blank strings).
- Rewrote invalid patterns like `HAVING total_revenue > 0` → `HAVING SUM(...) > 0`.

---

## Key diagnostic + fix (named bind placeholders)

Failure observed: Postgres syntax error `sqlstate=42601` “syntax error at or near ':'” for queries containing `:start_date` / similar placeholders.

Root cause: In the hosted psycopg setup, Pandas query execution was still sending literal `:named` parameters through to Postgres (even when wrapping with SQLAlchemy `text()`), so Postgres saw `:start_date` and errored.

Fix: execute queries via SQLAlchemy (so the dialect compiles bind params) and build the DataFrame from the result set (avoid `pandas.read_sql_query()`):

- `munero-platform/backend/app/core/database.py` adds `execute_query_df()` (uses `Connection.execute(text(sql), params)`), and `get_data()` uses it.
- `munero-platform/backend/app/services/llm_service.py` uses `execute_query_df()` for SQL execution.
- `munero-platform/backend/app/api/chat.py` uses `execute_query_df()` for CSV export.

If `sqlstate=42601` at `:` still appears after redeploy, you’re likely running an older build.

---

## Remaining known issue

- CORS preflight (`OPTIONS`) returning `400` + frontend “Failed to fetch” typically means Render `CORS_ORIGINS` is still set to localhost-only.

Render env var to set:

- `CORS_ORIGINS` to include your Vercel domain(s) **and** localhost for dev, e.g.
  - `https://<your-vercel-domain>,http://localhost:3000`
  - or JSON list form: `["https://<your-vercel-domain>","http://localhost:3000"]`
  - common gotchas: trailing slash (`https://x.vercel.app/`) or extra wrapping quotes in the env var value

Helper script:

- `munero-platform/scripts/check_cors_preflight.sh` (runs a curl `OPTIONS` probe and prints CORS headers)

---

## What to do next (checklist)

1. Redeploy Render backend from commit `e868c73` (or later).
2. Set/verify Render env vars:
   - `DATABASE_URL` (Supabase pooler, read-only login, `postgresql+psycopg://...`)
   - `LLM_API_KEY` (or `GEMINI_API_KEY`)
   - `CORS_ORIGINS` (include Vercel)
3. Verify in order:
   - `GET /health`
   - `GET /api/chat/health`
   - `POST /api/dashboard/headline` with `{}` (or minimal filters)
4. If DB errors persist, capture logs with `sqlstate` + message (now included by `munero-platform/backend/app/core/database.py`).
