#!/usr/bin/env python3
"""P4 migrations: config→progress, effort estimates"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def table_exists(conn, table):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Issue 48: Config → Progress table
        if not table_exists(conn, "progress"):
            conn.execute("""
                CREATE TABLE progress (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_phase INTEGER DEFAULT 0,
                    current_week INTEGER DEFAULT 1,
                    started_at TEXT,
                    last_activity_at TEXT
                )
            """)
            
            # Migrate from config if exists
            if table_exists(conn, "config"):
                cur = conn.execute("SELECT key, value FROM config")
                config = {row[0]: row[1] for row in cur.fetchall()}
                start_date = config.get('start_date')
                conn.execute("""
                    INSERT INTO progress (id, current_phase, current_week, started_at)
                    VALUES (1, ?, ?, ?)
                """, (
                    int(config.get('current_phase', 0)),
                    int(config.get('current_week', 1)),
                    start_date
                ))
                print("✓ Created progress table, migrated config")
            else:
                conn.execute("INSERT INTO progress (id) VALUES (1)")
                print("✓ Created progress table")
        else:
            print("  progress table already exists")
        
        # Issue 51: Effort estimates
        if not column_exists(conn, "resources", "estimated_minutes"):
            conn.execute("ALTER TABLE resources ADD COLUMN estimated_minutes INTEGER")
            print("✓ Added estimated_minutes column")
        else:
            print("  estimated_minutes column already exists")
        
        if not column_exists(conn, "resources", "difficulty"):
            conn.execute("ALTER TABLE resources ADD COLUMN difficulty TEXT")
            print("✓ Added difficulty column")
        else:
            print("  difficulty column already exists")
        
        # Set default estimates by resource type
        defaults = {
            'Article': (20, 'easy'),
            'Docs': (45, 'medium'),
            'Tutorial': (90, 'medium'),
            'Course': (240, 'hard'),
            'Video': (30, 'easy'),
            'Project': (180, 'hard'),
            'Lab': (120, 'medium'),
            'Action': (15, 'easy'),
            'Note': (5, 'easy'),
            'Deliverable': (240, 'hard')
        }
        
        for rtype, (minutes, diff) in defaults.items():
            result = conn.execute("""
                UPDATE resources 
                SET estimated_minutes = ?, difficulty = ?
                WHERE (estimated_minutes IS NULL OR difficulty IS NULL)
                AND id IN (
                    SELECT r.id FROM resources r
                    JOIN resource_tags rt ON r.id = rt.resource_id
                    JOIN tags t ON rt.tag_id = t.id
                    WHERE t.name = ?
                )
            """, (minutes, diff, rtype))
            if result.rowcount > 0:
                print(f"  Set estimates for {result.rowcount} {rtype} resources")
        
        conn.commit()
        print("\n✓ P4 migrations complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running P4 migrations...\n")
    migrate()

