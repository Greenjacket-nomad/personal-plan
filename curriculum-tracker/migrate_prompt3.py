#!/usr/bin/env python3
"""Prompt 3 database migrations: schedule system, settings, blocked days"""

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
        # Add scheduled_date to resources
        if not column_exists(conn, "resources", "scheduled_date"):
            conn.execute("ALTER TABLE resources ADD COLUMN scheduled_date DATE")
            print("✓ Added scheduled_date to resources")
        else:
            print("  scheduled_date column already exists")
        
        # Add original_date to resources
        if not column_exists(conn, "resources", "original_date"):
            conn.execute("ALTER TABLE resources ADD COLUMN original_date DATE")
            print("✓ Added original_date to resources")
        else:
            print("  original_date column already exists")
        
        # Create blocked_days table
        if not table_exists(conn, "blocked_days"):
            conn.execute("""
                CREATE TABLE blocked_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created blocked_days table")
        else:
            print("  blocked_days table already exists")
        
        # Create settings table
        if not table_exists(conn, "settings"):
            conn.execute("""
                CREATE TABLE settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            print("✓ Created settings table")
        else:
            print("  settings table already exists")
        
        conn.commit()
        print("\n✓ Prompt 3 migrations complete!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running Prompt 3 migrations...\n")
    migrate()

