"""
Database connection and query execution utilities.
Provides a unified interface for executing SQL queries and returning DataFrames.
"""
import os
from typing import Optional
from sqlalchemy import create_engine
import pandas as pd

# LOGIC: 
# __file__ is backend/app/core/database.py
# We need to navigate up to the project root: backend/app/core -> backend/app -> backend -> munero-platform
# Then go into /data
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "munero.sqlite")
DATABASE_URL = f"sqlite:///{DB_PATH}"

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
