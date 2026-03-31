#!/usr/bin/env python3
"""
Family Hub — Export All Data as JSON

Connects to the PostgreSQL database and exports every user-defined table
as a JSON array, saved into a single portable JSON file.

Usage:
    python export-json.py                          # writes familyhub_export.json
    python export-json.py -o /path/to/output.json  # custom output path

Environment variables (or ../.env):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
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


def json_serializer(obj):
    """Handle non-serializable types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def get_user_tables(cur) -> list[str]:
    """Return a sorted list of user-defined table names in the public schema."""
    cur.execute(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
        """
    )
    return [row[0] for row in cur.fetchall()]


def export_table(cur, table: str) -> list[dict]:
    """Export all rows from a table as a list of dicts."""
    cur.execute(f'SELECT * FROM "{table}"')  # noqa: S608
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Family Hub DB to JSON")
    parser.add_argument(
        "-o", "--output",
        default="familyhub_export.json",
        help="Output JSON file path (default: familyhub_export.json)",
    )
    args = parser.parse_args()

    # Load .env
    script_dir = Path(__file__).resolve().parent
    load_env(str(script_dir.parent / ".env"))

    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "familyhub"),
        user=os.environ.get("POSTGRES_USER", "familyhub"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )

    try:
        cur = conn.cursor()
        tables = get_user_tables(cur)

        if not tables:
            print("No tables found in the public schema.")
            return

        export_data: dict[str, list[dict]] = {}
        for table in tables:
            rows = export_table(cur, table)
            export_data[table] = rows
            print(f"  {table}: {len(rows)} row(s)")

        with open(args.output, "w") as f:
            json.dump(export_data, f, indent=2, default=json_serializer)

        print(f"\nExported {len(tables)} table(s) to {args.output}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
