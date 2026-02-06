"""
Database connection and query execution utilities.
Provides a unified interface for executing SQL queries and returning DataFrames.
"""
import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
import pandas as pd

from app.core.config import settings
from app.core.logging_utils import redact_params_for_log, redact_sql_for_log

DB_PATH = settings.DB_FILE
DATABASE_URL = settings.DB_URI

url = make_url(DATABASE_URL)
safe_url = url.render_as_string(hide_password=True)
connect_args: dict = {}

logger = logging.getLogger(__name__)

logger.info("🗄️  Database dialect: %s", url.get_backend_name())
logger.info("🔗 Database URL: %s", safe_url)
if url.drivername.startswith("sqlite"):
    logger.info("📄 SQLite file: %s", DB_PATH)

# Create Engine (check_same_thread=False is needed for SQLite with FastAPI)
if url.drivername.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif url.get_backend_name() == "postgresql":
    connect_args = {"options": f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}"}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)


def get_data(query: str, params: Optional[dict] = None) -> pd.DataFrame:
    """
    Execute raw SQL and return a Pandas DataFrame.
    This is the core function for both Dashboard and AI queries.
    
    Args:
        query: SQL query string (can use :param_name for parameter binding)
        params: Dictionary of parameters for safe SQL parameter binding
        
    Returns:
        pd.DataFrame: Query results as a DataFrame
        
    Example:
        >>> df = get_data("SELECT * FROM fact_orders WHERE order_date >= :start", 
        ...               params={"start": "2025-01-01"})
    """
    try:
        # pd.read_sql supports standard SQL parameter binding for security
        df = pd.read_sql(query, engine, params=params)
        if settings.DEBUG:
            logger.debug("✅ Query executed (rows=%s, sql=%s)", len(df), redact_sql_for_log(query))
        return df
    except Exception as e:
        debug_log_prompts = bool(settings.DEBUG and settings.DEBUG_LOG_PROMPTS)
        logger.error(
            "❌ Database error (exc_type=%s, sql=%s, params=%s)",
            type(e).__name__,
            redact_sql_for_log(query, include_prefix=debug_log_prompts),
            redact_params_for_log(params or {}),
        )
        # Return empty DF on error to prevent API crash
        return pd.DataFrame()


def test_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        df = get_data("SELECT 1 as test")
        return not df.empty
    except Exception as e:
        logger.error("❌ Database connection test failed (exc_type=%s)", type(e).__name__)
        return False
