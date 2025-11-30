#!/usr/bin/env python3
"""Prompt 4 database migrations: attachments, uploads folder, junk tag cleanup"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"
UPLOAD_FOLDER = Path(__file__).parent / "uploads"

def table_exists(conn, table):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Create attachments table
        if not table_exists(conn, "attachments"):
            conn.execute("""
                CREATE TABLE attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    resource_id INTEGER,
                    journal_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
                    FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE
                )
            """)
            print("✓ Created attachments table")
        else:
            print("  attachments table already exists")
        
        # Create uploads folder
        if not UPLOAD_FOLDER.exists():
            UPLOAD_FOLDER.mkdir()
            print("✓ Created uploads folder")
        else:
            print("  uploads folder already exists")
        
        # Cleanup junk tags
        junk = ['Postgres', 'postgres', 'test', 'TODO', 'temp']
        removed_count = 0
        for tag in junk:
            cur = conn.execute("SELECT COUNT(*) FROM tags WHERE name = ?", (tag,))
            count = cur.fetchone()[0]
            if count > 0:
                conn.execute("DELETE FROM tags WHERE name = ?", (tag,))
                removed_count += count
        
        # Remove orphaned resource_tags
        conn.execute("""
            DELETE FROM resource_tags 
            WHERE tag_id NOT IN (SELECT id FROM tags)
        """)
        
        # Remove tags with no resources
        conn.execute("""
            DELETE FROM tags 
            WHERE id NOT IN (SELECT DISTINCT tag_id FROM resource_tags WHERE tag_id IS NOT NULL)
        """)
        
        if removed_count > 0:
            print(f"✓ Cleaned up {removed_count} junk tags")
        else:
            print("  No junk tags found")
        
        conn.commit()
        print("\n✓ Prompt 4 migrations complete!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Running Prompt 4 migrations...\n")
    migrate()

