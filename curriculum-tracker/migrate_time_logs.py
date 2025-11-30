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
        # Add week column to time_logs
        if not column_exists(conn, "time_logs", "week"):
            conn.execute("ALTER TABLE time_logs ADD COLUMN week INTEGER")
            print("✓ Added 'week' column to time_logs")
        else:
            print("  'week' column already exists in time_logs")
        
        # Add day column to time_logs
        if not column_exists(conn, "time_logs", "day"):
            conn.execute("ALTER TABLE time_logs ADD COLUMN day INTEGER")
            print("✓ Added 'day' column to time_logs")
        else:
            print("  'day' column already exists in time_logs")
        
        # Add resource_id column to time_logs
        if not column_exists(conn, "time_logs", "resource_id"):
            conn.execute("ALTER TABLE time_logs ADD COLUMN resource_id INTEGER REFERENCES resources(id)")
            print("✓ Added 'resource_id' column to time_logs")
        else:
            print("  'resource_id' column already exists in time_logs")
        
        # Add resource_id column to completed_metrics
        if not column_exists(conn, "completed_metrics", "resource_id"):
            conn.execute("ALTER TABLE completed_metrics ADD COLUMN resource_id INTEGER REFERENCES resources(id)")
            print("✓ Added 'resource_id' column to completed_metrics")
        else:
            print("  'resource_id' column already exists in completed_metrics")
        
        conn.commit()
        print("\n✓ Migration complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running time_logs migration...\n")
    migrate()

