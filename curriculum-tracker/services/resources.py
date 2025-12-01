#!/usr/bin/env python3
"""
Resource service for Curriculum Tracker.
Handles resource CRUD operations, tagging, and status management.
"""

from flask_login import current_user
from database import get_db, get_db_cursor


def get_resources(phase_index=None, user_id=None):
    """Get resources with tags in a single query (fixes N+1 problem)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    if phase_index is not None:
        query = """
            SELECT r.*, 
                   STRING_AGG(t.name, '|||') as tag_names,
                   STRING_AGG(t.color, '|||') as tag_colors
            FROM resources r
            LEFT JOIN resource_tags rt ON r.id = rt.resource_id
            LEFT JOIN tags t ON rt.tag_id = t.id
            WHERE r.user_id = %s AND (r.phase_index = %s OR r.phase_index IS NULL)
            GROUP BY r.id
            ORDER BY r.week, r.day, r.is_favorite DESC, r.created_at DESC
        """
        cur.execute(query, (user_id, phase_index))
    else:
        query = """
            SELECT r.*,
                   STRING_AGG(t.name, '|||') as tag_names,
                   STRING_AGG(t.color, '|||') as tag_colors
            FROM resources r
            LEFT JOIN resource_tags rt ON r.id = rt.resource_id
            LEFT JOIN tags t ON rt.tag_id = t.id
            WHERE r.user_id = %s
            GROUP BY r.id
            ORDER BY r.phase_index, r.week, r.day, r.is_favorite DESC, r.created_at DESC
        """
        cur.execute(query, (user_id,))
    
    rows = cur.fetchall()
    cur.close()

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
    """Get all resources."""
    return get_resources()


def get_all_tags():
    """Get all tags."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM tags ORDER BY name")
    results = cur.fetchall()
    cur.close()
    return results


def get_resources_by_week(phase_index, week, user_id=None):
    """Get resources for a specific week with tags in single query (fixes N+1)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    query = """
        SELECT r.*,
               STRING_AGG(t.name, '|||') as tag_names,
               STRING_AGG(t.color, '|||') as tag_colors
        FROM resources r
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE r.user_id = %s AND r.phase_index = %s AND r.week = %s
        GROUP BY r.id
        ORDER BY r.day, r.sort_order, r.is_favorite DESC, r.created_at DESC
    """
    cur.execute(query, (user_id, phase_index, week))
    rows = cur.fetchall()
    cur.close()
    
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


def get_day_completion(phase_index, week, day, user_id=None):
    """Get completion stats for a specific day. Returns (completed, total)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as completed FROM resources WHERE user_id = %s AND phase_index = %s AND week = %s AND day = %s",
        (user_id, phase_index, week, day)
    )
    row = cur.fetchone()
    cur.close()
    total = row["total"] or 0
    completed = row["completed"] or 0
    return (completed, total)


def get_week_completion(phase_index, week, user_id=None):
    """Get completion stats for a specific week. Returns (completed, total, percent)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as completed FROM resources WHERE user_id = %s AND phase_index = %s AND week = %s",
        (user_id, phase_index, week)
    )
    row = cur.fetchone()
    cur.close()
    total = row["total"] or 0
    completed = row["completed"] or 0
    percent = (completed / total * 100) if total > 0 else 0
    return (completed, total, percent)


def get_phase_completion(phase_index, user_id=None):
    """Get completion stats for a specific phase. Returns (completed, total, percent)."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as completed FROM resources WHERE user_id = %s AND phase_index = %s",
        (user_id, phase_index)
    )
    row = cur.fetchone()
    cur.close()
    total = row["total"] or 0
    completed = row["completed"] or 0
    percent = (completed / total * 100) if total > 0 else 0
    return (completed, total, percent)


def get_continue_resource(current_phase, current_week, user_id=None):
    """Get the resource to continue working on."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # First check for in_progress
    cur.execute(
        "SELECT * FROM resources WHERE user_id = %s AND status = 'in_progress' AND phase_index IS NOT NULL AND week IS NOT NULL AND day IS NOT NULL ORDER BY phase_index, week, day LIMIT 1",
        (user_id,)
    )
    in_progress = cur.fetchone()
    
    if in_progress:
        resource = dict(in_progress)
        # Verify all required fields are present
        if resource.get('phase_index') is not None and resource.get('week') is not None and resource.get('id') is not None:
            cur.close()
            return resource
    
    # If none, get first incomplete in current position
    cur.execute(
        "SELECT * FROM resources WHERE user_id = %s AND status = 'not_started' AND phase_index = %s AND week = %s AND day IS NOT NULL ORDER BY day, sort_order LIMIT 1",
        (user_id, current_phase, current_week)
    )
    incomplete = cur.fetchone()
    cur.close()
    
    if incomplete:
        resource = dict(incomplete)
        # Verify all required fields are present
        if resource.get('phase_index') is not None and resource.get('week') is not None and resource.get('id') is not None:
            return resource
    
    return None


def get_hours_for_resource(resource_id, user_id=None):
    """Get total hours logged for a specific resource."""
    if user_id is None:
        user_id = current_user.id
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE user_id = %s AND resource_id = %s",
        (user_id, resource_id)
    )
    result = cur.fetchone()
    cur.close()
    return result["total"] if result else 0

