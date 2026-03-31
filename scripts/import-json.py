#!/usr/bin/env python3
"""
Family Hub — Import Data from JSON

Reads a JSON export file (produced by export-json.py) and inserts the data
into the PostgreSQL database. Existing rows with conflicting primary keys
are skipped by default, or can be upserted with --upsert.

Usage:
    python import-json.py familyhub_export.json
    python import-json.py familyhub_export.json --upsert

Environment variables (or ../.env):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("psycopg2 is required. Install with: pip install psycopg2-binary")


def load_env(env_path: str) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ."""
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def get_primary_keys(cur, table: str) -> list[str]:
    """Return the primary key column(s) for a table."""
    cur.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass
          AND i.indisprimary;
        """,
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


def import_table(cur, table: str, rows: list[dict], upsert: bool = False) -> tuple[int, int]:
    """
    Insert rows into the given table.

    Returns (inserted_count, skipped_count).
    """
    if not rows:
        return 0, 0

    columns = list(rows[0].keys())
    col_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))

    pk_cols = get_primary_keys(cur, table)

    inserted = 0
    skipped = 0

    for row in rows:
        values = [row.get(c) for c in columns]

        if upsert and pk_cols:
            conflict_cols = ", ".join(f'"{c}"' for c in pk_cols)
            update_cols = [c for c in columns if c not in pk_cols]
            if update_cols:
                update_set = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
                sql = (
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
                    f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}"
                )
            else:
                sql = (
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
                    f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                )
        elif pk_cols:
            conflict_cols = ", ".join(f'"{c}"' for c in pk_cols)
            sql = (
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
                f"ON CONFLICT ({conflict_cols}) DO NOTHING"
            )
        else:
            sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        try:
            cur.execute(sql, values)
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except psycopg2.IntegrityError:
            cur.connection.rollback()
            skipped += 1

    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import JSON data into Family Hub DB")
    parser.add_argument("input_file", help="Path to the JSON export file")
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Update existing rows on primary-key conflict (default: skip)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        sys.exit(f"Error: File not found: {args.input_file}")

    # Load .env
    script_dir = Path(__file__).resolve().parent
    load_env(str(script_dir.parent / ".env"))

    with open(args.input_file) as f:
        data: dict[str, list[dict]] = json.load(f)

    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "familyhub"),
        user=os.environ.get("POSTGRES_USER", "familyhub"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )

    try:
        cur = conn.cursor()

        for table, rows in data.items():
            inserted, skipped = import_table(cur, table, rows, upsert=args.upsert)
            status = f"{inserted} inserted"
            if skipped:
                status += f", {skipped} skipped"
            print(f"  {table}: {status}")

        conn.commit()
        print(f"\nImport complete ({len(data)} table(s)).")

    except Exception as e:
        conn.rollback()
        sys.exit(f"Import failed: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
