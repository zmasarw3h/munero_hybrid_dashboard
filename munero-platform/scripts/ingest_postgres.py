"""
Munero AI Platform - Postgres Ingestion

Loads the Munero CSV dataset into a PostgreSQL database using SQLAlchemy + pandas.

This is intended for hosted deployments (Render/Koyeb/etc.) where SQLite is not suitable.

Usage:
  python3 scripts/ingest_postgres.py --db-url "$DATABASE_URL" --csv-dir "/path/to/Munero_CSV_Data"

Environment variables:
  - DATABASE_URL / DB_URI: Postgres connection string
  - MUNERO_CSV_DIR: directory containing the CSV files (optional)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


DEFAULT_CSV_FILES: dict[str, str] = {
    "dim_customer": "dim_customer_rows.csv",
    "dim_products": "dim_products_rows.csv",
    "dim_suppliers": "dim_suppliers_rows.csv",
    "fact_orders": "fact_orders_rows_converted.csv",
}


def _normalize_postgres_url(url: str) -> str:
    # Some providers still return postgres:// which SQLAlchemy may not accept
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Keep dates as ISO strings (YYYY-MM-DD). This works well across SQLite/Postgres and
    # preserves lexical sort order in SQL when stored as TEXT.
    date_columns = [col for col in df.columns if "date" in col.lower()]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Munero CSVs into PostgreSQL")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("DB_URI"),
        help="PostgreSQL connection string (or set DATABASE_URL/DB_URI)",
    )
    parser.add_argument(
        "--csv-dir",
        default=os.environ.get("MUNERO_CSV_DIR"),
        help="Directory containing Munero CSV files (or set MUNERO_CSV_DIR)",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Optional target schema (default: database default schema)",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=2000,
        help="Insert chunksize for pandas.to_sql",
    )
    args = parser.parse_args()

    if not args.db_url:
        raise SystemExit("Missing --db-url (or DATABASE_URL/DB_URI env var).")
    if not args.csv_dir:
        raise SystemExit("Missing --csv-dir (or MUNERO_CSV_DIR env var).")

    db_url = _normalize_postgres_url(str(args.db_url))
    csv_dir = Path(args.csv_dir).expanduser().resolve()

    if not csv_dir.exists():
        raise SystemExit(f"CSV directory not found: {csv_dir}")

    print("🚀 Munero Postgres ingestion starting")
    print(f"📁 CSV dir: {csv_dir}")
    if args.schema:
        print(f"🧩 Target schema: {args.schema}")

    engine = create_engine(db_url, pool_pre_ping=True)

    for table, filename in DEFAULT_CSV_FILES.items():
        path = csv_dir / filename
        if not path.exists():
            raise SystemExit(f"Missing CSV for {table}: {path}")

        print(f"\n📊 Loading {table} from {filename}")
        df = _load_csv(path)
        print(f"   ✓ Rows: {len(df):,} | Cols: {len(df.columns)}")

        df.to_sql(
            table,
            engine,
            if_exists="replace",
            index=False,
            schema=args.schema,
            method="multi",
            chunksize=args.chunksize,
        )
        print(f"   ✅ Wrote table: {table}")

    print("\n🔍 Verifying row counts...")
    with engine.begin() as conn:
        for table in DEFAULT_CSV_FILES.keys():
            qualified = f"{args.schema}.{table}" if args.schema else table
            count = conn.execute(text(f"SELECT COUNT(*) FROM {qualified}")).scalar_one()
            print(f"   - {qualified}: {count:,} rows")

    print("\n🎉 Ingestion complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

