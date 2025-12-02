#!/usr/bin/env python3
"""
Resource service for Curriculum Tracker.
Handles resource CRUD operations, tagging, and status management.
"""

from flask_login import current_user
from database import get_db, get_db_cursor
from services.structure import get_or_create_inbox


def validate_resource_fks(user_id):
    """Validate all resources have valid day_id FK, move orphans to Inbox.
    
    This function checks for resources with NULL or invalid day_id and automatically
    moves them to the Inbox to prevent "zombie data" from stale FK references.
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    try:
        # Find resources with NULL day_id or invalid FK
        cur.execute("""
            SELECT r.id
            FROM resources r
            WHERE r.user_id = %s 
            AND (r.day_id IS NULL OR NOT EXISTS (
                SELECT 1 FROM days d 
                WHERE d.id = r.day_id AND d.user_id = %s
            ))
        """, (user_id, user_id))
        
        orphaned_resources = cur.fetchall()
        
        if not orphaned_resources:
            cur.close()
            return 0
        
        # Get or create Inbox day_id
        inbox_day_id = get_or_create_inbox(user_id)
        
        # Move orphaned resources to Inbox
        orphaned_ids = [r['id'] for r in orphaned_resources]
        placeholders = ','.join(['%s'] * len(orphaned_ids))
        
        cur.execute(f"""
            UPDATE resources
            SET day_id = %s
            WHERE id IN ({placeholders}) AND user_id = %s
        """, [inbox_day_id] + orphaned_ids + [user_id])
        
        conn.commit()
        cur.close()
        return len(orphaned_ids)
        
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e


def get_resources(phase_index=None, user_id=None):
    """Get resources with tags, strictly enforcing FK relationships.
    
    NO HYBRID FALLBACK: Resources must have valid day_id FK or be in Inbox.
    Legacy phase_index/week/day columns are ignored for structure queries.
    """
    if user_id is None:
        user_id = current_user.id
    
    # Validate and fix orphaned resources before querying
    validate_resource_fks(user_id)
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Build query that ONLY uses day_id FK, no fallback to legacy columns
    base_query = """
        SELECT r.*,
               STRING_AGG(DISTINCT t.name, '|||') FILTER (WHERE t.name IS NOT NULL) as tag_names,
               STRING_AGG(DISTINCT t.color, '|||') FILTER (WHERE t.color IS NOT NULL) as tag_colors,
               p.title as phase_title,
               w.title as week_title,
               d.title as day_title
        FROM resources r
        INNER JOIN days d ON r.day_id = d.id AND d.user_id = r.user_id
        INNER JOIN weeks w ON d.week_id = w.id AND w.user_id = r.user_id
        INNER JOIN phases p ON w.phase_id = p.id AND p.user_id = r.user_id
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE r.user_id = %s
    """
    
    params = [user_id]
    
    if phase_index is not None:
        base_query += " AND p.order_index = %s"
        params.append(phase_index)
    
    base_query += """
        GROUP BY r.id, d.id, w.id, p.id, d.order_index, w.order_index, p.order_index
        ORDER BY p.order_index, w.order_index, d.order_index,
                 r.is_favorite DESC, r.created_at DESC
    """
    
    cur.execute(base_query, params)
    rows = cur.fetchall()
    cur.close()

    resources = []
    for r in rows:
        item = dict(r)
        # Parse concatenated tags
        if r.get("tag_names"):
            item["tags"] = r["tag_names"].split("|||")
            if r.get("tag_colors"):
                item["tag_colors"] = r["tag_colors"].split("|||")
            else:
                item["tag_colors"] = []
        else:
            item["tags"] = []
            item["tag_colors"] = []
        resources.append(item)
    return resources


def get_all_resources():
    """Get all resources."""
    return get_resources()


def get_resources_filtered(user_id, search_query=None, resource_type=None, 
                          phase_index=None, tag=None, status=None):
    """Get resources with database-side filtering, strictly enforcing FK relationships.
    
    All filtering is done in SQL, not Python, for optimal performance.
    Resources must have valid day_id FK - orphaned resources are automatically moved to Inbox.
    """
    # Validate and fix orphaned resources before querying
    validate_resource_fks(user_id)
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Build query with WHERE clauses - enforce FK relationships
    conditions = ["r.user_id = %s", "r.day_id IS NOT NULL"]
    params = [user_id]
    
    # Search filter (title, notes, topic)
    if search_query:
        search_pattern = f"%{search_query.lower()}%"
        conditions.append("(LOWER(r.title) LIKE %s OR LOWER(COALESCE(r.notes, '')) LIKE %s OR LOWER(COALESCE(r.topic, '')) LIKE %s)")
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # Type filter
    if resource_type:
        conditions.append("r.resource_type = %s")
        params.append(resource_type)
    
    # Phase filter - use FK structure only (p.order_index)
    if phase_index is not None:
        try:
            phase_idx = int(phase_index)
            conditions.append("EXISTS (SELECT 1 FROM days d JOIN weeks w ON d.week_id = w.id JOIN phases p ON w.phase_id = p.id WHERE d.id = r.day_id AND p.user_id = %s AND p.order_index = %s)")
            params.extend([user_id, phase_idx])
        except ValueError:
            pass
    
    # Status filter
    if status == "completed":
        conditions.append("r.is_completed = TRUE")
    elif status == "pending":
        conditions.append("r.is_completed = FALSE")
    elif status == "favorites":
        conditions.append("r.is_favorite = TRUE")
    
    # Build query with FK enforcement - INNER JOIN ensures valid day_id
    query = """
        SELECT DISTINCT r.*,
               STRING_AGG(DISTINCT t.name, '|||') FILTER (WHERE t.name IS NOT NULL) as tag_names,
               STRING_AGG(DISTINCT t.color, '|||') FILTER (WHERE t.color IS NOT NULL) as tag_colors
        FROM resources r
        INNER JOIN days d ON r.day_id = d.id AND d.user_id = r.user_id
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE """ + " AND ".join(conditions)
    
    # Tag filter - add to conditions
    if tag:
        query += " AND EXISTS (SELECT 1 FROM resource_tags rt2 JOIN tags t2 ON rt2.tag_id = t2.id WHERE rt2.resource_id = r.id AND t2.name = %s)"
        params.append(tag)
    
    query += """
        GROUP BY r.id
        ORDER BY r.created_at DESC
    """
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    
    # Process results and parse tags
    resources = []
    for r in rows:
        item = dict(r)
        # Parse concatenated tags
        if r.get("tag_names"):
            item["tags"] = r["tag_names"].split("|||")
            if r.get("tag_colors"):
                item["tag_colors"] = r["tag_colors"].split("|||")
            else:
                item["tag_colors"] = []
        else:
            item["tags"] = []
            item["tag_colors"] = []
        resources.append(item)
    
    return resources


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


def upsert_resource_from_curriculum(resource_data, user_id, day_id=None):
    """Safely upsert resource from curriculum import, preserving user modifications.
    
    This function should be used when importing/updating resources from curriculum
    (e.g., from CSV or YAML). It respects user_modified flag and only updates
    structural fields if the user has modified the resource.
    
    Args:
        resource_data: Dictionary with resource fields (title, topic, url, resource_type, notes, etc.)
        user_id: User ID who owns the resource
        day_id: Optional day_id for the resource. If None, will try to derive from phase/week/day.
    
    Returns:
        Tuple of (resource_id, was_created) where was_created is True if resource was newly created.
    
    Preserved fields (if user_modified=True):
        - notes
        - status
        - url
        - is_completed
        - is_favorite
    
    Always updated fields (structural):
        - phase_index, week, day (legacy)
        - day_id (FK)
        - title
        - topic
        - resource_type
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    try:
        title = resource_data.get('title', '').strip()
        if not title:
            cur.close()
            raise ValueError("Resource title is required")
        
        # Check if resource already exists (by title and user)
        # Note: This assumes resources are uniquely identified by title within a user's scope
        # If your system uses a different identifier (like external_id), adjust this query
        cur.execute("""
            SELECT id, user_modified, notes, status, url, is_completed, is_favorite, day_id
            FROM resources
            WHERE user_id = %s AND title = %s
            LIMIT 1
        """, (user_id, title))
        
        existing = cur.fetchone()
        
        if existing and existing.get('user_modified'):
            # Resource exists and user has modified it - preserve user-editable fields
            resource_id = existing['id']
            
            # Only update structural fields
            update_fields = []
            update_params = []
            
            if day_id is not None:
                update_fields.append("day_id = %s")
                update_params.append(day_id)
            
            # Update legacy columns if provided
            if 'phase_index' in resource_data and resource_data['phase_index'] is not None:
                update_fields.append("phase_index = %s")
                update_params.append(resource_data['phase_index'])
            
            if 'week' in resource_data and resource_data['week'] is not None:
                update_fields.append("week = %s")
                update_params.append(resource_data['week'])
            
            if 'day' in resource_data and resource_data['day'] is not None:
                update_fields.append("day = %s")
                update_params.append(resource_data['day'])
            
            if 'topic' in resource_data:
                update_fields.append("topic = %s")
                update_params.append(resource_data.get('topic'))
            
            if 'resource_type' in resource_data:
                update_fields.append("resource_type = %s")
                update_params.append(resource_data.get('resource_type', 'link'))
            
            # Always update title (may have changed in curriculum)
            update_fields.append("title = %s")
            update_params.append(title)
            
            # Update source to indicate it came from curriculum
            update_fields.append("source = %s")
            update_params.append('curriculum')
            
            # Preserve user-modified fields (do NOT update)
            # notes, status, url, is_completed, is_favorite are preserved
            
            if update_fields:
                update_params.extend([resource_id, user_id])
                cur.execute(f"""
                    UPDATE resources
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                """, update_params)
            
            conn.commit()
            cur.close()
            return (resource_id, False)  # Updated existing resource
        
        elif existing:
            # Resource exists but user hasn't modified it - update all fields
            resource_id = existing['id']
            
            cur.execute("""
                UPDATE resources
                SET day_id = COALESCE(%s, day_id),
                    phase_index = %s,
                    week = %s,
                    day = %s,
                    title = %s,
                    topic = %s,
                    url = %s,
                    resource_type = %s,
                    notes = %s,
                    source = %s,
                    user_modified = FALSE
                WHERE id = %s AND user_id = %s
            """, (
                day_id,
                resource_data.get('phase_index'),
                resource_data.get('week'),
                resource_data.get('day'),
                title,
                resource_data.get('topic'),
                resource_data.get('url'),
                resource_data.get('resource_type', 'link'),
                resource_data.get('notes'),
                'curriculum',
                resource_id,
                user_id
            ))
            
            conn.commit()
            cur.close()
            return (resource_id, False)  # Updated existing resource
        
        else:
            # New resource - insert with source='curriculum'
            # Ensure day_id is set (use inbox if not provided)
            if day_id is None:
                from services.structure import get_or_create_inbox
                day_id = get_or_create_inbox(user_id)
            
            cur.execute("""
                INSERT INTO resources
                (user_id, day_id, phase_index, week, day, title, topic, url, resource_type, notes, source, user_modified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            """, (
                user_id,
                day_id,
                resource_data.get('phase_index'),
                resource_data.get('week'),
                resource_data.get('day'),
                title,
                resource_data.get('topic'),
                resource_data.get('url'),
                resource_data.get('resource_type', 'link'),
                resource_data.get('notes'),
                'curriculum'
            ))
            
            result = cur.fetchone()
            resource_id = result['id'] if result else None
            
            conn.commit()
            cur.close()
            return (resource_id, True)  # Created new resource
            
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e

