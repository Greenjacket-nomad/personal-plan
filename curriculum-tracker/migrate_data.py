#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# SQLite connection
SQLITE_DB = Path(__file__).parent / "tracker.db"

# PostgreSQL configuration
PG_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

def migrate_table(sqlite_conn, pg_conn, table_name, columns_to_skip=None, id_column='id', include_id=False):
    """Migrate a single table from SQLite to PostgreSQL."""
    if columns_to_skip is None:
        columns_to_skip = []
    
    print(f"\nMigrating {table_name}...")
    
    # Get data from SQLite
    sqlite_cur = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return 0
    
    # Get column names
    if rows:
        all_columns = [desc[0] for desc in sqlite_cur.description]
        if include_id:
            # Include id column for tables like progress that need it
            columns = [col for col in all_columns if col not in columns_to_skip]
        else:
            # Exclude id for SERIAL columns (let PostgreSQL generate)
            columns = [col for col in all_columns if col not in columns_to_skip and col != id_column]
    else:
        columns = []
    
    if not columns:
        print(f"  No columns to migrate for {table_name}")
        return 0
    
    # Insert into PostgreSQL
    inserted = 0
    errors = 0
    
    for row in rows:
        pg_cur = pg_conn.cursor()
        # Build values list
        values = []
        placeholders = []
        
        for col in columns:
            value = row[col]
            
            # Convert boolean values (SQLite uses 0/1, PostgreSQL uses TRUE/FALSE)
            if isinstance(value, int) and col in ['is_completed', 'is_favorite', 'user_modified']:
                value = bool(value)
            
            values.append(value)
            placeholders.append('%s')
        
        # Build INSERT statement
        col_names = ', '.join(columns)
        placeholders_str = ', '.join(placeholders)
        
        try:
            pg_cur.execute(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders_str})",
                values
            )
            pg_conn.commit()
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 3:  # Only show first 3 errors
                print(f"  ⚠ Skipping row (foreign key or constraint issue): {str(e)[:80]}")
            pg_conn.rollback()
        finally:
            pg_cur.close()
    
    if errors > 0:
        print(f"  ✓ Migrated {inserted} rows ({errors} skipped due to constraints)")
    else:
        print(f"  ✓ Migrated {inserted} rows")
    return inserted

def reset_sequences(pg_conn):
    """Reset PostgreSQL sequences after manual inserts."""
    print("\nResetting sequences...")
    pg_cur = pg_conn.cursor()
    
    sequences = [
        ('resources', 'resources_id_seq'),
        ('time_logs', 'time_logs_id_seq'),
        ('completed_metrics', 'completed_metrics_id_seq'),
        ('tags', 'tags_id_seq'),
        ('activity_log', 'activity_log_id_seq'),
        ('journal_entries', 'journal_entries_id_seq'),
        ('attachments', 'attachments_id_seq'),
        ('blocked_days', 'blocked_days_id_seq'),
    ]
    
    for table_name, seq_name in sequences:
        try:
            pg_cur.execute(f"SELECT MAX(id) FROM {table_name}")
            max_id = pg_cur.fetchone()[0]
            if max_id:
                pg_cur.execute(f"SELECT setval('{seq_name}', {max_id})")
                print(f"  ✓ Reset {seq_name} to {max_id}")
        except Exception as e:
            print(f"  ⚠ Could not reset {seq_name}: {e}")
    
    pg_conn.commit()
    pg_cur.close()

def main():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    
    # Connect to SQLite
    if not SQLITE_DB.exists():
        print(f"\n✗ SQLite database not found: {SQLITE_DB}")
        return
    
    print(f"\nConnecting to SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL
    print(f"Connecting to PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    try:
        pg_conn = psycopg2.connect(**PG_CONFIG)
    except Exception as e:
        print(f"\n✗ Failed to connect to PostgreSQL: {e}")
        print("\nPlease check your .env file and PostgreSQL connection.")
        return
    
    print("✓ Connected to both databases\n")
    
    # Migration order matters for foreign keys
    # 1. Independent tables first
    # 2. Tables with foreign keys after
    
    total_migrated = 0
    
    # Independent tables (no foreign keys or simple ones)
    # Progress needs ID included since it's not SERIAL
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'config', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'progress', columns_to_skip=[], include_id=True)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'tags', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'resources', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'time_logs', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'completed_metrics', columns_to_skip=[], include_id=False)
    # Resource_tags may have foreign key issues - skip invalid ones
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'resource_tags', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'activity_log', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'journal_entries', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'settings', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'attachments', columns_to_skip=[], include_id=False)
    total_migrated += migrate_table(sqlite_conn, pg_conn, 'blocked_days', columns_to_skip=[], include_id=False)
    
    # Reset sequences
    reset_sequences(pg_conn)
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print(f"Migration complete! Migrated {total_migrated} total rows.")
    print("=" * 60)
    print("\nYou can now use your app with PostgreSQL!")
    print("Your SQLite database (tracker.db) is still there as a backup.")

if __name__ == "__main__":
    main()

