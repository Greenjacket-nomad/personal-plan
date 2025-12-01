#!/usr/bin/env python3
"""
Utility functions for Curriculum Tracker.
Helper functions for dates, file validation, formatting, and curriculum loading.
"""

import os
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from flask import flash

# Path constants
APP_DIR = Path(__file__).parent
CURRICULUM_PATH = APP_DIR / "curriculum.yaml"
UPLOAD_FOLDER = APP_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)  # Create folder if it doesn't exist

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico',
    # Documents
    'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'pptx', 'ppt', 'txt', 'md', 'rtf',
    # Code files
    'py', 'js', 'ts', 'jsx', 'tsx', 'sql', 'json', 'html', 'css', 'scss', 'sass', 'xml', 'yaml', 'yml',
    # Archives
    'zip', 'tar', 'gz', 'rar', '7z',
    # Videos
    'mp4', 'mov', 'avi', 'webm', 'mkv', 'flv', 'wmv', 'm4v', '3gp',
    # Audio
    'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'
}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_week_dates(date_str):
    """Get start and end dates of the week containing the given date."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def get_start_date():
    """Get start date from settings."""
    from database import get_db, get_db_cursor
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT value FROM settings WHERE key = 'start_date'")
    result = cur.fetchone()
    cur.close()
    return result['value'] if result else None


def set_start_date(date_str):
    """Set start date in settings."""
    from database import get_db, get_db_cursor
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("INSERT INTO settings (key, value) VALUES ('start_date', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (date_str, date_str))
    cur.close()
    conn.commit()


def calculate_schedule(start_date):
    """Assign scheduled_date to each curriculum day, skipping blocked days."""
    from database import get_db, get_db_cursor
    conn = get_db()
    
    # Get all unique curriculum days in order
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        WHERE phase_index IS NOT NULL AND week IS NOT NULL AND day IS NOT NULL
        ORDER BY phase_index, week, day
    """)
    curriculum_days = cur.fetchall()
    
    if not curriculum_days:
        cur.close()
        return  # No curriculum days to schedule
    
    # Get blocked dates
    cur.execute("SELECT date FROM blocked_days")
    blocked = set(row['date'] for row in cur.fetchall())
    
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    for row in curriculum_days:
        phase_idx = row['phase_index']
        week = row['week']
        day = row['day']
        # Skip blocked days
        while current_date.strftime("%Y-%m-%d") in blocked:
            current_date += timedelta(days=1)
        
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Assign this date to all resources on this curriculum day
        # Set original_date only if it's not already set
        cur.execute("""
            UPDATE resources 
            SET scheduled_date = %s, 
                original_date = COALESCE(original_date, %s)
            WHERE phase_index = %s AND week = %s AND day = %s
        """, (date_str, date_str, phase_idx, week, day))
        
        current_date += timedelta(days=1)
    
    cur.close()
    conn.commit()


def recalculate_schedule_from(from_date):
    """Recalculate scheduled_dates from a specific date forward."""
    from database import get_db, get_db_cursor
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Find which curriculum day was on or after this date
    cur.execute("""
        SELECT MIN(phase_index) as min_phase, MIN(week) as min_week, MIN(day) as min_day
        FROM resources 
        WHERE scheduled_date >= %s
    """, (from_date,))
    affected = cur.fetchone()
    
    if not affected or affected['min_phase'] is None:
        cur.close()
        return  # Nothing to recalculate
    
    # Get curriculum days from this point forward
    cur.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        WHERE (phase_index > %s) 
           OR (phase_index = %s AND week > %s)
           OR (phase_index = %s AND week = %s AND day >= %s)
        ORDER BY phase_index, week, day
    """, (affected['min_phase'], affected['min_phase'], affected['min_week'], affected['min_phase'], affected['min_week'], affected['min_day']))
    curriculum_days = cur.fetchall()
    
    if not curriculum_days:
        cur.close()
        return
    
    # Get blocked dates >= from_date
    cur.execute("SELECT date FROM blocked_days WHERE date >= %s", (from_date,))
    blocked = set(row['date'] for row in cur.fetchall())
    
    current_date = datetime.strptime(from_date, "%Y-%m-%d")
    
    for row in curriculum_days:
        phase_idx = row['phase_index']
        week = row['week']
        day = row['day']
        while current_date.strftime("%Y-%m-%d") in blocked:
            current_date += timedelta(days=1)
        
        date_str = current_date.strftime("%Y-%m-%d")
        
        cur.execute("""
            UPDATE resources 
            SET scheduled_date = %s
            WHERE phase_index = %s AND week = %s AND day = %s
        """, (date_str, phase_idx, week, day))
        
        current_date += timedelta(days=1)
    
    cur.close()
    conn.commit()


def get_projected_end_date():
    """Get projected end date from maximum scheduled_date."""
    from database import get_db, get_db_cursor
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT MAX(scheduled_date) as max_date FROM resources WHERE scheduled_date IS NOT NULL"
    )
    result = cur.fetchone()
    cur.close()
    return result['max_date'] if result and result['max_date'] else None


def load_curriculum():
    """Load curriculum YAML file with error handling."""
    try:
        with open(CURRICULUM_PATH) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        flash("Curriculum file not found. Please ensure curriculum.yaml exists.", "error")
        return {"phases": []}
    except yaml.YAMLError as e:
        flash(f"Error parsing curriculum file: {e}", "error")
        return {"phases": []}

