#!/usr/bin/env python3
"""Test PostgreSQL connection"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

print("Testing PostgreSQL connection...")
print(f"Connecting to: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
print(f"User: {DB_CONFIG['user']}")

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("✓ Connection successful!")
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Test query
    cur.execute("SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'public'")
    result = cur.fetchone()
    print(f"✓ Found {result['count']} tables in database")
    
    # List tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print("\nTables found:")
    for table in tables:
        print(f"  - {table['table_name']}")
    
    cur.close()
    conn.close()
    print("\n✓ All tests passed! PostgreSQL is ready to use.")
    
except psycopg2.OperationalError as e:
    print(f"\n✗ Connection failed!")
    print(f"Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL is running")
    print("2. Check your .env file has correct credentials")
    print("3. Verify the database 'curriculum_tracker' exists")
    print("4. Try connecting in SQL Pro Studio first to verify credentials")
except Exception as e:
    print(f"\n✗ Error: {e}")

