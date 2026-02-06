# Change 2 (P0-2) Verification Report
Server-side filter injection so the LLM never sees filter values

Date: 2026-02-05

## Executive summary
All requirements **R1–R6: PASS** based on static inspection + the requested command outputs, plus an optional runtime “sentinel value” check (executed via the backend venv Python).

---

## R1) Placeholder token contract exists and is enforced — **PASS**

### Evidence
- Placeholder token constant: `munero-platform/backend/app/services/llm_service.py:22`
- Prompt contract (requires exactly one token + `WHERE __MUNERO_FILTERS__`): `munero-platform/backend/app/services/llm_service.py:275`–`munero-platform/backend/app/services/llm_service.py:284`, `munero-platform/backend/app/services/llm_service.py:305`–`munero-platform/backend/app/services/llm_service.py:316`
- Enforced after LLM returns:
  - Count check + fail on missing/multiple: `munero-platform/backend/app/services/llm_service.py:242`–`munero-platform/backend/app/services/llm_service.py:250`
  - Replacement before execution: `munero-platform/backend/app/services/llm_service.py:252`–`munero-platform/backend/app/services/llm_service.py:253`
- Chat endpoint uses the enforcement and fails safely with user-facing copy:
  - Injection performed immediately after generation: `munero-platform/backend/app/api/chat.py:141`–`munero-platform/backend/app/api/chat.py:143`
  - Safe failure + user-friendly `answer_text` on `ValueError`: `munero-platform/backend/app/api/chat.py:147`–`munero-platform/backend/app/api/chat.py:157`

### Notes
- Enforcement is **token count based** (`sql.count(...)`) and does not verify the token is in a `WHERE` clause or outside of quotes/comments (see Risks).

---

## R2) LLM prompt contains NO literal filter values — **PASS**

### Evidence (static)
- Active filters summary is intentionally non-sensitive (counts/on-off only): `munero-platform/backend/app/services/llm_service.py:153`–`munero-platform/backend/app/services/llm_service.py:181`
- Prompt explicitly says “do NOT include literal values” and includes only the summary: `munero-platform/backend/app/services/llm_service.py:275`–`munero-platform/backend/app/services/llm_service.py:284`
- Required grep checks:
  - No prompt-building joins like `", ".join(filters.clients)` etc:
    - `rg -n "join\\(filters\\.|Clients:|Suppliers:|Brands:|Countries:" munero-platform/backend/app/services/llm_service.py` → **no matches** (exit code 1)

### Evidence (optional runtime sentinel check — executed)
Ran a snippet using `munero-platform/backend/venv/bin/python` that:
1) Built a prompt with filters containing sentinels like `CLIENT_SENTINEL_123`.
2) Confirmed the prompt string does **not** contain any sentinel values.
3) Confirmed the params dict produced by the server-side predicate builder **does** contain all sentinels.

Observed output (key lines):
- `prompt_contains_any_sentinel False`
- `params_contains_all_sentinels True`

Related code path:
- Prompt builder: `munero-platform/backend/app/services/llm_service.py:255`
- Predicate params builder: `munero-platform/backend/app/services/llm_service.py:183`

### Notes
- The schema prompt includes **static** example values (e.g., brand examples) in the schema description (`munero-platform/backend/app/services/llm_service.py:127`–`munero-platform/backend/app/services/llm_service.py:145`). These are not derived from the active dashboard filters.

---

## R3) Filter predicate builder is safe + parameterized — **PASS**

### Evidence
- Always includes `is_test = 0`: `munero-platform/backend/app/services/llm_service.py:191`
- Date filters are parameterized (no concatenation): `munero-platform/backend/app/services/llm_service.py:198`–`munero-platform/backend/app/services/llm_service.py:207`
- List filters:
  - Postgres safe array binding pattern: `munero-platform/backend/app/services/llm_service.py:213`–`munero-platform/backend/app/services/llm_service.py:216`
  - SQLite/other uses named placeholders (values never embedded into SQL): `munero-platform/backend/app/services/llm_service.py:218`–`munero-platform/backend/app/services/llm_service.py:225`
- Returns `(predicate_sql, params_dict)`: `munero-platform/backend/app/services/llm_service.py:232`

---

## R4) Chat execution path uses params — **PASS**

### Evidence
- `pd.read_sql_query(..., params=...)` is used for execution: `munero-platform/backend/app/services/llm_service.py:494`
- Chat endpoint executes with bound params after placeholder replacement:
  - Replacement + params returned: `munero-platform/backend/app/services/llm_service.py:252`–`munero-platform/backend/app/services/llm_service.py:253`
  - Execution with params: `munero-platform/backend/app/api/chat.py:187`

### Notes
- With this design, filter values live in the bound params dict, not interpolated into the SQL string.

---

## R5) Export CSV path remains correct and uses the SAME filters as the originating message — **PASS**

### Evidence (frontend)
- Chat stores the exact API-form filters used when the message was sent:
  - Filters transformed once per send: `munero-platform/frontend/components/chat/ChatSidebar.tsx:60`–`munero-platform/frontend/components/chat/ChatSidebar.tsx:83`
  - Stored on the assistant message as `requestFilters`: `munero-platform/frontend/components/chat/ChatSidebar.tsx:84`–`munero-platform/frontend/components/chat/ChatSidebar.tsx:93`
  - Type includes `requestFilters?: DashboardFilters`: `munero-platform/frontend/lib/types.ts:338`–`munero-platform/frontend/lib/types.ts:345`
- Export uses the stored filters (not current UI state): `munero-platform/frontend/components/chat/ChatMessage.tsx:39`–`munero-platform/frontend/components/chat/ChatMessage.tsx:47`
- Export request posts both `sql_query` and `filters`: `munero-platform/frontend/lib/api-client.ts:256`–`munero-platform/frontend/lib/api-client.ts:265`

### Evidence (backend)
- Export request model accepts filters: `munero-platform/backend/app/api/chat.py:38`–`munero-platform/backend/app/api/chat.py:43`
- Export enforces safety cap `LIMIT 10000`: `munero-platform/backend/app/api/chat.py:429`–`munero-platform/backend/app/api/chat.py:430`
- Export executes with parameter binding: `munero-platform/backend/app/api/chat.py:433`
- Handles both cases:
  - Placeholder present → inject + params: `munero-platform/backend/app/api/chat.py:410`–`munero-platform/backend/app/api/chat.py:413`
  - Placeholder absent (expected if exporting `sql_query` returned by chat) → derive params and bind only used keys: `munero-platform/backend/app/api/chat.py:418`–`munero-platform/backend/app/api/chat.py:427`

---

## R6) Frontend chat request filters are aligned with backend DashboardFilters — **PASS**

### Evidence
- `ChatRequest.filters` is typed to backend-style `DashboardFilters` (start/end dates, lists, etc.): `munero-platform/frontend/lib/types.ts:313`–`munero-platform/frontend/lib/types.ts:317`
- Backend-style `DashboardFilters` shape in frontend types: `munero-platform/frontend/lib/types.ts:7`–`munero-platform/frontend/lib/types.ts:18`
- ChatSidebar sends API-shaped filters via `transformFiltersForAPI(...)`: `munero-platform/frontend/components/chat/ChatSidebar.tsx:60`–`munero-platform/frontend/components/chat/ChatSidebar.tsx:83`
- `transformFiltersForAPI(...)` maps UI `dateRange` to API `start_date`/`end_date`: `munero-platform/frontend/components/dashboard/FilterContext.tsx:106`–`munero-platform/frontend/components/dashboard/FilterContext.tsx:140`
- Old `date_range` payload shape detection:
  - `rg -n "date_range" munero-platform/frontend munero-platform/backend` → **no frontend matches** (matches only appear in backend code/comments, e.g. `munero-platform/backend/app/services/llm_service.py:162`)

---

## Evidence gathering commands (key results)

0) Token + quote/comment validation logic:
- `rg -n "(__MUNERO_FILTERS__|token|comment|block comment|line comment|single-quote|double-quote)" munero-platform/backend/app/services munero-platform/backend/app/api`
  - Key matches: `munero-platform/backend/app/services/llm_service.py:22`, `munero-platform/backend/app/services/llm_service.py:240`–`munero-platform/backend/app/services/llm_service.py:244`

1) Token + injection locations:
- `rg -n "__MUNERO_FILTERS__" munero-platform/backend munero-platform/frontend`
  - Key matches only in `munero-platform/backend/app/services/llm_service.py` (token constant + docstring)

2) Prompt construction + filter value joins:
- `rg -n "join\\(filters\\.|Clients:|Suppliers:|Brands:|Countries:" munero-platform/backend/app/services/llm_service.py`
  - No matches
- `rg -n "IN \\('\\{|IN \\('\\\"|\\\"\\, \\\"\\.join\\(|'\\, '\\.join\\(" munero-platform/backend/app/services/llm_service.py`
  - Match is only placeholder construction (no literal values): `munero-platform/backend/app/services/llm_service.py:224`

2.5) Old frontend filter shape detection:
- `rg -n "date_range" munero-platform/frontend munero-platform/backend`
  - No matches in `munero-platform/frontend`

3) Export CSV request/handler:
- `rg -n "class ExportCSVRequest|export_csv\\(" munero-platform/backend/app/api/chat.py`
  - Key matches: `munero-platform/backend/app/api/chat.py:38`, `munero-platform/backend/app/api/chat.py:383`

4) Frontend chat + export wiring:
- `rg -n "sendChatMessage\\(|exportChatCSV\\(|handleExportCSV|transformFiltersForAPI\\(" munero-platform/frontend`
  - Key matches: `munero-platform/frontend/components/chat/ChatSidebar.tsx:62`, `munero-platform/frontend/components/chat/ChatSidebar.tsx:79`, `munero-platform/frontend/components/chat/ChatMessage.tsx:39`–`munero-platform/frontend/components/chat/ChatMessage.tsx:43`

Basic sanity:
- `python3 -m compileall munero-platform/backend` → **completed successfully (exit code 0)**

---

## Risks / regressions discovered
- Token enforcement is **count-based only**; a malicious/buggy LLM output could place `__MUNERO_FILTERS__` inside a string literal or SQL comment and still pass the “count == 1” check, leading to filters not being applied (or unexpected SQL execution errors). Relevant logic: `munero-platform/backend/app/services/llm_service.py:242`–`munero-platform/backend/app/services/llm_service.py:253`.
- Export endpoint accepts client-provided SQL; while parameter binding + `LIMIT 10000` are enforced (`munero-platform/backend/app/api/chat.py:405`–`munero-platform/backend/app/api/chat.py:433`), a user could still request an expensive query shape (e.g., heavy aggregations) that is limited only by DB performance and the safety cap.

---

## Minimal fix plan (only if any requirement were FAIL)
N/A — all requirements R1–R6 PASS in this verification.

