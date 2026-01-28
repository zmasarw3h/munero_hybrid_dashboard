"""
Database connection and query execution utilities.
Provides a unified interface for executing SQL queries and returning DataFrames.
"""
from typing import Optional
from sqlalchemy import create_engine
import pandas as pd

from app.core.config import settings

DB_PATH = settings.DB_FILE
DATABASE_URL = settings.DB_URI

print(f"📊 Connecting to Database at: {DB_PATH}")
print(f"🔗 Database URL: {DATABASE_URL}")

# Create Engine (check_same_thread=False is needed for SQLite with FastAPI)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


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
        print(f"✅ Query executed successfully: {len(df)} rows returned")
        return df
    except Exception as e:
        print(f"❌ Database Error: {e}")
        if settings.DEBUG_LOG_PROMPTS:
            print(f"   Query: {query}")
            print(f"   Params: {params}")
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
        print(f"❌ Database connection test failed: {e}")
        return False
