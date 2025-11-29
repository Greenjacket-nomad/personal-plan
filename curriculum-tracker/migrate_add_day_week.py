#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Add day column if missing
        if not column_exists(conn, "resources", "day"):
            conn.execute("ALTER TABLE resources ADD COLUMN day INTEGER")
        # Add week column if missing (phase-relative week 1-5)
        if not column_exists(conn, "resources", "week"):
            conn.execute("ALTER TABLE resources ADD COLUMN week INTEGER")
        conn.commit()
        print("Migration complete: day/week columns present on resources.")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
