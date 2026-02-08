"""
LLM Service for AI Chat Integration.
Ports the AI functionality from the Streamlit app (app.py) to FastAPI.
Handles natural language to SQL conversion with dashboard filter context.
"""
import re
import pandas as pd
from typing import Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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
        predicate_parts: list[str] = ["is_test = 0"]
        params: dict[str, Any] = {}

        if filters is None:
            return " AND ".join(predicate_parts), params

        # Date range filter
        if filters.start_date and filters.end_date:
            predicate_parts.append("order_date BETWEEN :munero_start_date AND :munero_end_date")
            params["munero_start_date"] = str(filters.start_date)
            params["munero_end_date"] = str(filters.end_date)
        elif filters.start_date:
            predicate_parts.append("order_date >= :munero_start_date")
            params["munero_start_date"] = str(filters.start_date)
        elif filters.end_date:
            predicate_parts.append("order_date <= :munero_end_date")
            params["munero_end_date"] = str(filters.end_date)

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

        The LLM output must contain `__MUNERO_FILTERS__` exactly once.
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

        predicate, params = self.build_filter_predicate(filters)
        return sql.replace(FILTER_PLACEHOLDER_TOKEN, predicate), params

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
        month_grouping = (
            "to_char(order_date::date, 'YYYY-MM')" if settings.db_dialect == "postgresql"
            else "strftime('%Y-%m', order_date)"
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
- "revenue" or "sales" → SUM(order_price_in_aed)
- "profit" or "gross profit" → SUM(order_price_in_aed - cogs_in_aed)
- "margin" or "profit margin" → (SUM(order_price_in_aed) - SUM(cogs_in_aed)) / SUM(order_price_in_aed) * 100
- "orders" or "order count" → COUNT(DISTINCT order_number)
- "quantity sold" → SUM(quantity)
- "AOV" or "average order value" → SUM(order_price_in_aed) / COUNT(DISTINCT order_number)

CRITICAL SQL RULES:
-------------------
1. fact_orders is DENORMALIZED - NO JOINS needed for most queries!
2. You MUST include: WHERE {FILTER_PLACEHOLDER_TOKEN} (exactly once)
3. Return exactly ONE SQL statement (no extra semicolons)
4. The statement MUST start with SELECT or WITH (read-only)
5. NEVER use write/admin keywords: INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, INTO, COPY, EXEC/EXECUTE, CALL, VACUUM, PRAGMA, ATTACH/DETACH
6. Dates in order_date are in YYYY-MM-DD format
7. For monthly grouping: {month_grouping}
8. For "Top N" queries: Use ORDER BY <metric> DESC LIMIT N
9. Always use table alias if needed (e.g., fo for fact_orders)
10. Round currency values: ROUND(SUM(order_price_in_aed), 2)
11. Handle NULL COGS: COALESCE(cogs_in_aed, 0)
12. End queries with semicolon
13. NO markdown formatting in output - just raw SQL

EXAMPLE QUERIES:
----------------
Q: "What are my top 5 products by revenue?"
A: SELECT product_name, ROUND(SUM(order_price_in_aed), 2) as total_revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN}
   GROUP BY product_name 
   ORDER BY total_revenue DESC 
   LIMIT 5;

Q: "Show monthly revenue trend"
A: SELECT {month_grouping} as month, ROUND(SUM(order_price_in_aed), 2) as revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN}
   GROUP BY month 
   ORDER BY month;

Q: "What is total revenue?"
A: SELECT ROUND(SUM(order_price_in_aed), 2) as total_revenue 
   FROM fact_orders 
   WHERE {FILTER_PLACEHOLDER_TOKEN};

NOW ANSWER THIS QUESTION:
{question}

Return ONLY the raw SQL query. No markdown. No explanations. No extra text.

SQL:"""

    def _invoke_llm_with_timeout(self, prompt: str) -> str:
        """
        Invoke the LLM with timeout protection.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            str: The LLM response content
            
        Raises:
            TimeoutError: If the request exceeds the timeout
        """
        def _invoke() -> str:
            if self.provider != "gemini":
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            return self.gemini.generate_text(prompt)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_invoke)
            try:
                return future.result(timeout=self.llm_timeout)
            except FuturesTimeoutError:
                raise TimeoutError(f"LLM request timed out after {self.llm_timeout} seconds")
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
        
        # Method 1: Extract from ```sql code block
        match = re.search(r'```sql\s+(.*?)\s+```', response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Method 2: Extract from generic ``` code block
        match = re.search(r'```\s+(.*?)\s+```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Method 3: Find SELECT/WITH statement
        match = re.search(
            r'((?:WITH|SELECT|INSERT|UPDATE|DELETE)\s+.*?)(?:;|\n\n|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if match:
            sql = match.group(1).strip()
            # Ensure it ends with semicolon
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        # Method 4: Remove common prefixes and return
        cleaned = re.sub(r'^(SQL:|Query:)\s*', '', response, flags=re.IGNORECASE)
        return cleaned.strip()
    
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

    def execute_sql(
        self,
        sql: str,
        conn: Optional[Any] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute SQL query with timeout protection.
        
        Args:
            sql: SQL query to execute
            conn: Optional SQLAlchemy/DBAPI connection (defaults to configured engine)
            params: Optional bound params dict for safe execution
            
        Returns:
            pd.DataFrame: Query results
            
        Raises:
            TimeoutError: If query exceeds timeout
            Exception: If query execution fails
        """
        sql_conn: Any = conn or engine
        
        def _execute():
            return execute_query_df(sql, conn=sql_conn, params=params)
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute)
                try:
                    return future.result(timeout=self.sql_timeout)
                except FuturesTimeoutError:
                    raise TimeoutError(f"SQL query timed out after {self.sql_timeout} seconds")
        finally:
            # If the caller provided a connection, they own its lifecycle.
            pass

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
