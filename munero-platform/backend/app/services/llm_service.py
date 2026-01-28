"""
LLM Service for AI Chat Integration.
Ports the AI functionality from the Streamlit app (app.py) to FastAPI.
Handles natural language to SQL conversion with dashboard filter context.
"""
import re
import sqlite3
import pandas as pd
from typing import Optional, Tuple, List, Any, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from langchain_ollama import ChatOllama

from app.models import DashboardFilters
from app.core.config import settings


# ============================================================================
# CONFIGURATION
# ============================================================================

LLM_CONFIG = {
    "model": settings.OLLAMA_MODEL,
    "base_url": settings.OLLAMA_BASE_URL,
    "temperature": settings.LLM_TEMPERATURE,
    "llm_timeout": settings.LLM_TIMEOUT,  # Timeout for LLM requests in seconds
    "sql_timeout": settings.SQL_TIMEOUT,  # Timeout for SQL execution in seconds
}

DB_PATH = Path(settings.DB_FILE)


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
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        llm_timeout: Optional[int] = None,
        sql_timeout: Optional[int] = None,
        db_path: Optional[Path] = None,
    ):
        """
        Initialize the LLM service.
        
        Args:
            model: Ollama model name (default: qwen2.5-coder:7b)
            base_url: Ollama server URL (default: http://localhost:11434)
            temperature: LLM temperature (default: 0)
            llm_timeout: Timeout for LLM requests in seconds (default: 60)
            sql_timeout: Timeout for SQL execution in seconds (default: 30)
            db_path: Path to SQLite database (default: backend/data/munero.sqlite)
        """
        self.model = model or LLM_CONFIG["model"]
        self.base_url = base_url or LLM_CONFIG["base_url"]
        self.temperature = temperature if temperature is not None else LLM_CONFIG["temperature"]
        self.llm_timeout = llm_timeout or LLM_CONFIG["llm_timeout"]
        self.sql_timeout = sql_timeout or LLM_CONFIG["sql_timeout"]
        self.db_path = db_path or DB_PATH
        
        self._llm: Optional[ChatOllama] = None
    
    @property
    def llm(self) -> ChatOllama:
        """Lazy-load the LLM instance."""
        if self._llm is None:
            self._llm = ChatOllama(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature,
            )
        return self._llm
    
    def check_connection(self) -> bool:
        """
        Check if Ollama is running and the model is available.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if our model (or its base name) is available
                return any(self.model in name or name.startswith(self.model.split(":")[0]) for name in model_names)
            return False
        except Exception:
            return False
    
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
  - order_date (TEXT): Transaction date in YYYY-MM-DD format

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

    def build_filter_clause(self, filters: Optional[DashboardFilters]) -> Tuple[str, str]:
        """
        Convert dashboard filters into SQL WHERE clause components.
        
        Args:
            filters: Dashboard filter state from frontend
            
        Returns:
            Tuple of (human_readable_context, sql_where_clause)
        """
        if filters is None:
            return "No active filters (analyzing all data)", "is_test = 0"
        
        context_parts = []
        where_clauses = ["is_test = 0"]  # Always filter out test data
        
        # Date range filter
        if filters.start_date:
            end_date_str = str(filters.end_date) if filters.end_date else "present"
            context_parts.append(f"Date Range: {filters.start_date} to {end_date_str}")
            
            if filters.end_date:
                where_clauses.append(
                    f"order_date BETWEEN '{filters.start_date}' AND '{filters.end_date}'"
                )
            else:
                where_clauses.append(f"order_date >= '{filters.start_date}'")
        
        # Country filter
        if filters.countries:
            context_parts.append(f"Countries: {', '.join(filters.countries)}")
            country_list = "', '".join(filters.countries)
            where_clauses.append(f"client_country IN ('{country_list}')")
        
        # Product types filter
        if filters.product_types:
            context_parts.append(f"Product Types: {', '.join(filters.product_types)}")
            type_list = "', '".join(filters.product_types)
            where_clauses.append(f"order_type IN ('{type_list}')")
        
        # Clients filter
        if filters.clients:
            context_parts.append(f"Clients: {', '.join(filters.clients)}")
            client_list = "', '".join(filters.clients)
            where_clauses.append(f"client_name IN ('{client_list}')")
        
        # Brands filter
        if filters.brands:
            context_parts.append(f"Brands: {', '.join(filters.brands)}")
            brand_list = "', '".join(filters.brands)
            where_clauses.append(f"product_brand IN ('{brand_list}')")
        
        # Suppliers filter
        if filters.suppliers:
            context_parts.append(f"Suppliers: {', '.join(filters.suppliers)}")
            supplier_list = "', '".join(filters.suppliers)
            where_clauses.append(f"supplier_name IN ('{supplier_list}')")
        
        context_str = "\n- ".join([""] + context_parts) if context_parts else "No active filters"
        where_clause_sql = " AND ".join(where_clauses)
        
        return context_str.strip(), where_clause_sql

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
        filter_context, where_clause = self.build_filter_clause(filters)
        
        # Build filter injection section
        if filters and (filters.start_date or filters.countries or filters.product_types 
                       or filters.clients or filters.brands or filters.suppliers):
            filter_section = f"""
ACTIVE DASHBOARD FILTERS (apply these to your query):
{filter_context}

Your SQL MUST include this WHERE clause (or extend it):
WHERE {where_clause}
"""
        else:
            filter_section = f"""
NO ACTIVE FILTERS - but ALWAYS include:
WHERE {where_clause}
"""
        
        return f"""You are a SQLite expert for the 'Munero' sales analytics database.

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
2. Dates in order_date are in YYYY-MM-DD format
3. Use BETWEEN for date ranges: WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31'
4. For monthly grouping: strftime('%Y-%m', order_date)
5. For "Top N" queries: Use ORDER BY <metric> DESC LIMIT N
6. Always use table alias if needed (e.g., fo for fact_orders)
7. Round currency values: ROUND(SUM(order_price_in_aed), 2)
8. Handle NULL COGS: COALESCE(cogs_in_aed, 0)
9. End queries with semicolon
10. NO markdown formatting in output - just raw SQL

EXAMPLE QUERIES:
----------------
Q: "What are my top 5 products by revenue?"
A: SELECT product_name, ROUND(SUM(order_price_in_aed), 2) as total_revenue 
   FROM fact_orders 
   WHERE {where_clause}
   GROUP BY product_name 
   ORDER BY total_revenue DESC 
   LIMIT 5;

Q: "Show monthly revenue trend"
A: SELECT strftime('%Y-%m', order_date) as month, ROUND(SUM(order_price_in_aed), 2) as revenue 
   FROM fact_orders 
   WHERE {where_clause}
   GROUP BY month 
   ORDER BY month;

Q: "What is total revenue?"
A: SELECT ROUND(SUM(order_price_in_aed), 2) as total_revenue 
   FROM fact_orders 
   WHERE {where_clause};

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
            response = self.llm.invoke(prompt)
            content = response.content
            # Handle case where content might be a list
            if isinstance(content, list):
                return str(content[0]) if content else ""
            return str(content)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_invoke)
            try:
                return future.result(timeout=self.llm_timeout)
            except FuturesTimeoutError:
                raise TimeoutError(f"LLM request timed out after {self.llm_timeout} seconds")

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
            raise Exception(f"Invalid SQL generated: {sql_query[:100]}...")
        
        return sql_query

    def execute_sql(self, sql: str, conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
        """
        Execute SQL query with timeout protection.
        
        Args:
            sql: SQL query to execute
            conn: Optional SQLite connection (creates new one if not provided)
            
        Returns:
            pd.DataFrame: Query results
            
        Raises:
            TimeoutError: If query exceeds timeout
            Exception: If query execution fails
        """
        should_close_conn = False
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            should_close_conn = True
        
        def _execute():
            return pd.read_sql_query(sql, conn)
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute)
                try:
                    return future.result(timeout=self.sql_timeout)
                except FuturesTimeoutError:
                    raise TimeoutError(f"SQL query timed out after {self.sql_timeout} seconds")
        finally:
            if should_close_conn:
                conn.close()

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
        sql = self.generate_sql(question, filters)
        df = self.execute_sql(sql)
        return df, sql


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_llm_service() -> LLMService:
    """Factory function to get a configured LLMService instance."""
    return LLMService()
