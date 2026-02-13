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


def _find_first_keyword_at_top_level(
    sql: str,
    keywords: tuple[str, ...],
    *,
    start: int = 0,
) -> int | None:
    """
    Find the first occurrence of any keyword at SQL top level (paren_depth==0),
    outside of comments/quoted strings/quoted identifiers/dollar-quoted strings.
    """
    upper_sql = sql.upper()
    upper_keywords = tuple(k.upper() for k in keywords)

    i = max(0, int(start))
    state = "code"
    dollar_delim: str | None = None
    paren_depth = 0

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            if ch == "(":
                paren_depth += 1
                i += 1
                continue
            if ch == ")":
                paren_depth -= 1
                i += 1
                continue

            if paren_depth == 0:
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


def _is_sql_parentheses_balanced(sql: str) -> bool:
    """
    Return True when parentheses are balanced outside comments/quotes/dollar-quotes.
    """
    if not isinstance(sql, str) or not sql:
        return False

    i = 0
    state = "code"
    dollar_delim: str | None = None
    depth = 0

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                depth -= 1
                if depth < 0:
                    return False
                i += 1
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

    return depth == 0


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
  - order_type (TEXT): One of 'gift_card' or 'merchandise' (exact values; lowercase; singular).

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
        aov_expr = f"SUM({revenue_expr}) / NULLIF(COUNT(DISTINCT order_number), 0)"
        round_aov_expr = (
            f"ROUND(({aov_expr})::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else f"ROUND({aov_expr}, 2)"
        )
        profit_margin_cte_expr = "((revenue - cogs) / NULLIF(revenue, 0) * 100)"
        round_profit_margin_cte_expr = (
            f"ROUND(({profit_margin_cte_expr})::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else f"ROUND({profit_margin_cte_expr}, 2)"
        )
        round_revenue_cte_expr = (
            "ROUND(revenue::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else "ROUND(revenue, 2)"
        )
        round_cogs_cte_expr = (
            "ROUND(cogs::numeric, 2)::double precision"
            if settings.db_dialect == "postgresql"
            else "ROUND(cogs, 2)"
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

ORDER TYPE VALUES (Important):
-----------------------------
- When filtering by order_type, only use the exact schema values (lowercase singular):
  - 'gift_card'
  - 'merchandise'

TIME SERIES / TREND (Important):
-------------------------------
- If the question asks for a trend over time (daily/weekly/monthly/yearly), return exactly ONE time bucket column and ONE metric
  (add a second metric only if explicitly requested).
- For daily trends: use {order_date_expr} AS order_date (a real date bucket). Do NOT use EXTRACT(DAY FROM ...) — it is numeric and loses month/year context.
- For monthly trends: use {month_grouping} AS month.
- Always GROUP BY 1 ORDER BY 1.

BREAKDOWNS / VS / SPLIT QUERIES (Important):
-------------------------------------------
- If the question implies a split/breakdown/vs/compare across a dimension (e.g. by order_type), return BOTH:
  - COUNT(DISTINCT order_number) AS orders
  - {round_revenue_sum_expr} AS total_revenue
  and GROUP BY the requested dimension (use positional refs like GROUP BY 1).

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
16. For margin/profit breakdowns (especially negative margins), prefer a CTE (WITH agg AS (...)) to compute aggregates first and avoid repeating long expressions.

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
(Note: Do NOT use EXTRACT(DAY FROM ...) for daily trends; use the full date bucket in {order_date_expr}.)
A: SELECT {order_date_expr} as order_date, {round_revenue_sum_expr} as revenue
   FROM fact_orders
   WHERE {FILTER_PLACEHOLDER_TOKEN}
     AND {client_name_contains_example}
     AND {order_date_expr} BETWEEN '2025-06-01' AND '2025-06-30'
   GROUP BY 1
   ORDER BY 1;

Q: "What is the split of gift cards vs merchandise?"
A: SELECT order_type,
          COUNT(DISTINCT order_number) AS orders,
          {round_revenue_sum_expr} AS total_revenue
   FROM fact_orders
   WHERE {FILTER_PLACEHOLDER_TOKEN}
     AND order_type IN ('gift_card', 'merchandise')
   GROUP BY 1
   ORDER BY total_revenue DESC;

Q: "Top 10 clients by AOV"
A: SELECT client_name,
          {round_aov_expr} AS aov
   FROM fact_orders
   WHERE {FILTER_PLACEHOLDER_TOKEN}
   GROUP BY 1
   ORDER BY aov DESC
   LIMIT 10;

Q: "Which brands have negative margins?"
A: WITH agg AS (
     SELECT product_brand,
            SUM({revenue_expr}) AS revenue,
            SUM(COALESCE({cogs_expr}, 0)) AS cogs
     FROM fact_orders
     WHERE {FILTER_PLACEHOLDER_TOKEN}
       AND product_brand IS NOT NULL
       AND TRIM(product_brand) <> ''
     GROUP BY 1
   )
   SELECT product_brand,
          {round_profit_margin_cte_expr} AS profit_margin,
          {round_revenue_cte_expr} AS total_revenue,
          {round_cogs_cte_expr} AS total_cogs
   FROM agg
   WHERE {profit_margin_cte_expr} < 0
   ORDER BY profit_margin ASC, total_revenue DESC;

Q: "What is total revenue?"
A: SELECT {round_revenue_sum_expr} as total_revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN};

NOW ANSWER THIS QUESTION:
{question}

Return ONLY the raw SQL query. No markdown. No explanations. No extra text.

SQL:"""

    def _invoke_llm_with_timeout(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        """
        Invoke the LLM (network timeout is enforced by the Gemini client).
        
        Args:
            prompt: The prompt to send to the LLM

        Returns:
            str: The LLM response content
        """
        if self.provider != "gemini":
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        return self.gemini.generate_text(prompt, model=model, max_output_tokens=max_output_tokens)

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
        cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _numeric_expr(self, col: str) -> str:
        if settings.db_dialect == "postgresql":
            return f"NULLIF(regexp_replace({col}::text, '[^0-9.+-]', '', 'g'), '')::double precision"
        return f"{col}"

    def _round_2dp(self, expr: str) -> str:
        if settings.db_dialect == "postgresql":
            return f"ROUND(({expr})::numeric, 2)::double precision"
        return f"ROUND(({expr}), 2)"

    def _filters_placeholder_is_valid(self, sql_template: str) -> bool:
        if not isinstance(sql_template, str) or not sql_template:
            return False

        if sql_template.count(FILTER_PLACEHOLDER_TOKEN) != 1:
            return False

        token_positions = _find_occurrences_outside_sql_literals(
            sql_template,
            FILTER_PLACEHOLDER_TOKEN,
            max_matches=2,
        )
        return len(token_positions) == 1

    def _extract_profitability_dimension(self, question: str) -> str | None:
        q = (question or "").lower()
        if not q:
            return None

        if re.search(r"\bbrands?\b", q):
            return "product_brand"
        if re.search(r"\bsuppliers?\b", q):
            return "supplier_name"
        if re.search(r"\b(clients?|customers?)\b", q):
            return "client_name"
        if re.search(r"\b(products?|items?)\b", q):
            return "product_name"
        if re.search(r"\bcountries?\b", q) or re.search(r"\bcountry\b", q):
            return "client_country"

        mentions_order_type = bool(
            re.search(r"\border[_\s-]?type\b", q)
            or re.search(r"\bproduct[_\s-]?type\b", q)
            or "order_type" in q
            or ("category" in q and ("order" in q or "product" in q))
        )
        if mentions_order_type:
            return "order_type"

        return None

    def _maybe_build_negative_margin_by_dimension_sql_template(self, question: str) -> str | None:
        """
        Deterministic fallback for "negative margin" prompts by a supported dimension.

        Example: "Which brands have negative margins?"
        """
        q = (question or "").strip()
        if not q:
            return None

        q_lower = q.lower()
        if "margin" not in q_lower:
            return None

        negative_intent = bool(
            "negative" in q_lower
            or re.search(r"<\s*0", q_lower)
            or re.search(r"\b(below|under|less than)\s*0\b", q_lower)
        )
        if not negative_intent:
            return None

        dim_col = self._extract_profitability_dimension(q)
        if not dim_col:
            return None

        revenue_expr = self._numeric_expr("order_price_in_aed")
        cogs_expr = self._numeric_expr("cogs_in_aed")

        profit_margin_expr = "((revenue - cogs) / NULLIF(revenue, 0) * 100)"

        return (
            "WITH agg AS (\n"
            "  SELECT\n"
            f"    {dim_col} AS {dim_col},\n"
            f"    SUM({revenue_expr}) AS revenue,\n"
            f"    SUM(COALESCE({cogs_expr}, 0)) AS cogs\n"
            "  FROM fact_orders\n"
            f"  WHERE {FILTER_PLACEHOLDER_TOKEN}\n"
            f"    AND {dim_col} IS NOT NULL\n"
            f"    AND TRIM({dim_col}) <> ''\n"
            "  GROUP BY 1\n"
            ")\n"
            "SELECT\n"
            f"  {dim_col},\n"
            f"  {self._round_2dp(profit_margin_expr)} AS profit_margin,\n"
            f"  {self._round_2dp('revenue')} AS total_revenue,\n"
            f"  {self._round_2dp('cogs')} AS total_cogs\n"
            "FROM agg\n"
            f"WHERE {profit_margin_expr} < 0\n"
            "ORDER BY profit_margin ASC, total_revenue DESC;\n"
        )

    def _maybe_build_profit_margin_kpi_sql_template(self, question: str) -> str | None:
        """
        Deterministic fallback for profit margin KPI prompts.

        Example: "what is my margin"
        """
        q = (question or "").strip()
        if not q:
            return None

        q_lower = q.lower()
        if "margin" not in q_lower:
            return None
        if "negative" in q_lower:
            return None

        breakdown_intent = bool(
            re.search(r"\b(by|per|grouped by|split by|breakdown)\b", q_lower)
            or "for each" in q_lower
        )
        if breakdown_intent:
            return None

        revenue_expr = self._numeric_expr("order_price_in_aed")
        cogs_expr = self._numeric_expr("cogs_in_aed")
        gross_profit_expr = f"(SUM({revenue_expr}) - SUM(COALESCE({cogs_expr}, 0)))"
        margin_expr = f"(({gross_profit_expr}) / NULLIF(SUM({revenue_expr}), 0) * 100)"

        return (
            "SELECT\n"
            f"  {self._round_2dp(margin_expr)} AS profit_margin\n"
            "FROM fact_orders\n"
            f"WHERE {FILTER_PLACEHOLDER_TOKEN};\n"
        )

    def _maybe_build_gross_profit_sql_template(self, question: str) -> str | None:
        """
        Deterministic fallback for gross profit KPI prompts.
        """
        q = (question or "").strip()
        if not q:
            return None

        q_lower = q.lower()
        if not re.search(r"\bgross\s+profit\b", q_lower):
            return None

        breakdown_intent = bool(
            re.search(r"\b(by|per|grouped by|split by|breakdown)\b", q_lower)
            or "for each" in q_lower
        )
        if breakdown_intent:
            return None

        revenue_expr = self._numeric_expr("order_price_in_aed")
        cogs_expr = self._numeric_expr("cogs_in_aed")
        gross_profit_expr = f"(SUM({revenue_expr}) - SUM(COALESCE({cogs_expr}, 0)))"

        return (
            "SELECT\n"
            f"  {self._round_2dp(gross_profit_expr)} AS gross_profit\n"
            "FROM fact_orders\n"
            f"WHERE {FILTER_PLACEHOLDER_TOKEN};\n"
        )

    def _maybe_insert_filters_placeholder(self, sql_template: str) -> str | None:
        """
        Best-effort backstop for LLM SQL that forgot to include `__MUNERO_FILTERS__`.

        Safety constraints:
        - Only applies to single SELECT statements (no WITH).
        - Must select from fact_orders (no JOINs; no multi-table FROM).
        """
        if not isinstance(sql_template, str):
            return None

        sql = sql_template.strip()
        if not sql or FILTER_PLACEHOLDER_TOKEN in sql:
            return None

        statement_start = _find_first_keyword_outside_sql_literals(sql, ("WITH", "SELECT"))
        if statement_start is None:
            return None

        leading = sql[:statement_start].strip()
        if leading:
            return None

        starts = sql[statement_start:].lstrip().upper()
        if starts.startswith("WITH"):
            return None
        if not starts.startswith("SELECT"):
            return None

        from_pos = _find_first_keyword_at_top_level(sql, ("FROM",), start=statement_start)
        if from_pos is None:
            return None

        # Parse the first table reference after FROM
        i = from_pos + len("FROM")
        while i < len(sql) and sql[i].isspace():
            i += 1
        if i >= len(sql) or sql[i] in "();":
            return None

        table_start = i
        while i < len(sql):
            ch = sql[i]
            if ch.isspace() or ch in ",;":
                break
            i += 1
        table_token = sql[table_start:i].strip()
        if not table_token:
            return None

        table_name = table_token.split(".")[-1].strip('"').strip().lower()
        if table_name != "fact_orders":
            return None

        join_pos = _find_first_keyword_at_top_level(sql, ("JOIN",), start=from_pos)
        if join_pos is not None:
            return None

        clause_after_from = _find_first_keyword_at_top_level(
            sql,
            ("WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET", "FETCH", "UNION", "EXCEPT", "INTERSECT"),
            start=from_pos + len("FROM"),
        )
        statement_end = None
        semis = _find_occurrences_outside_sql_literals(sql, ";", start=statement_start, max_matches=1)
        if semis:
            statement_end = semis[0]
        if clause_after_from is None:
            clause_after_from = statement_end if statement_end is not None else len(sql)

        # Disallow multi-table FROM (comma-separated) between FROM and the next clause.
        from_segment = sql[from_pos:clause_after_from]
        comma_positions = _find_occurrences_outside_sql_literals(from_segment, ",", max_matches=1)
        if comma_positions:
            return None

        where_pos = _find_first_keyword_at_top_level(sql, ("WHERE",), start=from_pos)
        if where_pos is not None:
            next_clause = _find_first_keyword_at_top_level(
                sql,
                ("GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET", "FETCH", "UNION", "EXCEPT", "INTERSECT"),
                start=where_pos + len("WHERE"),
            )
            if next_clause is None:
                next_clause = statement_end if statement_end is not None else len(sql)

            original_predicate = sql[where_pos + len("WHERE") : next_clause]
            if not original_predicate.strip():
                return None

            replacement = f"WHERE {FILTER_PLACEHOLDER_TOKEN} AND ({original_predicate.strip()})\n"
            rebuilt = f"{sql[:where_pos]}{replacement}{sql[next_clause:]}"
            return rebuilt.strip()

        insert_pos = clause_after_from
        if statement_end is not None:
            insert_pos = min(insert_pos, statement_end)

        insertion = f"\nWHERE {FILTER_PLACEHOLDER_TOKEN}\n"
        rebuilt = f"{sql[:insert_pos].rstrip()}{insertion}{sql[insert_pos:].lstrip()}"
        return rebuilt.strip()

    def _is_sql_balanced(self, sql: str) -> bool:
        return _is_sql_parentheses_balanced(sql)

    def _extract_requested_top_n(
        self,
        question: str,
        *,
        default: int = 10,
        min_n: int = 1,
        max_n: int = 1000,
    ) -> int:
        match = re.search(r"\btop\s+(\d{1,4})\b", (question or "").lower())
        if not match:
            requested = default
        else:
            try:
                requested = int(match.group(1))
            except Exception:
                requested = default

        requested = max(min_n, min(int(requested), max_n))
        return requested

    def _maybe_build_top_clients_by_aov_sql_template(self, question: str) -> str | None:
        """
        Deterministic fallback for: "Top N clients/customers by AOV".

        This bypasses the LLM for a highly common/structured query pattern that can
        otherwise fail due to non-SQL or policy-filtered responses.
        """
        q = (question or "").strip()
        if not q:
            return None

        q_lower = q.lower()
        if not re.search(r"\btop\s+\d{1,4}\b", q_lower):
            return None
        if not (re.search(r"\baov\b", q_lower) or "average order value" in q_lower):
            return None
        if not re.search(r"\b(clients?|customers?)\b", q_lower):
            return None

        limit = self._extract_requested_top_n(q, default=10, min_n=1, max_n=1000)

        if settings.db_dialect == "postgresql":
            revenue_expr = (
                "NULLIF(regexp_replace(order_price_in_aed::text, '[^0-9.+-]', '', 'g'), '')::double precision"
            )
            aov_expr = (
                f"ROUND((SUM({revenue_expr}) / NULLIF(COUNT(DISTINCT order_number), 0))::numeric, 2)::double precision"
            )
        else:
            aov_expr = "ROUND(SUM(order_price_in_aed) / NULLIF(COUNT(DISTINCT order_number), 0), 2)"

        return (
            "SELECT\n"
            "  client_name,\n"
            f"  {aov_expr} AS aov\n"
            "FROM fact_orders\n"
            f"WHERE {FILTER_PLACEHOLDER_TOKEN}\n"
            "GROUP BY 1\n"
            "ORDER BY aov DESC\n"
            f"LIMIT {limit};"
        )

    def generate_sql(self, question: str, filters: Optional[DashboardFilters] = None) -> str:
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
        for builder in (
            self._maybe_build_negative_margin_by_dimension_sql_template,
            self._maybe_build_profit_margin_kpi_sql_template,
            self._maybe_build_gross_profit_sql_template,
            self._maybe_build_top_clients_by_aov_sql_template,
        ):
            deterministic = builder(question)
            if deterministic:
                return deterministic

        max_attempts_raw = getattr(settings, "LLM_SQL_GENERATION_MAX_ATTEMPTS", 1)
        try:
            max_attempts = int(max_attempts_raw or 1)
        except Exception:
            max_attempts = 1
        max_attempts = max(1, min(max_attempts, 5))

        fallback_model = (getattr(settings, "LLM_FALLBACK_MODEL", None) or "").strip() or None
        fallback_max_tokens_raw = getattr(settings, "LLM_FALLBACK_MAX_OUTPUT_TOKENS", None)
        try:
            fallback_max_tokens = int(fallback_max_tokens_raw) if fallback_max_tokens_raw is not None else None
        except Exception:
            fallback_max_tokens = None
        if fallback_max_tokens is not None and fallback_max_tokens <= 0:
            fallback_max_tokens = None

        previous_output: str | None = None
        previous_reason: str | None = None

        def _reason_to_text(reason: str | None) -> str:
            return (
                reason
                or "The SQL did not meet the required contract (filters placeholder + valid single-statement SQL)."
            )

        for attempt in range(1, max_attempts + 1):
            question_for_prompt = question
            if attempt > 1:
                prev = (previous_output or "").strip()
                if len(prev) > 1800:
                    prev = prev[:1800] + "…"
                question_for_prompt = (
                    f"{question}\n\n"
                    f"IMPORTANT: Your previous output was rejected because: {_reason_to_text(previous_reason)}\n"
                    f"Return a corrected query that fully follows the filter injection contract.\n\n"
                    f"Previous output (for reference):\n{prev}\n"
                )

            prompt = self._build_sql_prompt(question_for_prompt, filters)
            use_fallback = attempt > 1 and bool(fallback_model)
            sql_model = fallback_model if use_fallback else None
            max_tokens_override = fallback_max_tokens if attempt > 1 else None

            raw_response = self._invoke_llm_with_timeout(
                prompt,
                model=sql_model,
                max_output_tokens=max_tokens_override,
            )
            sql_query = self.extract_sql_from_response(raw_response)
            candidate = (sql_query or "").strip()

            if not candidate or not candidate.upper().startswith(("SELECT", "WITH")):
                previous_output = candidate or raw_response
                previous_reason = "Output must be a single SELECT/WITH statement."
                continue

            if not self._is_sql_balanced(candidate):
                previous_output = candidate or raw_response
                previous_reason = "SQL appears truncated or has unbalanced parentheses."
                continue

            if candidate.count(FILTER_PLACEHOLDER_TOKEN) == 0:
                inserted = self._maybe_insert_filters_placeholder(candidate)
                if inserted:
                    candidate = inserted.strip()
                else:
                    previous_output = candidate or raw_response
                    previous_reason = f"Missing required filters placeholder token: {FILTER_PLACEHOLDER_TOKEN}"
                    continue

            if not self._filters_placeholder_is_valid(candidate):
                previous_output = candidate or raw_response
                previous_reason = (
                    f"SQL must include {FILTER_PLACEHOLDER_TOKEN} exactly once outside comments/quotes."
                )
                continue

            return candidate

        raise Exception(f"Invalid SQL generated ({redact_sql_for_log(previous_output)})")

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

ORDER TYPE VALUES (Important):
- When filtering by order_type, only use the exact schema values (lowercase singular):
  - 'gift_card'
  - 'merchandise'

BREAKDOWNS / VS / SPLIT QUERIES (Important):
- If the question implies a split/breakdown/vs/compare across a dimension (e.g. by order_type), return BOTH:
  - COUNT(DISTINCT order_number) AS orders
  - {round_revenue_sum_expr} AS total_revenue
  and GROUP BY the requested dimension (use positional refs like GROUP BY 1).

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

        fallback_model = (getattr(settings, "LLM_FALLBACK_MODEL", None) or "").strip() or None
        fallback_max_tokens_raw = getattr(settings, "LLM_FALLBACK_MAX_OUTPUT_TOKENS", None)
        try:
            fallback_max_tokens = int(fallback_max_tokens_raw) if fallback_max_tokens_raw is not None else None
        except Exception:
            fallback_max_tokens = None
        if fallback_max_tokens is not None and fallback_max_tokens <= 0:
            fallback_max_tokens = None

        raw_response = self._invoke_llm_with_timeout(
            prompt,
            model=fallback_model,
            max_output_tokens=fallback_max_tokens,
        )
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
