#!/usr/bin/env python3
"""
Structure service for Curriculum Tracker.
Handles CRUD operations and reordering for phases, weeks, and days.
"""

from database import get_db, get_db_cursor


def get_structure(user_id, include_resources=False):
    """Get full nested structure: phases -> weeks -> days.
    
    OPTIMIZED: Uses JOINs to fetch entire structure in 1-2 queries instead of 100+.
    If include_resources=True, also includes resources for each day.
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Single query to get all structure data (phases, weeks, days) with JOINs
    query = """
        SELECT 
            p.id as phase_id, 
            p.title as phase_title, 
            p.order_index as phase_order,
            p.color as phase_color, 
            COALESCE(p.metrics, ARRAY[]::TEXT[]) as phase_metrics,
            w.id as week_id, 
            w.title as week_title, 
            w.order_index as week_order,
            d.id as day_id, 
            d.title as day_title, 
            d.order_index as day_order
        FROM phases p
        LEFT JOIN weeks w ON p.id = w.phase_id AND w.user_id = %s
        LEFT JOIN days d ON w.id = d.week_id AND d.user_id = %s
        WHERE p.user_id = %s
        ORDER BY p.order_index, w.order_index NULLS LAST, d.order_index NULLS LAST
    """
    cur.execute(query, (user_id, user_id, user_id))
    rows = cur.fetchall()
    
    # Build nested structure from flat data
    phases_dict = {}
    weeks_dict = {}
    days_dict = {}
    
    for row in rows:
        phase_id = row['phase_id']
        week_id = row['week_id']
        day_id = row['day_id']
        
        # Build phase (only once per phase)
        if phase_id not in phases_dict:
            phases_dict[phase_id] = {
                'id': phase_id,
                'title': row['phase_title'],
                'order_index': row['phase_order'],
                'color': row['phase_color'],
                'metrics': row['phase_metrics'] or [],
                'weeks': []
            }
        
        # Build week (only if week exists and not already added)
        if week_id and week_id not in weeks_dict:
            weeks_dict[week_id] = {
                'id': week_id,
                'title': row['week_title'],
                'order_index': row['week_order'],
                'days': []
            }
            phases_dict[phase_id]['weeks'].append(weeks_dict[week_id])
        
        # Build day (only if day exists and not already added)
        if day_id and day_id not in days_dict:
            days_dict[day_id] = {
                'id': day_id,
                'title': row['day_title'],
                'order_index': row['day_order'],
                'resources': []
            }
            if week_id:
                weeks_dict[week_id]['days'].append(days_dict[day_id])
    
    # If resources are needed, fetch all in a single query
    if include_resources and days_dict:
        day_ids = list(days_dict.keys())
        placeholders = ','.join(['%s'] * len(day_ids))
        cur.execute(f"""
            SELECT id, title, url, resource_type, status, difficulty, 
                   estimated_minutes, scheduled_date, is_completed, day_id, sort_order
            FROM resources
            WHERE user_id = %s AND day_id IN ({placeholders})
            ORDER BY day_id, sort_order, created_at
        """, [user_id] + day_ids)
        
        resources = cur.fetchall()
        
        # Group resources by day_id
        for resource in resources:
            day_id = resource['day_id']
            if day_id in days_dict:
                resource_dict = {
                    'id': resource['id'],
                    'title': resource['title'],
                    'url': resource.get('url'),
                    'resource_type': resource.get('resource_type'),
                    'status': resource.get('status'),
                    'difficulty': resource.get('difficulty'),
                    'estimated_minutes': resource.get('estimated_minutes'),
                    'scheduled_date': resource.get('scheduled_date'),
                    'is_completed': resource.get('is_completed', False)
                }
                days_dict[day_id]['resources'].append(resource_dict)
    
    cur.close()
    
    # Convert to list and sort by order_index
    result = sorted(phases_dict.values(), key=lambda x: x['order_index'])
    
    # Sort weeks and days within each phase
    for phase in result:
        phase['weeks'] = sorted(phase['weeks'], key=lambda x: x['order_index'])
        for week in phase['weeks']:
            week['days'] = sorted(week['days'], key=lambda x: x['order_index'])
    
    return {'phases': result}


def get_structure_for_dashboard(user_id):
    """Get curriculum structure in dashboard-compatible format.
    
    Converts DB structure to YAML-like format expected by dashboard template:
    {phases: [{name, weeks (int), hours, metrics, index, id}]}
    
    Hours are calculated from time_logs aggregation using phase_index (order_index).
    """
    from services.progress import get_hours_for_phase
    
    structure = get_structure(user_id, include_resources=False)
    
    curriculum_phases = []
    for phase in structure['phases']:
        phase_order = phase['order_index']
        weeks_count = len(phase['weeks'])
        
        # Calculate hours from time_logs using phase_index (order_index)
        # This maintains compatibility with existing get_hours_for_phase function
        hours_logged = get_hours_for_phase(phase_order, None, user_id)
        
        # Default hours calculation: 24 hours per week (same as YAML structure)
        default_hours = weeks_count * 24
        
        # Use logged hours if available, otherwise use default
        phase_hours = int(hours_logged) if hours_logged > 0 else default_hours
        
        curriculum_phases.append({
            'name': phase['title'],
            'weeks': weeks_count,
            'hours': phase_hours,
            'metrics': phase.get('metrics', []) or [],
            'index': phase_order,
            'id': phase['id'],
            'color': phase.get('color', '#6366f1'),
            'weeks_list': phase['weeks']  # Keep for reference if needed
        })
    
    return {'phases': curriculum_phases}


def get_phases(user_id):
    """Get all phases for a user ordered by order_index."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT id, title, order_index, color, created_at
        FROM phases
        WHERE user_id = %s
        ORDER BY order_index
    """, (user_id,))
    phases = cur.fetchall()
    cur.close()
    return [dict(p) for p in phases]


def get_weeks(phase_id, user_id):
    """Get all weeks for a phase ordered by order_index."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT id, phase_id, title, order_index, created_at
        FROM weeks
        WHERE user_id = %s AND phase_id = %s
        ORDER BY order_index
    """, (user_id, phase_id))
    weeks = cur.fetchall()
    cur.close()
    return [dict(w) for w in weeks]


def get_days(week_id, user_id):
    """Get all days for a week ordered by order_index."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT id, week_id, title, order_index, created_at
        FROM days
        WHERE user_id = %s AND week_id = %s
        ORDER BY order_index
    """, (user_id, week_id))
    days = cur.fetchall()
    cur.close()
    return [dict(d) for d in days]


def create_phase(user_id, title, color=None):
    """Create a new phase. Auto-calculates order_index."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Get max order_index
    cur.execute("""
        SELECT COALESCE(MAX(order_index), -1) as max_order
        FROM phases
        WHERE user_id = %s
    """, (user_id,))
    max_order = cur.fetchone()['max_order']
    new_order = max_order + 1
    
    # Default color
    if color is None:
        color = '#6366f1'
    
    cur.execute("""
        INSERT INTO phases (user_id, title, order_index, color)
        VALUES (%s, %s, %s, %s)
        RETURNING id, title, order_index, color
    """, (user_id, title, new_order, color))
    
    result = cur.fetchone()
    cur.close()
    conn.commit()
    return dict(result)


def create_week(user_id, phase_id, title):
    """Create a new week. Auto-calculates order_index."""
    # Verify phase belongs to user
    conn = get_db()
    cur = get_db_cursor(conn)
    
    cur.execute("SELECT id FROM phases WHERE id = %s AND user_id = %s", (phase_id, user_id))
    if not cur.fetchone():
        cur.close()
        raise ValueError("Phase not found or access denied")
    
    # Get max order_index for this phase
    cur.execute("""
        SELECT COALESCE(MAX(order_index), -1) as max_order
        FROM weeks
        WHERE user_id = %s AND phase_id = %s
    """, (user_id, phase_id))
    max_order = cur.fetchone()['max_order']
    new_order = max_order + 1
    
    cur.execute("""
        INSERT INTO weeks (user_id, phase_id, title, order_index)
        VALUES (%s, %s, %s, %s)
        RETURNING id, phase_id, title, order_index
    """, (user_id, phase_id, title, new_order))
    
    result = cur.fetchone()
    cur.close()
    conn.commit()
    return dict(result)


def create_day(user_id, week_id, title):
    """Create a new day. Auto-calculates order_index."""
    # Verify week belongs to user
    conn = get_db()
    cur = get_db_cursor(conn)
    
    cur.execute("SELECT id FROM weeks WHERE id = %s AND user_id = %s", (week_id, user_id))
    if not cur.fetchone():
        cur.close()
        raise ValueError("Week not found or access denied")
    
    # Get max order_index for this week
    cur.execute("""
        SELECT COALESCE(MAX(order_index), -1) as max_order
        FROM days
        WHERE user_id = %s AND week_id = %s
    """, (user_id, week_id))
    max_order = cur.fetchone()['max_order']
    new_order = max_order + 1
    
    cur.execute("""
        INSERT INTO days (user_id, week_id, title, order_index)
        VALUES (%s, %s, %s, %s)
        RETURNING id, week_id, title, order_index
    """, (user_id, week_id, title, new_order))
    
    result = cur.fetchone()
    cur.close()
    conn.commit()
    return dict(result)


def update_structure_title(model, item_id, user_id, title, color=None):
    """Update title (and optionally color) for phase/week/day."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    table_map = {
        'phase': 'phases',
        'week': 'weeks',
        'day': 'days'
    }
    
    if model not in table_map:
        cur.close()
        raise ValueError(f"Invalid model: {model}")
    
    table = table_map[model]
    
    # Verify ownership
    cur.execute(f"SELECT id FROM {table} WHERE id = %s AND user_id = %s", (item_id, user_id))
    if not cur.fetchone():
        cur.close()
        raise ValueError(f"{model.capitalize()} not found or access denied")
    
    # Update
    if model == 'phase' and color is not None:
        cur.execute(f"""
            UPDATE {table}
            SET title = %s, color = %s
            WHERE id = %s AND user_id = %s
            RETURNING id, title, order_index, color
        """, (title, color, item_id, user_id))
    else:
        cur.execute(f"""
            UPDATE {table}
            SET title = %s
            WHERE id = %s AND user_id = %s
            RETURNING id, title, order_index
        """, (title, item_id, user_id))
    
    result = cur.fetchone()
    cur.close()
    conn.commit()
    return dict(result)


def delete_structure_item(model, item_id, user_id):
    """Delete phase/week/day. Cascade handled by FK constraints."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    table_map = {
        'phase': 'phases',
        'week': 'weeks',
        'day': 'days'
    }
    
    if model not in table_map:
        cur.close()
        raise ValueError(f"Invalid model: {model}")
    
    table = table_map[model]
    
    # Verify ownership
    cur.execute(f"SELECT id FROM {table} WHERE id = %s AND user_id = %s", (item_id, user_id))
    if not cur.fetchone():
        cur.close()
        raise ValueError(f"{model.capitalize()} not found or access denied")
    
    # Delete (cascade handled by FK)
    cur.execute(f"DELETE FROM {table} WHERE id = %s AND user_id = %s", (item_id, user_id))
    cur.close()
    conn.commit()
    return True


def get_or_create_inbox(user_id):
    """Get or create the inbox structure: 'Migrated Items' Phase -> 'Unsorted' Week -> 'Inbox' Day."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    try:
        # Try to find existing inbox phase
        cur.execute("""
            SELECT id FROM phases
            WHERE user_id = %s AND title = 'Migrated Items'
            ORDER BY id
            LIMIT 1
        """, (user_id,))
        phase_row = cur.fetchone()
        
        if phase_row:
            phase_id = phase_row['id']
        else:
            # Create phase
            cur.execute("""
                INSERT INTO phases (user_id, title, order_index, color)
                VALUES (%s, 'Migrated Items', 99999, '#9ca3af')
                RETURNING id
            """, (user_id,))
            phase_id = cur.fetchone()['id']
        
        # Try to find existing unsorted week
        cur.execute("""
            SELECT id FROM weeks
            WHERE user_id = %s AND phase_id = %s AND title = 'Unsorted'
            LIMIT 1
        """, (user_id, phase_id))
        week_row = cur.fetchone()
        
        if week_row:
            week_id = week_row['id']
        else:
            # Create week
            cur.execute("""
                INSERT INTO weeks (user_id, phase_id, title, order_index)
                VALUES (%s, %s, 'Unsorted', 1)
                RETURNING id
            """, (user_id, phase_id))
            week_id = cur.fetchone()['id']
        
        # Try to find existing inbox day
        cur.execute("""
            SELECT id FROM days
            WHERE user_id = %s AND week_id = %s AND title = 'Inbox'
            LIMIT 1
        """, (user_id, week_id))
        day_row = cur.fetchone()
        
        if day_row:
            day_id = day_row['id']
        else:
            # Create day
            cur.execute("""
                INSERT INTO days (user_id, week_id, title, order_index)
                VALUES (%s, %s, 'Inbox', 1)
                RETURNING id
            """, (user_id, week_id))
            day_id = cur.fetchone()['id']
        
        conn.commit()
        return day_id
        
    finally:
        cur.close()


def reorder_structure(model, item_id, new_parent_id, new_index, user_id):
    """Reorder structure item (week or day) with atomic operations and proper locking.
    
    CRITICAL: Uses SERIALIZABLE isolation level and SELECT FOR UPDATE to prevent race conditions.
    Prevents duplicate order_index values when concurrent requests modify the same parent.
    
    Algorithm:
    1. Lock item and fetch current state
    2. Lock all siblings in both old and new parent
    3. Pull item out (set order_index to temporary negative value)
    4. Shift neighbors atomically
    5. Insert item at new_index
    6. Close gap in old location
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    try:
        # Start transaction with SERIALIZABLE isolation level to prevent race conditions
        conn.autocommit = False
        cur.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        
        table_map = {
            'week': ('weeks', 'phase_id'),
            'day': ('days', 'week_id')
        }
        
        if model not in table_map:
            raise ValueError(f"Invalid model for reordering: {model}. Must be 'week' or 'day'")
        
        table, parent_column = table_map[model]
        
        # Step 1: Fetch item being moved WITH LOCK
        cur.execute(f"""
            SELECT id, {parent_column} as old_parent_id, order_index as old_order_index
            FROM {table}
            WHERE id = %s AND user_id = %s
            FOR UPDATE
        """, (item_id, user_id))
        
        item = cur.fetchone()
        if not item:
            conn.rollback()
            conn.autocommit = True
            raise ValueError(f"{model.capitalize()} not found or access denied")
        
        old_parent_id = item['old_parent_id']
        old_order_index = item['old_order_index']
        
        # If moving within same parent to same position, no-op
        if old_parent_id == new_parent_id and old_order_index == new_index:
            conn.rollback()
            conn.autocommit = True
            return True
        
        # Verify new parent belongs to user
        parent_table_map = {
            'week': 'phases',
            'day': 'weeks'
        }
        parent_table = parent_table_map[model]
        
        cur.execute(f"""
            SELECT id FROM {parent_table}
            WHERE id = %s AND user_id = %s
        """, (new_parent_id, user_id))
        
        if not cur.fetchone():
            conn.rollback()
            conn.autocommit = True
            raise ValueError(f"New parent {model} not found or access denied")
        
        # Step 2: Lock all siblings in both old and new parent to prevent concurrent modifications
        # Lock old parent siblings
        cur.execute(f"""
            SELECT id FROM {table}
            WHERE user_id = %s AND {parent_column} = %s AND id != %s
            FOR UPDATE
        """, (user_id, old_parent_id, item_id))
        cur.fetchall()  # Execute lock
        
        # Lock new parent siblings (if different parent)
        if old_parent_id != new_parent_id:
            cur.execute(f"""
                SELECT id FROM {table}
                WHERE user_id = %s AND {parent_column} = %s
                FOR UPDATE
            """, (user_id, new_parent_id))
            cur.fetchall()  # Execute lock
        
        # Step 3: Pull item out (set to temporary negative value to avoid constraint violation)
        cur.execute(f"""
            UPDATE {table}
            SET order_index = -9999
            WHERE id = %s AND user_id = %s
        """, (item_id, user_id))
        
        # Step 4 & 6: Handle shifting based on move direction
        if old_parent_id != new_parent_id:
            # Moving to different parent
            # Step 4: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s AND order_index >= %s
            """, (user_id, new_parent_id, new_index))
        elif new_index < old_order_index:
            # Moving earlier in same parent
            # Step 4: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s 
                AND order_index >= %s AND order_index < %s
            """, (user_id, new_parent_id, new_index, old_order_index))
        elif new_index > old_order_index:
            # Moving later in same parent
            # Step 6 first: Close gap in OLD location (items shift left)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index - 1
                WHERE user_id = %s AND {parent_column} = %s 
                AND order_index > %s AND order_index <= %s
            """, (user_id, old_parent_id, old_order_index, new_index))
            # Step 4: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s AND order_index > %s
            """, (user_id, new_parent_id, new_index))
        
        # Step 5: Insert item at new_index
        cur.execute(f"""
            UPDATE {table}
            SET {parent_column} = %s, order_index = %s
            WHERE id = %s AND user_id = %s
        """, (new_parent_id, new_index, item_id, user_id))
        
        # Step 6: Shift neighbors in OLD location (close gap) - only for different parent
        if old_parent_id != new_parent_id:
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index - 1
                WHERE user_id = %s AND {parent_column} = %s AND order_index > %s
            """, (user_id, old_parent_id, old_order_index))
        
        # Commit transaction
        conn.commit()
        return True
        
    except Exception as e:
        # Rollback on error (including serialization failures)
        conn.rollback()
        raise e
    finally:
        conn.autocommit = True
        cur.close()

