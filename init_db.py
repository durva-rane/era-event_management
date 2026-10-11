#!/usr/bin/env python3
"""
ERA: Event Resource & Administration System
Database Initialization & Seeding Script
"""

import os
import sys
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

# Load environment configuration
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "era_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "SEPro@22")
DB_NAME = os.getenv("DB_NAME", "era_db")


def run_sql_file(cursor, file_path: Path):
    """Executes multi-statement SQL script cleanly."""
    print(f"[*] Executing {file_path.name}...")
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split statements by semicolon while respecting comments and blocks
    statements = []
    current_stmt = []
    in_comment = False

    for line in sql_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
            continue
        current_stmt.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current_stmt))
            current_stmt = []

    for stmt in statements:
        clean = stmt.strip()
        if clean:
            cursor.execute(clean)


def init_database():
    """Initializes schema and seeds sample records."""
    print("=" * 60)
    print("ERA Database Initialization & Seeding")
    print("=" * 60)
    print(f"Target Server: {DB_HOST}:{DB_PORT}")
    print(f"User:          {DB_USER}")
    print(f"Database:      {DB_NAME}")
    print("-" * 60)

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        cursor = conn.cursor()

        # Ensure database exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{DB_NAME}`;")

        # Execute schema
        schema_path = BASE_DIR / "schema.sql"
        run_sql_file(cursor, schema_path)
        print("[✓] Schema created successfully.")

        # Execute seeds
        seeds_path = BASE_DIR / "seeds.sql"
        run_sql_file(cursor, seeds_path)
        print("[✓] Seed data inserted successfully.")

        # Summary of created tables
        cursor.execute("SHOW TABLES;")
        tables = [t[0] for t in cursor.fetchall()]
        print("-" * 60)
        print(f"Total Tables in `{DB_NAME}`: {len(tables)}")
        for t in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`;")
            count = cursor.fetchone()[0]
            print(f"  - {t:<28}: {count} records")

        # Check required index on bookings
        cursor.execute("SHOW INDEX FROM bookings WHERE Key_name = 'idx_bookings_venue_conflict';")
        idx_cols = [row[4] for row in cursor.fetchall()]
        print("-" * 60)
        print(f"[✓] Conflict Index `idx_bookings_venue_conflict`: {idx_cols}")

        cursor.close()
        conn.close()
        print("=" * 60)
        print("Database initialized and ready.")
        print("=" * 60)

    except mysql.connector.Error as err:
        print(f"[!] MySQL Error: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as ex:
        print(f"[!] Error: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    init_database()
