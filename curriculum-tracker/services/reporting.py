#!/usr/bin/env python3
"""
Reporting service for Curriculum Tracker.
Handles analytics, burndown charts, and time reports.
"""

from datetime import datetime
from database import get_db, get_db_cursor
from utils import get_start_date


def get_burndown_data():
    """Get burndown chart data showing hours remaining vs time."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Get cumulative hours by date
    cur.execute("""
        SELECT date, SUM(hours) as hours
        FROM time_logs
        GROUP BY date
        ORDER BY date
    """)
    daily_logs = cur.fetchall()
    cur.close()
    
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


def get_time_reports():
    """Get time reporting data for analytics."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Hours by phase
    cur.execute("""
        SELECT r.phase_index, SUM(t.hours) as hours
        FROM time_logs t
        JOIN resources r ON t.resource_id = r.id
        WHERE r.phase_index IS NOT NULL
        GROUP BY r.phase_index
        ORDER BY r.phase_index
    """)
    by_phase = cur.fetchall()
    
    # Hours by resource type
    cur.execute("""
        SELECT r.resource_type, SUM(t.hours) as hours
        FROM time_logs t
        JOIN resources r ON t.resource_id = r.id
        WHERE r.resource_type IS NOT NULL
        GROUP BY r.resource_type
    """)
    by_type = cur.fetchall()
    
    # Hours by week (PostgreSQL uses TO_CHAR instead of strftime)
    cur.execute("""
        SELECT TO_CHAR(date, 'IYYY-IW') as week, SUM(hours) as hours
        FROM time_logs
        GROUP BY TO_CHAR(date, 'IYYY-IW')
        ORDER BY week
    """)
    by_week = cur.fetchall()
    
    # Daily average
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs")
    total_hours = cur.fetchone()['total']
    cur.execute("SELECT COUNT(DISTINCT date) as count FROM time_logs")
    total_days = cur.fetchone()['count']
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
    
    cur.close()
    
    return {
        "by_phase": [dict(row) for row in by_phase],
        "by_type": [dict(row) for row in by_type],
        "by_week": [dict(row) for row in by_week],
        "daily_avg": daily_avg,
        "needed_daily": needed_daily,
        "total_hours": total_hours
    }

