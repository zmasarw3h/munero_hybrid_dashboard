# Munero AI Assistant — P0/P1 Hardening Implementation Plan (Before Gemini Switch)

This plan implements the **P0 and P1 recommendations** from `munero-platform/AI_ASSISTANT_ARCHITECTURE_REPORT.md` **before** swapping Ollama → a hosted LLM (Gemini 2.5 Flash).

Primary goals:
- Prevent **row-level data** (fact rows) from ever being sent to a third‑party LLM by default.
- Prevent dashboard **filter value lists** (client/supplier names, etc.) from being included in LLM prompts.
- Harden SQL execution to **read-only**, **single-statement** queries.
- Ensure secrets (future Gemini API key) and sensitive payloads do not leak via **logs** or **error responses**.
- Keep the system simple and performant (no heavy SQL parsing required).

Non-goals (explicitly out of scope for this plan):
- Implementing the Gemini provider switch itself (that comes after these hardening steps).
- Adding auth / user accounts (recommended later, but not required for this hardening batch).
- Introducing heavy SQL AST dependencies unless you explicitly choose that option.

---

## 0) Ground rules & workflow

Recommended workflow:
1. Create a branch for this work: `git switch -c hardening/ai-p0-p1`
2. Implement one change at a time (each prompt below is designed to be **single-change**).
3. After each change:
   - run a quick backend syntax check: `python3 -m compileall munero-platform/backend`
   - manually sanity check chat endpoints if you have a running env
   - commit with a clear message: `git commit -am "p0: <change>"`

---

## 1) Key design decision (P0-2): Server-side filter injection with a placeholder token

### Why this is the best option (privacy + performance)

This approach avoids:
- **sending filter value lists** (PII) to the LLM prompt, and
- **blowing up prompt size** and latency when filters have many values.

It also avoids introducing a SQL parser dependency.

### The contract (v1)

**LLM must include a single placeholder token in the SQL WHERE clause:**

- Token: `__MUNERO_FILTERS__`
- The token must appear **exactly once**, outside of quoted strings.

Example:

```sql
SELECT product_name, SUM(order_price_in_aed) AS revenue
FROM fact_orders
WHERE __MUNERO_FILTERS__
GROUP BY product_name
ORDER BY revenue DESC
LIMIT 10;
```

### Server-side replacement

The backend replaces the token with a parameterized predicate built from `DashboardFilters`, e.g.:

```sql
is_test = 0
AND order_date >= :start_date
AND order_date <= :end_date
AND client_country = ANY(CAST(:countries AS text[]))
AND client_name = ANY(CAST(:clients AS text[]))
```

…and executes with a `params` dict (values never go to the LLM, only to the DB).

### Postgres list filter pattern (recommended for performance)

Use `ANY(CAST(:param AS text[]))` for list filters on Postgres. This keeps SQL compact even with many selected values.

SQLite fallback (optional):
- Use `IN (:param_0, :param_1, ...)` if you still want local SQLite support.

---

## 2) Implementation order (recommended)

### P0 (must-do before Gemini)
1. P0-1: Remove/guard any “row preview → LLM prompt” code paths (`llm_engine.py` foot-gun).
2. P0-2: Implement filter placeholder + server-side injection (no filter values in prompts).
3. P0-3: Add SQL safety validation (SELECT-only + single statement) and apply it to chat + export.
4. P0-4: Sanitize errors returned to clients (no raw exception text).
5. P0-5: Ensure DB credentials are read-only in Supabase (operational step + small doc updates).

### P1 (should-do)
6. P1-1: Centralize logging + redact sensitive payloads (start with AI endpoints).
7. P1-2: Production defaults: debug off; ensure prompt logging is off by default.
8. P1-3: Enforce DB-level statement timeout (Postgres) to stop runaway queries.

---

## 3) Change-by-change prompt templates (run one at a time)

Each template is self-contained. Copy/paste into Codex.

---

### Change 1 (P0-1): Eliminate row-level “data preview → LLM” foot-gun

**Intent**
- Ensure no code path sends `df.head()` / markdown tables / raw rows to an LLM.
- `llm_engine.py` is currently not wired into FastAPI, but is easy to reuse accidentally later.

**Files likely involved**
- `munero-platform/backend/app/services/llm_engine.py`

**Acceptance criteria**
- No LLM prompt in the repo contains `df.head`, `to_markdown`, or `to_string` for data previews.
- If `llm_engine.py` remains, it must not include row-level preview injection into any prompt.

**Codex prompt template**
```text
Implement ONLY “Change 1 (P0-1): Eliminate row-level data previews being sent to any LLM”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- Do not implement Gemini or any LLM provider changes.
- Do not change API routes.
- Do not add dependencies.

Tasks:
1) In `munero-platform/backend/app/services/llm_engine.py`, remove or hard-disable any logic that builds LLM prompts containing row-level data previews (e.g., `df.head(...)`, `.to_markdown(...)`, `.to_string(...)`) and any subsequent `llm.invoke(...)` that uses such prompts.
2) Ensure the module cannot accidentally send row samples even if someone calls it later. Prefer deleting the preview logic over “just don’t call it”.

Validation:
- Run `rg -n "df\\.head\\(|to_markdown\\(|to_string\\(" munero-platform/backend/app/services` and ensure no remaining LLM prompt includes those in a way that crosses an LLM boundary.
- Run `python3 -m compileall munero-platform/backend`.

Return:
- Summarize what changed and the files touched.
```

---

### Change 2 (P0-2): Stop sending filter value lists to the LLM (server-side injection)

**Intent**
- LLM should not see literal filter values (client names, suppliers, etc.).
- Backend must still enforce filters when executing SQL.

**Files likely involved**
- Backend:
  - `munero-platform/backend/app/services/llm_service.py`
  - `munero-platform/backend/app/api/chat.py`
  - (new) `munero-platform/backend/app/services/filter_injection.py` or similar helper
- Frontend (to keep chat filters consistent and to support export):
  - `munero-platform/frontend/components/chat/ChatSidebar.tsx`
  - `munero-platform/frontend/lib/types.ts`
  - `munero-platform/frontend/lib/api-client.ts`
  - `munero-platform/frontend/components/chat/ChatMessage.tsx`

**Acceptance criteria**
- LLM prompt text must not contain:
  - literal `clients: ...`, `suppliers: ...` value lists
  - literal country/client/brand/supplier values
- LLM prompt must require `WHERE __MUNERO_FILTERS__`.
- Backend executes SQL by replacing `__MUNERO_FILTERS__` with a parameterized predicate and passing params to the DB.
- Export CSV still works and exports the same result set as the message it belongs to (not “current filters”).

**Recommended approach**
- Use Postgres `ANY(CAST(:param AS text[]))` for list filters to keep SQL compact and fast.

**Codex prompt template**
```text
Implement ONLY “Change 2 (P0-2): Server-side filter injection so the LLM never sees filter values”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- Do not switch LLM providers (no Gemini yet).
- Do not add dependencies.
- Keep behavior the same except that filter values are no longer present in prompts and filters are enforced server-side.

Backend tasks:
1) Introduce a single placeholder token contract for the LLM: SQL must include `__MUNERO_FILTERS__` exactly once.
2) Update `munero-platform/backend/app/services/llm_service.py` prompt building:
   - Remove any prompt content that embeds literal filter values.
   - Replace it with a short “active filters summary” (counts / on/off) and the required placeholder rule:
     - “Always include: WHERE __MUNERO_FILTERS__”
3) Implement a safe filter predicate builder that returns `(sql_predicate, params_dict)` from `DashboardFilters`.
   - Must always include `is_test = 0`.
   - Must use bound params (no quoting/concatenation of values into SQL).
   - For Postgres list filters, use `= ANY(CAST(:param AS text[]))`.
4) After the LLM returns SQL (in `generate_sql` or in the chat endpoint), replace the placeholder token with the built predicate and execute using `pd.read_sql_query(..., params=params)`.
   - If the token is missing or appears multiple times, fail safely with a user-friendly message.

Frontend tasks (to keep chat/export correct):
5) Align frontend chat request filters to the backend `DashboardFilters` shape:
   - Update `munero-platform/frontend/lib/types.ts` so `ChatRequest.filters?: DashboardFilters`.
   - Update `munero-platform/frontend/components/chat/ChatSidebar.tsx` to use the existing `transformFiltersForAPI(...)` helper when sending chat requests (so `start_date/end_date` work).
6) Ensure CSV export uses the same filters used for the original message:
   - Store the exact request filters used for each assistant message in the frontend message state.
   - Update `exportChatCSV(...)` to send both `sql_query` and the stored `filters` to `POST /api/chat/export-csv`.
   - Update backend `ExportCSVRequest` in `munero-platform/backend/app/api/chat.py` to accept `filters` and to execute with params derived from those filters.

Validation:
- Ensure prompt text produced by `LLMService._build_sql_prompt` does not include literal filter values.
- Run `python3 -m compileall munero-platform/backend`.

Return:
- Summarize changes by file.
```

---

### Change 3 (P0-3): SQL safety validator (SELECT-only + single statement) for chat + export

**Intent**
- Defense-in-depth for executing LLM-generated SQL and export SQL.

**Files likely involved**
- `munero-platform/backend/app/services/llm_service.py`
- `munero-platform/backend/app/api/chat.py`
- (new helper) `munero-platform/backend/app/services/sql_safety.py`

**Acceptance criteria**
- Both chat execution and export-csv reject:
  - multiple statements
  - non-SELECT/WITH
  - DDL/DML keywords (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/GRANT/REVOKE)
- Export-csv still caps results (e.g., 10k rows).

**Codex prompt template**
```text
Implement ONLY “Change 3 (P0-3): SQL safety validator for chat + export”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- No LLM provider changes.
- No filter-injection changes (assume Change 2 exists or keep compatible with both states).
- No new dependencies.

Tasks:
1) Add a small helper module (e.g. `munero-platform/backend/app/services/sql_safety.py`) that validates SQL strings:
   - must be a single statement (allow trailing semicolon only)
   - must start with SELECT or WITH (after leading whitespace/comments)
   - must not contain DDL/DML keywords (case-insensitive)
2) Apply the validator before executing SQL in:
   - chat flow (where SQL is executed)
   - `POST /api/chat/export-csv`
3) Ensure error responses are user-friendly (don’t include raw SQL).

Validation:
- Add/adjust minimal checks so invalid SQL returns 400-like behavior (or a ChatResponse error) without crashing.
- Run `python3 -m compileall munero-platform/backend`.

Return:
- List validator rules and where it’s applied.
```

---

### Change 4 (P0-4): Sanitize errors returned to clients (no raw exception text)

**Intent**
- Prevent future Gemini SDK/API errors from leaking secrets/headers/prompt details to users.

**Files likely involved**
- `munero-platform/backend/app/api/chat.py`
- (optional) `munero-platform/backend/app/services/llm_service.py`

**Acceptance criteria**
- `ChatResponse.error` does not include raw exception strings from LLM/DB layers.
- HTTPException details from export do not include raw DB exception text.
- Server logs keep enough detail (redacted) to debug.

**Codex prompt template**
```text
Implement ONLY “Change 4 (P0-4): Sanitize errors returned to clients”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- No LLM provider changes.
- No SQL logic changes except error handling.
- No new dependencies.

Tasks:
1) In `munero-platform/backend/app/api/chat.py`, replace places that return `str(e)` or raw DB error messages in responses with:
   - a generic user-facing error message
   - an internal correlation id (short uuid) included in logs (not necessarily returned)
2) In export-csv, avoid returning raw SQLAlchemy exception text in `HTTPException(detail=...)`.
3) Log full details server-side with redaction (avoid logging API keys; avoid logging full prompts).

Validation:
- Run `python3 -m compileall munero-platform/backend`.

Return:
- Summarize changes and show example error payloads (generic).
```

---

### Change 5 (P0-5): Read-only DB role (Supabase) + doc/config touch-ups

**Intent**
- Even if the LLM generates unexpected SQL, the DB role cannot mutate data.

**Implementation**
- In Supabase SQL Editor, create a `munero_app` login role granted only SELECT on required tables.
- Update docs to instruct using a read-only `DATABASE_URL` for the backend.

**Codex prompt template (docs-only)**
```text
Implement ONLY “Change 5 (P0-5): Update docs/config to encourage a read-only DB role”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- Documentation/config updates only (no code logic changes).

Tasks:
1) Update `munero-platform/HOSTED_SUPABASE_DEPLOYMENT_RUNBOOK.md` to strongly recommend using a read-only DB role for the backend `DATABASE_URL`.
2) If helpful, update `munero-platform/backend/.env.example` with a comment about using a read-only role.

Return:
- Summarize doc changes.
```

---

### Change 6 (P1-1): Centralize logging + redact sensitive payloads (start with AI surfaces)

**Intent**
- Replace ad-hoc `print(...)` with structured logging that can be safely enabled in production.

**Files likely involved**
- `munero-platform/backend/app/api/chat.py`
- `munero-platform/backend/app/services/llm_service.py`
- (optional) `munero-platform/backend/main.py`
- (optional) dashboard endpoints that log filters (`munero-platform/backend/app/api/dashboard.py`)

**Acceptance criteria**
- No logs print literal client/supplier lists.
- No logs print full SQL by default.
- Debug logging remains possible via env flags.

**Codex prompt template**
```text
Implement ONLY “Change 6 (P1-1): Logging + redaction for AI endpoints”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- No behavior changes to endpoints besides logging.
- No new dependencies.

Tasks:
1) Introduce Python `logging` usage (module-level `logger = logging.getLogger(__name__)`).
2) Replace `print(...)` in AI chat surfaces with `logger.info/debug/warning/exception`.
3) Add small redaction helpers for:
   - filter values (don’t log lists; log counts)
   - SQL (log a hash or first N chars only)
4) Ensure logs are controlled by existing flags (`DEBUG`, `DEBUG_LOG_PROMPTS`) and defaults are safe for production.

Validation:
- Run `python3 -m compileall munero-platform/backend`.

Return:
- Summarize what is now logged at info vs debug.
```

---

### Change 7 (P1-2): Production-safe defaults (DEBUG off; prompts not logged)

**Intent**
- Make “safe” the default: production deploys shouldn’t accidentally run with debug on.

**Files likely involved**
- `munero-platform/backend/app/core/config.py`
- `munero-platform/backend/.env.example`

**Codex prompt template**
```text
Implement ONLY “Change 7 (P1-2): Production-safe debug defaults”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- Config changes only.

Tasks:
1) Set safer defaults in `munero-platform/backend/app/core/config.py`:
   - `DEBUG` default false (or clearly documented)
   - `DEBUG_LOG_PROMPTS` default false
2) Update `munero-platform/backend/.env.example` comments to reflect hosted deployment expectations.

Validation:
- Run `python3 -m compileall munero-platform/backend`.
```

---

### Change 8 (P1-3): DB-level statement timeout (Postgres)

**Intent**
- Python-level timeouts don’t stop the DB query itself; `statement_timeout` does.

**Files likely involved**
- `munero-platform/backend/app/core/config.py` (new setting)
- `munero-platform/backend/app/core/database.py` (Postgres connect args)

**Acceptance criteria**
- Postgres connections set `statement_timeout` (configurable via env).
- SQLite behavior unchanged.

**Codex prompt template**
```text
Implement ONLY “Change 8 (P1-3): Postgres statement_timeout”.

Repo: Munero_Hybrid_Dashboard/

Strict scope:
- No query logic changes beyond adding DB-level timeout configuration.
- No new dependencies.

Tasks:
1) Add a new setting in `munero-platform/backend/app/core/config.py`, e.g. `DB_STATEMENT_TIMEOUT_MS` (default 30000).
2) In `munero-platform/backend/app/core/database.py`, when dialect is Postgres, set `connect_args` so that connections enforce:
   - `statement_timeout=<DB_STATEMENT_TIMEOUT_MS>`
   (Use the Postgres `options='-c statement_timeout=...'` pattern.)
3) Confirm SQLite connect args remain unchanged.

Validation:
- Run `python3 -m compileall munero-platform/backend`.

Return:
- Summarize the new env var and defaults.
```

---

## 4) Final “ready for Gemini” checklist

Before swapping to Gemini 2.5 Flash:
- [ ] No LLM prompt contains row-level data previews.
- [ ] LLM prompt contains **no literal filter values** (only counts/on-off summaries).
- [ ] SQL execution is validated (single statement, SELECT/WITH only).
- [ ] Export endpoint cannot execute arbitrary unsafe SQL.
- [ ] Client-facing error responses are sanitized.
- [ ] Production env uses `DEBUG=false` and `DEBUG_LOG_PROMPTS=false`.
- [ ] Postgres `statement_timeout` is enabled.
- [ ] Backend uses a **read-only** Supabase DB role.

