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
import html

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


def validate_file_mime_type(file, expected_extensions=None):
    """Validate file's actual MIME type matches extension to prevent malicious uploads.
    
    Args:
        file: File object from request.files
        expected_extensions: Set of allowed extensions (defaults to ALLOWED_EXTENSIONS)
    
    Returns:
        tuple: (is_valid: bool, detected_mime: str, expected_mime: str)
    """
    try:
        import magic
    except ImportError:
        # If python-magic is not installed, fall back to extension-only validation
        # This is less secure but allows the app to function
        return (True, None, None)
    
    if expected_extensions is None:
        expected_extensions = ALLOWED_EXTENSIONS
    
    # Get file extension
    if '.' not in file.filename:
        return (False, None, None)
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    
    if ext not in expected_extensions:
        return (False, None, None)
    
    # Read file content (first 1024 bytes) for MIME detection
    file.seek(0)
    content = file.read(1024)
    file.seek(0)  # Reset file pointer
    
    # Detect MIME type from content
    detected_mime = magic.from_buffer(content, mime=True)
    
    # Map extension to expected MIME types
    mime_map = {
        # Images
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'bmp': 'image/bmp',
        'ico': 'image/x-icon',
        # Documents
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'csv': 'text/csv',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'ppt': 'application/vnd.ms-powerpoint',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'rtf': 'application/rtf',
        # Code files
        'py': 'text/x-python',
        'js': 'text/javascript',
        'ts': 'text/typescript',
        'jsx': 'text/javascript',
        'tsx': 'text/typescript',
        'sql': 'application/sql',
        'json': 'application/json',
        'html': 'text/html',
        'css': 'text/css',
        'scss': 'text/x-scss',
        'sass': 'text/x-sass',
        'xml': 'application/xml',
        'yaml': 'text/yaml',
        'yml': 'text/yaml',
        # Archives
        'zip': 'application/zip',
        'tar': 'application/x-tar',
        'gz': 'application/gzip',
        'rar': 'application/vnd.rar',
        '7z': 'application/x-7z-compressed',
        # Videos
        'mp4': 'video/mp4',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
        'webm': 'video/webm',
        'mkv': 'video/x-matroska',
        'flv': 'video/x-flv',
        'wmv': 'video/x-ms-wmv',
        'm4v': 'video/x-m4v',
        '3gp': 'video/3gpp',
        # Audio
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'aac': 'audio/aac',
        'm4a': 'audio/mp4',
        'wma': 'audio/x-ms-wma'
    }
    
    expected_mime = mime_map.get(ext)
    
    if not expected_mime:
        # If we don't have a mapping, allow it (extension was already validated)
        return (True, detected_mime, None)
    
    # Allow variations and subtypes
    is_valid = (
        detected_mime == expected_mime or
        detected_mime.startswith(expected_mime.split('/')[0] + '/') or
        # Some files may have slightly different MIME types
        (ext in ['jpg', 'jpeg'] and detected_mime in ['image/jpeg', 'image/jpg']) or
        (ext in ['txt', 'md'] and detected_mime.startswith('text/'))
    )
    
    return (is_valid, detected_mime, expected_mime)


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


def sanitize_flash_message(message):
    """Sanitize flash message content to prevent XSS attacks.
    
    Escapes HTML special characters so that flash messages are rendered
    as plain text and cannot execute malicious JavaScript.
    """
    return html.escape(str(message))


def safe_flash(message, category='message'):
    """Flash a message with automatic XSS sanitization.
    
    This is a secure wrapper around Flask's flash() function that
    automatically escapes HTML content to prevent XSS attacks.
    """
    sanitized = sanitize_flash_message(message)
    flash(sanitized, category)


def load_curriculum_seed_data():
    """
    DEPRECATED: Use only for seeding/migrations.
    
    Runtime data must come from database via services.structure.get_structure().
    This function is kept only for migration scripts and initial data seeding.
    
    Load curriculum YAML file with error handling.
    
    Raises:
        DeprecationWarning: When called
    """
    import warnings
    warnings.warn(
        "load_curriculum_seed_data() is deprecated. "
        "Use services.structure.get_structure() or services.structure.get_structure_for_dashboard() for runtime data.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        with open(CURRICULUM_PATH) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        flash("Curriculum file not found. Please ensure curriculum.yaml exists.", "error")
        return {"phases": []}
    except yaml.YAMLError as e:
        flash(f"Error parsing curriculum file: {e}", "error")
        return {"phases": []}


# Keep alias for backward compatibility during migration
def load_curriculum():
    """DEPRECATED: Use load_curriculum_seed_data() or services.structure.get_structure()."""
    return load_curriculum_seed_data()

