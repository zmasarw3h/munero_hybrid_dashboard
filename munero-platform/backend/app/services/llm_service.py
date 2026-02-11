"""
LLM Service for AI Chat Integration.
Ports the AI functionality from the Streamlit app (app.py) to FastAPI.
Handles natural language to SQL conversion with dashboard filter context.
"""
import re
import pandas as pd
from typing import Optional, Tuple, Any

from app.models import DashboardFilters
from app.core.config import settings
from app.core.database import engine, execute_query_df
from app.core.logging_utils import redact_sql_for_log
from app.services.gemini_client import (
    GeminiClient,
    GeminiClientConfig,
    GeminiClientError,
    can_check_gemini_connection,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

FILTER_PLACEHOLDER_TOKEN = "__MUNERO_FILTERS__"

LLM_CONFIG = {
    "provider": settings.LLM_PROVIDER,
    "api_key": settings.LLM_API_KEY,
    "model": settings.LLM_MODEL,
    "base_url": settings.LLM_BASE_URL,
    "temperature": settings.LLM_TEMPERATURE,
    "llm_timeout": settings.LLM_TIMEOUT,  # Timeout for LLM requests in seconds
    "max_output_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
    "retries": settings.LLM_RETRIES,
    "sql_timeout": settings.SQL_TIMEOUT,  # Timeout for SQL execution in seconds
}

def _match_postgres_dollar_quote_delimiter(text: str, start: int) -> str | None:
    if start >= len(text) or text[start] != "$":
        return None

    end = text.find("$", start + 1)
    if end == -1:
        return None

    tag = text[start + 1 : end]
    if any((not (ch.isalnum() or ch == "_")) for ch in tag):
        return None

    return text[start : end + 1]


def _find_occurrences_outside_sql_literals(
    sql: str,
    needle: str,
    *,
    start: int = 0,
    max_matches: int | None = None,
) -> list[int]:
    if not needle:
        return []

    indices: list[int] = []
    i = max(0, int(start))

    state = "code"
    dollar_delim: str | None = None

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            if sql.startswith(needle, i):
                indices.append(i)
                if max_matches is not None and len(indices) >= max_matches:
                    return indices
                i += len(needle)
                continue

            if ch == "'":
                state = "single_quote"
                i += 1
                continue
            if ch == '"':
                state = "double_quote"
                i += 1
                continue
            if ch == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
                state = "block_comment"
                i += 2
                continue

            if ch == "$":
                delim = _match_postgres_dollar_quote_delimiter(sql, i)
                if delim:
                    state = "dollar_quote"
                    dollar_delim = delim
                    i += len(delim)
                    continue

            i += 1
            continue

        if state == "single_quote":
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "double_quote":
            if ch == '"':
                if i + 1 < len(sql) and sql[i + 1] == '"':
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue

        if state == "dollar_quote":
            if dollar_delim and sql.startswith(dollar_delim, i):
                state = "code"
                i += len(dollar_delim)
                dollar_delim = None
                continue
            i += 1
            continue

        i += 1

    return indices


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _find_first_keyword_outside_sql_literals(
    sql: str,
    keywords: tuple[str, ...],
    *,
    start: int = 0,
) -> int | None:
    upper_sql = sql.upper()
    upper_keywords = tuple(k.upper() for k in keywords)

    i = max(0, int(start))
    state = "code"
    dollar_delim: str | None = None

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            for keyword in upper_keywords:
                end = i + len(keyword)
                if end > len(sql):
                    continue
                if not upper_sql.startswith(keyword, i):
                    continue
                before_ok = i == 0 or not _is_identifier_char(sql[i - 1])
                after_ok = end == len(sql) or not _is_identifier_char(sql[end])
                if before_ok and after_ok:
                    return i

            if ch == "'":
                state = "single_quote"
                i += 1
                continue
            if ch == '"':
                state = "double_quote"
                i += 1
                continue
            if ch == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
                state = "block_comment"
                i += 2
                continue

            if ch == "$":
                delim = _match_postgres_dollar_quote_delimiter(sql, i)
                if delim:
                    state = "dollar_quote"
                    dollar_delim = delim
                    i += len(delim)
                    continue

            i += 1
            continue

        if state == "single_quote":
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "double_quote":
            if ch == '"':
                if i + 1 < len(sql) and sql[i + 1] == '"':
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue

        if state == "dollar_quote":
            if dollar_delim and sql.startswith(dollar_delim, i):
                state = "code"
                i += len(dollar_delim)
                dollar_delim = None
                continue
            i += 1
            continue

        i += 1

    return None


# ============================================================================
# LLM SERVICE CLASS
# ============================================================================

class LLMService:
    """
    Service class for LLM-powered SQL generation and execution.
    Provides context-aware SQL generation with dashboard filter injection.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        llm_timeout: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        retries: Optional[int] = None,
        sql_timeout: Optional[int] = None,
    ):
        """
        Initialize the LLM service.
        
        Args:
            provider: LLM provider name (default: gemini)
            api_key: Provider API key (server-side only)
            model: Provider model name (default: gemini-2.5-flash)
            base_url: Provider base URL (default: Generative Language API base)
            temperature: LLM temperature (default: 0)
            llm_timeout: Timeout for LLM requests in seconds (default: 60)
            max_output_tokens: Max tokens for LLM response (default: 512)
            retries: Retry count for transient failures (default: 2)
            sql_timeout: Timeout for SQL execution in seconds (default: 30)
        """
        self.provider = (provider or LLM_CONFIG["provider"] or "gemini").lower()
        self.api_key = api_key if api_key is not None else LLM_CONFIG["api_key"]
        self.model = model or LLM_CONFIG["model"]
        self.base_url = base_url or LLM_CONFIG["base_url"]
        self.temperature = temperature if temperature is not None else LLM_CONFIG["temperature"]
        self.llm_timeout = llm_timeout or LLM_CONFIG["llm_timeout"]
        self.max_output_tokens = max_output_tokens or LLM_CONFIG["max_output_tokens"]
        self.retries = retries if retries is not None else LLM_CONFIG["retries"]
        self.sql_timeout = sql_timeout or LLM_CONFIG["sql_timeout"]
        
        self._gemini: Optional[GeminiClient] = None
    
    @property
    def gemini(self) -> GeminiClient:
        """Lazy-load the Gemini client."""
        if self._gemini is None:
            config = GeminiClientConfig(
                api_key=str(self.api_key or ""),
                model=str(self.model or ""),
                base_url=str(self.base_url or ""),
                temperature=float(self.temperature),
                max_output_tokens=int(self.max_output_tokens),
                timeout_s=float(self.llm_timeout),
                retries=int(self.retries),
            )
            self._gemini = GeminiClient(config)
        return self._gemini

    def close(self) -> None:
        client = self._gemini
        if client is None:
            return
        try:
            client.close()
        except Exception:
            pass
        self._gemini = None
    
    def check_connection(self) -> bool:
        """
        Best-effort check if the configured LLM is reachable.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.provider != "gemini":
            return False
        return can_check_gemini_connection(
            api_key=str(self.api_key or ""),
            model=str(self.model or ""),
            base_url=str(self.base_url or ""),
            timeout_s=5.0,
        )
    
    def get_database_schema(self) -> str:
        """
        Get enhanced schema information for the fact_orders table.
        
        Returns:
            str: Schema description with column details and relationships.
        """
        return """
DATABASE SCHEMA:
================

TABLE: fact_orders (DENORMALIZED - Contains ALL transaction data)
------------------------------------------------------------------
This is the main table containing all order/transaction data. No JOINs needed!

COLUMNS:
--------
Transaction Identifiers:
  - order_number (TEXT): Unique order identifier
  - order_date (DATE): Transaction date in YYYY-MM-DD format

Financial Metrics:
  - order_price_in_aed (REAL): Revenue/sale price in AED (primary currency)
  - cogs_in_aed (REAL): Cost of goods sold in AED
  - quantity (INTEGER): Quantity ordered
  - sale_price (REAL): Unit sale price
  - cost_price (REAL): Unit cost price

Customer/Client Information:
  - client_name (TEXT): Customer/client name
  - client_country (TEXT): Customer country (e.g., 'AE', 'SA', 'UAE', 'Saudi Arabia')
  - client_balance (REAL): Customer account balance
  - customer_id (INTEGER): Internal customer ID

Product Information:
  - product_name (TEXT): Product name
  - product_brand (TEXT): Product brand (e.g., 'Apple', 'Amazon', 'Google')
  - product_sku (TEXT): Product SKU code
  - product_id (INTEGER): Internal product ID
  - order_type (TEXT): Product category/type (e.g., 'gift_cards', 'merchandise', 'vouchers')

Supplier Information:
  - supplier_name (TEXT): Supplier name
  - supplier_id (INTEGER): Internal supplier ID

Flags:
  - is_test (INTEGER): Test data flag (0=real data, 1=test data)

FOREIGN KEY RELATIONSHIPS (for reference - usually not needed due to denormalization):
  - fact_orders.customer_id → dim_customer.customer_id
  - fact_orders.product_id → dim_products.product_id
  - fact_orders.supplier_id → dim_suppliers.supplier_id
"""

    def _build_active_filters_summary(self, filters: Optional[DashboardFilters]) -> str:
        """
        Build a non-sensitive summary of active filters for prompts.

        This deliberately does not include any literal filter values.
        """
        if filters is None:
            return "\n".join(
                [
                    "- date_range: off",
                    "- countries: all",
                    "- product_types: all",
                    "- clients: all",
                    "- brands: all",
                    "- suppliers: all",
                ]
            )

        date_on = bool(filters.start_date or filters.end_date)
        return "\n".join(
            [
                f"- date_range: {'on' if date_on else 'off'}",
                f"- countries: {len(filters.countries)} selected" if filters.countries else "- countries: all",
                f"- product_types: {len(filters.product_types)} selected" if filters.product_types else "- product_types: all",
                f"- clients: {len(filters.clients)} selected" if filters.clients else "- clients: all",
                f"- brands: {len(filters.brands)} selected" if filters.brands else "- brands: all",
                f"- suppliers: {len(filters.suppliers)} selected" if filters.suppliers else "- suppliers: all",
            ]
        )

    def build_filter_predicate(self, filters: Optional[DashboardFilters]) -> Tuple[str, dict[str, Any]]:
        """
        Build a safe, parameterized SQL predicate from dashboard filters.

        - Always includes `is_test = 0`.
        - Uses bound params (never quotes/concatenates values into SQL).
        - For PostgreSQL list filters uses `= ANY(CAST(:param AS text[]))`.
        """
        is_test_predicate = "is_test = 0"
        order_date_expr = "order_date"
        if settings.db_dialect == "postgresql":
            # In hosted Supabase, ingested columns may be TEXT/BOOLEAN/INT. Make this predicate tolerant.
            is_test_predicate = "COALESCE(NULLIF(lower(is_test::text), ''), '0') IN ('0','false','f')"
            order_date_expr = "NULLIF(order_date::text, '')::date"

        predicate_parts: list[str] = [is_test_predicate]
        params: dict[str, Any] = {}

        if filters is None:
            return " AND ".join(predicate_parts), params

        def _bind_date(d) -> Any:
            # Prefer date-typed binds for Postgres; fall back to strings for SQLite/other.
            if settings.db_dialect == "postgresql":
                return d
            return str(d)

        # Date range filter
        if filters.start_date and filters.end_date:
            predicate_parts.append(f"{order_date_expr} BETWEEN :munero_start_date AND :munero_end_date")
            params["munero_start_date"] = _bind_date(filters.start_date)
            params["munero_end_date"] = _bind_date(filters.end_date)
        elif filters.start_date:
            predicate_parts.append(f"{order_date_expr} >= :munero_start_date")
            params["munero_start_date"] = _bind_date(filters.start_date)
        elif filters.end_date:
            predicate_parts.append(f"{order_date_expr} <= :munero_end_date")
            params["munero_end_date"] = _bind_date(filters.end_date)

        def _add_list_filter(values: list[str], column: str, param_name: str) -> None:
            if not values:
                return

            if settings.db_dialect == "postgresql":
                predicate_parts.append(f"{column} = ANY(CAST(:{param_name} AS text[]))")
                params[param_name] = values
                return

            # SQLite / other: parameterize each value as a named placeholder
            placeholders: list[str] = []
            for i, value in enumerate(values):
                key = f"{param_name}_{i}"
                placeholders.append(f":{key}")
                params[key] = value
            predicate_parts.append(f"{column} IN ({', '.join(placeholders)})")

        _add_list_filter(filters.countries, "client_country", "munero_countries")
        _add_list_filter(filters.product_types, "order_type", "munero_product_types")
        _add_list_filter(filters.clients, "client_name", "munero_clients")
        _add_list_filter(filters.brands, "product_brand", "munero_brands")
        _add_list_filter(filters.suppliers, "supplier_name", "munero_suppliers")

        return " AND ".join(predicate_parts), params

    def inject_filters_into_sql(
        self, sql: str, filters: Optional[DashboardFilters]
    ) -> Tuple[str, dict[str, Any]]:
        """
        Replace the placeholder token with the parameterized predicate and return params.

        The LLM output must contain `__MUNERO_FILTERS__` exactly once and it must
        appear in executable SQL (not inside comments or quoted strings/identifiers).
        """
        token_count = sql.count(FILTER_PLACEHOLDER_TOKEN)
        if token_count != 1:
            if token_count == 0:
                raise ValueError(
                    f"Generated SQL is missing required filters placeholder: {FILTER_PLACEHOLDER_TOKEN}"
                )
            raise ValueError(
                    f"Generated SQL contains filters placeholder multiple times: {FILTER_PLACEHOLDER_TOKEN}"
                )

        token_positions = _find_occurrences_outside_sql_literals(
            sql,
            FILTER_PLACEHOLDER_TOKEN,
            max_matches=2,
        )
        if len(token_positions) != 1:
            raise ValueError(
                f"Generated SQL must include {FILTER_PLACEHOLDER_TOKEN} exactly once outside comments/quotes."
            )

        predicate, params = self.build_filter_predicate(filters)
        start = token_positions[0]
        end = start + len(FILTER_PLACEHOLDER_TOKEN)
        injected_sql = f"{sql[:start]}{predicate}{sql[end:]}"
        return injected_sql, params

    def _build_sql_prompt(self, question: str, filters: Optional[DashboardFilters]) -> str:
        """
        Build the complete SQL generation prompt with schema and filter context.
        
        Args:
            question: User's natural language question
            filters: Current dashboard filter state
            
        Returns:
            str: Complete prompt for the LLM
        """
        schema_info = self.get_database_schema()
        filters_summary = self._build_active_filters_summary(filters)

        db_name = "PostgreSQL" if settings.db_dialect == "postgresql" else "SQLite"
        order_date_expr = (
            "NULLIF(order_date::text, '')::date"
            if settings.db_dialect == "postgresql"
            else "order_date"
        )
        numeric_expr_template = (
            "NULLIF(regexp_replace({col}::text, '[^0-9.+-]', '', 'g'), '')::double precision"
            if settings.db_dialect == "postgresql"
            else "{col}"
        )
        revenue_expr = numeric_expr_template.format(col="order_price_in_aed")
        cogs_expr = numeric_expr_template.format(col="cogs_in_aed")
        round_revenue_sum_expr = (
            f"ROUND(SUM({revenue_expr})::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else f"ROUND(SUM({revenue_expr}), 2)"
        )

        client_name_contains_example = (
            "client_name ILIKE '%loylogic%'"
            if settings.db_dialect == "postgresql"
            else "LOWER(client_name) LIKE '%' || LOWER('loylogic') || '%'"
        )

        month_grouping = (
            f"to_char({order_date_expr}, 'YYYY-MM')" if settings.db_dialect == "postgresql"
            else "strftime('%Y-%m', order_date)"
        )

        group_by_alias_rule = (
            "On PostgreSQL, do NOT use SELECT aliases in GROUP BY/HAVING. Use positional refs (GROUP BY 1) "
            "or repeat the full expression."
            if settings.db_dialect == "postgresql"
            else "Avoid SELECT aliases in GROUP BY/HAVING. Use positional refs (GROUP BY 1) or repeat the expression."
        )

        filter_section = f"""
ACTIVE FILTERS SUMMARY (do NOT include literal values):
{filters_summary}

FILTER INJECTION CONTRACT (REQUIRED):
1) The backend will inject dashboard filter values server-side.
2) Your SQL MUST include the token {FILTER_PLACEHOLDER_TOKEN} exactly once.
3) Always include: WHERE {FILTER_PLACEHOLDER_TOKEN}
4) If you need extra conditions, append them with AND after the token.
"""
        
        return f"""You are a {db_name} SQL expert for the 'Munero' sales analytics database.

{schema_info}

{filter_section}

TERMINOLOGY MAPPING (Critical - use these definitions):
-------------------------------------------------------
- "client" or "customer" → fact_orders.client_name
- "product category" or "type" → fact_orders.order_type
- "supplier" → fact_orders.supplier_name
- "brand" → fact_orders.product_brand
- "revenue" or "sales" → SUM({revenue_expr})
- "profit" or "gross profit" → SUM({revenue_expr}) - SUM(COALESCE({cogs_expr}, 0))
- "margin" or "profit margin" → (SUM({revenue_expr}) - SUM(COALESCE({cogs_expr}, 0))) / NULLIF(SUM({revenue_expr}), 0) * 100
- "orders" or "order count" → COUNT(DISTINCT order_number)
- "quantity sold" → SUM(quantity)
- "AOV" or "average order value" → SUM({revenue_expr}) / NULLIF(COUNT(DISTINCT order_number), 0)

CLIENT NAME MATCHING (Important):
--------------------------------
- Client names are often longer than what the user types (e.g. "Loylogic Rewards FZE").
- If the user provides a partial client name, prefer a case-insensitive substring match instead of exact equality.
  Example: {client_name_contains_example}

CRITICAL SQL RULES:
-------------------
1. fact_orders is DENORMALIZED - NO JOINS needed for most queries!
2. You MUST include: WHERE {FILTER_PLACEHOLDER_TOKEN} (exactly once)
3. Return exactly ONE SQL statement (no extra semicolons)
4. The statement MUST start with SELECT or WITH (read-only)
5. NEVER use write/admin keywords: INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, INTO, COPY, EXEC/EXECUTE, CALL, VACUUM, PRAGMA, ATTACH/DETACH
6. Dates in order_date are in YYYY-MM-DD format
7. For monthly grouping: {month_grouping}
8. {group_by_alias_rule}
9. For client filters from user-entered text, prefer substring matching (see CLIENT NAME MATCHING).
10. For "Top N" queries: Use ORDER BY <metric> DESC LIMIT N
11. Always use table alias if needed (e.g., fo for fact_orders)
12. Round currency values: {round_revenue_sum_expr}
13. Handle NULL COGS: COALESCE({cogs_expr}, 0)
14. End queries with semicolon
15. NO markdown formatting in output - just raw SQL

EXAMPLE QUERIES:
----------------
Q: "What are my top 5 products by revenue?"
A: SELECT product_name, {round_revenue_sum_expr} as total_revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN}
   GROUP BY product_name 
   ORDER BY total_revenue DESC 
   LIMIT 5;

Q: "Show monthly revenue trend"
A: SELECT {month_grouping} as month, {round_revenue_sum_expr} as revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN}
   GROUP BY 1 
   ORDER BY 1;

Q: "Show me a daily trend of the revenue sold to loylogic during June 2025"
A: SELECT {order_date_expr} as order_date, {round_revenue_sum_expr} as revenue
   FROM fact_orders
   WHERE {FILTER_PLACEHOLDER_TOKEN}
     AND {client_name_contains_example}
     AND {order_date_expr} BETWEEN '2025-06-01' AND '2025-06-30'
   GROUP BY 1
   ORDER BY 1;

Q: "What is total revenue?"
A: SELECT {round_revenue_sum_expr} as total_revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN};

NOW ANSWER THIS QUESTION:
{question}

Return ONLY the raw SQL query. No markdown. No explanations. No extra text.

SQL:"""

    def _invoke_llm_with_timeout(self, prompt: str) -> str:
        """
        Invoke the LLM (network timeout is enforced by the Gemini client).
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            str: The LLM response content
        """
        if self.provider != "gemini":
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        try:
            return self.gemini.generate_text(prompt)
        except GeminiClientError as e:
            raise Exception("LLM invocation failed") from e

    def extract_sql_from_response(self, response: str) -> str:
        """
        Extract clean SQL from LLM response.
        Handles markdown blocks, think tags, and various LLM output formats.
        
        Args:
            response: Raw LLM output
            
        Returns:
            str: Cleaned SQL query
        """
        # Step 0: Remove <think> tags (DeepSeek-R1 specific)
        response = self._remove_think_tags(response)
        response = response.strip()

        sql_candidate = response

        # Method 1: Extract from ```sql code block
        match = re.search(r"```sql\s+(.*?)\s+```", response, re.DOTALL | re.IGNORECASE)
        if match:
            sql_candidate = match.group(1).strip()
        else:
            # Method 2: Extract from generic ``` code block
            match = re.search(r"```\s+(.*?)\s+```", response, re.DOTALL)
            if match:
                sql_candidate = match.group(1).strip()

        cleaned = re.sub(r"^(SQL:|Query:)\s*", "", sql_candidate, flags=re.IGNORECASE).strip()
        statement_start = _find_first_keyword_outside_sql_literals(cleaned, ("WITH", "SELECT"))
        if statement_start is None:
            return cleaned.strip()

        semicolon_positions = _find_occurrences_outside_sql_literals(
            cleaned,
            ";",
            start=statement_start,
            max_matches=1,
        )
        if semicolon_positions:
            sql = cleaned[statement_start : semicolon_positions[0] + 1]
        else:
            sql = cleaned[statement_start:].rstrip()
            if not sql.endswith(";"):
                sql += ";"

        return sql.strip()
    
    def _remove_think_tags(self, response: str) -> str:
        """
        Remove DeepSeek-R1's <think>...</think> reasoning tags from response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            str: Response with think tags removed
        """
        # Remove all <think> blocks (case-insensitive, multiline, greedy)
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def generate_sql(
        self, 
        question: str, 
        filters: Optional[DashboardFilters] = None
    ) -> str:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            filters: Dashboard filter state to inject into query
            
        Returns:
            str: Generated SQL query
            
        Raises:
            TimeoutError: If LLM request times out
            Exception: If SQL generation fails
        """
        # Build the prompt
        prompt = self._build_sql_prompt(question, filters)
        
        # Call LLM with timeout
        try:
            raw_response = self._invoke_llm_with_timeout(prompt)
        except TimeoutError:
            raise
        except Exception as e:
            raise Exception(f"LLM invocation failed: {str(e)}")
        
        # Extract and clean SQL
        sql_query = self.extract_sql_from_response(raw_response)
        
        # Basic validation
        if not sql_query or not sql_query.upper().strip().startswith(('SELECT', 'WITH')):
            raise Exception(f"Invalid SQL generated ({redact_sql_for_log(sql_query)})")
        
        return sql_query

    def repair_sql_template(
        self,
        *,
        question: str,
        filters: Optional[DashboardFilters],
        failed_sql_template: str,
        injected_predicate: str,
        db_error: str,
    ) -> str:
        """
        Attempt to repair a failed SQL *template* (must still contain the filter placeholder token).

        This is used when the initial SQL executes unsuccessfully in hosted Postgres. The repair
        prompt includes the DB error message and the injected predicate (without literal values).
        """
        schema_info = self.get_database_schema()
        filters_summary = self._build_active_filters_summary(filters)
        db_name = "PostgreSQL" if settings.db_dialect == "postgresql" else "SQLite"

        order_date_expr = (
            "NULLIF(order_date::text, '')::date"
            if settings.db_dialect == "postgresql"
            else "order_date"
        )
        numeric_expr_template = (
            "NULLIF(regexp_replace({col}::text, '[^0-9.+-]', '', 'g'), '')::double precision"
            if settings.db_dialect == "postgresql"
            else "{col}"
        )
        revenue_expr = numeric_expr_template.format(col="order_price_in_aed")
        cogs_expr = numeric_expr_template.format(col="cogs_in_aed")
        round_revenue_sum_expr = (
            f"ROUND(SUM({revenue_expr})::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else f"ROUND(SUM({revenue_expr}), 2)"
        )
        month_grouping = (
            f"to_char({order_date_expr}, 'YYYY-MM')" if settings.db_dialect == "postgresql"
            else "strftime('%Y-%m', order_date)"
        )
        client_name_contains_example = (
            "client_name ILIKE '%loylogic%'"
            if settings.db_dialect == "postgresql"
            else "LOWER(client_name) LIKE '%' || LOWER('loylogic') || '%'"
        )

        prompt = f"""You are a {db_name} SQL expert for the 'Munero' sales analytics database.

The previous SQL template failed when executed. Fix the SQL template so it executes successfully.

{schema_info}

ACTIVE FILTERS SUMMARY (do NOT include literal values):
{filters_summary}

FILTER INJECTION CONTRACT (REQUIRED):
1) The backend will inject dashboard filter values server-side.
2) Your SQL MUST include the token {FILTER_PLACEHOLDER_TOKEN} exactly once.
3) Always include: WHERE {FILTER_PLACEHOLDER_TOKEN}
4) If you need extra conditions, append them with AND after the token.

HOSTED POSTGRES TYPE SAFETY (Important):
- If numeric columns might be stored as text, coerce them safely, e.g.:
  - revenue numeric expr: {revenue_expr}
  - cogs numeric expr: {cogs_expr}
- Postgres does NOT support ROUND(double precision, integer). For 2-decimal rounding, cast to numeric:
  - rounded revenue sum: {round_revenue_sum_expr}
- If order_date might be stored as text, cast safely:
  - date expr: {order_date_expr}
  - month grouping: {month_grouping}

CLIENT NAME MATCHING (Important):
- Client names are often longer than what the user types (e.g. "Loylogic Rewards FZE").
- If the user provides a partial client name, prefer a case-insensitive substring match instead of exact equality.
  Example: {client_name_contains_example}

EXECUTION ERROR (from the database):
{db_error}

FAILED SQL TEMPLATE (contains {FILTER_PLACEHOLDER_TOKEN}):
{failed_sql_template}

INJECTED FILTER PREDICATE (backend replaces the token with this predicate):
{injected_predicate}

REPAIR RULES:
1) Return exactly ONE SQL statement.
2) The statement MUST start with SELECT or WITH (read-only).
3) Do NOT use write/admin keywords: INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, INTO, COPY, EXEC/EXECUTE, CALL, VACUUM, PRAGMA, ATTACH/DETACH.
4) Preserve the filter token exactly once: WHERE {FILTER_PLACEHOLDER_TOKEN}
5) Return ONLY the raw SQL (no markdown, no explanations).

REPAIRED SQL TEMPLATE:"""

        raw_response = self._invoke_llm_with_timeout(prompt)
        sql_query = self.extract_sql_from_response(raw_response)

        if not sql_query or not sql_query.upper().strip().startswith(("SELECT", "WITH")):
            raise Exception(f"Invalid repaired SQL generated ({redact_sql_for_log(sql_query)})")

        token_count = sql_query.count(FILTER_PLACEHOLDER_TOKEN)
        if token_count != 1:
            raise Exception(
                f"Repaired SQL must include {FILTER_PLACEHOLDER_TOKEN} exactly once (found={token_count})"
            )

        token_positions = _find_occurrences_outside_sql_literals(
            sql_query,
            FILTER_PLACEHOLDER_TOKEN,
            max_matches=2,
        )
        if len(token_positions) != 1:
            raise Exception(
                f"Repaired SQL must include {FILTER_PLACEHOLDER_TOKEN} exactly once outside comments/quotes."
            )

        return sql_query

    def execute_sql(
        self,
        sql: str,
        conn: Optional[Any] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute SQL query (server-side statement timeout is enforced by the DB connection).
        
        Args:
            sql: SQL query to execute
            conn: Optional SQLAlchemy/DBAPI connection (defaults to configured engine)
            params: Optional bound params dict for safe execution
            
        Returns:
            pd.DataFrame: Query results
            
        """
        sql_conn: Any = conn or engine
        return execute_query_df(
            sql,
            conn=sql_conn,
            params=params,
            max_rows=int(settings.MAX_DISPLAY_ROWS),
        )

    def query(
        self, 
        question: str, 
        filters: Optional[DashboardFilters] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        Complete query pipeline: generate SQL from question and execute it.
        
        Args:
            question: Natural language question
            filters: Dashboard filter state
            
        Returns:
            Tuple of (DataFrame results, SQL query string)
            
        Raises:
            TimeoutError: If LLM or SQL times out
            Exception: If generation or execution fails
        """
        sql_template = self.generate_sql(question, filters)
        sql, params = self.inject_filters_into_sql(sql_template, filters)
        df = self.execute_sql(sql, params=params)
        return df, sql


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_llm_service() -> LLMService:
    """Factory function to get a configured LLMService instance."""
    return LLMService()
