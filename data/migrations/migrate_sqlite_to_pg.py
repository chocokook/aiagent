#!/usr/bin/env python3
"""
Migrate TechHub data from SQLite → PostgreSQL.

Prerequisites:
    1. PostgreSQL running and DATABASE_URL set in .env
    2. Schema already created:  psql $DATABASE_URL -f data/migrations/schema.sql
    3. Dependencies installed:  uv sync

Usage:
    uv run python data/migrations/migrate_sqlite_to_pg.py
"""

import os
import sqlite3
import sys
from pathlib import Path

# ── allow running from any working directory ─────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

SQLITE_PATH = ROOT / "data" / "structured" / "techhub.db"
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("ERROR: psycopg2 not installed. Run: uv add psycopg2-binary")
    sys.exit(1)


def migrate():
    print(f"Reading SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"Connecting to PostgreSQL…")
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cur = pg_conn.cursor()

    tables = [
        (
            "customers",
            "INSERT INTO customers (customer_id, email, name, segment) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            lambda r: (r["customer_id"], r["email"], r["name"], r["segment"]),
        ),
        (
            "products",
            "INSERT INTO products (product_id, name, category, price, in_stock) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            lambda r: (r["product_id"], r["name"], r["category"], r["price"], bool(r["in_stock"])),
        ),
        (
            "orders",
            "INSERT INTO orders (order_id, customer_id, status, order_date, shipped_date, tracking_number) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            lambda r: (r["order_id"], r["customer_id"], r["status"], r["order_date"], r["shipped_date"], r["tracking_number"]),
        ),
        (
            "order_items",
            "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            lambda r: (r["order_item_id"], r["order_id"], r["product_id"], r["quantity"], r["price_per_unit"]),
        ),
    ]

    for table, sql, mapper in tables:
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        data = [mapper(r) for r in rows]
        execute_batch(pg_cur, sql, data, page_size=100)
        pg_conn.commit()
        print(f"  ✓ {table}: {len(data)} rows migrated")

    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    migrate()
