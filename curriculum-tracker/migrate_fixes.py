#!/usr/bin/env python3
"""
Migration script to add source, topic columns to resources and phase_index to time_logs.
Also backfills phase_index for existing time_logs based on date ranges.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import yaml

DB_PATH = Path(__file__).parent / "tracker.db"
CURRICULUM_PATH = Path(__file__).parent / "curriculum.yaml"


def column_exists(conn, table, column):
    """Check if a column exists in a table."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def get_config(conn, key, default=None):
    """Get a config value from the database."""
    cur = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else default


def load_curriculum():
    """Load curriculum from YAML file."""
    with open(CURRICULUM_PATH) as f:
        return yaml.safe_load(f)


def calculate_phase_index_for_date(date_str, curriculum, start_date):
    """Calculate which phase a date belongs to based on date ranges."""
    if not start_date:
        return None
    
    try:
        log_date = datetime.strptime(date_str, "%Y-%m-%d")
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return None
    
    # Calculate which week this date falls into
    days_diff = (log_date - start).days
    week_number = days_diff // 7 + 1  # 1-indexed week
    
    # Find which phase this week belongs to
    weeks_accumulated = 0
    for i, phase in enumerate(curriculum["phases"]):
        weeks_accumulated += phase["weeks"]
        if week_number <= weeks_accumulated:
            return i
    
    # If beyond all phases, return the last phase index
    return len(curriculum["phases"]) - 1


def migrate():
    """Run all migrations."""
    conn = sqlite3.connect(DB_PATH)
    try:
        print("Starting migrations...")
        
        # 1. Add source column to resources
        if not column_exists(conn, "resources", "source"):
            print("Adding 'source' column to resources table...")
            conn.execute("ALTER TABLE resources ADD COLUMN source TEXT DEFAULT 'user'")
            # Update existing resources to have 'user' as source
            conn.execute("UPDATE resources SET source = 'user' WHERE source IS NULL")
            conn.commit()
            print("✓ Added 'source' column")
        else:
            print("✓ 'source' column already exists")
        
        # 2. Add topic column to resources
        if not column_exists(conn, "resources", "topic"):
            print("Adding 'topic' column to resources table...")
            conn.execute("ALTER TABLE resources ADD COLUMN topic TEXT")
            conn.commit()
            print("✓ Added 'topic' column")
        else:
            print("✓ 'topic' column already exists")
        
        # 3. Add phase_index column to time_logs
        if not column_exists(conn, "time_logs", "phase_index"):
            print("Adding 'phase_index' column to time_logs table...")
            conn.execute("ALTER TABLE time_logs ADD COLUMN phase_index INTEGER")
            conn.commit()
            print("✓ Added 'phase_index' column")
        else:
            print("✓ 'phase_index' column already exists")
        
        # 4. Backfill phase_index for existing time_logs
        print("Backfilling phase_index for existing time_logs...")
        curriculum = load_curriculum()
        start_date = get_config(conn, "start_date")
        
        if start_date:
            # Get all time_logs with NULL phase_index
            cur = conn.execute("SELECT id, date FROM time_logs WHERE phase_index IS NULL")
            rows = cur.fetchall()
            
            updated_count = 0
            for row_id, date_str in rows:
                phase_idx = calculate_phase_index_for_date(date_str, curriculum, start_date)
                if phase_idx is not None:
                    conn.execute("UPDATE time_logs SET phase_index = ? WHERE id = ?", (phase_idx, row_id))
                    updated_count += 1
            
            conn.commit()
            print(f"✓ Backfilled phase_index for {updated_count} time_log entries")
        else:
            print("⚠ No start_date found in config, skipping phase_index backfill")
        
        print("\nMigration complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

