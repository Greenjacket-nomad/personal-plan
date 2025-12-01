#!/usr/bin/env python3
"""Verify data was migrated successfully"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

PG_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("PostgreSQL Data Verification")
print("=" * 60)

tables = [
    'config', 'progress', 'tags', 'resources', 'time_logs',
    'completed_metrics', 'resource_tags', 'activity_log',
    'journal_entries', 'settings', 'attachments', 'blocked_days'
]

for table in tables:
    cur.execute(f"SELECT COUNT(*) as count FROM {table}")
    result = cur.fetchone()
    print(f"{table:20} : {result['count']:4} rows")

print("\n" + "=" * 60)
print("Sample data from resources (first 3):")
print("=" * 60)

cur.execute("SELECT id, title, phase_index, week, day, status FROM resources ORDER BY id LIMIT 3")
for row in cur.fetchall():
    print(f"  ID {row['id']:3}: {row['title'][:50]} (P{row['phase_index']} W{row['week']} D{row['day']}) - {row['status']}")

cur.close()
conn.close()

print("\n✓ Data verification complete!")

