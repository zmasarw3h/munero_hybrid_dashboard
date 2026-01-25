"""
Core configuration for Munero AI Platform backend.
Centralized settings for database, LLM, and application behavior.
"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Munero AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database
    DB_FILE: str = str(Path(__file__).parent.parent.parent.parent / "data" / "munero.sqlite")
    DB_URI: str = f"sqlite:///{DB_FILE}"
    
    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT: int = 60  # seconds
    SQL_TIMEOUT: int = 30  # seconds
    
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
