#!/usr/bin/env python3
"""P3 database migrations: journal, status, streaks, activity log, sort order"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def table_exists(conn, table):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Issue 37: Journal entries table
        if not table_exists(conn, "journal_entries"):
            conn.execute("""
                CREATE TABLE journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    content TEXT,
                    mood TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created journal_entries table")
        else:
            print("  journal_entries table already exists")

        # Issue 38: Status column for resources
        if not column_exists(conn, "resources", "status"):
            conn.execute("ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'not_started'")
            # Migrate existing is_completed data
            conn.execute("UPDATE resources SET status = 'complete' WHERE is_completed = 1")
            conn.execute("UPDATE resources SET status = 'not_started' WHERE is_completed = 0 OR is_completed IS NULL")
            print("✓ Added status column and migrated is_completed data")
        else:
            print("  status column already exists")

        # Issue 40: completed_at timestamp
        if not column_exists(conn, "resources", "completed_at"):
            conn.execute("ALTER TABLE resources ADD COLUMN completed_at TEXT")
            print("✓ Added completed_at column")
        else:
            print("  completed_at column already exists")

        # Issue 40: Activity log table
        if not table_exists(conn, "activity_log"):
            conn.execute("""
                CREATE TABLE activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id INTEGER,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created activity_log table")
        else:
            print("  activity_log table already exists")

        # Issue 43: sort_order column
        if not column_exists(conn, "resources", "sort_order"):
            conn.execute("ALTER TABLE resources ADD COLUMN sort_order INTEGER DEFAULT 0")
            print("✓ Added sort_order column")
        else:
            print("  sort_order column already exists")

        conn.commit()
        print("\n✓ P3 migrations complete!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running P3 migrations...\n")
    migrate()

