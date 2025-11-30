#!/usr/bin/env python3
"""Prompt 2 database migrations: journal entries curriculum day linking"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Link journal entries to curriculum days
        if not column_exists(conn, "journal_entries", "phase_index"):
            conn.execute("ALTER TABLE journal_entries ADD COLUMN phase_index INTEGER")
            print("✓ Added phase_index to journal_entries")
        else:
            print("  phase_index column already exists")
        
        if not column_exists(conn, "journal_entries", "week"):
            conn.execute("ALTER TABLE journal_entries ADD COLUMN week INTEGER")
            print("✓ Added week to journal_entries")
        else:
            print("  week column already exists")
        
        if not column_exists(conn, "journal_entries", "day"):
            conn.execute("ALTER TABLE journal_entries ADD COLUMN day INTEGER")
            print("✓ Added day to journal_entries")
        else:
            print("  day column already exists")
        
        conn.commit()
        print("\n✓ Prompt 2 migrations complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running Prompt 2 migrations...\n")
    migrate()

