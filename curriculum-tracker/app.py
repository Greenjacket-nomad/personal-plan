#!/usr/bin/env python3
"""
Curriculum Tracker - Web Dashboard with SQLite
"""

import os
import json
import sqlite3
import calendar
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, g, send_from_directory
import yaml
from constants import STATUS_CYCLE, STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_COMPLETE

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "tracker.db"
CURRICULUM_PATH = APP_DIR / "curriculum.yaml"
UPLOAD_FOLDER = APP_DIR / "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'docx', 'xlsx', 'csv', 'py', 'js', 'sql', 'json', 'html', 'css', 'zip'}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def get_db():
    """Get database connection using Flask's g object for automatic cleanup."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Automatically close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
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
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        created_directly = True
    
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY, current_phase INTEGER DEFAULT 0, current_week INTEGER DEFAULT 1, started_at TEXT, last_activity_at TEXT);
        CREATE TABLE IF NOT EXISTS time_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, hours REAL NOT NULL, notes TEXT, phase_index INTEGER, week INTEGER, day INTEGER, resource_id INTEGER);
        CREATE TABLE IF NOT EXISTS completed_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER NOT NULL, metric_text TEXT NOT NULL, completed_date TEXT NOT NULL, resource_id INTEGER, UNIQUE(phase_index, metric_text));
        CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER, week INTEGER, day INTEGER, title TEXT NOT NULL, url TEXT, resource_type TEXT DEFAULT 'link', notes TEXT, is_completed INTEGER DEFAULT 0, is_favorite INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, source TEXT DEFAULT 'user', topic TEXT, status TEXT DEFAULT 'not_started', completed_at TEXT, sort_order INTEGER DEFAULT 0, estimated_minutes INTEGER, difficulty TEXT, user_modified INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT DEFAULT '#6366f1');
        CREATE TABLE IF NOT EXISTS resource_tags (resource_id INTEGER, tag_id INTEGER, PRIMARY KEY (resource_id, tag_id));
        CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL UNIQUE, content TEXT, mood TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """
    )
    conn.commit()
    
    # Close connection if we created it directly (outside Flask context)
    if created_directly:
        conn.close()


def get_progress():
    """Get progress data from singleton progress table."""
    conn = get_db()
    cur = conn.execute("SELECT * FROM progress WHERE id = 1")
    row = cur.fetchone()
    
    if not row:
        # Initialize if missing
        conn = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        conn.execute("INSERT INTO progress (id, current_phase, current_week, started_at) VALUES (1, 0, 1, ?)", (today,))
        conn.commit()
        return get_progress()
    
    return {
        'current_phase': row['current_phase'] if row['current_phase'] is not None else 0,
        'current_week': row['current_week'] if row['current_week'] is not None else 1,
        'started_at': row['started_at'],
        'last_activity_at': row['last_activity_at']
    }


def update_progress(**kwargs):
    """Update progress table with provided fields."""
    conn = get_db()
    # Whitelist allowed fields to prevent SQL injection
    allowed_fields = {'current_phase', 'current_week', 'started_at', 'last_activity_at'}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not filtered_kwargs:
        return
    sets = ', '.join(f"{k} = ?" for k in filtered_kwargs.keys())
    values = list(filtered_kwargs.values()) + [datetime.now().isoformat()]
    conn.execute(f"UPDATE progress SET {sets}, last_activity_at = ? WHERE id = 1", values)
    conn.commit()


def init_if_needed():
    """Ensure progress table is initialized."""
    progress = get_progress()
    # get_progress() auto-initializes if missing
    return progress


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


def get_week_dates(date_str):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def get_current_week_hours():
    today = datetime.now().strftime("%Y-%m-%d")
    week_start, week_end = get_week_dates(today)
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date >= ? AND date <= ?", (week_start, week_end))
    result = cur.fetchone()
    return result["total"]


def get_total_hours():
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs")
    result = cur.fetchone()
    return result["total"]


def get_hours_for_phase(phase_index, curriculum):
    # Query by phase_index column instead of date ranges
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE phase_index = ?", (phase_index,))
    result = cur.fetchone()
    return result["total"]


def get_hours_for_week(phase_index, week):
    """Get total hours logged for a specific week."""
    conn = get_db()
    cur = conn.execute(
        "SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE phase_index = ? AND week = ?",
        (phase_index, week)
    )
    result = cur.fetchone()
    return result["total"] if result else 0


def get_hours_for_resource(resource_id):
    """Get total hours logged for a specific resource."""
    conn = get_db()
    cur = conn.execute(
        "SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE resource_id = ?",
        (resource_id,)
    )
    result = cur.fetchone()
    return result["total"] if result else 0


def get_completed_metrics(phase_index=None):
    conn = get_db()
    if phase_index is not None:
        cur = conn.execute("SELECT * FROM completed_metrics WHERE phase_index = ?", (phase_index,))
    else:
        cur = conn.execute("SELECT * FROM completed_metrics")
    results = cur.fetchall()
    return results


def get_recent_logs(days=7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_db()
    cur = conn.execute("SELECT date, hours, notes FROM time_logs WHERE date >= ? ORDER BY date DESC", (cutoff,))
    results = cur.fetchall()
    return results


def get_resources(phase_index=None):
    """Get resources with tags in a single query (fixes N+1 problem)."""
    conn = get_db()
    if phase_index is not None:
        query = """
            SELECT r.*, 
                   GROUP_CONCAT(t.name, '|||') as tag_names,
                   GROUP_CONCAT(t.color, '|||') as tag_colors
            FROM resources r
            LEFT JOIN resource_tags rt ON r.id = rt.resource_id
            LEFT JOIN tags t ON rt.tag_id = t.id
            WHERE r.phase_index = ? OR r.phase_index IS NULL
            GROUP BY r.id
            ORDER BY r.week, r.day, r.is_favorite DESC, r.created_at DESC
        """
        cur = conn.execute(query, (phase_index,))
    else:
        query = """
            SELECT r.*,
                   GROUP_CONCAT(t.name, '|||') as tag_names,
                   GROUP_CONCAT(t.color, '|||') as tag_colors
            FROM resources r
            LEFT JOIN resource_tags rt ON r.id = rt.resource_id
            LEFT JOIN tags t ON rt.tag_id = t.id
            GROUP BY r.id
            ORDER BY r.phase_index, r.week, r.day, r.is_favorite DESC, r.created_at DESC
        """
        cur = conn.execute(query)
    
    rows = cur.fetchall()

    resources = []
    for r in rows:
        item = dict(r)
        # Parse concatenated tags
        if r["tag_names"]:
            item["tags"] = r["tag_names"].split("|||")
            item["tag_colors"] = r["tag_colors"].split("|||")
        else:
            item["tags"] = []
            item["tag_colors"] = []
        resources.append(item)
    return resources


def get_all_resources():
    return get_resources()


def get_all_tags():
    conn = get_db()
    cur = conn.execute("SELECT * FROM tags ORDER BY name")
    results = cur.fetchall()
    return results


def log_activity(action, entity_type=None, entity_id=None, details=None):
    """Log an activity to the activity_log table."""
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
        (action, entity_type, entity_id, details)
    )
    conn.commit()


def get_current_streak():
    """Calculate current consecutive days with logged hours ending today/yesterday."""
    conn = get_db()
    cur = conn.execute("SELECT DISTINCT date FROM time_logs ORDER BY date DESC")
    dates = [row["date"] for row in cur.fetchall()]
    
    if not dates:
        return 0
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Check if most recent log is today or yesterday
    most_recent = datetime.strptime(dates[0], "%Y-%m-%d").date()
    if most_recent not in [today, yesterday]:
        return 0  # Streak is broken
    
    # Count backwards
    streak = 1
    expected_date = most_recent - timedelta(days=1)
    
    for date_str in dates[1:]:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if date == expected_date:
            streak += 1
            expected_date = date - timedelta(days=1)
        else:
            break
    
    return streak


def get_longest_streak():
    """Calculate longest ever consecutive days with logged hours."""
    conn = get_db()
    cur = conn.execute("SELECT DISTINCT date FROM time_logs ORDER BY date")
    dates = [datetime.strptime(row["date"], "%Y-%m-%d").date() for row in cur.fetchall()]
    
    if not dates:
        return 0
    
    longest = 1
    current = 1
    
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    
    return longest


def get_week_activity():
    """Get count of days with logged hours this week (Mon-Sun)."""
    conn = get_db()
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
    
    cur = conn.execute(
        "SELECT COUNT(DISTINCT date) as count FROM time_logs WHERE date >= ? AND date <= ?",
        (week_start, week_end)
    )
    result = cur.fetchone()
    
    return result["count"] if result else 0


def get_today_position(start_date):
    """Calculate expected position based on actual curriculum structure."""
    if not start_date:
        return None
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()
    days_elapsed = (today - start).days
    
    # Get actual curriculum structure from database
    # Count total curriculum days and find which one we should be on
    conn = get_db()
    
    # Get all unique phase/week/day combinations ordered
    curriculum_days = conn.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        ORDER BY phase_index, week, day
    """).fetchall()
    
    # days_elapsed maps to curriculum day index
    if days_elapsed < 0:
        return {"status": "not_started"}
    
    if days_elapsed >= len(curriculum_days):
        expected_idx = len(curriculum_days) - 1  # Cap at last day
        status = "complete"
    else:
        expected_idx = days_elapsed
        status = "in_progress"
    
    expected = curriculum_days[expected_idx]
    
    return {
        "expected_phase": expected[0],
        "expected_week": expected[1],
        "expected_day": expected[2],
        "days_elapsed": days_elapsed,
        "total_curriculum_days": len(curriculum_days),
        "status": status
    }


def get_continue_resource(current_phase, current_week):
    """Get the resource to continue working on."""
    conn = get_db()
    
    # First check for in_progress
    in_progress = conn.execute(
        "SELECT * FROM resources WHERE status = 'in_progress' ORDER BY phase_index, week, day LIMIT 1"
    ).fetchone()
    
    if in_progress:
        return dict(in_progress)
    
    # If none, get first incomplete in current position
    incomplete = conn.execute(
        "SELECT * FROM resources WHERE status = 'not_started' AND phase_index = ? AND week = ? ORDER BY day, sort_order LIMIT 1",
        (current_phase, current_week)
    ).fetchone()
    
    if incomplete:
        return dict(incomplete)
    
    return None


def get_hours_today():
    """Get hours logged today."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date = ?", (today,))
    result = cur.fetchone()
    return result["total"] if result else 0


def get_start_date():
    """Get start date from settings."""
    conn = get_db()
    result = conn.execute("SELECT value FROM settings WHERE key = 'start_date'").fetchone()
    return result[0] if result else None


def set_start_date(date_str):
    """Set start date in settings."""
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('start_date', ?)", (date_str,))
    conn.commit()


def calculate_schedule(start_date):
    """Assign scheduled_date to each curriculum day, skipping blocked days."""
    conn = get_db()
    
    # Get all unique curriculum days in order
    curriculum_days = conn.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        WHERE phase_index IS NOT NULL AND week IS NOT NULL AND day IS NOT NULL
        ORDER BY phase_index, week, day
    """).fetchall()
    
    if not curriculum_days:
        return  # No curriculum days to schedule
    
    # Get blocked dates
    blocked = set(row[0] for row in conn.execute(
        "SELECT date FROM blocked_days"
    ).fetchall())
    
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    for phase_idx, week, day in curriculum_days:
        # Skip blocked days
        while current_date.strftime("%Y-%m-%d") in blocked:
            current_date += timedelta(days=1)
        
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Assign this date to all resources on this curriculum day
        # Set original_date only if it's not already set
        conn.execute("""
            UPDATE resources 
            SET scheduled_date = ?, 
                original_date = COALESCE(original_date, ?)
            WHERE phase_index = ? AND week = ? AND day = ?
        """, (date_str, date_str, phase_idx, week, day))
        
        current_date += timedelta(days=1)
    
    conn.commit()


def recalculate_schedule_from(from_date):
    """Recalculate scheduled_dates from a specific date forward."""
    conn = get_db()
    
    # Find which curriculum day was on or after this date
    affected = conn.execute("""
        SELECT MIN(phase_index), MIN(week), MIN(day)
        FROM resources 
        WHERE scheduled_date >= ?
    """, (from_date,)).fetchone()
    
    if not affected or affected[0] is None:
        return  # Nothing to recalculate
    
    # Get curriculum days from this point forward
    curriculum_days = conn.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        WHERE (phase_index > ?) 
           OR (phase_index = ? AND week > ?)
           OR (phase_index = ? AND week = ? AND day >= ?)
        ORDER BY phase_index, week, day
    """, (affected[0], affected[0], affected[1], affected[0], affected[1], affected[2])).fetchall()
    
    if not curriculum_days:
        return
    
    # Get blocked dates >= from_date
    blocked = set(row[0] for row in conn.execute(
        "SELECT date FROM blocked_days WHERE date >= ?", (from_date,)
    ).fetchall())
    
    current_date = datetime.strptime(from_date, "%Y-%m-%d")
    
    for phase_idx, week, day in curriculum_days:
        while current_date.strftime("%Y-%m-%d") in blocked:
            current_date += timedelta(days=1)
        
        date_str = current_date.strftime("%Y-%m-%d")
        
        conn.execute("""
            UPDATE resources 
            SET scheduled_date = ?
            WHERE phase_index = ? AND week = ? AND day = ?
        """, (date_str, phase_idx, week, day))
        
        current_date += timedelta(days=1)
    
    conn.commit()


def get_projected_end_date():
    """Get projected end date from maximum scheduled_date."""
    conn = get_db()
    result = conn.execute(
        "SELECT MAX(scheduled_date) FROM resources WHERE scheduled_date IS NOT NULL"
    ).fetchone()
    return result[0] if result and result[0] else None


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_burndown_data():
    """Get burndown chart data showing hours remaining vs time."""
    conn = get_db()
    
    # Get cumulative hours by date
    daily_logs = conn.execute("""
        SELECT date, SUM(hours) as hours
        FROM time_logs
        GROUP BY date
        ORDER BY date
    """).fetchall()
    
    total_hours = 408
    cumulative = 0
    actual_data = []
    
    for row in daily_logs:
        date = row["date"]
        hours = row["hours"] or 0
        cumulative += hours
        actual_data.append({
            "date": date,
            "remaining": total_hours - cumulative
        })
    
    return {
        "total": total_hours,
        "logged": cumulative,
        "remaining": total_hours - cumulative,
        "actual": actual_data
    }


def get_overdue_days():
    """Get overdue curriculum days (scheduled_date < today and not complete)."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    
    overdue = conn.execute("""
        SELECT DISTINCT phase_index, week, day, scheduled_date,
               COUNT(*) as total_resources,
               SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed
        FROM resources
        WHERE scheduled_date < ? AND scheduled_date IS NOT NULL
        GROUP BY phase_index, week, day, scheduled_date
        HAVING completed < total_resources
        ORDER BY scheduled_date
    """, (today,)).fetchall()
    
    return [dict(row) for row in overdue]


def get_time_reports():
    """Get time reporting data for analytics."""
    conn = get_db()
    
    # Hours by phase
    by_phase = conn.execute("""
        SELECT r.phase_index, SUM(t.hours) as hours
        FROM time_logs t
        JOIN resources r ON t.resource_id = r.id
        WHERE r.phase_index IS NOT NULL
        GROUP BY r.phase_index
        ORDER BY r.phase_index
    """).fetchall()
    
    # Hours by resource type
    by_type = conn.execute("""
        SELECT r.resource_type, SUM(t.hours) as hours
        FROM time_logs t
        JOIN resources r ON t.resource_id = r.id
        WHERE r.resource_type IS NOT NULL
        GROUP BY r.resource_type
    """).fetchall()
    
    # Hours by week
    by_week = conn.execute("""
        SELECT strftime('%Y-%W', date) as week, SUM(hours) as hours
        FROM time_logs
        GROUP BY week
        ORDER BY week
    """).fetchall()
    
    # Daily average
    total_hours = conn.execute("SELECT COALESCE(SUM(hours), 0) FROM time_logs").fetchone()[0]
    total_days = conn.execute("SELECT COUNT(DISTINCT date) FROM time_logs").fetchone()[0]
    daily_avg = total_hours / total_days if total_days > 0 else 0
    
    # Calculate needed daily average (408 hours total, estimate days remaining)
    start_date = get_start_date()
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        today = datetime.now()
        days_elapsed = (today - start).days
        days_remaining = 119 - days_elapsed  # 17 weeks * 7 days
        needed_daily = (408 - total_hours) / days_remaining if days_remaining > 0 else 0
    else:
        needed_daily = 0
    
    return {
        "by_phase": [dict(row) for row in by_phase],
        "by_type": [dict(row) for row in by_type],
        "by_week": [dict(row) for row in by_week],
        "daily_avg": daily_avg,
        "needed_daily": needed_daily,
        "total_hours": total_hours
    }


def get_resources_by_week(phase_index, week):
    """Get resources for a specific week with tags in single query (fixes N+1)."""
    conn = get_db()
    query = """
        SELECT r.*,
               GROUP_CONCAT(t.name, '|||') as tag_names,
               GROUP_CONCAT(t.color, '|||') as tag_colors
        FROM resources r
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE r.phase_index = ? AND r.week = ?
        GROUP BY r.id
        ORDER BY r.day, r.sort_order, r.is_favorite DESC, r.created_at DESC
    """
    cur = conn.execute(query, (phase_index, week))
    rows = cur.fetchall()
    
    grouped = {i: [] for i in range(1, 7)}
    ungrouped = []
    for r in rows:
        item = dict(r)
        # Parse concatenated tags
        if r["tag_names"]:
            item["tags"] = r["tag_names"].split("|||")
            item["tag_colors"] = r["tag_colors"].split("|||")
        else:
            item["tags"] = []
            item["tag_colors"] = []
        
        d = r["day"]
        if isinstance(d, int) and d in grouped:
            grouped[d].append(item)
        else:
            ungrouped.append(item)
    return grouped, ungrouped


def get_day_completion(phase_index, week, day):
    """Get completion stats for a specific day. Returns (completed, total)."""
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_completed) as completed FROM resources WHERE phase_index = ? AND week = ? AND day = ?",
        (phase_index, week, day)
    )
    row = cur.fetchone()
    total = row["total"] or 0
    completed = row["completed"] or 0
    return (completed, total)


def get_week_completion(phase_index, week):
    """Get completion stats for a specific week. Returns (completed, total, percent)."""
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_completed) as completed FROM resources WHERE phase_index = ? AND week = ?",
        (phase_index, week)
    )
    row = cur.fetchone()
    total = row["total"] or 0
    completed = row["completed"] or 0
    percent = (completed / total * 100) if total > 0 else 0
    return (completed, total, percent)


def get_phase_completion(phase_index):
    """Get completion stats for a specific phase. Returns (completed, total, percent)."""
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_completed) as completed FROM resources WHERE phase_index = ?",
        (phase_index,)
    )
    row = cur.fetchone()
    total = row["total"] or 0
    completed = row["completed"] or 0
    percent = (completed / total * 100) if total > 0 else 0
    return (completed, total, percent)


@app.route("/")
@app.route("/view/<int:view_phase>/<int:view_week>")
def dashboard(view_phase=None, view_week=None):
    init_if_needed()
    curriculum = load_curriculum()
    progress = get_progress()
    current_phase = progress['current_phase']
    current_week = progress['current_week']
    
    # Handle view mode (doesn't change state)
    if view_phase is not None and view_week is not None:
        # Validate view parameters
        if view_phase >= len(curriculum["phases"]):
            view_phase = len(curriculum["phases"]) - 1
        if view_phase < 0:
            view_phase = 0
        phase = curriculum["phases"][view_phase]
        if view_week < 1:
            view_week = 1
        if view_week > phase["weeks"]:
            view_week = phase["weeks"]
        # Use view values for display, but keep current_phase/current_week for state
        display_phase = view_phase
        display_week = view_week
    else:
        # Normal mode - use current phase/week
        if current_phase >= len(curriculum["phases"]):
            current_phase = len(curriculum["phases"]) - 1
        display_phase = current_phase
        display_week = current_week
        view_phase = None
        view_week = None
    
    phase = curriculum["phases"][display_phase]
    week_hours = get_current_week_hours()
    total_hours = get_total_hours()
    curriculum_total = sum(p["hours"] for p in curriculum["phases"])
    expected_weekly = phase["hours"] / phase["weeks"] if phase["weeks"] > 0 else 0
    completed = get_completed_metrics(display_phase)
    completed_texts = {m["metric_text"] for m in completed}
    total_weeks = sum(p["weeks"] for p in curriculum["phases"])
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:display_phase])
    current_absolute_week = weeks_before + display_week
    overall_progress = (total_hours / curriculum_total * 100) if curriculum_total > 0 else 0
    recent_logs = get_recent_logs()
    resources = get_resources(display_phase)
    grouped_week, ungrouped_week = get_resources_by_week(display_phase, display_week)
    all_tags = get_all_tags()
    
    # Add logged hours to each resource
    resource_hours = {}
    for r in resources:
        hours = get_hours_for_resource(r["id"])
        if hours > 0:
            resource_hours[r["id"]] = hours
    
    # Also add to grouped_week resources
    for day_resources in grouped_week.values():
        for r in day_resources:
            hours = get_hours_for_resource(r["id"])
            if hours > 0:
                r["logged_hours"] = hours
    phases_data = []
    for i, p in enumerate(curriculum["phases"]):
        phase_completed = get_completed_metrics(i)
        metrics_total = len(p.get("metrics", []))
        phases_data.append({
            "index": i, "name": p["name"], "weeks": p["weeks"], "hours": p["hours"],
            "logged": get_hours_for_phase(i, curriculum), "is_current": i == current_phase,
            "is_complete": len(phase_completed) == metrics_total if metrics_total > 0 else False, "metrics_done": len(phase_completed),
            "metrics_total": metrics_total
        })
    
    # Get search query and tag filter if present
    search_query = request.args.get("q", "").strip()
    tag_filter = request.args.get("tag", "").strip()
    
    # Apply filters
    if search_query or tag_filter:
        filtered_grouped = {}
        for day, day_resources in grouped_week.items():
            filtered_day = day_resources
            
            # Apply search filter
            if search_query:
                search_lower = search_query.lower()
                filtered_day = [
                    r for r in filtered_day
                    if search_lower in (r.get("title", "") or "").lower()
                    or search_lower in (r.get("notes", "") or "").lower()
                    or search_lower in (r.get("topic", "") or "").lower()
                ]
            
            # Apply tag filter
            if tag_filter:
                filtered_day = [
                    r for r in filtered_day
                    if tag_filter in r.get("tags", [])
                ]
            
            if filtered_day:
                filtered_grouped[day] = filtered_day
        
        grouped_week = filtered_grouped
        
        # Apply same filters to ungrouped
        filtered_ungrouped = ungrouped_week
        if search_query:
            search_lower = search_query.lower()
            filtered_ungrouped = [
                r for r in filtered_ungrouped
                if search_lower in (r.get("title", "") or "").lower()
                or search_lower in (r.get("notes", "") or "").lower()
                or search_lower in (r.get("topic", "") or "").lower()
            ]
        if tag_filter:
            filtered_ungrouped = [
                r for r in filtered_ungrouped
                if tag_filter in r.get("tags", [])
            ]
        ungrouped_week = filtered_ungrouped
    
    # Calculate completion rollups
    phase_completed, phase_total, phase_percent = get_phase_completion(display_phase)
    week_completed, week_total, week_percent = get_week_completion(display_phase, display_week)
    day_completions = {}
    for day in range(1, 7):
        day_completed, day_total = get_day_completion(display_phase, display_week, day)
        day_completions[day] = {"completed": day_completed, "total": day_total}
    
    # Calculate completion for all weeks in this phase for tab indicators
    all_weeks_completion = {}
    for w in range(1, phase["weeks"] + 1):
        w_completed, w_total, w_percent = get_week_completion(display_phase, w)
        all_weeks_completion[w] = {
            "completed": w_completed,
            "total": w_total,
            "percent": w_percent,
            "is_complete": w_completed == w_total and w_total > 0,
            "is_partial": w_completed > 0 and w_completed < w_total
        }
    
    # Calculate streaks for header display
    current_streak = get_current_streak()
    longest_streak = get_longest_streak()
    week_activity = get_week_activity()
    
    # Get Today View data
    today_position = None
    if progress.get('started_at'):
        today_position = get_today_position(progress['started_at'])
    
    # Get Continue resource
    continue_resource = get_continue_resource(current_phase, current_week)
    
    # Get today's journal entry
    today_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    today_journal = conn.execute("SELECT * FROM journal_entries WHERE date = ?", (today_date,)).fetchone()
    today_journal_dict = dict(today_journal) if today_journal else None
    
    # Get hours logged today
    hours_today = get_hours_today()
    
    # Get start date
    start_date = get_start_date()
    
    # Calculate schedule if start_date exists but scheduled_date is NULL
    if start_date:
        # Check if any resources have scheduled_date
        has_scheduled = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE scheduled_date IS NOT NULL"
        ).fetchone()[0] > 0
        
        if not has_scheduled:
            calculate_schedule(start_date)
    
    # Get projected end date
    projected_end_date = get_projected_end_date() if start_date else None
    
    # Get resources for expected position (if available)
    expected_resources = []
    if today_position and today_position.get('status') != 'not_started':
        expected_resources = conn.execute(
            "SELECT * FROM resources WHERE phase_index = ? AND week = ? AND day = ?",
            (today_position['expected_phase'], today_position['expected_week'], today_position['expected_day'])
        ).fetchall()
        expected_resources = [dict(r) for r in expected_resources]
    
    return render_template("dashboard.html", phase=phase, phase_index=display_phase, current_week=display_week,
        current_phase=current_phase, current_week_state=current_week, view_phase=view_phase, view_week=view_week,
        week_hours=week_hours, expected_weekly=expected_weekly, total_hours=total_hours,
        curriculum_total=curriculum_total, overall_progress=min(overall_progress, 100),
        completed_texts=completed_texts, recent_logs=recent_logs, phases=phases_data,
        resources=resources, grouped_week_resources=grouped_week, ungrouped_week_resources=ungrouped_week, all_tags=all_tags, today=today_date,
        current_absolute_week=current_absolute_week, total_weeks=total_weeks, search_query=search_query,
        phase_completed=phase_completed, phase_total=phase_total, phase_percent=phase_percent,
        week_completed=week_completed, week_total=week_total, week_percent=week_percent,
        day_completions=day_completions, resource_hours=resource_hours, all_weeks_completion=all_weeks_completion,
        current_streak=current_streak, longest_streak=longest_streak, week_activity=week_activity,
        today_position=today_position, continue_resource=continue_resource, today_journal=today_journal_dict,
        hours_today=hours_today, expected_resources=expected_resources, curriculum=curriculum,
        start_date=start_date, projected_end_date=projected_end_date, today=datetime.now().strftime("%Y-%m-%d"),
        burndown_data=get_burndown_data() if start_date else None,
        overdue_days=get_overdue_days() if start_date else [])


@app.route("/resources")
def resources_page():
    """Show all resources with filters."""
    curriculum = load_curriculum()
    all_resources = get_all_resources()
    
    # Read filter parameters
    search_query = request.args.get("q", "").strip()
    filter_type = request.args.get("type", "").strip()
    filter_phase = request.args.get("phase", "").strip()
    filter_tag = request.args.get("tag", "").strip()
    filter_status = request.args.get("status", "").strip()
    
    # Apply filters
    filtered_resources = all_resources
    
    # Search filter (title, notes, topic)
    if search_query:
        search_lower = search_query.lower()
        filtered_resources = [
            r for r in filtered_resources
            if search_lower in (r.get("title", "") or "").lower()
            or search_lower in (r.get("notes", "") or "").lower()
            or search_lower in (r.get("topic", "") or "").lower()
        ]
    
    # Type filter
    if filter_type:
        filtered_resources = [
            r for r in filtered_resources
            if r.get("resource_type") == filter_type
        ]
    
    # Phase filter
    if filter_phase:
        try:
            phase_index = int(filter_phase)
            filtered_resources = [
                r for r in filtered_resources
                if r.get("phase_index") == phase_index
            ]
        except ValueError:
            pass
    
    # Tag filter
    if filter_tag:
        filtered_resources = [
            r for r in filtered_resources
            if filter_tag in r.get("tags", [])
        ]
    
    # Status filter
    if filter_status == "completed":
        filtered_resources = [r for r in filtered_resources if r.get("is_completed")]
    elif filter_status == "pending":
        filtered_resources = [r for r in filtered_resources if not r.get("is_completed")]
    elif filter_status == "favorites":
        filtered_resources = [r for r in filtered_resources if r.get("is_favorite")]
    
    # Add logged hours to each resource
    resource_hours = {}
    for r in filtered_resources:
        hours = get_hours_for_resource(r["id"])
        if hours > 0:
            resource_hours[r["id"]] = hours
    
    # Get overdue resources
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    overdue_resource_ids = set()
    overdue_resources = conn.execute("""
        SELECT DISTINCT id FROM resources
        WHERE scheduled_date < ? AND scheduled_date IS NOT NULL
          AND status != 'complete'
    """, (today,)).fetchall()
    for row in overdue_resources:
        overdue_resource_ids.add(row["id"])
    
    return render_template("resources.html", 
        resources=filtered_resources,
        phases=curriculum["phases"],
        all_tags=get_all_tags(),
        search_query=search_query,
        filter_type=filter_type,
        filter_phase=filter_phase,
        filter_tag=filter_tag,
        filter_status=filter_status,
        resource_hours=resource_hours,
        overdue_resource_ids=overdue_resource_ids)


@app.route("/log", methods=["POST"])
def log_hours():
    """Log hours with input validation."""
    try:
        hours_str = request.form.get("hours", "0").strip()
        hours = float(hours_str) if hours_str else 0.0
    except (ValueError, TypeError):
        flash("Oops, invalid hours value", "error")
        return redirect(url_for("dashboard"))
    
    log_date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()
    
    # Validate date format
    try:
        datetime.strptime(log_date, "%Y-%m-%d")
    except ValueError:
        flash("Oops, invalid date format", "error")
        return redirect(url_for("dashboard"))
    
    # New: Accept week, day, and resource_id from form
    week_str = request.form.get("week", "").strip()
    day_str = request.form.get("day", "").strip()
    resource_id_str = request.form.get("resource_id", "").strip()
    
    week = int(week_str) if week_str and week_str.isdigit() else None
    day = int(day_str) if day_str and day_str.isdigit() else None
    resource_id = int(resource_id_str) if resource_id_str and resource_id_str.isdigit() else None
    
    # Validate hours range
    if hours <= 0 or hours > 24:
        flash("Hours must be between 0.25 and 24.", "error")
        return redirect(url_for("dashboard"))
    
    # Get current phase_index for this log entry
    progress = get_progress()
    current_phase = progress['current_phase']
    
    conn = get_db()
    # Insert new log entry with week, day, and resource_id if provided
    conn.execute(
        "INSERT INTO time_logs (date, hours, notes, phase_index, week, day, resource_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (log_date, hours, notes, current_phase, week, day, resource_id)
    )
    conn.commit()
    
    # Log activity
    details = f"{hours}h on {log_date}"
    if notes:
        details += f": {notes[:50]}"
    log_activity("hours_logged", "time_log", None, details)
    
    flash(f"Locked in {hours} hours!", "success")
    return redirect(url_for("dashboard"))


@app.route("/complete-metric", methods=["POST"])
def complete_metric():
    """Complete a metric with input validation."""
    try:
        phase_index = int(request.form.get("phase_index", 0))
    except (ValueError, TypeError):
        flash("Invalid phase index.", "error")
        return redirect(url_for("dashboard"))
    
    metric_text = request.form.get("metric_text", "").strip()
    if not metric_text:
        flash("Metric text is required.", "error")
        return redirect(url_for("dashboard"))
    
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO completed_metrics (phase_index, metric_text, completed_date) VALUES (?, ?, ?)",
        (phase_index, metric_text, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    
    # Log activity
    log_activity("metric_completed", "metric", phase_index, metric_text[:100])
    
    return redirect(url_for("dashboard"))


@app.route("/uncomplete-metric", methods=["POST"])
def uncomplete_metric():
    """Uncomplete a metric with input validation."""
    try:
        phase_index = int(request.form.get("phase_index", 0))
    except (ValueError, TypeError):
        flash("Invalid phase index.", "error")
        return redirect(url_for("dashboard"))
    
    metric_text = request.form.get("metric_text", "").strip()
    if not metric_text:
        flash("Metric text is required.", "error")
        return redirect(url_for("dashboard"))
    
    conn = get_db()
    conn.execute("DELETE FROM completed_metrics WHERE phase_index = ? AND metric_text = ?", (phase_index, metric_text))
    conn.commit()
    return redirect(url_for("dashboard"))


@app.route("/next-week", methods=["POST"])
def next_week():
    curriculum = load_curriculum()
    progress = get_progress()
    current_phase = progress['current_phase']
    current_week = progress['current_week']
    if current_phase >= len(curriculum["phases"]):
        return redirect(url_for("dashboard"))
    phase = curriculum["phases"][current_phase]
    if current_week < phase["weeks"]:
        update_progress(current_week=current_week + 1)
    elif current_phase + 1 < len(curriculum["phases"]):
        update_progress(current_phase=current_phase + 1, current_week=1)
    return redirect(url_for("dashboard"))


@app.route("/prev-week", methods=["POST"])
def prev_week():
    curriculum = load_curriculum()
    progress = get_progress()
    current_phase = progress['current_phase']
    current_week = progress['current_week']
    if current_week > 1:
        update_progress(current_week=current_week - 1)
    elif current_phase > 0:
        update_progress(current_phase=current_phase - 1, current_week=curriculum["phases"][current_phase - 1]["weeks"])
    return redirect(url_for("dashboard"))


@app.route("/jump-to-phase/<int:phase_index>", methods=["POST"])
def jump_to_phase(phase_index):
    curriculum = load_curriculum()
    if 0 <= phase_index < len(curriculum["phases"]):
        update_progress(current_phase=phase_index, current_week=1)
    return redirect(url_for("dashboard"))


@app.route("/add-resource", methods=["POST"])
def add_resource():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    resource_type = request.form.get("resource_type", "link")
    notes = request.form.get("notes", "").strip()
    topic = request.form.get("topic", "").strip()
    phase_index = request.form.get("phase_index", "").strip()
    week_str = request.form.get("week", "").strip()
    day_str = request.form.get("day", "").strip()
    estimated_minutes_str = request.form.get("estimated_minutes", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    
    if not title:
        flash("Oops, title is required", "error")
        return redirect(request.referrer or url_for("dashboard"))
    
    # Validate phase_index safely
    phase_idx = None
    if phase_index and phase_index.isdigit():
        try:
            phase_idx = int(phase_index)
        except (ValueError, TypeError):
            phase_idx = None
    
    week_val = int(week_str) if week_str and week_str.isdigit() else None
    day_val = int(day_str) if day_str and day_str.isdigit() else None
    estimated_minutes = int(estimated_minutes_str) if estimated_minutes_str and estimated_minutes_str.isdigit() else None
    
    # Check for duplicate
    conn = get_db()
    if phase_idx is not None and week_val is not None and day_val is not None:
        existing = conn.execute(
            "SELECT id FROM resources WHERE phase_index = ? AND week = ? AND day = ? AND title = ?",
            (phase_idx, week_val, day_val, title)
        ).fetchone()
        
        if existing:
            flash(f"Resource '{title}' already exists for this day.", "warning")
            return redirect(request.referrer or url_for("dashboard"))
    
    try:
        conn.execute("""INSERT INTO resources 
            (phase_index, week, day, title, topic, url, resource_type, notes, source, estimated_minutes, difficulty, user_modified) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user', ?, ?, 1)""",
            (phase_idx, week_val, day_val, title, topic or None, url or None, resource_type, notes or None, estimated_minutes, difficulty or None))
        conn.commit()
        flash(f"Added: {title}", "success")
    except sqlite3.IntegrityError:
        flash("Duplicate resource detected.", "warning")
    
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-resource/<int:resource_id>", methods=["POST"])
def toggle_resource(resource_id):
    """Toggle resource status with validation."""
    # Capture query parameters to preserve filters
    search_query = request.form.get("q", "")
    tag_filter = request.form.get("tag", "")
    
    conn = get_db()
    # Get current state and resource details
    resource = conn.execute("SELECT phase_index, week, day, status FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not resource:
        flash("Oops, resource not found", "error")
        return redirect(request.referrer or url_for("dashboard"))
    
    phase_index = resource["phase_index"]
    week = resource["week"]
    day = resource["day"]
    current_status = resource["status"] or "not_started"
    
    # Cycle through states: not_started → in_progress → complete → not_started
    status_cycle = {
        "not_started": "in_progress",
        "in_progress": "complete",
        "complete": "not_started",
        "skipped": "not_started"
    }
    new_status = status_cycle.get(current_status, "in_progress")
    
    # Update resource with new status and timestamp
    if new_status == "complete":
        conn.execute(
            "UPDATE resources SET status = ?, is_completed = 1, completed_at = ? WHERE id = ?",
            (new_status, datetime.now().isoformat(), resource_id)
        )
    else:
        conn.execute(
            "UPDATE resources SET status = ?, is_completed = 0, completed_at = NULL WHERE id = ?",
            (new_status, resource_id)
        )
    
    # If this is Day 6 (BUILD DAY), link to metrics based on new status
    if day == 6 and phase_index is not None and week is not None:
        curriculum = load_curriculum()
        if phase_index < len(curriculum["phases"]):
            phase = curriculum["phases"][phase_index]
            metrics = phase.get("metrics", [])
            # Map week to metric index: Week 1 → metrics[0], Week 2 → metrics[1], etc.
            metric_index = week - 1  # week is 1-indexed, metrics are 0-indexed
            if 0 <= metric_index < len(metrics):
                metric_text = metrics[metric_index]
                
                if new_status == "complete":
                    # Auto-complete the metric and store the resource_id that triggered it
                    conn.execute(
                        "INSERT OR IGNORE INTO completed_metrics (phase_index, metric_text, completed_date, resource_id) VALUES (?, ?, ?, ?)",
                        (phase_index, metric_text, datetime.now().strftime("%Y-%m-%d"), resource_id)
                    )
                else:
                    # Auto-delete the metric if not complete
                    conn.execute(
                        "DELETE FROM completed_metrics WHERE phase_index = ? AND metric_text = ?",
                        (phase_index, metric_text)
                    )
    
    conn.commit()
    
    # Log the activity
    log_activity(
        f"resource_{new_status}",
        "resource",
        resource_id,
        f"Phase {phase_index + 1} Week {week} Day {day}"
    )
    
    # Build redirect URL with preserved query parameters
    redirect_url = request.referrer or url_for("dashboard")
    if search_query or tag_filter:
        params = []
        if search_query:
            params.append(f"q={search_query}")
        if tag_filter:
            params.append(f"tag={tag_filter}")
        if params:
            separator = "?" if "?" not in redirect_url else "&"
            redirect_url = f"{redirect_url}{separator}{'&'.join(params)}"
    
    return redirect(redirect_url)


@app.route("/toggle-favorite/<int:resource_id>", methods=["POST"])
def toggle_favorite(resource_id):
    conn = get_db()
    conn.execute("UPDATE resources SET is_favorite = NOT is_favorite WHERE id = ?", (resource_id,))
    conn.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    conn = get_db()
    conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    conn.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-log/<date>", methods=["POST"])
def delete_log(date):
    conn = get_db()
    conn.execute("DELETE FROM time_logs WHERE date = ?", (date,))
    conn.commit()
    return redirect(url_for("dashboard"))


@app.route("/add-tag", methods=["POST"])
def add_tag():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#6366f1")
    if not name:
        return redirect(request.referrer or url_for("resources_page"))
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (name, color))
    conn.commit()
    flash(f"Tag '{name}' created", "success")
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/delete-tag/<int:tag_id>", methods=["POST"])
def delete_tag(tag_id):
    conn = get_db()
    conn.execute("DELETE FROM resource_tags WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/export")
def export_data():
    conn = get_db()
    config = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM config").fetchall()}
    time_logs = [dict(r) for r in conn.execute("SELECT date, hours, notes, phase_index FROM time_logs ORDER BY date").fetchall()]
    metrics = [dict(r) for r in conn.execute("SELECT phase_index, metric_text, completed_date FROM completed_metrics").fetchall()]
    resources = [dict(r) for r in conn.execute("SELECT phase_index, week, day, title, topic, url, resource_type, notes, is_completed, is_favorite, source FROM resources").fetchall()]
    tags = [dict(r) for r in conn.execute("SELECT name, color FROM tags").fetchall()]
    data = {"exported_at": datetime.now().isoformat(), "config": config, "time_logs": time_logs,
            "completed_metrics": metrics, "resources": resources, "tags": tags}
    return Response(json.dumps(data, indent=2), mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=curriculum_export.json"})


@app.route("/activity")
def activity():
    """Show activity history."""
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    return render_template("activity.html", logs=logs)


@app.route("/journal")
def journal():
    """Show all journal entries."""
    conn = get_db()
    entries = conn.execute(
        "SELECT * FROM journal_entries ORDER BY date DESC"
    ).fetchall()
    
    # Get curriculum and today position for pre-populating dropdowns
    curriculum = load_curriculum()
    progress = get_progress()
    today_position = None
    if progress.get('started_at'):
        today_position = get_today_position(progress['started_at'])
    
    phases_data = []
    for i, p in enumerate(curriculum["phases"]):
        phases_data.append({
            "index": i, "name": p["name"], "weeks": p["weeks"]
        })
    
    return render_template("journal.html", entries=entries, today=datetime.now().strftime("%Y-%m-%d"),
                          phases=phases_data, today_position=today_position, editing=None)


@app.route("/journal", methods=["POST"])
def save_journal():
    """Save or update today's journal entry."""
    date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    content = request.form.get("content", "").strip()
    mood = request.form.get("mood", "").strip()
    
    # Get curriculum day linking (optional)
    link_to_day = request.form.get("link_to_day", "").strip()
    phase_index = request.form.get("phase_index", "").strip()
    week = request.form.get("week", "").strip()
    day = request.form.get("day", "").strip()
    
    phase_index_val = int(phase_index) if phase_index and phase_index.isdigit() else None
    week_val = int(week) if week and week.isdigit() else None
    day_val = int(day) if day and day.isdigit() else None
    
    conn = get_db()
    # Check if entry exists for this date
    existing = conn.execute("SELECT id FROM journal_entries WHERE date = ?", (date,)).fetchone()
    
    if existing:
        if link_to_day and phase_index_val is not None:
            conn.execute(
                "UPDATE journal_entries SET content = ?, mood = ?, phase_index = ?, week = ?, day = ?, updated_at = ? WHERE date = ?",
                (content, mood, phase_index_val, week_val, day_val, datetime.now().isoformat(), date)
            )
        else:
            conn.execute(
                "UPDATE journal_entries SET content = ?, mood = ?, phase_index = NULL, week = NULL, day = NULL, updated_at = ? WHERE date = ?",
                (content, mood, datetime.now().isoformat(), date)
            )
        flash("Reflection updated!", "success")
    else:
        if link_to_day and phase_index_val is not None:
            conn.execute(
                "INSERT INTO journal_entries (date, content, mood, phase_index, week, day) VALUES (?, ?, ?, ?, ?, ?)",
                (date, content, mood, phase_index_val, week_val, day_val)
            )
        else:
            conn.execute(
                "INSERT INTO journal_entries (date, content, mood) VALUES (?, ?, ?)",
                (date, content, mood)
            )
        flash("Reflection logged", "success")
    
    conn.commit()
    
    return redirect(url_for("journal"))


@app.route("/journal/<int:entry_id>/edit", methods=["GET", "POST"])
def edit_journal(entry_id):
    """Edit a journal entry."""
    conn = get_db()
    entry = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    
    if not entry:
        flash("Journal entry not found.", "error")
        return redirect(url_for("journal"))
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        mood = request.form.get("mood", "").strip()
        
        # Get curriculum day linking (optional)
        link_to_day = request.form.get("link_to_day", "").strip()
        phase_index = request.form.get("phase_index", "").strip()
        week = request.form.get("week", "").strip()
        day = request.form.get("day", "").strip()
        
        phase_index_val = int(phase_index) if phase_index and phase_index.isdigit() else None
        week_val = int(week) if week and week.isdigit() else None
        day_val = int(day) if day and day.isdigit() else None
        
        if link_to_day and phase_index_val is not None:
            conn.execute(
                "UPDATE journal_entries SET content = ?, mood = ?, phase_index = ?, week = ?, day = ?, updated_at = ? WHERE id = ?",
                (content, mood, phase_index_val, week_val, day_val, datetime.now().isoformat(), entry_id)
            )
        else:
            conn.execute(
                "UPDATE journal_entries SET content = ?, mood = ?, phase_index = NULL, week = NULL, day = NULL, updated_at = ? WHERE id = ?",
                (content, mood, datetime.now().isoformat(), entry_id)
            )
        conn.commit()
        flash("Reflection updated!", "success")
        return redirect(url_for("journal"))
    
    # GET: Show edit form
    entries = conn.execute("SELECT * FROM journal_entries ORDER BY date DESC").fetchall()
    
    # Get curriculum for dropdowns
    curriculum = load_curriculum()
    phases_data = []
    for i, p in enumerate(curriculum["phases"]):
        phases_data.append({
            "index": i, "name": p["name"], "weeks": p["weeks"]
        })
    
    return render_template("journal.html", entries=entries, today=datetime.now().strftime("%Y-%m-%d"),
                          editing=dict(entry), phases=phases_data, today_position=None)


@app.route("/journal/<int:entry_id>/delete", methods=["POST"])
def delete_journal(entry_id):
    """Delete a journal entry."""
    conn = get_db()
    entry = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    
    if not entry:
        flash("Journal entry not found.", "error")
        return redirect(url_for("journal"))
    
    conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    conn.commit()
    flash("Reflection removed", "success")
    return redirect(url_for("journal"))


@app.route("/bulk", methods=["POST"])
def bulk_action():
    """Perform bulk action on multiple resources with validation."""
    action = request.form.get("action")
    if action not in ["complete", "progress", "skip", "delete"]:
        flash("Oops, invalid action", "error")
        return redirect(url_for("dashboard"))
    
    ids_str = request.form.get("ids", "")
    ids = []
    for id_str in ids_str.split(','):
        id_str = id_str.strip()
        if id_str and id_str.isdigit():
            try:
                ids.append(int(id_str))
            except (ValueError, TypeError):
                continue
    
    if not ids:
        flash("Oops, no valid resources selected", "error")
        return redirect(url_for("dashboard"))
    
    conn = get_db()
    
    if action == "complete":
        for rid in ids:
            conn.execute("UPDATE resources SET status = 'complete', is_completed = 1, completed_at = ? WHERE id = ?",
                (datetime.now().isoformat(), rid))
        flash(f"Crushed {len(ids)} resources", "success")
    elif action == "progress":
        for rid in ids:
            conn.execute("UPDATE resources SET status = 'in_progress', is_completed = 0 WHERE id = ?", (rid,))
        flash(f"Marked {len(ids)} resources as in progress", "success")
    elif action == "skip":
        for rid in ids:
            conn.execute("UPDATE resources SET status = 'skipped', is_completed = 0 WHERE id = ?", (rid,))
        flash(f"Skipped {len(ids)} resources", "success")
    elif action == "delete":
        for rid in ids:
            conn.execute("DELETE FROM resources WHERE id = ?", (rid,))
        flash(f"Deleted {len(ids)} resources", "success")
    
    conn.commit()
    
    return redirect(url_for("dashboard"))


@app.route("/reorder", methods=["POST"])
def reorder_resource():
    """Reorder resources via drag-and-drop with validation."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400
    
    try:
        data = request.json
    except Exception:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400
    
    resource_id = data.get("resource_id")
    new_position = data.get("new_position")
    day = data.get("day")
    week = data.get("week")
    phase = data.get("phase")
    
    # Validate all required fields
    if None in [resource_id, new_position, day, week, phase]:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    try:
        resource_id = int(resource_id)
        new_position = int(new_position)
        day = int(day)
        week = int(week)
        phase = int(phase)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid field types"}), 400
    
    conn = get_db()
    # Get all resources for this day
    resources = conn.execute(
        "SELECT id FROM resources WHERE phase_index = ? AND week = ? AND day = ? ORDER BY sort_order, id",
        (phase, week, day)
    ).fetchall()
    
    # Update sort orders
    for i, r in enumerate(resources):
        conn.execute("UPDATE resources SET sort_order = ? WHERE id = ?", (i * 10, r["id"]))
    
    # Set the moved resource to its new position
    conn.execute("UPDATE resources SET sort_order = ? WHERE id = ?", 
        (new_position * 10 + 5, resource_id))
    
    conn.commit()
    
    return jsonify({"success": True})


@app.route("/calendar")
@app.route("/calendar/<int:year>/<int:month>")
def calendar_view(year=None, month=None):
    """Display month calendar with logged hours and curriculum days."""
    if year is None or month is None:
        today = datetime.now()
        year, month = today.year, today.month
    
    # Get first/last day of month
    first_day = datetime(year, month, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    last_day = datetime(year, month, days_in_month)
    
    # Get all time logs for this month
    conn = get_db()
    logs_by_date = {}
    cur = conn.execute(
        "SELECT date, SUM(hours) as total_hours FROM time_logs WHERE date >= ? AND date <= ? GROUP BY date",
        (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    )
    for row in cur.fetchall():
        logs_by_date[row["date"]] = row["total_hours"]
    
    # Get curriculum schedule for this month
    curriculum_schedule = {}
    cur = conn.execute("""
        SELECT DISTINCT r.phase_index, r.week, r.day, r.scheduled_date,
               COUNT(r.id) as resource_count,
               SUM(CASE WHEN r.status = 'complete' THEN 1 ELSE 0 END) as completed_count
        FROM resources r
        WHERE r.scheduled_date IS NOT NULL 
          AND r.scheduled_date >= ? 
          AND r.scheduled_date <= ?
        GROUP BY r.phase_index, r.week, r.day, r.scheduled_date
        ORDER BY r.scheduled_date
    """, (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")))
    
    for row in cur.fetchall():
        date_str = row["scheduled_date"]
        if date_str not in curriculum_schedule:
            curriculum_schedule[date_str] = []
        curriculum_schedule[date_str].append({
            "phase": row["phase_index"],
            "week": row["week"],
            "day": row["day"],
            "resource_count": row["resource_count"],
            "completed_count": row["completed_count"]
        })
    
    # Get blocked days for this month
    blocked_days = set()
    cur = conn.execute(
        "SELECT date FROM blocked_days WHERE date >= ? AND date <= ?",
        (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    )
    for row in cur.fetchall():
        blocked_days.add(row["date"])
    
    # Build calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = first_day.strftime("%B %Y")
    
    # Calculate prev/next month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Get overdue days for this month
    overdue_days_map = {}
    overdue = get_overdue_days()
    for day in overdue:
        if day["scheduled_date"]:
            overdue_days_map[day["scheduled_date"]] = day
    
    return render_template("calendar.html",
        calendar_grid=cal,
        month_name=month_name,
        year=year,
        month=month,
        logs_by_date=logs_by_date,
        curriculum_schedule=curriculum_schedule,
        blocked_days=blocked_days,
        overdue_days_map=overdue_days_map,
        today_str=today_str,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month
    )


@app.route("/settings/start-date", methods=["POST"])
def update_start_date():
    """Update start date and recalculate schedule."""
    date_str = request.form.get("start_date")
    if not date_str:
        flash("Oops, start date is required", "error")
        return redirect(url_for("dashboard"))
    
    set_start_date(date_str)
    calculate_schedule(date_str)
    flash("Start date locked in! Schedule calculated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/curriculum/edit")
def curriculum_editor():
    """Show curriculum editor page with tree structure."""
    curriculum = load_curriculum()
    conn = get_db()
    
    # Build tree structure: Phase -> Week -> Day -> Resources
    curriculum_tree = []
    
    for phase_idx, phase in enumerate(curriculum["phases"]):
        weeks_data = []
        for week_num in range(1, phase["weeks"] + 1):
            days_data = []
            # Get all days that have resources for this week
            existing_days = conn.execute("""
                SELECT DISTINCT day FROM resources 
                WHERE phase_index = ? AND week = ?
                ORDER BY day
            """, (phase_idx, week_num)).fetchall()
            
            day_numbers = [row["day"] for row in existing_days if row["day"]]
            if not day_numbers:
                # If no days exist, show days 1-6
                day_numbers = list(range(1, 7))
            
            for day_num in day_numbers:
                # Get resources for this day
                resources = conn.execute("""
                    SELECT * FROM resources 
                    WHERE phase_index = ? AND week = ? AND day = ?
                    ORDER BY sort_order
                """, (phase_idx, week_num, day_num)).fetchall()
                
                days_data.append({
                    "number": day_num,
                    "resources": [dict(r) for r in resources]
                })
            
            # Calculate week resource count
            week_count = conn.execute(
                "SELECT COUNT(*) FROM resources WHERE phase_index = ? AND week = ?",
                (phase_idx, week_num)
            ).fetchone()[0]
            
            weeks_data.append({
                "number": week_num,
                "days": days_data,
                "resource_count": week_count
            })
        
        # Calculate phase resource count
        phase_count = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE phase_index = ?",
            (phase_idx,)
        ).fetchone()[0]
        
        curriculum_tree.append({
            "index": phase_idx,
            "name": phase["name"],
            "weeks": weeks_data,
            "resource_count": phase_count
        })
    
    return render_template("curriculum_editor.html", curriculum_tree=curriculum_tree)


@app.route("/api/calendar-day/<date_str>")
def api_calendar_day(date_str):
    """Get details for a specific calendar day."""
    conn = get_db()
    
    # Check if blocked
    blocked = conn.execute(
        "SELECT reason FROM blocked_days WHERE date = ?", (date_str,)
    ).fetchone()
    
    # Get curriculum days for this date
    curriculum_days = []
    cur = conn.execute("""
        SELECT DISTINCT r.phase_index, r.week, r.day,
               COUNT(r.id) as resource_count,
               SUM(CASE WHEN r.status = 'complete' THEN 1 ELSE 0 END) as completed_count
        FROM resources r
        WHERE r.scheduled_date = ?
        GROUP BY r.phase_index, r.week, r.day
    """, (date_str,))
    
    for row in cur.fetchall():
        # Get resources for this curriculum day
        resources = conn.execute("""
            SELECT id, title, status FROM resources
            WHERE phase_index = ? AND week = ? AND day = ? AND scheduled_date = ?
            ORDER BY sort_order
        """, (row["phase_index"], row["week"], row["day"], date_str)).fetchall()
        
        curriculum_days.append({
            "phase": row["phase_index"],
            "week": row["week"],
            "day": row["day"],
            "resource_count": row["resource_count"],
            "completed_count": row["completed_count"],
            "resources": [dict(r) for r in resources]
        })
    
    # Get hours logged
    hours_result = conn.execute(
        "SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date = ?", (date_str,)
    ).fetchone()
    hours = hours_result["total"] if hours_result else 0
    
    return jsonify({
        "blocked": blocked is not None,
        "blocked_reason": blocked["reason"] if blocked else None,
        "curriculum_days": curriculum_days,
        "hours": hours
    })


@app.route("/schedule/block", methods=["POST"])
def block_day():
    """Block a day and recalculate schedule."""
    date_str = request.form.get("date")
    reason = request.form.get("reason", "").strip()
    
    if not date_str:
        flash("Date is required.", "error")
        return redirect(url_for("calendar_view"))
    
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO blocked_days (date, reason) VALUES (?, ?)",
        (date_str, reason)
    )
    conn.commit()
    
    # Recalculate schedule from this date forward
    recalculate_schedule_from(date_str)
    
    flash("Day blocked and schedule shifted.", "success")
    return redirect(url_for("calendar_view"))


@app.route("/schedule/unblock", methods=["POST"])
def unblock_day():
    """Unblock a day and recalculate schedule."""
    date_str = request.form.get("date")
    
    if not date_str:
        flash("Date is required.", "error")
        return redirect(url_for("calendar_view"))
    
    conn = get_db()
    conn.execute("DELETE FROM blocked_days WHERE date = ?", (date_str,))
    conn.commit()
    
    # Recalculate schedule from this date forward
    recalculate_schedule_from(date_str)
    
    flash("Day unblocked and schedule shifted.", "success")
    return redirect(url_for("calendar_view"))


@app.route("/api/resource", methods=["POST"])
def api_add_resource():
    """Add new resource via API."""
    try:
        phase_index = int(request.form.get("phase_index"))
        week = int(request.form.get("week"))
        day = int(request.form.get("day"))
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip() or None
        resource_type = request.form.get("resource_type", "link")
        notes = request.form.get("notes", "").strip() or None
        estimated_minutes = request.form.get("estimated_minutes", "").strip()
        difficulty = request.form.get("difficulty", "").strip() or None
        
        estimated_minutes_val = int(estimated_minutes) if estimated_minutes and estimated_minutes.isdigit() else None
        
        if not title:
            return jsonify({"success": False, "error": "Title is required"}), 400
        
        conn = get_db()
        
        # Get max sort_order for this day
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM resources WHERE phase_index = ? AND week = ? AND day = ?",
            (phase_index, week, day)
        ).fetchone()[0]
        
        conn.execute("""
            INSERT INTO resources (phase_index, week, day, title, url, resource_type, notes, estimated_minutes, difficulty, sort_order, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'user')
        """, (phase_index, week, day, title, url, resource_type, notes, estimated_minutes_val, difficulty, max_order + 1))
        conn.commit()
        
        return jsonify({"success": True, "id": conn.lastrowid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/resource/<int:resource_id>", methods=["PUT"])
def api_update_resource(resource_id):
    """Update resource via API."""
    try:
        data = request.json
        conn = get_db()
        
        # Build update query dynamically
        updates = []
        values = []
        allowed_fields = ['title', 'url', 'resource_type', 'notes', 'estimated_minutes', 'difficulty']
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        if not updates:
            return jsonify({"success": False, "error": "No fields to update"}), 400
        
        values.append(resource_id)
        conn.execute(
            f"UPDATE resources SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/resource/<int:resource_id>", methods=["DELETE"])
def api_delete_resource(resource_id):
    """Delete resource via API."""
    try:
        conn = get_db()
        conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/resource/<int:resource_id>/reorder", methods=["POST"])
def api_reorder_resource(resource_id):
    """Update resource sort_order via API."""
    try:
        data = request.json
        new_position = int(data.get("new_position"))
        day = int(data.get("day"))
        week = int(data.get("week"))
        phase_index = int(data.get("phase_index"))
        
        conn = get_db()
        
        # Get current resource
        resource = conn.execute("SELECT sort_order FROM resources WHERE id = ?", (resource_id,)).fetchone()
        if not resource:
            return jsonify({"success": False, "error": "Resource not found"}), 404
        
        old_position = resource["sort_order"]
        
        # Get all resources for this day
        all_resources = conn.execute("""
            SELECT id, sort_order FROM resources 
            WHERE phase_index = ? AND week = ? AND day = ?
            ORDER BY sort_order
        """, (phase_index, week, day)).fetchall()
        
        # Reorder
        if new_position < old_position:
            # Moving up
            conn.execute("""
                UPDATE resources 
                SET sort_order = sort_order + 1 
                WHERE phase_index = ? AND week = ? AND day = ? 
                  AND sort_order >= ? AND sort_order < ?
            """, (phase_index, week, day, new_position, old_position))
        else:
            # Moving down
            conn.execute("""
                UPDATE resources 
                SET sort_order = sort_order - 1 
                WHERE phase_index = ? AND week = ? AND day = ? 
                  AND sort_order > ? AND sort_order <= ?
            """, (phase_index, week, day, old_position, new_position))
        
        # Set new position
        conn.execute(
            "UPDATE resources SET sort_order = ? WHERE id = ?",
            (new_position, resource_id)
        )
        conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/upload/resource/<int:resource_id>", methods=["POST"])
def upload_resource_file(resource_id):
    """Upload file attachment to a resource."""
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        
        conn = get_db()
        conn.execute("""
            INSERT INTO attachments (filename, original_filename, file_type, file_size, resource_id)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, file.filename, ext, filepath.stat().st_size, resource_id))
        conn.commit()
        
        return jsonify({"success": True, "filename": filename})
    
    return jsonify({"error": "File type not allowed"}), 400


@app.route("/upload/journal/<int:journal_id>", methods=["POST"])
def upload_journal_file(journal_id):
    """Upload file attachment to a journal entry."""
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        
        conn = get_db()
        conn.execute("""
            INSERT INTO attachments (filename, original_filename, file_type, file_size, journal_id)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, file.filename, ext, filepath.stat().st_size, journal_id))
        conn.commit()
        
        return jsonify({"success": True, "filename": filename})
    
    return jsonify({"error": "File type not allowed"}), 400


@app.route("/uploads/<filename>")
def serve_file(filename):
    """Serve uploaded files."""
    return send_from_directory(str(UPLOAD_FOLDER), filename)


@app.route("/attachment/<int:attachment_id>/delete", methods=["POST"])
def delete_attachment(attachment_id):
    """Delete an attachment."""
    conn = get_db()
    attachment = conn.execute("SELECT filename FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    if attachment:
        filepath = UPLOAD_FOLDER / attachment[0]
        if filepath.exists():
            filepath.unlink()
        conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()
        flash("Attachment removed", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/reports")
def reports():
    """Show time reports and analytics."""
    reports_data = get_time_reports()
    return render_template("reports.html", reports=reports_data)


@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    conn.execute("DELETE FROM config")
    conn.execute("DELETE FROM time_logs")
    conn.execute("DELETE FROM completed_metrics")
    conn.execute("UPDATE resources SET is_completed = 0")
    conn.execute("UPDATE resources SET is_favorite = 0")
    conn.execute("UPDATE resources SET status = 'not_started'")
    conn.execute("UPDATE resources SET completed_at = NULL")
    conn.commit()
    
    # Log activity
    log_activity("progress_reset", None, None, "All progress reset")
    
    init_if_needed()
    flash("Fresh slate!", "info")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html', error='Something went wrong. Please try again.'), 500


if __name__ == "__main__":
    print("\n🎓 Curriculum Tracker")
    print("=" * 40)
    print("Initializing database...")
    init_db()
    print("✓ Database ready!")
    print("\nOpen: http://localhost:5000")
    print("Ctrl+C to stop\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
