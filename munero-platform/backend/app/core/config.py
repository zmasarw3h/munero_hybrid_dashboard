"""
Core configuration for Munero AI Platform backend.
Centralized settings for database, LLM, and application behavior.
"""
import ast
import json
from importlib.util import find_spec
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlsplit
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Munero AI Platform"
    APP_VERSION: str = "1.0.0"
    # Production-safe defaults. Enable only for local development.
    DEBUG: bool = False
    # WARNING: When enabled, logs may include sensitive user prompts/responses.
    DEBUG_LOG_PROMPTS: bool = False
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    # CORS Origins as a comma-separated string or JSON list
    # Examples:
    #   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
    #   CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Database
    DB_FILE: str = str(Path(__file__).parent.parent.parent.parent / "data" / "munero.sqlite")
    # Allow common hosting env var name (DATABASE_URL)
    DB_URI: Optional[str] = Field(default=None, validation_alias=AliasChoices("DB_URI", "DATABASE_URL"))
    # Postgres per-statement timeout (milliseconds). Applied via connection options.
    DB_STATEMENT_TIMEOUT_MS: int = 30000
    
    # LLM Configuration
    # Provider name. For hosted deployments, default to Gemini.
    LLM_PROVIDER: str = "gemini"
    # Provider API key (server-side only). Supports common aliases.
    LLM_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    # Provider model name. For Gemini, e.g. "gemini-2.5-flash".
    LLM_MODEL: str = "gemini-2.5-flash"
    # Provider base URL (for Gemini API, this is the Generative Language API base).
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT: int = 60  # seconds
    LLM_MAX_OUTPUT_TOKENS: int = 512
    LLM_RETRIES: int = 2
    SQL_TIMEOUT: int = 30  # seconds
    # When SQL execution fails, optionally let the LLM attempt a single repair of the SQL template.
    # Set to 0 to disable (recommended for strict/low-latency deployments).
    LLM_SQL_REPAIR_MAX_ATTEMPTS: int = 1
    
    # Query Settings
    MAX_DISPLAY_ROWS: int = 1000
    SHOW_SQL_DEFAULT: bool = True
    
    # SmartRender Configuration
    MAX_CHART_CATEGORIES: int = 15
    LONG_LABEL_THRESHOLD: int = 20
    PIE_CHART_MAX: int = 8
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def model_post_init(self, __context) -> None:
        # Normalize common but non-SQLAlchemy DSN scheme
        if self.DB_URI and self.DB_URI.startswith("postgres://"):
            self.DB_URI = self.DB_URI.replace("postgres://", "postgresql://", 1)

        # SQLAlchemy defaults to the psycopg2 driver for "postgresql://" URLs.
        # Our hosted stack uses psycopg (v3) via `psycopg[binary]`, so make the
        # driver explicit when a plain Postgres URL is provided (e.g. from
        # Supabase or Render).
        if self.DB_URI and self.DB_URI.startswith("postgresql://") and find_spec("psycopg") is not None:
            self.DB_URI = self.DB_URI.replace("postgresql://", "postgresql+psycopg://", 1)

        if not self.DB_URI:
            self.DB_URI = f"sqlite:///{self.DB_FILE}"

    @property
    def cors_origins_list(self) -> List[str]:
        raw_value = (self.CORS_ORIGINS or "").strip()
        if not raw_value:
            return []

        value = raw_value.strip()
        # Some hosting dashboards wrap env var values in quotes; be tolerant.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1].strip()

        def _clean_origin(origin: object) -> str:
            o = str(origin).strip()
            if not o:
                return ""

            # Strip surrounding quotes repeatedly (common misconfiguration).
            for _ in range(2):
                if len(o) >= 2 and o[0] == o[-1] and o[0] in ("'", '"'):
                    o = o[1:-1].strip()

            # Origins never include trailing slashes; strip if present.
            o = o.rstrip("/")

            # If someone pasted a full URL (with path/query), normalize to origin.
            if o.startswith(("http://", "https://")):
                split = urlsplit(o)
                if split.scheme and split.netloc:
                    o = f"{split.scheme}://{split.netloc}"
            return o

        parsed_origins: list[str] | None = None

        # Prefer list formats when provided.
        if value.startswith("[") or value.startswith("("):
            # 1) JSON list
            try:
                loaded = json.loads(value)
            except Exception:
                loaded = None

            if isinstance(loaded, list):
                parsed_origins = [_clean_origin(o) for o in loaded]
            else:
                # 2) Python/INI-style list, e.g. ['https://x','http://localhost:3000']
                try:
                    loaded = ast.literal_eval(value)
                except Exception:
                    loaded = None
                if isinstance(loaded, (list, tuple, set)):
                    parsed_origins = [_clean_origin(o) for o in loaded]

        if parsed_origins is None:
            # Comma/semicolon-separated
            parts = value.replace(";", ",").split(",")
            parsed_origins = [_clean_origin(p) for p in parts]

        # Filter empties and dedupe (preserve order).
        seen: set[str] = set()
        origins: list[str] = []
        for origin in parsed_origins:
            if not origin:
                continue
            if origin in seen:
                continue
            seen.add(origin)
            origins.append(origin)

        return origins

    @property
    def db_dialect(self) -> str:
        """
        A lightweight database dialect hint used for SQL string generation.

        Returns:
            "sqlite", "postgresql", or "unknown"
        """
        uri = (self.DB_URI or "").lower()
        if uri.startswith("sqlite"):
            return "sqlite"
        if uri.startswith("postgres"):
            return "postgresql"
        return "unknown"


# Singleton instance
settings = Settings()


# Database tables configuration
DB_TABLES = ['dim_customer', 'dim_products', 'dim_suppliers', 'fact_orders']


# SQL Prompt Template Constants
SCHEMA_FOREIGN_KEYS = """
FOREIGN KEY RELATIONSHIPS:
- fact_orders.customer_id → dim_customer.customer_id (PK)
- fact_orders.product_id → dim_products.product_id (PK)
- fact_orders.supplier_id → dim_suppliers.supplier_id (PK)
"""

TERMINOLOGY_MAPPING = """
TERMINOLOGY MAPPING:
- User says "client" or "customer" → Use fact_orders.client_name
- User says "product category" → Use fact_orders.order_type
- User says "supplier" → Use fact_orders.supplier_name
- User says "revenue" or "sales" → Calculate as (fact_orders.sale_price * fact_orders.quantity)
- User says "orders" → Count distinct fact_orders.order_number
- User says "quantity sold" → SUM(fact_orders.quantity)
"""

SQL_GENERATION_RULES = """
CRITICAL RULES:
1. You can use <think> tags for your reasoning, then output ONLY the SQL query
2. Dates in order_date column are in YYYY-MM-DD format
3. Use BETWEEN for date ranges: WHERE order_date BETWEEN '2025-06-01' AND '2025-06-07'
4. For monthly queries: WHERE strftime('%Y-%m', order_date) = '2025-06'
5. Always use table aliases for joins
6. ORDER BY can ONLY reference columns in SELECT or use aggregate functions that are in SELECT
7. For "Top N" queries: Use ORDER BY with the aggregate column then LIMIT N
8. End with semicolon
9. No markdown formatting in the final SQL output
"""
