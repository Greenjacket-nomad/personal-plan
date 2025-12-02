#!/usr/bin/env python3
"""
API routes for Curriculum Tracker.
JSON API endpoints and form handling routes.
"""

import psycopg2
import uuid
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from constants import STATUS_CYCLE

# Import from new modular structure
from database import get_db, get_db_cursor
from utils import load_curriculum, allowed_file, UPLOAD_FOLDER, recalculate_schedule_from
from services.progress import (
    get_progress, update_progress, log_activity
)
from services.resources import get_resources_by_week
from services.structure import (
    get_structure, create_phase, create_week, create_day,
    update_structure_title, delete_structure_item,
    get_or_create_inbox, reorder_structure
)

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route("/log", methods=["POST"])
@login_required
def log_hours():
    """Log hours with input validation."""
    try:
        hours_str = request.form.get("hours", "0").strip()
        hours = float(hours_str) if hours_str else 0.0
    except (ValueError, TypeError):
        flash("Oops, invalid hours value", "error")
        return redirect(url_for("main.dashboard"))
    
    log_date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()
    
    # Validate date format
    try:
        datetime.strptime(log_date, "%Y-%m-%d")
    except ValueError:
        flash("Oops, invalid date format", "error")
        return redirect(url_for("main.dashboard"))
    
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
        return redirect(url_for("main.dashboard"))
    
    # Get current phase_index for this log entry
    progress = get_progress()
    current_phase = progress['current_phase']
    
    conn = get_db()
    cur = get_db_cursor(conn)
    # Insert new log entry with week, day, and resource_id if provided
    cur.execute(
        "INSERT INTO time_logs (user_id, date, hours, notes, phase_index, week, day, resource_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (current_user.id, log_date, hours, notes, current_phase, week, day, resource_id)
    )
    cur.close()
    conn.commit()
    
    # Log activity
    details = f"{hours}h on {log_date}"
    if notes:
        details += f": {notes[:50]}"
    log_activity("hours_logged", "time_log", None, details)
    
    flash(f"Locked in {hours} hours!", "success")
    return redirect(url_for("main.dashboard"))


@api_bp.route("/complete-metric", methods=["POST"])
@login_required
def complete_metric():
    """Complete a metric with input validation."""
    try:
        phase_index = int(request.form.get("phase_index", 0))
    except (ValueError, TypeError):
        flash("Invalid phase index.", "error")
        return redirect(url_for("main.dashboard"))
    
    metric_text = request.form.get("metric_text", "").strip()
    if not metric_text:
        flash("Metric text is required.", "error")
        return redirect(url_for("main.dashboard"))
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("INSERT INTO completed_metrics (user_id, phase_index, metric_text, completed_date) VALUES (%s, %s, %s, %s) ON CONFLICT (phase_index, metric_text) DO NOTHING",
        (current_user.id, phase_index, metric_text, datetime.now().strftime("%Y-%m-%d")))
    cur.close()
    conn.commit()
    
    # Log activity
    log_activity("metric_completed", "metric", phase_index, metric_text[:100])
    
    return redirect(url_for("main.dashboard"))


@api_bp.route("/uncomplete-metric", methods=["POST"])
def uncomplete_metric():
    """Uncomplete a metric with input validation."""
    try:
        phase_index = int(request.form.get("phase_index", 0))
    except (ValueError, TypeError):
        flash("Invalid phase index.", "error")
        return redirect(url_for("main.dashboard"))
    
    metric_text = request.form.get("metric_text", "").strip()
    if not metric_text:
        flash("Metric text is required.", "error")
        return redirect(url_for("main.dashboard"))
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM completed_metrics WHERE phase_index = %s AND metric_text = %s", (phase_index, metric_text))
    cur.close()
    conn.commit()
    return redirect(url_for("main.dashboard"))


@api_bp.route("/next-week", methods=["POST"])
def next_week():
    curriculum = load_curriculum()
    progress = get_progress()
    current_phase = progress['current_phase']
    current_week = progress['current_week']
    if current_phase >= len(curriculum["phases"]):
        return redirect(url_for("main.dashboard"))
    phase = curriculum["phases"][current_phase]
    if current_week < phase["weeks"]:
        update_progress(current_week=current_week + 1)
    elif current_phase + 1 < len(curriculum["phases"]):
        update_progress(current_phase=current_phase + 1, current_week=1)
    return redirect(url_for("main.dashboard"))


@api_bp.route("/prev-week", methods=["POST"])
def prev_week():
    curriculum = load_curriculum()
    progress = get_progress()
    current_phase = progress['current_phase']
    current_week = progress['current_week']
    if current_week > 1:
        update_progress(current_week=current_week - 1)
    elif current_phase > 0:
        update_progress(current_phase=current_phase - 1, current_week=curriculum["phases"][current_phase - 1]["weeks"])
    return redirect(url_for("main.dashboard"))


@api_bp.route("/api/navigate-week", methods=["POST"])
def api_navigate_week():
    """Navigate to next/previous week without page reload."""
    data = request.json
    direction = data.get("direction")  # "next" or "prev"
    current_phase = data.get("current_phase")
    current_week = data.get("current_week")
    
    curriculum_data = load_curriculum()
    if current_phase >= len(curriculum_data["phases"]):
        return jsonify({"success": False, "error": "Already at last phase"})
    
    phase = curriculum_data["phases"][current_phase]
    
    if direction == "next":
        if current_week < phase["weeks"]:
            new_week = current_week + 1
            new_phase = current_phase
        elif current_phase + 1 < len(curriculum_data["phases"]):
            new_phase = current_phase + 1
            new_week = 1
        else:
            return jsonify({"success": False, "error": "Already at last week"})
    else:  # prev
        if current_week > 1:
            new_week = current_week - 1
            new_phase = current_phase
        elif current_phase > 0:
            new_phase = current_phase - 1
            new_week = curriculum_data["phases"][new_phase]["weeks"]
        else:
            return jsonify({"success": False, "error": "Already at first week"})
    
    # Update session/database
    update_progress(current_phase=new_phase, current_week=new_week)
    
    return jsonify({
        "success": True,
        "new_phase": new_phase,
        "new_week": new_week
    })


@api_bp.route("/api/week-content")
def api_week_content():
    """Get week content for AJAX loading."""
    phase_index = request.args.get("phase", type=int)
    week = request.args.get("week", type=int)
    
    if phase_index is None or week is None:
        return jsonify({"error": "Phase and week required"}), 400
    
    grouped_week, ungrouped_week = get_resources_by_week(phase_index, week)
    
    return jsonify({
        "grouped": {str(k): [dict(r) for r in v] for k, v in grouped_week.items()},
        "ungrouped": [dict(r) for r in ungrouped_week]
    })


@api_bp.route("/jump-to-phase/<int:phase_index>", methods=["POST"])
def jump_to_phase(phase_index):
    curriculum = load_curriculum()
    if 0 <= phase_index < len(curriculum["phases"]):
        update_progress(current_phase=phase_index, current_week=1)
    return redirect(url_for("main.dashboard"))


@api_bp.route("/add-resource", methods=["POST"])
@login_required
def add_resource():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    resource_type = request.form.get("resource_type", "link")
    notes = request.form.get("notes", "").strip()
    topic = request.form.get("topic", "").strip()
    
    # New: Accept day_id parameter
    day_id_str = request.form.get("day_id", "").strip()
    day_id = int(day_id_str) if day_id_str and day_id_str.isdigit() else None
    
    # Legacy: Accept old phase/week/day parameters
    phase_index = request.form.get("phase_index", "").strip()
    week_str = request.form.get("week", "").strip()
    day_str = request.form.get("day", "").strip()
    estimated_minutes_str = request.form.get("estimated_minutes", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    
    if not title:
        flash("Oops, title is required", "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    
    # Validate legacy parameters safely
    phase_idx = None
    if phase_index and phase_index.isdigit():
        try:
            phase_idx = int(phase_index)
        except (ValueError, TypeError):
            phase_idx = None
    
    week_val = int(week_str) if week_str and week_str.isdigit() else None
    day_val = int(day_str) if day_str and day_str.isdigit() else None
    estimated_minutes = int(estimated_minutes_str) if estimated_minutes_str and estimated_minutes_str.isdigit() else None
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Determine day_id: use provided, or look up from legacy params, or use inbox
    if day_id is None:
        if phase_idx is not None and week_val is not None and day_val is not None:
            # Try to look up day_id from legacy parameters
            cur.execute("""
                SELECT d.id FROM days d
                JOIN weeks w ON d.week_id = w.id
                JOIN phases p ON w.phase_id = p.id
                WHERE p.user_id = %s AND p.order_index = %s 
                AND w.order_index = %s AND d.order_index = %s
                LIMIT 1
            """, (current_user.id, phase_idx, week_val, day_val))
            day_row = cur.fetchone()
            if day_row:
                day_id = day_row['id']
        
        # If still no day_id, use inbox
        if day_id is None:
            day_id = get_or_create_inbox(current_user.id)
    
    # Check for duplicate (using day_id)
    if day_id:
        cur.execute(
            "SELECT id FROM resources WHERE user_id = %s AND day_id = %s AND title = %s",
            (current_user.id, day_id, title)
        )
        existing = cur.fetchone()
        
        if existing:
            cur.close()
            flash(f"Resource '{title}' already exists for this day.", "warning")
            return redirect(request.referrer or url_for("main.dashboard"))
    
    try:
        # Insert with day_id (and optionally backfill legacy columns)
        cur.execute("""INSERT INTO resources 
            (user_id, day_id, phase_index, week, day, title, topic, url, resource_type, notes, source, estimated_minutes, difficulty, user_modified) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'user', %s, %s, TRUE) RETURNING id""",
            (current_user.id, day_id, phase_idx, week_val, day_val, title, topic or None, url or None, resource_type, notes or None, estimated_minutes, difficulty or None))
        cur.close()
        conn.commit()
        flash(f"Locked in: {title}", "success")
    except psycopg2.IntegrityError:
        cur.close()
        flash("Duplicate resource detected.", "warning")
    
    return redirect(request.referrer or url_for("main.dashboard"))


@api_bp.route("/toggle-resource/<int:resource_id>", methods=["POST"])
@login_required
def toggle_resource(resource_id):
    """Toggle resource status with validation."""
    # Capture query parameters to preserve filters
    search_query = request.form.get("q", "")
    tag_filter = request.form.get("tag", "")
    
    conn = get_db()
    cur = get_db_cursor(conn)
    # Get current state and resource details including is_milestone
    cur.execute("SELECT phase_index, week, day, status, is_milestone FROM resources WHERE user_id = %s AND id = %s", (current_user.id, resource_id))
    resource = cur.fetchone()
    if not resource:
        cur.close()
        flash("Oops, resource not found", "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    
    phase_index = resource["phase_index"]
    week = resource["week"]
    day = resource["day"]
    current_status = resource["status"] or "not_started"
    is_milestone = resource.get("is_milestone", False)
    
    # Cycle through states using STATUS_CYCLE constant
    new_status = STATUS_CYCLE.get(current_status, "in_progress")
    
    # Update resource with new status and timestamp
    if new_status == "complete":
        cur.execute(
            "UPDATE resources SET status = %s, is_completed = TRUE, completed_at = %s WHERE user_id = %s AND id = %s",
            (new_status, datetime.now().isoformat(), current_user.id, resource_id)
        )
    else:
        cur.execute(
            "UPDATE resources SET status = %s, is_completed = FALSE, completed_at = NULL WHERE user_id = %s AND id = %s",
            (new_status, current_user.id, resource_id)
        )
    
    # If this is a milestone resource, link to metrics based on new status
    if is_milestone and phase_index is not None and week is not None:
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
                    cur.execute(
                        "INSERT INTO completed_metrics (user_id, phase_index, metric_text, completed_date, resource_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (phase_index, metric_text) DO NOTHING",
                        (current_user.id, phase_index, metric_text, datetime.now().strftime("%Y-%m-%d"), resource_id)
                    )
                else:
                    # Auto-delete the metric if not complete
                    cur.execute(
                        "DELETE FROM completed_metrics WHERE user_id = %s AND phase_index = %s AND metric_text = %s",
                        (current_user.id, phase_index, metric_text)
                    )
    
    cur.close()
    conn.commit()
    
    # Log the activity
    log_activity(
        f"resource_{new_status}",
        "resource",
        resource_id,
        f"Phase {phase_index + 1} Week {week} Day {day}"
    )
    
    # Build redirect URL with preserved query parameters
    redirect_url = request.referrer or url_for("main.dashboard")
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


@api_bp.route("/toggle-favorite/<int:resource_id>", methods=["POST"])
def toggle_favorite(resource_id):
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("UPDATE resources SET is_favorite = NOT is_favorite WHERE id = %s", (resource_id,))
    cur.close()
    conn.commit()
    return redirect(request.referrer or url_for("main.dashboard"))


@api_bp.route("/delete-resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
    cur.close()
    conn.commit()
    return redirect(request.referrer or url_for("main.dashboard"))


@api_bp.route("/delete-log/<date>", methods=["POST"])
def delete_log(date):
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM time_logs WHERE date = %s", (date,))
    cur.close()
    conn.commit()
    return redirect(url_for("main.dashboard"))


@api_bp.route("/add-tag", methods=["POST"])
def add_tag():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#6366f1")
    if not name:
        return redirect(request.referrer or url_for("main.resources_page"))
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("INSERT INTO tags (name, color) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (name, color))
    cur.close()
    conn.commit()
    flash(f"Tag '{name}' locked in", "success")
    return redirect(request.referrer or url_for("main.resources_page"))


@api_bp.route("/delete-tag/<int:tag_id>", methods=["POST"])
def delete_tag(tag_id):
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM resource_tags WHERE tag_id = %s", (tag_id,))
    cur.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
    cur.close()
    conn.commit()
    return redirect(request.referrer or url_for("main.resources_page"))


@api_bp.route("/bulk", methods=["POST"])
def bulk_action():
    """Perform bulk action on multiple resources with validation."""
    action = request.form.get("action")
    if action not in ["complete", "progress", "skip", "delete"]:
        flash("Oops, invalid action", "error")
        return redirect(url_for("main.dashboard"))
    
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
        return redirect(url_for("main.dashboard"))
    
    conn = get_db()
    
    cur = get_db_cursor(conn)
    if action == "complete":
        for rid in ids:
            cur.execute("UPDATE resources SET status = 'complete', is_completed = TRUE, completed_at = %s WHERE id = %s",
                (datetime.now().isoformat(), rid))
        flash(f"Crushed {len(ids)} resources", "success")
    elif action == "progress":
        for rid in ids:
            cur.execute("UPDATE resources SET status = 'in_progress', is_completed = FALSE WHERE id = %s", (rid,))
        flash(f"Marked {len(ids)} resources as in progress", "success")
    elif action == "skip":
        for rid in ids:
            cur.execute("UPDATE resources SET status = 'skipped', is_completed = FALSE WHERE id = %s", (rid,))
        flash(f"Skipped {len(ids)} resources", "success")
    elif action == "delete":
        for rid in ids:
            cur.execute("DELETE FROM resources WHERE id = %s", (rid,))
        flash(f"Yeeted {len(ids)} resource{'s' if len(ids) > 1 else ''} into the void", "success")
    
    cur.close()
    conn.commit()
    
    return redirect(url_for("main.dashboard"))


@api_bp.route("/reorder", methods=["POST"])
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
    cur = get_db_cursor(conn)
    # Get all resources for this day
    cur.execute(
        "SELECT id FROM resources WHERE phase_index = %s AND week = %s AND day = %s ORDER BY sort_order, id",
        (phase, week, day)
    )
    resources = cur.fetchall()
    
    # Update sort orders
    for i, r in enumerate(resources):
        cur.execute("UPDATE resources SET sort_order = %s WHERE id = %s", (i * 10, r["id"]))
    
    # Set the moved resource to its new position
    cur.execute("UPDATE resources SET sort_order = %s WHERE id = %s", 
        (new_position * 10 + 5, resource_id))
    
    cur.close()
    conn.commit()
    
    return jsonify({"success": True})


@api_bp.route("/schedule/block", methods=["POST"])
def block_day():
    """Block a day and recalculate schedule."""
    date_str = request.form.get("date")
    reason = request.form.get("reason", "").strip()
    
    if not date_str:
        flash("Date is required.", "error")
        return redirect(url_for("main.calendar_view"))
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "INSERT INTO blocked_days (user_id, date, reason) VALUES (%s, %s, %s) ON CONFLICT (date) DO UPDATE SET reason = %s",
        (current_user.id, date_str, reason, reason)
    )
    cur.close()
    conn.commit()
    
    # Recalculate schedule from this date forward
    recalculate_schedule_from(date_str)
    
    flash("Day blocked and schedule shifted.", "success")
    return redirect(url_for("main.calendar_view"))


@api_bp.route("/schedule/unblock", methods=["POST"])
def unblock_day():
    """Unblock a day and recalculate schedule."""
    date_str = request.form.get("date")
    
    if not date_str:
        flash("Date is required.", "error")
        return redirect(url_for("main.calendar_view"))
    
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM blocked_days WHERE date = %s", (date_str,))
    cur.close()
    conn.commit()
    
    # Recalculate schedule from this date forward
    recalculate_schedule_from(date_str)
    
    flash("Day unblocked and schedule shifted.", "success")
    return redirect(url_for("main.calendar_view"))


@api_bp.route("/api/resource", methods=["POST"])
@login_required
def api_add_resource():
    """Add new resource via API."""
    try:
        # Accept JSON or form data
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()
        
        # New: Accept day_id parameter
        day_id = data.get("day_id")
        if day_id:
            try:
                day_id = int(day_id)
            except (ValueError, TypeError):
                day_id = None
        
        # Legacy: Accept old phase/week/day parameters
        phase_index = data.get("phase_index")
        week = data.get("week")
        day = data.get("day")
        
        # Convert to int if provided
        phase_idx = None
        week_val = None
        day_val = None
        
        if phase_index is not None:
            try:
                phase_idx = int(phase_index)
            except (ValueError, TypeError):
                pass
        
        if week is not None:
            try:
                week_val = int(week)
            except (ValueError, TypeError):
                pass
        
        if day is not None:
            try:
                day_val = int(day)
            except (ValueError, TypeError):
                pass
        
        title = data.get("title", "").strip()
        url = data.get("url", "").strip() or None
        resource_type = data.get("resource_type", "link")
        notes = data.get("notes", "").strip() or None
        estimated_minutes_str = data.get("estimated_minutes", "").strip()
        difficulty = data.get("difficulty", "").strip() or None
        
        estimated_minutes_val = int(estimated_minutes) if estimated_minutes_str and estimated_minutes_str.isdigit() else None
        
        if not title:
            return jsonify({"success": False, "error": "Title is required"}), 400
        
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Determine day_id: use provided, or look up from legacy params, or use inbox
        if day_id is None:
            if phase_idx is not None and week_val is not None and day_val is not None:
                # Try to look up day_id from legacy parameters
                cur.execute("""
                    SELECT d.id FROM days d
                    JOIN weeks w ON d.week_id = w.id
                    JOIN phases p ON w.phase_id = p.id
                    WHERE p.user_id = %s AND p.order_index = %s 
                    AND w.order_index = %s AND d.order_index = %s
                    LIMIT 1
                """, (current_user.id, phase_idx, week_val, day_val))
                day_row = cur.fetchone()
                if day_row:
                    day_id = day_row['id']
            
            # If still no day_id, use inbox
            if day_id is None:
                day_id = get_or_create_inbox(current_user.id)
        
        # Get max sort_order for this day
        cur.execute(
            "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM resources WHERE day_id = %s",
            (day_id,)
        )
        max_order = cur.fetchone()['max_order']
        
        cur.execute("""
            INSERT INTO resources (user_id, day_id, phase_index, week, day, title, url, resource_type, notes, estimated_minutes, difficulty, sort_order, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'user') RETURNING id
        """, (current_user.id, day_id, phase_idx, week_val, day_val, title, url, resource_type, notes, estimated_minutes_val, difficulty, max_order + 1))
        new_id = cur.fetchone()['id']
        cur.close()
        conn.commit()
        
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/api/resource/<int:resource_id>", methods=["PUT"])
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
                updates.append(f"{field} = %s")
                values.append(data[field])
        
        if not updates:
            return jsonify({"success": False, "error": "No fields to update"}), 400
        
        values.append(resource_id)
        cur = get_db_cursor(conn)
        cur.execute(
            f"UPDATE resources SET {', '.join(updates)} WHERE id = %s",
            values
        )
        cur.close()
        conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/api/resource/<int:resource_id>", methods=["DELETE"])
def api_delete_resource(resource_id):
    """Delete resource via API."""
    try:
        conn = get_db()
        cur = get_db_cursor(conn)
        cur.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
        cur.close()
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/api/resource/<int:resource_id>/status", methods=["POST"])
def update_resource_status(resource_id):
    """Update resource status via API."""
    data = request.json
    new_status = data.get("status")
    
    if new_status not in ["not_started", "in_progress", "complete", "skipped"]:
        return jsonify({"success": False, "error": "Invalid status"}), 400
    
    conn = get_db()
    
    cur = get_db_cursor(conn)
    # Update status
    if new_status == "complete":
        cur.execute(
            "UPDATE resources SET status = %s, is_completed = TRUE, completed_at = %s WHERE id = %s",
            (new_status, datetime.now().isoformat(), resource_id)
        )
    else:
        cur.execute(
            "UPDATE resources SET status = %s, is_completed = FALSE, completed_at = NULL WHERE id = %s",
            (new_status, resource_id)
        )
    
    cur.close()
    conn.commit()
    
    return jsonify({"success": True})


@api_bp.route("/api/resource/<int:resource_id>/reorder", methods=["POST"])
def api_reorder_resource(resource_id):
    """Update resource sort_order via API."""
    try:
        data = request.json
        new_position = int(data.get("new_position"))
        day = int(data.get("day"))
        week = int(data.get("week"))
        phase_index = int(data.get("phase_index"))
        
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Get current resource
        cur.execute("SELECT sort_order FROM resources WHERE id = %s", (resource_id,))
        resource = cur.fetchone()
        if not resource:
            cur.close()
            return jsonify({"success": False, "error": "Resource not found"}), 404
        
        old_position = resource["sort_order"]
        
        # Get all resources for this day
        cur.execute("""
            SELECT id, sort_order FROM resources 
            WHERE phase_index = %s AND week = %s AND day = %s
            ORDER BY sort_order
        """, (phase_index, week, day))
        all_resources = cur.fetchall()
        
        # Reorder
        if new_position < old_position:
            # Moving up
            cur.execute("""
                UPDATE resources 
                SET sort_order = sort_order + 1 
                WHERE phase_index = %s AND week = %s AND day = %s 
                  AND sort_order >= %s AND sort_order < %s
            """, (phase_index, week, day, new_position, old_position))
        else:
            # Moving down
            cur.execute("""
                UPDATE resources 
                SET sort_order = sort_order - 1 
                WHERE phase_index = %s AND week = %s AND day = %s 
                  AND sort_order > %s AND sort_order <= %s
            """, (phase_index, week, day, old_position, new_position))
        
        # Set new position
        cur.execute(
            "UPDATE resources SET sort_order = %s WHERE id = %s",
            (new_position, resource_id)
        )
        conn.commit()
        cur.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/api/calendar-day/<date_str>")
def api_calendar_day(date_str):
    """Get details for a specific calendar day."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Check if blocked
    cur.execute("SELECT reason FROM blocked_days WHERE date = %s", (date_str,))
    blocked = cur.fetchone()
    
    # Get curriculum days for this date
    curriculum_days = []
    cur.execute("""
        SELECT DISTINCT r.phase_index, r.week, r.day,
               COUNT(r.id) as resource_count,
               SUM(CASE WHEN r.status = 'complete' THEN 1 ELSE 0 END) as completed_count
        FROM resources r
        WHERE r.scheduled_date = %s
        GROUP BY r.phase_index, r.week, r.day
    """, (date_str,))
    
    rows = cur.fetchall()
    for row in rows:
        # Get resources for this curriculum day
        cur.execute("""
            SELECT id, title, status, url, resource_type FROM resources
            WHERE phase_index = %s AND week = %s AND day = %s AND scheduled_date = %s
            ORDER BY sort_order
        """, (row["phase_index"], row["week"], row["day"], date_str))
        resources = cur.fetchall()
        
        curriculum_days.append({
            "phase": row["phase_index"],
            "week": row["week"],
            "day": row["day"],
            "resource_count": row["resource_count"],
            "completed_count": row["completed_count"],
            "resources": [dict(r) for r in resources]
        })
    
    # Get hours logged
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date = %s", (date_str,))
    hours_result = cur.fetchone()
    hours = hours_result["total"] if hours_result else 0
    cur.close()
    
    return jsonify({
        "blocked": blocked is not None,
        "blocked_reason": blocked["reason"] if blocked else None,
        "curriculum_days": curriculum_days,
        "hours": hours
    })


@api_bp.route("/upload/resource/<int:resource_id>", methods=["POST"])
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
        cur = get_db_cursor(conn)
        cur.execute("""
            INSERT INTO attachments (filename, original_filename, file_type, file_size, resource_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (filename, file.filename, ext, filepath.stat().st_size, resource_id))
        conn.commit()
        cur.close()
        
        return jsonify({"success": True, "filename": filename})
    
    return jsonify({"error": "File type not allowed"}), 400


@api_bp.route("/upload/journal/<int:journal_id>", methods=["POST"])
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
        cur = get_db_cursor(conn)
        cur.execute("""
            INSERT INTO attachments (filename, original_filename, file_type, file_size, journal_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (filename, file.filename, ext, filepath.stat().st_size, journal_id))
        conn.commit()
        cur.close()
        
        return jsonify({"success": True, "filename": filename})
    
    return jsonify({"error": "File type not allowed"}), 400


@api_bp.route("/api/attachments/resource/<int:resource_id>")
def api_get_resource_attachments(resource_id):
    """Get all attachments for a resource."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT id, filename, original_filename, file_type, file_size, created_at FROM attachments WHERE resource_id = %s ORDER BY created_at DESC",
        (resource_id,)
    )
    attachments = cur.fetchall()
    cur.close()
    return jsonify({
        "attachments": [dict(att) for att in attachments]
    })


@api_bp.route("/api/attachments/journal/<int:journal_id>")
def api_get_journal_attachments(journal_id):
    """Get all attachments for a journal entry."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT id, filename, original_filename, file_type, file_size, created_at FROM attachments WHERE journal_id = %s ORDER BY created_at DESC",
        (journal_id,)
    )
    attachments = cur.fetchall()
    cur.close()
    return jsonify({
        "attachments": [dict(att) for att in attachments]
    })


@api_bp.route("/api/completion-progress")
def completion_progress():
    """Get curriculum completion progress over time."""
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Get completion dates for all resources
    cur.execute("""
        SELECT DATE(completed_at) as date, COUNT(*) as completed
        FROM resources
        WHERE completed_at IS NOT NULL
        GROUP BY DATE(completed_at)
        ORDER BY DATE(completed_at)
    """)
    results = cur.fetchall()
    cur.close()
    
    # Calculate cumulative completion
    cumulative = 0
    data = []
    for row in results:
        cumulative += row["completed"]
        data.append({
            "date": row["date"],
            "completed": cumulative
        })
    
    return jsonify(data)


@api_bp.route("/api/metric-resources")
def api_metric_resources():
    """Get resources linked to a specific metric by metric_text."""
    metric_text = request.args.get("metric_text", "")
    
    if not metric_text:
        return jsonify({"error": "Missing metric_text parameter"}), 400
    
    conn = get_db()
    cur = get_db_cursor(conn)
    
    # Find ALL resources linked to this metric through completed_metrics table
    # This works for ANY day (not just Day 6)
    cur.execute("""
        SELECT DISTINCT 
            r.id,
            r.title,
            r.status,
            r.url,
            r.phase_index,
            r.week,
            r.day
        FROM resources r
        INNER JOIN completed_metrics cm ON r.id = cm.resource_id
        WHERE cm.metric_text = %s
        ORDER BY r.phase_index, r.week, r.day
    """, (metric_text,))
    
    resources = cur.fetchall()
    cur.close()
    
    return jsonify({
        "resources": [dict(r) for r in resources]
    })


# ============================================================================
# Structure Management Endpoints (Phases/Weeks/Days)
# ============================================================================

@api_bp.route("/api/structure", methods=["GET"])
@login_required
def api_get_structure():
    """Get full nested structure for Kanban board."""
    try:
        include_resources = request.args.get('include_resources', 'false').lower() == 'true'
        structure_data = get_structure(current_user.id, include_resources=include_resources)
        return jsonify(structure_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/structure/phase", methods=["POST"])
@login_required
def api_create_phase():
    """Create a new phase."""
    try:
        data = request.json or {}
        title = data.get("title", "").strip()
        color = data.get("color")
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
        
        phase = create_phase(current_user.id, title, color)
        return jsonify(phase), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/structure/week", methods=["POST"])
@login_required
def api_create_week():
    """Create a new week."""
    try:
        data = request.json or {}
        phase_id = data.get("phase_id")
        title = data.get("title", "").strip()
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
        if not phase_id:
            return jsonify({"error": "phase_id is required"}), 400
        
        week = create_week(current_user.id, phase_id, title)
        return jsonify(week), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/structure/day", methods=["POST"])
@login_required
def api_create_day():
    """Create a new day."""
    try:
        data = request.json or {}
        week_id = data.get("week_id")
        title = data.get("title", "").strip()
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
        if not week_id:
            return jsonify({"error": "week_id is required"}), 400
        
        day = create_day(current_user.id, week_id, title)
        return jsonify(day), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/structure/<string:type>/<int:item_id>", methods=["PUT"])
@login_required
def api_update_structure(type, item_id):
    """Update structure item title (and color for phases)."""
    try:
        data = request.json or {}
        title = data.get("title", "").strip()
        color = data.get("color")
        
        if not title and color is None:
            return jsonify({"error": "Title or color is required"}), 400
        
        if not title:
            # Only updating color for phase
            if type != "phase":
                return jsonify({"error": "Title is required for this operation"}), 400
            title = None
        
        model_map = {"phase": "phase", "week": "week", "day": "day"}
        if type not in model_map:
            return jsonify({"error": "Invalid type. Must be phase, week, or day"}), 400
        
        result = update_structure_title(model_map[type], item_id, current_user.id, title, color)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/structure/<string:type>/<int:item_id>", methods=["DELETE"])
@login_required
def api_delete_structure(type, item_id):
    """Delete structure item. Cascades to children."""
    try:
        model_map = {"phase": "phase", "week": "week", "day": "day"}
        if type not in model_map:
            return jsonify({"error": "Invalid type. Must be phase, week, or day"}), 400
        
        delete_structure_item(model_map[type], item_id, current_user.id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/structure/reorder", methods=["PUT"])
@login_required
def api_reorder_structure():
    """Reorder structure item (week or day) via drag-and-drop."""
    try:
        data = request.json or {}
        item_type = data.get("type")
        item_id = data.get("id")
        new_parent_id = data.get("new_parent_id")
        new_index = data.get("new_index")
        
        if not all([item_type, item_id is not None, new_parent_id is not None, new_index is not None]):
            return jsonify({"error": "Missing required fields: type, id, new_parent_id, new_index"}), 400
        
        if item_type not in ["week", "day"]:
            return jsonify({"error": "Type must be 'week' or 'day'"}), 400
        
        reorder_structure(item_type, item_id, new_parent_id, new_index, current_user.id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

