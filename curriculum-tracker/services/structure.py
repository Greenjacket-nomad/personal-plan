#!/usr/bin/env python3
"""
Structure service for Curriculum Tracker.
Handles CRUD operations and reordering for phases, weeks, and days.
"""

from database import get_db, get_db_cursor


def get_structure(user_id, include_resources=False):
    """Get full nested structure: phases -> weeks -> days.
    
    If include_resources=True, also includes resources for each day.
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Get all phases
    cur.execute("""
        SELECT id, title, order_index, color
        FROM phases
        WHERE user_id = %s
        ORDER BY order_index
    """, (user_id,))
    phases = cur.fetchall()
    
    result = []
    for phase in phases:
        phase_id = phase['id']
        
        # Get weeks for this phase
        cur.execute("""
            SELECT id, title, order_index
            FROM weeks
            WHERE user_id = %s AND phase_id = %s
            ORDER BY order_index
        """, (user_id, phase_id))
        weeks = cur.fetchall()
        
        weeks_list = []
        for week in weeks:
            week_id = week['id']
            
            # Get days for this week
            cur.execute("""
                SELECT id, title, order_index
                FROM days
                WHERE user_id = %s AND week_id = %s
                ORDER BY order_index
            """, (user_id, week_id))
            days = cur.fetchall()
            
            days_list = []
            for day in days:
                day_id = day['id']
                day_data = {
                    'id': day['id'],
                    'title': day['title'],
                    'order_index': day['order_index'],
                    'resources': []
                }
                
                # Get resources for this day if requested
                if include_resources:
                    cur.execute("""
                        SELECT id, title, url, resource_type, status, difficulty, 
                               estimated_minutes, scheduled_date, is_completed
                        FROM resources
                        WHERE user_id = %s AND day_id = %s
                        ORDER BY sort_order, created_at
                    """, (user_id, day_id))
                    resources = cur.fetchall()
                    day_data['resources'] = [dict(r) for r in resources]
                
                days_list.append(day_data)
            
            weeks_list.append({
                'id': week['id'],
                'title': week['title'],
                'order_index': week['order_index'],
                'days': days_list
            })
        
        result.append({
            'id': phase['id'],
            'title': phase['title'],
            'order_index': phase['order_index'],
            'color': phase['color'],
            'weeks': weeks_list
        })
    
    cur.close()
    return {'phases': result}


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
    """Reorder structure item (week or day) with transaction-based constraint handling.
    
    CRITICAL: Uses transaction to handle UniqueConstraint on (user_id, order_index).
    
    Algorithm:
    1. Fetch item being moved
    2. Pull item out (set order_index to -9999)
    3. Shift neighbors in NEW location
    4. Insert item at new_index
    5. Shift neighbors in OLD location (close gap)
    """
    conn = get_db()
    cur = get_db_cursor(conn)
    
    try:
        # Start transaction
        conn.autocommit = False
        
        table_map = {
            'week': ('weeks', 'phase_id'),
            'day': ('days', 'week_id')
        }
        
        if model not in table_map:
            raise ValueError(f"Invalid model for reordering: {model}. Must be 'week' or 'day'")
        
        table, parent_column = table_map[model]
        
        # Step 1: Fetch item being moved
        cur.execute(f"""
            SELECT id, {parent_column} as old_parent_id, order_index as old_order_index
            FROM {table}
            WHERE id = %s AND user_id = %s
        """, (item_id, user_id))
        
        item = cur.fetchone()
        if not item:
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
            raise ValueError(f"New parent {model} not found or access denied")
        
        # Step 2: Pull item out (set to temporary negative value)
        cur.execute(f"""
            UPDATE {table}
            SET order_index = -9999
            WHERE id = %s AND user_id = %s
        """, (item_id, user_id))
        
        # Step 3 & 5: Handle shifting based on move direction
        if old_parent_id != new_parent_id:
            # Moving to different parent
            # Step 3: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s AND order_index >= %s
            """, (user_id, new_parent_id, new_index))
        elif new_index < old_order_index:
            # Moving earlier in same parent
            # Step 3: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s 
                AND order_index >= %s AND order_index < %s
            """, (user_id, new_parent_id, new_index, old_order_index))
        elif new_index > old_order_index:
            # Moving later in same parent
            # Step 5 first: Close gap in OLD location (items shift left)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index - 1
                WHERE user_id = %s AND {parent_column} = %s 
                AND order_index > %s AND order_index <= %s
            """, (user_id, old_parent_id, old_order_index, new_index))
            # Step 3: Shift neighbors in NEW location (make room)
            cur.execute(f"""
                UPDATE {table}
                SET order_index = order_index + 1
                WHERE user_id = %s AND {parent_column} = %s AND order_index > %s
            """, (user_id, new_parent_id, new_index))
        
        # Step 4: Insert item at new_index
        cur.execute(f"""
            UPDATE {table}
            SET {parent_column} = %s, order_index = %s
            WHERE id = %s AND user_id = %s
        """, (new_parent_id, new_index, item_id, user_id))
        
        # Step 5: Shift neighbors in OLD location (close gap) - only for different parent or earlier move
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
        # Rollback on error
        conn.rollback()
        raise e
    finally:
        conn.autocommit = True
        cur.close()

