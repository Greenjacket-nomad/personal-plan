#!/usr/bin/env python3
"""
Main routes for Curriculum Tracker.
HTML rendering routes for dashboard, resources, journal, activity, etc.
"""

import json
import psycopg2
import calendar
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, current_app, send_from_directory, stream_with_context, send_file
from flask_login import login_user, logout_user, login_required, current_user
from constants import STATUS_CYCLE

# Import from new modular structure
from database import get_db, get_db_cursor
from utils import (
    load_curriculum, get_start_date, set_start_date, calculate_schedule,
    recalculate_schedule_from, get_projected_end_date, allowed_file, UPLOAD_FOLDER
)
from services.progress import (
    init_if_needed, get_progress, update_progress,
    get_current_week_hours, get_total_hours, get_hours_for_phase,
    get_recent_logs, get_completed_metrics, get_current_streak,
    get_longest_streak, get_week_activity, get_today_position,
    get_hours_today, get_overdue_days
)
from services.resources import (
    get_resources, get_all_resources, get_all_tags, get_resources_by_week,
    get_day_completion, get_week_completion, get_phase_completion,
    get_continue_resource, get_resources_filtered
)
from services.structure import get_structure_for_dashboard
from services.reporting import get_burndown_data
from services.progress import log_activity

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route("/static/data/<path:filename>")
def serve_data_file(filename):
    """Serve data files like journal prompts JSON."""
    from pathlib import Path
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / filename
    if file_path.exists() and file_path.is_file():
        return send_file(file_path)
    return jsonify({"error": "File not found"}), 404


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login route."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("login.html")
        
        from services.auth import authenticate_user
        user = authenticate_user(username, password)
        
        if user:
            login_user(user)
            from utils import sanitize_flash_message
            flash(f"Welcome back, {sanitize_flash_message(user.username)}!", "success")
            next_page = request.args.get("next") or url_for("main.dashboard")
            return redirect(next_page)
        else:
            flash("Invalid username or password", "error")
    
    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    """Logout route."""
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/")
@main_bp.route("/view/<int:view_phase>/<int:view_week>")
@login_required
def dashboard(view_phase=None, view_week=None):
    init_if_needed()
    # Use database structure instead of YAML
    curriculum = get_structure_for_dashboard(current_user.id)
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
    curriculum_total = sum(p["hours"] for p in curriculum["phases"])
    expected_weekly = phase["hours"] / phase["weeks"] if phase["weeks"] > 0 else 0
    completed = get_completed_metrics(display_phase)
    completed_texts = {m["metric_text"] for m in completed}
    total_weeks = sum(p["weeks"] for p in curriculum["phases"])
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:display_phase])
    current_absolute_week = weeks_before + display_week
    
    # Get unified progress metrics (Tasks Completed is primary)
    from services.progress import get_unified_progress
    unified_progress = get_unified_progress(current_user.id, curriculum_total)
    overall_progress = unified_progress['tasks_percent']  # Primary metric: Tasks Completed
    total_hours = unified_progress['hours_logged']  # Secondary metric: Hours Logged
    recent_logs = get_recent_logs()
    resources = get_resources(display_phase)
    grouped_week, ungrouped_week = get_resources_by_week(display_phase, display_week)
    all_tags = get_all_tags()
    
    # Batch query for resource hours (fixes N+1 query problem)
    all_resource_ids = [r["id"] for r in resources]
    for day_resources in grouped_week.values():
        all_resource_ids.extend([r["id"] for r in day_resources])
    all_resource_ids = list(set(all_resource_ids))  # Remove duplicates
    
    resource_hours = {}
    if all_resource_ids:
        conn = get_db()
        cur = get_db_cursor(conn)
        placeholders = ','.join(['%s'] * len(all_resource_ids))
        cur.execute(f"""
            SELECT resource_id, COALESCE(SUM(hours), 0) as total_hours
            FROM time_logs
            WHERE resource_id IN ({placeholders})
            GROUP BY resource_id
        """, all_resource_ids)
        hours_results = cur.fetchall()
        cur.close()
        
        # Create lookup dictionary
        hours_map = {row["resource_id"]: row["total_hours"] for row in hours_results}
        
        # Populate resource_hours dict (only non-zero hours)
        resource_hours = {r["id"]: hours_map.get(r["id"], 0) 
                          for r in resources if hours_map.get(r["id"], 0) > 0}
        
        # Populate grouped_week resources
        for day_resources in grouped_week.values():
            for r in day_resources:
                r["logged_hours"] = hours_map.get(r["id"], 0)
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
    
    # Calculate milestone days (days with at least one milestone resource)
    milestone_days = {}
    for day in range(1, 7):
        milestone_days[day] = any(r.get('is_milestone', False) for r in grouped_week.get(day, []))
    
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
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM journal_entries WHERE date = %s", (today_date,))
    today_journal = cur.fetchone()
    today_journal_dict = dict(today_journal) if today_journal else None
    
    # Get hours logged today
    hours_today = get_hours_today()
    
    # Get start date
    start_date = get_start_date()
    
    # Calculate schedule if start_date exists but scheduled_date is NULL
    if start_date:
        # Check if any resources have scheduled_date
        cur.execute("SELECT COUNT(*) as count FROM resources WHERE scheduled_date IS NOT NULL")
        has_scheduled = cur.fetchone()['count'] > 0
        
        if not has_scheduled:
            cur.close()
            calculate_schedule(start_date)
            cur = get_db_cursor(conn)
    
    cur.close()
    
    # Get projected end date
    projected_end_date = get_projected_end_date() if start_date else None
    
    # Generate time-appropriate greeting
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    
    # Generate recommendations for What's Next
    recommendations = []
    
    # 1. Incomplete high-priority items
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT r.*, p.phase_index, p.week, p.day
        FROM resources r
        JOIN (
            SELECT phase_index, week, day, MIN(sort_order) as min_order
            FROM resources
            WHERE user_id = %s AND status != 'complete'
            GROUP BY phase_index, week, day
        ) p ON r.phase_index = p.phase_index AND r.week = p.week AND r.day = p.day
        WHERE r.user_id = %s 
        AND r.status != 'complete'
        AND r.sort_order = p.min_order
        AND (r.scheduled_date IS NULL OR r.scheduled_date <= CURRENT_DATE)
        ORDER BY r.scheduled_date ASC NULLS LAST, r.phase_index ASC, r.week ASC, r.day ASC
        LIMIT 3
    """, (current_user.id, current_user.id))
    incomplete_resources = cur.fetchall()
    
    for res in incomplete_resources[:2]:
        res_dict = dict(res)
        # Handle scheduled_date - it may be a date object or string
        scheduled_date = res_dict.get('scheduled_date')
        if scheduled_date:
            if isinstance(scheduled_date, str):
                scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            elif hasattr(scheduled_date, 'date'):
                scheduled_date = scheduled_date.date()
        
        priority = 'high' if scheduled_date and scheduled_date <= datetime.now().date() else 'medium'
        recommendations.append({
            'title': res_dict.get('title', 'Untitled Resource'),
            'type': 'resource',
            'priority': priority,
            'description': f"Phase {res_dict.get('phase_index', 0) + 1}, Week {res_dict.get('week', 0)}, Day {res_dict.get('day', 0)}",
            'action_url': f"/view/{res_dict.get('phase_index', 0)}/{res_dict.get('week', 0)}#resource-{res_dict.get('id')}"
        })
    
    # 2. Approaching deadlines (within 3 days)
    cur.execute("""
        SELECT * FROM resources
        WHERE user_id = %s
        AND status != 'complete'
        AND scheduled_date IS NOT NULL
        AND scheduled_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 days'
        ORDER BY scheduled_date ASC
        LIMIT 2
    """, (current_user.id,))
    approaching = cur.fetchall()
    
    for res in approaching:
        res_dict = dict(res)
        if len(recommendations) < 4:  # Limit total recommendations
            recommendations.append({
                'title': res_dict.get('title', 'Untitled Resource'),
                'type': 'resource',
                'priority': 'high',
                'description': f"Due: {res_dict.get('scheduled_date')}",
                'action_url': f"/view/{res_dict.get('phase_index', 0)}/{res_dict.get('week', 0)}#resource-{res_dict.get('id')}"
            })
    
    cur.close()
    
    # Get resources for expected position (if available)
    expected_resources = []
    if today_position and today_position.get('status') != 'not_started':
        cur = get_db_cursor(conn)
        cur.execute(
            "SELECT * FROM resources WHERE phase_index = %s AND week = %s AND day = %s",
            (today_position['expected_phase'], today_position['expected_week'], today_position['expected_day'])
        )
        expected_resources = cur.fetchall()
        expected_resources = [dict(r) for r in expected_resources]
        cur.close()
    
    return render_template("dashboard.html", phase=phase, phase_index=display_phase, current_week=display_week,
        current_phase=current_phase, current_week_state=current_week, view_phase=view_phase, view_week=view_week,
        week_hours=week_hours, expected_weekly=expected_weekly, total_hours=total_hours,
        curriculum_total=curriculum_total, overall_progress=min(overall_progress, 100),
        unified_progress=unified_progress,
        completed_texts=completed_texts, recent_logs=recent_logs, phases=phases_data,
        resources=resources, grouped_week_resources=grouped_week, ungrouped_week_resources=ungrouped_week, all_tags=all_tags, today=today_date,
        current_absolute_week=current_absolute_week, total_weeks=total_weeks, search_query=search_query,
        phase_completed=phase_completed, phase_total=phase_total, phase_percent=phase_percent,
        week_completed=week_completed, week_total=week_total, week_percent=week_percent,
        day_completions=day_completions, milestone_days=milestone_days, resource_hours=resource_hours, all_weeks_completion=all_weeks_completion,
        current_streak=current_streak, longest_streak=longest_streak, week_activity=week_activity,
        today_position=today_position, continue_resource=continue_resource, today_journal=today_journal_dict,
        hours_today=hours_today, expected_resources=expected_resources, curriculum=curriculum,
        start_date=start_date, projected_end_date=projected_end_date,
        burndown_data=get_burndown_data() if start_date else None,
        overdue_days=get_overdue_days() if start_date else [],
        greeting=greeting, recommendations=recommendations)


@main_bp.route("/resources")
@login_required
def resources_page():
    """Show all resources with database-side filtering for optimal performance."""
    curriculum = load_curriculum()
    
    # Read filter parameters
    search_query = request.args.get("q", "").strip() or None
    filter_type = request.args.get("type", "").strip() or None
    filter_phase = request.args.get("phase", "").strip() or None
    filter_tag = request.args.get("tag", "").strip() or None
    filter_status = request.args.get("status", "").strip() or None
    
    # Convert phase filter to int if provided
    phase_index = None
    if filter_phase:
        try:
            phase_index = int(filter_phase)
        except ValueError:
            pass
    
    # Get filtered resources directly from database (no in-memory filtering)
    filtered_resources = get_resources_filtered(
        user_id=current_user.id,
        search_query=search_query,
        resource_type=filter_type,
        phase_index=phase_index,
        tag=filter_tag,
        status=filter_status
    )
    
    # Batch query for resource hours (fixes N+1 query problem)
    resource_hours = {}
    if filtered_resources:
        resource_ids = [r["id"] for r in filtered_resources]
        conn = get_db()
        cur = get_db_cursor(conn)
        placeholders = ','.join(['%s'] * len(resource_ids))
        cur.execute(f"""
            SELECT resource_id, COALESCE(SUM(hours), 0) as total_hours
            FROM time_logs
            WHERE resource_id IN ({placeholders})
            GROUP BY resource_id
        """, resource_ids)
        hours_results = cur.fetchall()
        cur.close()
        
        # Create lookup dictionary
        hours_map = {row["resource_id"]: row["total_hours"] for row in hours_results}
        
        # Populate resource_hours dict (only non-zero hours)
        resource_hours = {r["id"]: hours_map.get(r["id"], 0) 
                          for r in filtered_resources if hours_map.get(r["id"], 0) > 0}
    
    # Get overdue resources
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    overdue_resource_ids = set()
    cur = get_db_cursor(conn)
    cur.execute("""
        SELECT DISTINCT id FROM resources
        WHERE scheduled_date < %s AND scheduled_date IS NOT NULL
          AND status != 'complete'
    """, (today,))
    overdue_resources = cur.fetchall()
    cur.close()
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


@main_bp.route("/curriculum/board")
@login_required
def curriculum_board():
    """Show Kanban board view of curriculum structure."""
    return render_template("curriculum_board.html")


@main_bp.route("/activity")
@login_required
def activity():
    """Show activity history filtered by current user."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute(
        "SELECT * FROM activity_log WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
        (current_user.id,)
    )
    logs = cur.fetchall()
    cur.close()
    # Convert RealDictRow objects to dictionaries for JSON serialization
    logs = [dict(log) for log in logs]
    return render_template("activity.html", logs=logs)


@main_bp.route("/journal")
@login_required
def journal():
    """Show all journal entries."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM journal_entries WHERE user_id = %s ORDER BY date DESC", (current_user.id,))
    entries = cur.fetchall()
    
    # Get "On this day" entries - entries from previous years on the same month/day
    today = datetime.now()
    cur.execute("""
        SELECT * FROM journal_entries 
        WHERE user_id = %s 
        AND EXTRACT(MONTH FROM date::date) = %s 
        AND EXTRACT(DAY FROM date::date) = %s
        AND EXTRACT(YEAR FROM date::date) < %s
        ORDER BY date DESC
        LIMIT 5
    """, (current_user.id, today.month, today.day, today.year))
    on_this_day_entries = cur.fetchall()
    cur.close()
    
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
                          phases=phases_data, today_position=today_position, editing=None,
                          on_this_day_entries=[dict(e) for e in on_this_day_entries])


@main_bp.route("/journal", methods=["POST"])
@login_required
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
    cur = get_db_cursor(conn)
    # Check if entry exists for this date
    cur.execute("SELECT id FROM journal_entries WHERE date = %s", (date,))
    existing = cur.fetchone()
    
    if existing:
        if link_to_day and phase_index_val is not None:
            cur.execute(
                "UPDATE journal_entries SET content = %s, mood = %s, phase_index = %s, week = %s, day = %s, updated_at = %s WHERE user_id = %s AND date = %s",
                (content, mood, phase_index_val, week_val, day_val, datetime.now().isoformat(), current_user.id, date)
            )
        else:
            cur.execute(
                "UPDATE journal_entries SET content = %s, mood = %s, phase_index = NULL, week = NULL, day = NULL, updated_at = %s WHERE user_id = %s AND date = %s",
                (content, mood, datetime.now().isoformat(), current_user.id, date)
            )
        flash("Reflection locked in!", "success")
    else:
        if link_to_day and phase_index_val is not None:
            cur.execute(
                "INSERT INTO journal_entries (user_id, date, content, mood, phase_index, week, day) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (date) DO UPDATE SET content = %s, mood = %s, phase_index = %s, week = %s, day = %s, updated_at = CURRENT_TIMESTAMP",
                (current_user.id, date, content, mood, phase_index_val, week_val, day_val, content, mood, phase_index_val, week_val, day_val)
            )
        else:
            cur.execute(
                "INSERT INTO journal_entries (user_id, date, content, mood) VALUES (%s, %s, %s, %s) ON CONFLICT (date) DO UPDATE SET content = %s, mood = %s, updated_at = CURRENT_TIMESTAMP",
                (current_user.id, date, content, mood, content, mood)
            )
        flash("Reflection locked in", "success")
    
    cur.close()
    conn.commit()
    
    return redirect(url_for("main.journal"))


@main_bp.route("/journal/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_journal(entry_id):
    """Edit a journal entry."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM journal_entries WHERE id = %s AND user_id = %s", (entry_id, current_user.id))
    entry = cur.fetchone()
    cur.close()
    
    if not entry:
        flash("Journal entry not found.", "error")
        return redirect(url_for("main.journal"))
    
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
        
        cur = get_db_cursor(conn)
        if link_to_day and phase_index_val is not None:
            cur.execute(
                "UPDATE journal_entries SET content = %s, mood = %s, phase_index = %s, week = %s, day = %s, updated_at = %s WHERE user_id = %s AND id = %s",
                (content, mood, phase_index_val, week_val, day_val, datetime.now().isoformat(), current_user.id, entry_id)
            )
        else:
            cur.execute(
                "UPDATE journal_entries SET content = %s, mood = %s, phase_index = NULL, week = NULL, day = NULL, updated_at = %s WHERE user_id = %s AND id = %s",
                (content, mood, datetime.now().isoformat(), current_user.id, entry_id)
            )
        cur.close()
        conn.commit()
        flash("Reflection locked in!", "success")
        return redirect(url_for("main.journal"))
    
    # GET: Show edit form
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM journal_entries WHERE user_id = %s ORDER BY date DESC", (current_user.id,))
    entries = cur.fetchall()
    cur.close()
    
    # Get curriculum for dropdowns
    curriculum = load_curriculum()
    phases_data = []
    for i, p in enumerate(curriculum["phases"]):
        phases_data.append({
            "index": i, "name": p["name"], "weeks": p["weeks"]
        })
    
    return render_template("journal.html", entries=entries, today=datetime.now().strftime("%Y-%m-%d"),
                          editing=dict(entry), phases=phases_data, today_position=None)


@main_bp.route("/journal/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_journal(entry_id):
    """Delete a journal entry."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT * FROM journal_entries WHERE id = %s AND user_id = %s", (entry_id, current_user.id))
    entry = cur.fetchone()
    
    if not entry:
        cur.close()
        flash("Journal entry not found.", "error")
        return redirect(url_for("main.journal"))
    
    cur.execute("DELETE FROM journal_entries WHERE id = %s AND user_id = %s", (entry_id, current_user.id))
    cur.close()
    conn.commit()
    flash("Reflection yeeted into the void", "success")
    return redirect(url_for("main.journal"))


@main_bp.route("/calendar")
@main_bp.route("/calendar/<int:year>/<int:month>")
def calendar_view(year=None, month=None):
    """Redirect to dashboard with calendar section visible."""
    flash("Calendar has been merged into the dashboard.", "info")
    return redirect(url_for("main.dashboard", _anchor="week-calendar-view"))


@main_bp.route("/curriculum/edit")
@login_required
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
            cur = get_db_cursor(conn)
            cur.execute("""
                SELECT DISTINCT day FROM resources 
                WHERE phase_index = %s AND week = %s
                ORDER BY day
            """, (phase_idx, week_num))
            existing_days = cur.fetchall()
            cur.close()
            
            day_numbers = [row["day"] for row in existing_days if row["day"]]
            if not day_numbers:
                # If no days exist, show days 1-6
                day_numbers = list(range(1, 7))
            
            for day_num in day_numbers:
                # Get resources for this day
                cur = get_db_cursor(conn)
                cur.execute("""
                    SELECT * FROM resources 
                    WHERE phase_index = %s AND week = %s AND day = %s
                    ORDER BY sort_order
                """, (phase_idx, week_num, day_num))
                resources = cur.fetchall()
                cur.close()
                
                days_data.append({
                    "number": day_num,
                    "resources": [dict(r) for r in resources]
                })
            
            # Calculate week resource count
            cur = get_db_cursor(conn)
            cur.execute(
                "SELECT COUNT(*) as count FROM resources WHERE phase_index = %s AND week = %s",
                (phase_idx, week_num)
            )
            week_count = cur.fetchone()["count"]
            cur.close()
            
            weeks_data.append({
                "number": week_num,
                "days": days_data,
                "resource_count": week_count
            })
        
        # Calculate phase resource count
        cur = get_db_cursor(conn)
        cur.execute(
            "SELECT COUNT(*) as count FROM resources WHERE phase_index = %s",
            (phase_idx,)
        )
        phase_count = cur.fetchone()["count"]
        cur.close()
        
        curriculum_tree.append({
            "index": phase_idx,
            "name": phase["name"],
            "weeks": weeks_data,
            "resource_count": phase_count
        })
    
    return render_template("curriculum_editor.html", curriculum_tree=curriculum_tree)


@main_bp.route("/reports")
@login_required
def reports():
    """Show time reports and analytics."""
    from services.reporting import get_time_reports
    reports_data = get_time_reports()
    return render_template("reports.html", reports=reports_data)


@main_bp.route("/export")
@login_required
def export_data():
    """Export all user data as streaming JSON to prevent memory issues.
    
    Uses streaming response with stream_with_context to keep database connection
    alive during the download, preventing "connection closed" errors.
    """
    def generate():
        conn = get_db()
        cur = get_db_cursor(conn)
        
        try:
            # Start JSON object
            yield '{"exported_at": "' + datetime.now().isoformat() + '",\n'
            
            # Stream config/settings
            yield '"config": '
            cur.execute("SELECT key, value FROM settings")
            config_items = []
            for row in cur.fetchall():
                config_items.append(f'"{row["key"]}": {json.dumps(row["value"])}')
            if config_items:
                yield '{' + ','.join(config_items) + '}'
            else:
                yield '{}'
            yield ',\n'
            
            # Stream time_logs
            yield '"time_logs": [\n'
            cur.execute(
                "SELECT date, hours, notes, phase_index FROM time_logs WHERE user_id = %s ORDER BY date",
                (current_user.id,)
            )
            first = True
            for row in cur:
                if not first:
                    yield ',\n'
                yield json.dumps(dict(row), indent=2).replace('\n', '\n  ')
                first = False
            yield '\n],\n'
            
            # Stream completed_metrics
            yield '"completed_metrics": [\n'
            cur.execute(
                "SELECT phase_index, metric_text, completed_date FROM completed_metrics WHERE user_id = %s",
                (current_user.id,)
            )
            first = True
            for row in cur:
                if not first:
                    yield ',\n'
                yield json.dumps(dict(row), indent=2).replace('\n', '\n  ')
                first = False
            yield '\n],\n'
            
            # Stream resources
            yield '"resources": [\n'
            cur.execute(
                """SELECT phase_index, week, day, title, topic, url, resource_type, notes, 
                          is_completed, is_favorite, source, scheduled_date, status
                   FROM resources 
                   WHERE user_id = %s
                   ORDER BY phase_index, week, day""",
                (current_user.id,)
            )
            first = True
            for row in cur:
                if not first:
                    yield ',\n'
                yield json.dumps(dict(row), indent=2).replace('\n', '\n  ')
                first = False
            yield '\n],\n'
            
            # Stream tags (global but we'll include them)
            yield '"tags": [\n'
            cur.execute("SELECT name, color FROM tags ORDER BY name")
            first = True
            for row in cur:
                if not first:
                    yield ',\n'
                yield json.dumps(dict(row), indent=2).replace('\n', '\n  ')
                first = False
            yield '\n]\n'
            
            # Close JSON object
            yield '}'
        finally:
            cur.close()
    
    return Response(
        stream_with_context(generate()),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=curriculum_export.json"}
    )


@main_bp.route("/settings/start-date", methods=["POST"])
@login_required
def update_start_date():
    """Update start date and recalculate schedule."""
    date_str = request.form.get("start_date")
    if not date_str:
        flash("Oops, start date is required", "error")
        return redirect(url_for("main.dashboard"))
    
    set_start_date(date_str)
    calculate_schedule(date_str)
    flash("Start date locked in! Schedule calculated.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/reset", methods=["POST"])
@login_required
def reset():
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("DELETE FROM config")
    cur.execute("DELETE FROM time_logs")
    cur.execute("DELETE FROM completed_metrics")
    cur.execute("UPDATE resources SET is_completed = FALSE")
    cur.execute("UPDATE resources SET is_favorite = FALSE")
    cur.execute("UPDATE resources SET status = 'not_started'")
    cur.execute("UPDATE resources SET completed_at = NULL")
    conn.commit()
    cur.close()
    
    # Log activity
    log_activity("progress_reset", None, None, "All progress reset")
    
    init_if_needed()
    flash("Fresh slate!", "info")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/uploads/<filename>")
def serve_file(filename):
    """Serve uploaded files."""
    return send_from_directory(str(UPLOAD_FOLDER), filename)


@main_bp.route("/attachment/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id):
    """Delete an attachment."""
    conn = get_db()
    cur = get_db_cursor(conn)
    cur.execute("SELECT filename FROM attachments WHERE id = %s", (attachment_id,))
    attachment = cur.fetchone()
    if attachment:
        filepath = UPLOAD_FOLDER / attachment["filename"]
        if filepath.exists():
            filepath.unlink()
        cur.execute("DELETE FROM attachments WHERE id = %s", (attachment_id,))
        conn.commit()
        flash("Attachment yeeted into the void", "success")
    cur.close()
    return redirect(request.referrer or url_for("main.dashboard"))


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found'), 404


@main_bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    flash("File is too large. Maximum size is 16MB.", "error")
    return redirect(request.referrer or url_for("main.dashboard"))


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html', error='Something went wrong. Please try again.'), 500

