#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL with ID mapping for foreign keys
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

SQLITE_DB = Path(__file__).parent / "tracker.db"
PG_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

def migrate_with_id_mapping(sqlite_conn, pg_conn, table_name, id_column='id'):
    """Migrate table and return mapping of old_id -> new_id"""
    print(f"\nMigrating {table_name}...")
    
    sqlite_cur = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return {}
    
    all_columns = [desc[0] for desc in sqlite_cur.description]
    columns = [col for col in all_columns if col != id_column]
    
    if not columns:
        print(f"  No columns to migrate")
        return {}
    
    pg_cur = pg_conn.cursor()
    id_mapping = {}
    inserted = 0
    
    for row in rows:
        old_id = row[id_column]
        values = []
        placeholders = []
        
        for col in columns:
            value = row[col]
            if isinstance(value, int) and col in ['is_completed', 'is_favorite', 'user_modified']:
                value = bool(value)
            values.append(value)
            placeholders.append('%s')
        
        col_names = ', '.join(columns)
        placeholders_str = ', '.join(placeholders)
        
        try:
            pg_cur.execute(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders_str}) RETURNING {id_column}",
                values
            )
            new_id = pg_cur.fetchone()[0]
            id_mapping[old_id] = new_id
            inserted += 1
            pg_conn.commit()
        except Exception as e:
            print(f"  ⚠ Error: {str(e)[:80]}")
            pg_conn.rollback()
    
    pg_cur.close()
    print(f"  ✓ Migrated {inserted} rows")
    return id_mapping

def migrate_resource_tags(sqlite_conn, pg_conn, resource_id_map, tag_id_map):
    """Migrate resource_tags with ID mapping"""
    print(f"\nMigrating resource_tags...")
    
    sqlite_cur = sqlite_conn.execute("SELECT resource_id, tag_id FROM resource_tags")
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f"  No data in resource_tags")
        return 0
    
    pg_cur = pg_conn.cursor()
    inserted = 0
    errors = 0
    
    for row in rows:
        old_resource_id = row['resource_id']
        old_tag_id = row['tag_id']
        
        # Map to new IDs
        new_resource_id = resource_id_map.get(old_resource_id)
        new_tag_id = tag_id_map.get(old_tag_id)
        
        if not new_resource_id or not new_tag_id:
            errors += 1
            if errors <= 3:
                print(f"  ⚠ Skipping: resource_id {old_resource_id} -> {new_resource_id}, tag_id {old_tag_id} -> {new_tag_id}")
            continue
        
        try:
            pg_cur.execute(
                "INSERT INTO resource_tags (resource_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (new_resource_id, new_tag_id)
            )
            pg_conn.commit()
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ⚠ Error: {str(e)[:80]}")
            pg_conn.rollback()
    
    pg_cur.close()
    if errors > 0:
        print(f"  ✓ Migrated {inserted} rows ({errors} skipped)")
    else:
        print(f"  ✓ Migrated {inserted} rows")
    return inserted

def main():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration (with ID mapping)")
    print("=" * 60)
    
    if not SQLITE_DB.exists():
        print(f"\n✗ SQLite database not found: {SQLITE_DB}")
        return
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        pg_conn = psycopg2.connect(**PG_CONFIG)
    except Exception as e:
        print(f"\n✗ Failed to connect: {e}")
        return
    
    print("✓ Connected to both databases\n")
    
    # Migrate independent tables first, get ID mappings
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'config', id_column='key')  # config uses 'key' not 'id'
    
    # Progress needs special handling (not SERIAL)
    print("\nMigrating progress...")
    sqlite_cur = sqlite_conn.execute("SELECT * FROM progress")
    rows = sqlite_cur.fetchall()
    if rows:
        pg_cur = pg_conn.cursor()
        for row in rows:
            pg_cur.execute(
                "INSERT INTO progress (id, current_phase, current_week, started_at, last_activity_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (row['id'], row['current_phase'], row['current_week'], row['started_at'], row['last_activity_at'])
            )
        pg_conn.commit()
        pg_cur.close()
        print(f"  ✓ Migrated {len(rows)} rows")
    
    # Migrate tags and get ID mapping
    tag_id_map = migrate_with_id_mapping(sqlite_conn, pg_conn, 'tags')
    
    # Migrate resources and get ID mapping
    resource_id_map = migrate_with_id_mapping(sqlite_conn, pg_conn, 'resources')
    
    # Migrate other tables
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'time_logs')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'completed_metrics')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'activity_log')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'journal_entries')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'settings', id_column='key')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'attachments')
    migrate_with_id_mapping(sqlite_conn, pg_conn, 'blocked_days')
    
    # Migrate resource_tags with ID mapping
    migrate_resource_tags(sqlite_conn, pg_conn, resource_id_map, tag_id_map)
    
    # Reset sequences
    print("\nResetting sequences...")
    pg_cur = pg_conn.cursor()
    sequences = [
        ('resources', 'resources_id_seq'),
        ('tags', 'tags_id_seq'),
        ('time_logs', 'time_logs_id_seq'),
        ('completed_metrics', 'completed_metrics_id_seq'),
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
        except:
            pass
    pg_conn.commit()
    pg_cur.close()
    
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

