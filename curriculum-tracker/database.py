#!/usr/bin/env python3
"""
Database connection and initialization module for Curriculum Tracker.
Handles PostgreSQL connections, migrations, and schema setup.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, PermissionError, OSError):
    pass  # python-dotenv not installed or .env not accessible, use environment variables directly

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'curriculum_tracker'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


def get_db():
    """Get database connection using Flask's g object for automatic cleanup."""
    if 'db' not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db


def get_db_cursor(conn):
    """Get cursor that returns rows as dictionaries."""
    return conn.cursor(cursor_factory=RealDictCursor)


def close_db(exception):
    """Automatically close database connection and cursors at end of request."""
    db = g.pop('db', None)
    if db is not None:
        # Close any open cursors
        if hasattr(db, 'cursors'):
            for cursor in db.cursors:
                if not cursor.closed:
                    cursor.close()
        db.close()




def init_db():
    """
    Initialize database schema.
    
    RESOURCES TABLE FIELD GUIDE:
    - topic: Learning focus/area from CSV "Focus" column (e.g., "API Authentication") 
    - notes: Structured context from CSV: "Tasks: ... | Why: ..."
    - title: Resource name from CSV "Recommended Resource" column
    - url: Link to the resource (may be NULL for BUILD DAY deliverables)
    - resource_type: course, docs, article, video, project, lab, tutorial, action, note, deliverable
    - source: 'curriculum' (imported from CSV) or 'user' (manually added)
    - status: not_started, in_progress, complete, skipped (replaces is_completed)
    - is_completed: Legacy boolean, kept for backwards compatibility (0/1)
    - estimated_minutes: How long this resource takes (auto-set by type, user-editable)
    - difficulty: easy, medium, hard (auto-set by type, user-editable)
    - completed_at: ISO timestamp when marked complete
    - sort_order: For drag-and-drop ordering within days
    - user_modified: Flag indicating if user manually edited this resource
    """
    # Use get_db() if in Flask context, otherwise create direct connection
    created_directly = False
    try:
        conn = get_db()
    except RuntimeError:
        # Outside Flask context, create connection directly
        conn = psycopg2.connect(**DB_CONFIG)
        created_directly = True
    
    cur = get_db_cursor(conn)
    
    # Create tables with PostgreSQL syntax
    create_statements = [
        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)",
        "CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY, current_phase INTEGER DEFAULT 0, current_week INTEGER DEFAULT 1, started_at TIMESTAMP, last_activity_at TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS time_logs (id SERIAL PRIMARY KEY, date DATE NOT NULL, hours REAL NOT NULL, notes TEXT, phase_index INTEGER, week INTEGER, day INTEGER, resource_id INTEGER)",
        "CREATE TABLE IF NOT EXISTS completed_metrics (id SERIAL PRIMARY KEY, phase_index INTEGER NOT NULL, metric_text TEXT NOT NULL, completed_date DATE NOT NULL, resource_id INTEGER, UNIQUE(phase_index, metric_text))",
        "CREATE TABLE IF NOT EXISTS resources (id SERIAL PRIMARY KEY, phase_index INTEGER, week INTEGER, day INTEGER, title TEXT NOT NULL, url TEXT, resource_type TEXT DEFAULT 'link', notes TEXT, is_completed BOOLEAN DEFAULT FALSE, is_favorite BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source TEXT DEFAULT 'user', topic TEXT, status TEXT DEFAULT 'not_started', completed_at TIMESTAMP, sort_order INTEGER DEFAULT 0, estimated_minutes INTEGER, difficulty TEXT, user_modified BOOLEAN DEFAULT FALSE, scheduled_date DATE, original_date DATE)",
        "CREATE TABLE IF NOT EXISTS tags (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, color TEXT DEFAULT '#6366f1')",
        "CREATE TABLE IF NOT EXISTS resource_tags (resource_id INTEGER, tag_id INTEGER, PRIMARY KEY (resource_id, tag_id), FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE)",
        "CREATE TABLE IF NOT EXISTS activity_log (id SERIAL PRIMARY KEY, action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS journal_entries (id SERIAL PRIMARY KEY, date DATE NOT NULL UNIQUE, content TEXT, mood TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, phase_index INTEGER, week INTEGER, day INTEGER)",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)",
        "CREATE TABLE IF NOT EXISTS attachments (id SERIAL PRIMARY KEY, filename TEXT NOT NULL, original_filename TEXT NOT NULL, file_type TEXT, file_size INTEGER, resource_id INTEGER, journal_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE, FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE)",
        "CREATE TABLE IF NOT EXISTS blocked_days (id SERIAL PRIMARY KEY, date DATE NOT NULL UNIQUE, reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    
    for statement in create_statements:
        cur.execute(statement)
    
    cur.close()
    conn.commit()
    
    # Close connection if we created it directly (outside Flask context)
    if created_directly:
        conn.close()
    
    # Note: Schema changes are now handled by Alembic migrations
    # Run migrations with: alembic upgrade head

