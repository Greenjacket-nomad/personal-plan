#!/usr/bin/env python3
"""
Progress service for Curriculum Tracker.
Handles progress tracking, streaks, time logs, and activity logging.
"""

from datetime import datetime, timedelta
from flask_login import current_user
from database import get_db, get_db_cursor


def get_progress(user_id=None):
    """Get progress data for a user. If user_id is None, uses current_user."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM progress WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    
    if not row:
        # Initialize if missing
        today = datetime.now().strftime("%Y-%m-%d")
        cur = get_db_cursor(conn)
        cur.execute("INSERT INTO progress (user_id, current_phase, current_week, started_at) VALUES (%s, 0, 1, %s)", (user_id, today))
        cur.close()
        conn.commit()
        return get_progress(user_id)
    
    return {
        'current_phase': row['current_phase'] if row['current_phase'] is not None else 0,
        'current_week': row['current_week'] if row['current_week'] is not None else 1,
        'started_at': row['started_at'],
        'last_activity_at': row['last_activity_at']
    }


def update_progress(user_id=None, **kwargs):
    """Update progress table with provided fields."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    # Whitelist allowed fields to prevent SQL injection
    allowed_fields = {'current_phase', 'current_week', 'started_at', 'last_activity_at'}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not filtered_kwargs:
        return
    sets = ', '.join(f"{k} = %s" for k in filtered_kwargs.keys())
    values = list(filtered_kwargs.values()) + [datetime.now().isoformat(), user_id]
    cur = get_db_cursor(conn)
    cur.execute(f"UPDATE progress SET {sets}, last_activity_at = %s WHERE user_id = %s", values)
    cur.close()
    conn.commit()


def init_if_needed():
    """Ensure progress table is initialized."""
    progress = get_progress()
    # get_progress() auto-initializes if missing
    return progress


def get_current_week_hours(user_id=None):
    """Get total hours logged this week."""
    if user_id is None:
        user_id = current_user.id
    
    from utils import get_week_dates
    today = datetime.now().strftime("%Y-%m-%d")
    week_start, week_end = get_week_dates(today)
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s AND date >= %s AND date <= %s", (user_id, week_start, week_end))
    result = cur.fetchone()
    cur.close()
    return result["total"]


def get_total_hours(user_id=None):
    """Get total hours logged."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    return result["total"]


def get_hours_for_phase(phase_index, curriculum, user_id=None):
    """Get total hours logged for a specific phase."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s AND phase_index = %s", (user_id, phase_index))
    result = cur.fetchone()
    cur.close()
    return result["total"]


def get_hours_for_week(phase_index, week, user_id=None):
    """Get total hours logged for a specific week."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s AND phase_index = %s AND week = %s",
        (user_id, phase_index, week)
    )
    result = cur.fetchone()
    cur.close()
    return result["total"] if result else 0


def get_hours_today(user_id=None):
    """Get hours logged today."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cur = get_db_cursor(conn)
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s AND date = %s", (user_id, today))
    result = cur.fetchone()
    cur.close()
    return result["total"] if result else 0


def get_recent_logs(days=7, user_id=None):
    """Get recent time logs."""
    if user_id is None:
        user_id = current_user.id
    
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT date, hours, notes FROM time_logs WHERE user_id = %s AND date >= %s ORDER BY date DESC", (user_id, cutoff))
    results = cur.fetchall()
    cur.close()
    return results


def get_completed_metrics(phase_index=None, user_id=None):
    """Get completed metrics."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    if phase_index is not None:
        cur.execute("SELECT * FROM completed_metrics WHERE user_id = %s AND phase_index = %s", (user_id, phase_index))
    else:
        cur.execute("SELECT * FROM completed_metrics WHERE user_id = %s", (user_id,))
    results = cur.fetchall()
    cur.close()
    return results


def log_activity(action, entity_type=None, entity_id=None, details=None, user_id=None):
    """Log an activity to the activity_log table."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "INSERT INTO activity_log (action, entity_type, entity_id, details, user_id) VALUES (%s, %s, %s, %s, %s)",
        (action, entity_type, entity_id, details, user_id)
    )
    cur.close()
    conn.commit()


def get_current_streak(user_id=None):
    """Calculate current consecutive days with logged hours ending today/yesterday."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT DISTINCT date FROM time_logs WHERE user_id = %s ORDER BY date DESC", (user_id,))
    dates = [row["date"] for row in cur.fetchall()]
    cur.close()
    
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


def get_longest_streak(user_id=None):
    """Calculate longest ever consecutive days with logged hours."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT DISTINCT date FROM time_logs WHERE user_id = %s ORDER BY date", (user_id,))
    dates = [datetime.strptime(row["date"], "%Y-%m-%d").date() for row in cur.fetchall()]
    cur.close()
    
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


def get_week_activity(user_id=None):
    """Get count of days with logged hours this week (Mon-Sun)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
    
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COUNT(DISTINCT date) as count FROM time_logs WHERE user_id = %s AND date >= %s AND date <= %s",
        (user_id, week_start, week_end)
    )
    result = cur.fetchone()
    cur.close()
    
    return result["count"] if result else 0


def get_today_position(start_date):
    """Calculate expected position based on actual curriculum structure."""
    if not start_date:
        return None
    
    # Handle both string and datetime objects (PostgreSQL returns datetime, SQLite returns string)
    if isinstance(start_date, datetime):
        start = start_date
    elif isinstance(start_date, str):
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Try to convert date object to datetime
        from datetime import date
        if isinstance(start_date, date):
            start = datetime.combine(start_date, datetime.min.time())
        else:
            return None
    
    today = datetime.now()
    days_elapsed = (today - start).days
    
    # Get actual curriculum structure from database
    # Count total curriculum days and find which one we should be on
    conn = get_db()
    
    # Get all unique phase/week/day combinations ordered
    user_id = current_user.id
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT DISTINCT phase_index, week, day 
        FROM resources 
        WHERE user_id = %s
        ORDER BY phase_index, week, day
    """, (user_id,))
    curriculum_days = cur.fetchall()
    cur.close()
    
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
        "expected_phase": expected['phase_index'],
        "expected_week": expected['week'],
        "expected_day": expected['day'],
        "days_elapsed": days_elapsed,
        "total_curriculum_days": len(curriculum_days),
        "status": status
    }


def get_overdue_days(user_id=None):
    """Get overdue curriculum days (scheduled_date < today and not complete)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cur = get_db_cursor(conn)
    
    cur.execute("""
        SELECT DISTINCT phase_index, week, day, scheduled_date,
               COUNT(*) as total_resources,
               SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed
        FROM resources
        WHERE user_id = %s AND scheduled_date < %s AND scheduled_date IS NOT NULL
        GROUP BY phase_index, week, day, scheduled_date
        HAVING SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) < COUNT(*)
        ORDER BY scheduled_date
    """, (user_id, today))
    overdue = cur.fetchall()
    cur.close()
    
    return [dict(row) for row in overdue]


def get_unified_progress(user_id=None, curriculum_total_hours=None):
    """Get unified progress metrics from same dataset.
    
    Returns both tasks completed and hours logged, ensuring they use
    the same user_id filter for consistency.
    
    Args:
        user_id: User ID to filter by
        curriculum_total_hours: Total expected hours for curriculum (optional, for percentage)
    
    Returns:
        dict with:
        - tasks_completed: int (count of completed resources)
        - tasks_total: int (total resources)
        - tasks_percent: float (percentage of tasks completed)
        - hours_logged: float (total hours from time_logs)
        - hours_percent: float (percentage if curriculum_total_hours provided, else None)
    """
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Get tasks completed and total from resources table
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'complete' OR is_completed = TRUE THEN 1 ELSE 0 END) as completed
        FROM resources
        WHERE user_id = %s
    """, (user_id,))
    tasks_result = cur.fetchone()
    
    tasks_total = tasks_result['total'] or 0
    tasks_completed = tasks_result['completed'] or 0
    tasks_percent = (tasks_completed / tasks_total * 100) if tasks_total > 0 else 0
    
    # Get total hours from time_logs table (same user_id)
    cur.execute("""
        SELECT COALESCE(SUM(hours), 0) as total
        FROM time_logs
        WHERE user_id = %s
    """, (user_id,))
    hours_result = cur.fetchone()
    
    hours_logged = hours_result['total'] or 0
    hours_percent = (hours_logged / curriculum_total_hours * 100) if curriculum_total_hours and curriculum_total_hours > 0 else None
    
    cur.close()
    
    return {
        'tasks_completed': tasks_completed,
        'tasks_total': tasks_total,
        'tasks_percent': tasks_percent,
        'hours_logged': hours_logged,
        'hours_percent': hours_percent
    }

