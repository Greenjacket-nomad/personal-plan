#!/usr/bin/env python3
"""Fix resource_tags migration with proper ID mapping"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
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

# Connect
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
pg_conn = psycopg2.connect(**PG_CONFIG)

# Get tag mapping: old SQLite ID -> new PostgreSQL ID by name
print("Creating tag ID mapping...")
sqlite_tags = {row['id']: row['name'] for row in sqlite_conn.execute("SELECT id, name FROM tags").fetchall()}
pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)
pg_cur.execute("SELECT id, name FROM tags")
pg_tags = {row['name']: row['id'] for row in pg_cur.fetchall()}

tag_id_map = {}
for old_id, name in sqlite_tags.items():
    if name in pg_tags:
        tag_id_map[old_id] = pg_tags[name]
        print(f"  Tag '{name}': SQLite ID {old_id} -> PostgreSQL ID {pg_tags[name]}")

# Get resource mapping: old SQLite ID -> new PostgreSQL ID by title+phase+week+day
print("\nCreating resource ID mapping...")
sqlite_resources = {}
for row in sqlite_conn.execute("SELECT id, title, phase_index, week, day FROM resources").fetchall():
    key = (row['title'], row['phase_index'], row['week'], row['day'])
    sqlite_resources[key] = row['id']

pg_cur.execute("SELECT id, title, phase_index, week, day FROM resources ORDER BY id")
pg_resources = {}
for row in pg_cur.fetchall():
    key = (row['title'], row['phase_index'], row['week'], row['day'])
    # Use first occurrence if duplicates
    if key not in pg_resources:
        pg_resources[key] = row['id']

resource_id_map = {}
for key, old_id in sqlite_resources.items():
    if key in pg_resources:
        resource_id_map[old_id] = pg_resources[key]

print(f"  Mapped {len(resource_id_map)} resources")

# Migrate resource_tags
print("\nMigrating resource_tags...")
sqlite_cur = sqlite_conn.execute("SELECT resource_id, tag_id FROM resource_tags")
inserted = 0
errors = 0

for row in sqlite_cur.fetchall():
    old_resource_id = row['resource_id']
    old_tag_id = row['tag_id']
    
    new_resource_id = resource_id_map.get(old_resource_id)
    new_tag_id = tag_id_map.get(old_tag_id)
    
    if new_resource_id and new_tag_id:
        try:
            pg_cur.execute(
                "INSERT INTO resource_tags (resource_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (new_resource_id, new_tag_id)
            )
            pg_conn.commit()
            inserted += 1
        except Exception as e:
            errors += 1
            pg_conn.rollback()
    else:
        errors += 1
        if errors <= 5:
            print(f"  ⚠ Skipping: resource_id {old_resource_id} -> {new_resource_id}, tag_id {old_tag_id} -> {new_tag_id}")

print(f"  ✓ Migrated {inserted} rows ({errors} skipped)")

pg_cur.close()
sqlite_conn.close()
pg_conn.close()
print("\n✓ Done!")

