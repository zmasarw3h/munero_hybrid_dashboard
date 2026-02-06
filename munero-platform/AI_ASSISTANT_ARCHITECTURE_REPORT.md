# Munero Backend AI Assistant — Workflow & Data Exposure Report (As-Is)

Scope: **`munero-platform/backend/`** FastAPI backend (no Gemini switch; no code changes).  
Method: repo-wide `rg` + targeted file inspection with stable line numbers (`nl -ba`).

---

## A) Executive Summary

- The **only AI-chat endpoint wired into FastAPI** is `POST /api/chat/` (`munero-platform/backend/app/api/chat.py:64`), mounted in `munero-platform/backend/main.py:34-36`.
- The **current “live” chat workflow** sends **(a) user message**, **(b) dashboard filter values**, and **(c) a static schema description** to the LLM to generate SQL, then runs that SQL against the DB and uses **non‑LLM** SmartRender heuristics to decide chart + answer text.
- In the live chat flow, **DB query results are not sent back into the LLM** (no “summarize df/head” step); the LLM is used **only for SQL generation** (`munero-platform/backend/app/services/llm_service.py:395-432`).
- A second module, `munero-platform/backend/app/services/llm_engine.py`, contains LLM calls that **do send row-level data previews** (`df.head(5)`) and executed SQL back to the LLM (`munero-platform/backend/app/services/llm_engine.py:654-692`) — **but it is not currently imported/used by `main.py` routers**. It is still a major **future foot‑gun** if reused.
- **Biggest third‑party leakage risk when swapping Ollama → Gemini**: filter values (client names, suppliers, etc.) are embedded verbatim into prompts (`munero-platform/backend/app/services/llm_service.py:151-213`, `:214-310`).
- **Biggest “silent” leakage risk today** (even before Gemini): backend uses many unconditional `print(...)` statements; dashboard endpoints log full filter payloads (`filters.model_dump()`) without a debug gate (e.g., `munero-platform/backend/app/api/dashboard.py:185`).
- **Export exfil path**: `POST /api/chat/export-csv` executes caller-provided SQL with minimal rewriting and returns full CSV (`munero-platform/backend/app/api/chat.py:369-423`). If this endpoint is reachable, it can be used to exfiltrate far beyond intended “AI chat” outputs.
- Current DB URL logging is **password‑redacted** via SQLAlchemy `hide_password=True` (`munero-platform/backend/app/core/database.py:15-23`, `munero-platform/backend/main.py:38-52`), but other sensitive values (filters/SQL/error strings) can still land in logs or responses.

---

## B) Components & Entry Points

### FastAPI wiring

- Router mounting:
  - `app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])` (`munero-platform/backend/main.py:34-36`)

### AI assistant endpoints (current backend)

#### 1) `POST /api/chat/` — main chat endpoint

- Handler: `chat_with_data(request: ChatRequest)` (`munero-platform/backend/app/api/chat.py:64-281`)
- Receives from frontend (Pydantic):
  - `message: str` (1–500 chars) (`munero-platform/backend/app/models.py:181-186`)
  - `filters: DashboardFilters | null` (`munero-platform/backend/app/models.py:26-41`, `:181-186`)
  - `conversation_id: str | null` (currently **unused**) (`munero-platform/backend/app/models.py:181-186`, and no usage in code)
- Calls next:
  1. `LLMService.generate_sql(message, filters)` (`munero-platform/backend/app/api/chat.py:140`) → LLM prompt build + `ChatOllama.invoke(...)` (`munero-platform/backend/app/services/llm_service.py:214-337`)
  2. `LLMService.execute_sql(sql_query)` (`munero-platform/backend/app/api/chat.py:174`) → `pd.read_sql_query(...)` (`munero-platform/backend/app/services/llm_service.py:434-463`)
  3. `SmartRenderService.determine_chart_type(df, message)` (`munero-platform/backend/app/api/chat.py:225`) (heuristics; no LLM) (`munero-platform/backend/app/services/smart_render.py:44`)
  4. `SmartRenderService.prepare_data_for_chart(df, chart_config)` (`munero-platform/backend/app/api/chat.py:233`) (aggregation + row limiting) (`munero-platform/backend/app/services/smart_render.py:213-268`)
  5. `SmartRenderService.format_answer_text(df, message, chart_config)` (`munero-platform/backend/app/api/chat.py:244`) (heuristics; no LLM) (`munero-platform/backend/app/services/smart_render.py:270-334`)
- Returns to frontend:
  - `ChatResponse(answer_text, sql_query, data, chart_config, row_count, warnings, error)` (`munero-platform/backend/app/models.py:205-217`; returned at `munero-platform/backend/app/api/chat.py:258-266`)

#### 2) `GET /api/chat/health` — chat health endpoint

- Handler: `chat_health()` (`munero-platform/backend/app/api/chat.py:284-333`)
- Receives: no body
- Calls next:
  - `LLMService.check_connection()` which does `GET {OLLAMA_BASE_URL}/api/tags` (`munero-platform/backend/app/services/llm_service.py:78-96`)
- Returns:
  - `status`, `llm_available`, `model`, `base_url`, plus hints on `ollama pull/serve` (`munero-platform/backend/app/api/chat.py:307-332`)

#### 3) `POST /api/chat/export-csv` — export endpoint

- Handler: `export_csv(request: ExportCSVRequest)` (`munero-platform/backend/app/api/chat.py:369-427`)
- Receives:
  - `sql_query: str` and optional `filename` (`munero-platform/backend/app/api/chat.py:38-42`)
- Calls next:
  - Regex strips `LIMIT <n>` then appends `LIMIT 10000` (`munero-platform/backend/app/api/chat.py:389-394`)
  - Executes **caller-provided SQL**: `pd.read_sql_query(sql_query, engine)` (`munero-platform/backend/app/api/chat.py:396`)
- Returns:
  - Streaming CSV download with **all returned rows** up to 10,000 (`munero-platform/backend/app/api/chat.py:415-422`)

---

## C) Call Graph / Workflow

### Step-by-step (live `POST /api/chat/`)

1. Browser → `POST /api/chat/` with `{ message, filters }` (`munero-platform/backend/app/api/chat.py:64-132`).
2. FastAPI constructs `filters = request.filters or DashboardFilters()` (`munero-platform/backend/app/api/chat.py:130-132`).
3. Backend builds an LLM prompt:
   - Static schema text (`LLMService.get_database_schema`) (`munero-platform/backend/app/services/llm_service.py:97-149`)
   - Human-readable filter context + literal SQL WHERE clause containing filter values (`munero-platform/backend/app/services/llm_service.py:151-213`)
   - User question appended (`munero-platform/backend/app/services/llm_service.py:250-309`)
4. Backend sends prompt to LLM via LangChain `ChatOllama.invoke(prompt)` (`munero-platform/backend/app/services/llm_service.py:325`).
5. Backend extracts SQL and executes it against DB (`munero-platform/backend/app/services/llm_service.py:425-463`).
6. Backend runs SmartRender heuristics on the DataFrame to pick chart type and cap/aggregate data for frontend (`munero-platform/backend/app/services/smart_render.py:44`, `:213-268`).
7. Backend returns `ChatResponse` including:
   - `answer_text` (heuristic), `sql_query`, and **row data** (limited for display), plus `chart_config` (`munero-platform/backend/app/api/chat.py:258-266`).

### ASCII sequence diagram (live chat flow)

```
Browser
  |  POST /api/chat {message, filters}
  v
FastAPI (chat_with_data)
  |  build prompt = schema + filters + question
  v
LLM (ChatOllama.invoke)
  |  returns SQL text
  v
DB (pd.read_sql_query / SQLAlchemy engine)
  |  returns DataFrame
  v
SmartRender (determine_chart_type + prepare_data + format_answer_text)
  |  returns answer_text + chart_config + data_list
  v
Browser (ChatResponse JSON)
```

---

## D) LLM Invocation Inventory (MOST IMPORTANT)

This inventory lists **every LLM invocation present in the backend codebase** and the **exact prompt inputs** at the call site.

### 1) Live SQL generation (used by `POST /api/chat/`)

- Invocation:
  - `ChatOllama.invoke(prompt)` inside `LLMService._invoke_llm_with_timeout` (`munero-platform/backend/app/services/llm_service.py:311-337`, call at `:325`)
- Prompt/template source:
  - Built in `LLMService._build_sql_prompt(question, filters)` (`munero-platform/backend/app/services/llm_service.py:214-310`)
  - Schema text source is a hard-coded string in `LLMService.get_database_schema()` (`munero-platform/backend/app/services/llm_service.py:97-149`)
- Data elements included in the prompt (exactly, by construction):
  - **User message text**: appended verbatim at `NOW ANSWER THIS QUESTION:\n{question}` (`munero-platform/backend/app/services/llm_service.py:304-306`)
  - **Schema / column names**: full “DATABASE SCHEMA” block (columns + FK references) (`munero-platform/backend/app/services/llm_service.py:104-149`)
  - **Filter values** (dates + lists) in two ways:
    - Human-readable bullet context (e.g., `"Countries: ..."`), built by `build_filter_clause` (`munero-platform/backend/app/services/llm_service.py:167-209`)
    - A literal SQL `WHERE ...` clause that embeds the selected values into `IN ('...')` and `BETWEEN '...','...'` (`munero-platform/backend/app/services/llm_service.py:172-207`, assembled at `:210-212`, injected at `:241-248`)
  - **DB dialect hint** (`SQLite` vs `PostgreSQL`) and dialect-specific month grouping expression (`strftime` vs `to_char`) (`munero-platform/backend/app/services/llm_service.py:228-233`)
  - **Example queries** that include the computed `where_clause` (`munero-platform/backend/app/services/llm_service.py:282-303`)
- Row-level data included?
  - **No**. The prompt is constructed solely from static schema text + user message + filter values (no DB query results are read before the LLM call in this flow).
- Prompt/response logging behavior:
  - Prompt is **not printed** by `LLMService`.
  - The chat endpoint logs the user message only when `DEBUG_LOG_PROMPTS` is true (`munero-platform/backend/app/api/chat.py:120-123`).
  - The chat endpoint logs a **SQL snippet** (first 100 chars) when `DEBUG_LOG_PROMPTS` is true (`munero-platform/backend/app/api/chat.py:141-143`) — this can still contain filter values/PII if they appear early in the SQL.

### 2) **Dormant** LLM usage in `llm_engine.py` (not wired to FastAPI routers)

`munero-platform/backend/app/services/llm_engine.py` contains an alternative pipeline (`process_chat_query_async`, `_handle_data_query`) that calls the LLM multiple times. This file is **not imported by `munero-platform/backend/main.py`**, so these calls are not reachable through the current FastAPI app wiring. However, the code exists and is high-risk if reintroduced.

#### 2a) Driver analysis narration (LLM sees dimension entity names)

- Invocation:
  - `llm.invoke(prompt).content` (`munero-platform/backend/app/services/llm_engine.py:235`)
- Prompt/template source:
  - Inline f-string `prompt = f"""..."""` (`munero-platform/backend/app/services/llm_engine.py:205-233`)
- Data elements included:
  - User question (`munero-platform/backend/app/services/llm_engine.py:207`)
  - Aggregated driver-analysis outputs including:
    - Totals and change percentages (`munero-platform/backend/app/services/llm_engine.py:210-214`)
    - “Top driver” lines including **entity names** like client/brand/country/order_type (`top_driver['name']`) and deltas (`munero-platform/backend/app/services/llm_engine.py:189-197`, `:216-221`)
  - These entity names originate from DB query results returned by `/api/analyze/drivers` (called via httpx in `call_driver_analysis`) (`munero-platform/backend/app/services/llm_engine.py:153-172`)
- Row-level data included?
  - **No raw rows**, but **real entity names + numeric deltas** derived from DB aggregates are included.

#### 2b) SQL generation (LLM sees filters + schema + question)

- Invocation:
  - `raw_response = llm.invoke(prompt).content` (`munero-platform/backend/app/services/llm_engine.py:561`)
- Prompt/template source:
  - `prompt = get_sql_prompt(question, filters)` (`munero-platform/backend/app/services/llm_engine.py:558`)
  - `get_sql_prompt(...)` builds an f-string prompt that includes filter values, required WHERE clause, and schema summary (`munero-platform/backend/app/services/llm_engine.py:256+` with filter inclusion visible at `:267-305`, then prompt text at `:307-357`)
- Row-level data included?
  - **No** (SQL generation step only).

#### 2c) Executive summary generation (LLM sees executed SQL + **row preview**)

- Invocation:
  - `summary_response = llm.invoke(summary_prompt).content` (`munero-platform/backend/app/services/llm_engine.py:692`)
- Prompt/template source:
  - Inline f-string `summary_prompt = f"""..."""` (`munero-platform/backend/app/services/llm_engine.py:665-690`)
- Data elements included (explicitly in prompt):
  - User question (`munero-platform/backend/app/services/llm_engine.py:667`)
  - Active filters rendered with literal values (`munero-platform/backend/app/services/llm_engine.py:636-652`, included at `:669`)
  - **Executed SQL query text** (`munero-platform/backend/app/services/llm_engine.py:671-673`)
  - **Row-level data preview**: `data_preview = df.head(5).to_markdown(...) / to_string(...)` (`munero-platform/backend/app/services/llm_engine.py:654-655`, inserted at `:674-676`)
  - Total row count and basic numeric stats (`munero-platform/backend/app/services/llm_engine.py:656-677`)
- Row-level data included?
  - **Yes** (first 5 rows of the DataFrame are embedded into the LLM prompt).
- Logging behavior:
  - When `DEBUG_LOG_PROMPTS` is true, this file prints the question and full `filters.model_dump()` (`munero-platform/backend/app/services/llm_engine.py:462-465`).

---

## E) Data Exposure Analysis

Legend: “Sent to LLM” refers to data crossing the **LLM trust boundary** (local Ollama today; third‑party Gemini later).

| Data category | Sent to LLM in live `/api/chat` flow? | Where (code) | Notes |
|---|---:|---|---|
| User message text | Yes | `munero-platform/backend/app/services/llm_service.py:304-306` | Sent verbatim inside SQL prompt. |
| Filter values (countries/clients/brands/suppliers/dates) | Yes | Built in `build_filter_clause` (`munero-platform/backend/app/services/llm_service.py:151-213`) and injected into prompt (`:235-248`) | Values are embedded into both human context and a literal `WHERE ...` clause. |
| Schema (table/column names) | Yes | `munero-platform/backend/app/services/llm_service.py:97-149` | Static string describing `fact_orders`. |
| Generated SQL (as output) | No (live flow) | N/A | LLM outputs SQL; backend does not feed SQL back into LLM in `chat_with_data`. |
| Query results / row samples | **No (live flow)** | N/A | In live flow, query runs after LLM call and results are only used by SmartRender. |
| Aggregated metrics (totals, deltas) | No (live flow) | N/A | SmartRender does not call LLM. |
| Query results / row samples | **Yes (dormant `llm_engine.py`)** | `munero-platform/backend/app/services/llm_engine.py:654-692` | `df.head(5)` is embedded in the summary prompt. |

**Conclusion (as-is):** the live backend sends **message + filter values + schema** to the LLM, but **does not send DB result rows**. The repo still contains code that would send row previews if reactivated.

---

## F) Secret Exposure Analysis

### Where future `GEMINI_API_KEY` (or similar) could leak

Even though the key does not exist in code today, the following current patterns are the main leak vectors once a third‑party provider is introduced:

1. **Server logs (stdout)** via `print(...)`
   - Chat endpoint prints user message when `DEBUG_LOG_PROMPTS` is enabled (`munero-platform/backend/app/api/chat.py:120-123`).
   - Many dashboard endpoints log full filter payloads unconditionally (e.g., `munero-platform/backend/app/api/dashboard.py:185` and other `filters.model_dump()` sites).
   - If future Gemini client exceptions include request metadata, printing `str(e)` (see below) may include sensitive headers/URLs.

2. **Error strings returned to the frontend**
   - Chat endpoint includes exception strings in API responses:
     - SQL generation failure: `error=f"SQL generation failed: {str(e)}"` (`munero-platform/backend/app/api/chat.py:156-166`)
     - SQL execution failure: `error=f"SQL execution failed: {error_msg}"` (`munero-platform/backend/app/api/chat.py:188-207`)
     - Unexpected error: `error=str(e)` (`munero-platform/backend/app/api/chat.py:268-281`)
   - Export endpoint returns exception strings via `HTTPException(detail=...)` (`munero-platform/backend/app/api/chat.py:424-427`)
   - If a future Gemini SDK includes sensitive values in exception text, these can surface to clients.

3. **FastAPI debug mode**
   - Backend defaults `DEBUG: bool = True` (`munero-platform/backend/app/core/config.py:18`) and uses it for `FastAPI(..., debug=settings.DEBUG)` (`munero-platform/backend/main.py:17-22`).
   - Debug mode increases the risk of detailed error output (tracebacks) in responses depending on deployment.

### DB URL redaction status (current)

- DB connection string is rendered with password hidden:
  - At import time in `app/core/database.py`: `safe_url = url.render_as_string(hide_password=True)` and printed (`munero-platform/backend/app/core/database.py:15-23`).
  - At startup in `main.py`: `_safe_db_url(...hide_password=True)` and printed (`munero-platform/backend/main.py:38-52`).
- Remaining risk: the **host/database/user** are still logged; and SQL/text errors may include query strings (especially if future debug logging expands).

---

## G) Risk Register

| Risk | Where in code | Impact | Likelihood | Proposed mitigation |
|---|---|---:|---:|---|
| Filter values (PII) sent to third‑party LLM | Prompt includes literal values in `LLMService._build_sql_prompt` (`munero-platform/backend/app/services/llm_service.py:235-248`) | High (client/supplier names leaving perimeter) | High after Gemini switch | Stop embedding filter value lists in prompts; use server-side filter injection/parameterization (see H/P0). |
| Row-level “data preview” accidentally included in prompts | `df.head(5)` embedded into summary prompt in `llm_engine.py` (`munero-platform/backend/app/services/llm_engine.py:654-692`) | High (actual transaction rows sent) | Medium (file not wired today, but easy to reuse) | Delete/disable this pattern; enforce “no row samples in prompt” contract + tests. |
| Prompt/SQL/PII in logs when debug flags enabled | `DEBUG_LOG_PROMPTS` gates prints in chat/db/llm_engine (`munero-platform/backend/app/api/chat.py:120-123`, `munero-platform/backend/app/core/database.py:54-56`, `munero-platform/backend/app/services/llm_engine.py:462-465`) | Medium–High | Medium | Ensure debug flags are off in production; centralize logging with redaction; avoid printing raw user text/SQL. |
| Filters logged unconditionally (even without debug) | Example: `print(...filters.model_dump())` in dashboard (`munero-platform/backend/app/api/dashboard.py:185` etc.) | Medium (PII in logs) | High | Wrap behind debug level; redact list values; use structured logger. |
| Multi-statement / non-SELECT SQL execution | `LLMService.generate_sql` only checks prefix (`munero-platform/backend/app/services/llm_service.py:428-431`); export executes arbitrary SQL (`munero-platform/backend/app/api/chat.py:396`) | High (data modification / data exfil) | Medium–High (depends on DB driver permissions) | Enforce single-statement SELECT-only; reject `;` mid-string; defense-in-depth: read-only DB role. |
| LLM ignores required filters (“WHERE is_test=0” / dashboard filters) | Filters are prompt instructions only; no enforcement post-generation (`munero-platform/backend/app/services/llm_service.py:241-248`, `:269-279`) | Medium (wrong data, possible test data leak) | Medium | Validate generated SQL contains required predicates; or inject filters server-side. |
| Export endpoint can exfiltrate more than intended | `/api/chat/export-csv` accepts `sql_query` directly (`munero-platform/backend/app/api/chat.py:369-399`) | High | High if endpoint exposed | Require server-generated query token; restrict tables/columns; enforce predicate `is_test=0`; apply row/column allowlists. |
| No auth/authorization on AI endpoints | No evidence of auth dependencies in backend; endpoints accept raw requests | High (any caller can query DB & invoke LLM) | Depends on deployment | Add authn/authz at router level; restrict export to privileged users. |
| Secrets leaked through exception strings to client | Chat + export return `str(e)` in responses (`munero-platform/backend/app/api/chat.py:156-166`, `:268-281`, `:424-427`) | High after adding API keys | Medium | Sanitize errors returned to frontend; log redacted details server-side. |
| LLM egress to unexpected host | `OLLAMA_BASE_URL` is configurable; ChatOllama sends prompt to that URL (`munero-platform/backend/app/core/config.py:35`, `munero-platform/backend/app/services/llm_service.py:71-75`) | High | Medium | Enforce allowlist for LLM host; use network egress controls. |

---

## H) Recommended Changes BEFORE Gemini Switch

Priorities: **P0 = must-do before Gemini**, **P1 = strongly recommended**, **P2 = nice-to-have**. These are **code-specific** and reference the exact locations to change, but are recommendations only (no implementation in this report).

### P0 (blockers before Gemini)

1. **Guarantee no row-level data is ever sent to the LLM by default**
   - Audit/remove “data preview in prompt” patterns:
     - `munero-platform/backend/app/services/llm_engine.py:654-692` (`df.head(5)` → `summary_prompt`)
   - Add a hard rule: LLM prompts may contain **schema + question + (optional) aggregate statistics**, but never `df.head`, `to_markdown`, `to_string`, or raw record dumps.

2. **Stop sending filter value lists (client/supplier names) to the LLM**
   - Current leak point: `LLMService.build_filter_clause` embeds values into prompt (`munero-platform/backend/app/services/llm_service.py:167-207`) and `_build_sql_prompt` injects them (`:235-248`).
   - Design options (tradeoffs):
     - **Option A (best privacy):** LLM generates SQL without filter values; backend injects filters server-side (requires SQL rewriting/AST or a strict placeholder convention).
     - **Option B (balanced):** send only *which filters are active* (e.g., “Country filter active (N selected)”), not the values; backend still injects real values into SQL.
     - **Option C (least change):** only include filter values that the user explicitly referenced in `message` (requires robust matching/NER).

3. **Harden SQL execution to SELECT-only + single statement**
   - Add validation before execution in chat and export flows:
     - `munero-platform/backend/app/services/llm_service.py:395-463` (SQL generated/executed)
     - `munero-platform/backend/app/api/chat.py:369-399` (export-csv)
   - Minimum enforcement (no new deps): reject queries containing multiple `;`, DDL/DML keywords, or non-`fact_orders` tables (if that’s the intended scope).

4. **Ensure Gemini API key never reaches logs or clients**
   - When adding a future `GEMINI_API_KEY` setting (`munero-platform/backend/app/core/config.py`), store it as a secret type (e.g., `pydantic.SecretStr`) and never include it in any `model_dump()`/print path.
   - Sanitize error responses in:
     - `munero-platform/backend/app/api/chat.py:156-166`, `:268-281`
     - `munero-platform/backend/app/api/chat.py:424-427`

5. **Use a read-only DB role (defense in depth)**
   - The LLM-generated SQL is executed with the app’s DB credentials (`munero-platform/backend/app/core/database.py:28`).
   - For Supabase/Postgres: use a role limited to `SELECT` on required tables/views; consider Row Level Security (RLS) if multi-tenant.

### P1 (should-do)

1. **Turn off debug mode by default in production**
   - Change default `DEBUG=True` (`munero-platform/backend/app/core/config.py:18`) and ensure deployment sets it false; avoid returning detailed traces.

2. **Centralize logging and redact sensitive payloads**
   - Replace unconditional `print(...)` of filters (`munero-platform/backend/app/api/dashboard.py:185` etc.).
   - Implement redaction for: client/supplier names, SQL text, and any `*_API_KEY` env vars.

3. **Put a hard cap/timeout at the DB level**
   - Python timeouts (`ThreadPoolExecutor`) don’t stop the DB query itself (`munero-platform/backend/app/services/llm_service.py:455-460`).
   - Add `statement_timeout` (Postgres) or equivalent for defense-in-depth.

### P2 (nice-to-have)

1. **Egress allowlisting**
   - Restrict outbound connections so only Gemini endpoints are reachable after the switch (prevents accidental exfil to arbitrary URLs).

2. **Prompt minimization**
   - Reduce schema verbosity (still enough for SQL correctness) to limit what crosses the LLM boundary.

---

## I) “What to verify after implementing mitigations” checklist

Concrete checks (manual + unit-level) to confirm leakage controls:

1. **Prompts contain no data rows**
   - Unit test `LLMService._build_sql_prompt(...)` output contains no `to_markdown`/table-like blocks and no serialized records.
   - If `llm_engine.py` remains in repo, unit test its summary prompt builder contains no `df.head` content.

2. **Filter values are not sent to the LLM (if you implement server-side injection)**
   - Add a test that constructs `DashboardFilters(clients=[...], suppliers=[...])` and asserts the LLM prompt does **not** contain those literal strings.

3. **Debug logging is off in production**
   - Confirm env: `DEBUG_LOG_PROMPTS=False` (`munero-platform/backend/.env.example:6`).
   - Run `curl` and ensure logs do not include raw `message`, SQL, or filters.

4. **Gemini API key never appears in logs**
   - Search logs for patterns like `GEMINI_` / `API_KEY` and ensure zero hits.

5. **Chat still works end-to-end**
   - `curl -sS -X POST http://localhost:8000/api/chat/ -H 'Content-Type: application/json' -d '{"message":"total revenue","filters":{}}'`
   - Expect: `answer_text` present; `sql_query` is SELECT; `row_count` numeric.

6. **Export still works but is constrained**
   - `curl -sS -X POST http://localhost:8000/api/chat/export-csv -H 'Content-Type: application/json' -d '{"sql_query":"SELECT 1 as test","filename":"t.csv"}' -D -`
   - Confirm rejected queries (non-SELECT, multi-statement) return 400.

