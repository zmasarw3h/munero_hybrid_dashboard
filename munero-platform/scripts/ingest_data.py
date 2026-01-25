"""
Data Ingestion Script for Munero AI Platform
Loads CSV files into SQLite database with proper formatting and cleaning.
"""
import pandas as pd
import sqlite3
import os
from pathlib import Path

# CSV Source Paths
FILES = {
    "dim_customer": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_customer_rows.csv",
    "dim_products": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_products_rows.csv",
    "dim_suppliers": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_suppliers_rows.csv",
    "fact_orders": "/Users/zmasarweh/Documents/Munero_CSV_Data/fact_orders_rows_converted.csv"
}

# Output database path
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR.parent / "data" / "munero.sqlite"


def setup_database():
    """
    Loads CSVs into SQLite with proper date formatting and column cleaning.
    """
    print(f"🔧 Initializing database at: {DB_PATH}")
    
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database if present
    if DB_PATH.exists():
        print(f"⚠️  Removing existing database: {DB_PATH}")
        DB_PATH.unlink()
    
    # Create connection
    conn = sqlite3.connect(str(DB_PATH))
    
    for table_name, path in FILES.items():
        print(f"\n📊 Processing table: {table_name}")
        
        # Validate file exists
        if not os.path.exists(path):
            print(f"❌ ERROR: File not found: {path}")
            conn.close()
            return False
        
        # Load CSV
        print(f"   📥 Reading CSV: {path}")
        df = pd.read_csv(path)
        print(f"   ✓ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Clean column names (lowercase + snake_case)
        original_columns = df.columns.tolist()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        print(f"   ✓ Cleaned column names: {df.columns.tolist()[:5]}...")
        
        # Convert date columns to ISO format (YYYY-MM-DD)
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        if date_columns:
            print(f"   📅 Converting date columns: {date_columns}")
            for col in date_columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                null_count = df[col].isna().sum()
                if null_count > 0:
                    print(f"      ⚠️  {null_count} invalid dates converted to NULL in {col}")
        
        # Write to SQLite
        print(f"   💾 Writing to SQLite table: {table_name}")
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"   ✅ Successfully created table: {table_name}")
    
    # Verify tables were created
    print("\n🔍 Verifying database integrity...")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"✅ Database created successfully with {len(tables)} tables:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   - {table[0]}: {count:,} rows")
    
    conn.close()
    print(f"\n🎉 Database ready at: {DB_PATH}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Munero AI Platform - Data Ingestion")
    print("=" * 60)
    
    success = setup_database()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ DATA INGESTION COMPLETE")
        print("=" * 60)
        exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ DATA INGESTION FAILED")
        print("=" * 60)
        exit(1)
