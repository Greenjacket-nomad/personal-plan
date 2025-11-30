#!/usr/bin/env python3
"""P5 migrations: user_modified flag, unique index"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def index_exists(conn, index_name):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cur.fetchone() is not None

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Issue 55: user_modified flag
        if not column_exists(conn, "resources", "user_modified"):
            conn.execute("ALTER TABLE resources ADD COLUMN user_modified INTEGER DEFAULT 0")
            # Mark all existing user-added resources as user_modified
            conn.execute("UPDATE resources SET user_modified = 1 WHERE source = 'user'")
            print("✓ Added user_modified column")
        else:
            print("  user_modified column already exists")
        
        # Issue 57: Unique index for duplicate prevention
        if not index_exists(conn, "idx_resource_unique"):
            try:
                conn.execute("""
                    CREATE UNIQUE INDEX idx_resource_unique 
                    ON resources(phase_index, week, day, title)
                    WHERE phase_index IS NOT NULL AND week IS NOT NULL AND day IS NOT NULL
                """)
                print("✓ Created unique index for duplicate prevention")
            except sqlite3.IntegrityError:
                print("⚠ Could not create unique index (duplicates may exist)")
        else:
            print("  unique index already exists")
        
        conn.commit()
        print("\n✓ P5 migrations complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running P5 migrations...\n")
    migrate()

