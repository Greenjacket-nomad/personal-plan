#!/usr/bin/env python3
"""
Migration script to migrate curriculum structure from curriculum.yaml to database tables.

This script:
1. Loads curriculum.yaml ONCE
2. Iterates through all users
3. Creates phases, weeks, and days for each user based on YAML
4. Backfills resources.day_id by matching phase_index/week/day
5. Handles orphan resources by moving them to a catch-all "Migrated Items" structure
"""

import sys
import os
import yaml
from pathlib import Path

# Add parent directory to path to import modules
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

import psycopg2
from psycopg2.extras import RealDictCursor

# Define curriculum path (same as utils.py)
CURRICULUM_PATH = APP_DIR / "curriculum.yaml"


def load_curriculum_direct():
    """Load curriculum YAML file directly (without Flask dependencies)."""
    try:
        with open(CURRICULUM_PATH) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Curriculum file not found at {CURRICULUM_PATH}")
        return {"phases": []}
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse curriculum file: {e}")
        return {"phases": []}

# Database configuration (same as database.py)
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_db_cursor(conn):
    """Get cursor that returns rows as dictionaries."""
    return conn.cursor(cursor_factory=RealDictCursor)


def create_phase(conn, user_id, title, order_index, color='#6366f1', metrics=None):
    """Create or get existing phase for a user."""
    cur = get_db_cursor(conn)
    try:
        # Ensure metrics is a list (empty if None)
        metrics_list = metrics if metrics is not None else []
        
        # Try to insert (will fail silently if exists due to unique constraint)
        cur.execute("""
            INSERT INTO phases (user_id, title, order_index, color, metrics)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, order_index) 
            DO UPDATE SET metrics = EXCLUDED.metrics
            RETURNING id
        """, (user_id, title, order_index, color, metrics_list))
        
        result = cur.fetchone()
        if result:
            return result['id']
        
        # If insert didn't return ID, phase already exists - update metrics and fetch it
        cur.execute("""
            UPDATE phases SET metrics = %s
            WHERE user_id = %s AND order_index = %s
        """, (metrics_list, user_id, order_index))
        conn.commit()
        
        cur.execute("""
            SELECT id FROM phases
            WHERE user_id = %s AND order_index = %s
        """, (user_id, order_index))
        existing = cur.fetchone()
        return existing['id'] if existing else None
    finally:
        cur.close()


def create_week(conn, user_id, phase_id, title, order_index):
    """Create or get existing week for a phase."""
    cur = get_db_cursor(conn)
    try:
        cur.execute("""
            INSERT INTO weeks (user_id, phase_id, title, order_index)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, phase_id, order_index) DO NOTHING
            RETURNING id
        """, (user_id, phase_id, title, order_index))
        
        result = cur.fetchone()
        if result:
            return result['id']
        
        # If insert didn't return ID, week already exists - fetch it
        cur.execute("""
            SELECT id FROM weeks
            WHERE user_id = %s AND phase_id = %s AND order_index = %s
        """, (user_id, phase_id, order_index))
        existing = cur.fetchone()
        return existing['id'] if existing else None
    finally:
        cur.close()


def create_day(conn, user_id, week_id, title, order_index):
    """Create or get existing day for a week."""
    cur = get_db_cursor(conn)
    try:
        cur.execute("""
            INSERT INTO days (user_id, week_id, title, order_index)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, week_id, order_index) DO NOTHING
            RETURNING id
        """, (user_id, week_id, title, order_index))
        
        result = cur.fetchone()
        if result:
            return result['id']
        
        # If insert didn't return ID, day already exists - fetch it
        cur.execute("""
            SELECT id FROM days
            WHERE user_id = %s AND week_id = %s AND order_index = %s
        """, (user_id, week_id, order_index))
        existing = cur.fetchone()
        return existing['id'] if existing else None
    finally:
        cur.close()


def get_or_create_orphan_inbox(conn, user_id):
    """Get or create the catch-all structure for orphan resources."""
    cur = get_db_cursor(conn)
    try:
        # Get or create "Migrated Items" phase
        phase_id = create_phase(conn, user_id, "Migrated Items", 99999, '#9ca3af')
        
        # Get or create "Unsorted" week
        week_id = create_week(conn, user_id, phase_id, "Unsorted", 1)
        
        # Get or create "Inbox" day
        day_id = create_day(conn, user_id, week_id, "Inbox", 1)
        
        return day_id
    finally:
        cur.close()


def migrate_user(conn, user_id, curriculum_data):
    """Migrate curriculum structure for a single user."""
    cur = get_db_cursor(conn)
    try:
        print(f"  Migrating user {user_id}...")
        
        # Track created day IDs for backfilling
        day_map = {}  # (phase_index, week, day) -> day_id
        
        # Create phases and their weeks/days
        for phase_idx, phase_data in enumerate(curriculum_data.get('phases', [])):
            phase_title = phase_data.get('name', f'Phase {phase_idx + 1}')
            num_weeks = phase_data.get('weeks', 0)
            metrics = phase_data.get('metrics', [])  # Extract metrics from YAML
            
            # Create phase with metrics
            phase_id = create_phase(conn, user_id, phase_title, phase_idx, '#6366f1', metrics)
            if not phase_id:
                print(f"    Warning: Failed to create phase {phase_idx}")
                continue
            
            # Create weeks for this phase
            for week_num in range(1, num_weeks + 1):
                week_title = f"Week {week_num}"
                week_id = create_week(conn, user_id, phase_id, week_title, week_num)
                if not week_id:
                    print(f"    Warning: Failed to create week {week_num} for phase {phase_idx}")
                    continue
                
                # Create 6 days for this week
                for day_num in range(1, 7):
                    day_title = f"Day {day_num}"
                    day_id = create_day(conn, user_id, week_id, day_title, day_num)
                    if day_id:
                        day_map[(phase_idx, week_num, day_num)] = day_id
        
        conn.commit()
        
        # Backfill resources.day_id
        orphan_day_id = None
        cur.execute("""
            SELECT id, phase_index, week, day
            FROM resources
            WHERE user_id = %s AND day_id IS NULL
        """, (user_id,))
        
        resources = cur.fetchall()
        updated_count = 0
        orphan_count = 0
        
        for resource in resources:
            phase_index = resource['phase_index']
            week = resource['week']
            day = resource['day']
            
            if phase_index is not None and week is not None and day is not None:
                key = (phase_index, week, day)
                day_id = day_map.get(key)
                
                if day_id:
                    # Update resource with matched day_id
                    cur.execute("""
                        UPDATE resources
                        SET day_id = %s
                        WHERE id = %s
                    """, (day_id, resource['id']))
                    updated_count += 1
                else:
                    # Orphan resource - doesn't match YAML structure
                    if orphan_day_id is None:
                        orphan_day_id = get_or_create_orphan_inbox(conn, user_id)
                    
                    cur.execute("""
                        UPDATE resources
                        SET day_id = %s
                        WHERE id = %s
                    """, (orphan_day_id, resource['id']))
                    orphan_count += 1
            else:
                # Resource with NULL phase_index/week/day - treat as orphan
                if orphan_day_id is None:
                    orphan_day_id = get_or_create_orphan_inbox(conn, user_id)
                
                cur.execute("""
                    UPDATE resources
                    SET day_id = %s
                    WHERE id = %s
                """, (orphan_day_id, resource['id']))
                orphan_count += 1
        
        conn.commit()
        print(f"    Updated {updated_count} resources, moved {orphan_count} orphans to inbox")
        
    except Exception as e:
        conn.rollback()
        print(f"    ERROR migrating user {user_id}: {e}")
        raise
    finally:
        cur.close()


def main():
    """Main migration function."""
    print("Starting curriculum structure migration...")
    
    # Load curriculum.yaml ONCE
    print("Loading curriculum.yaml...")
    curriculum_data = load_curriculum_direct()
    
    if not curriculum_data or not curriculum_data.get('phases'):
        print("ERROR: No phases found in curriculum.yaml")
        return 1
    
    print(f"Found {len(curriculum_data['phases'])} phases in curriculum.yaml")
    
    # Connect to database
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return 1
    
    try:
        # Get all users
        cur = get_db_cursor(conn)
        cur.execute("SELECT id FROM users ORDER BY id")
        users = cur.fetchall()
        cur.close()
        
        if not users:
            print("WARNING: No users found in database")
            return 0
        
        print(f"Found {len(users)} users to migrate")
        
        # Migrate each user
        for user in users:
            user_id = user['id']
            try:
                migrate_user(conn, user_id, curriculum_data)
            except Exception as e:
                print(f"ERROR: Failed to migrate user {user_id}: {e}")
                # Continue with next user
                continue
        
        print("\nMigration completed!")
        return 0
        
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
