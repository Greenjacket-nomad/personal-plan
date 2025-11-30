#!/usr/bin/env python3
"""
Curriculum Tracker - Web Dashboard with SQLite
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import yaml

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "tracker.db"
CURRICULUM_PATH = APP_DIR / "curriculum.yaml"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS time_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, hours REAL NOT NULL, notes TEXT, phase_index INTEGER);
        CREATE TABLE IF NOT EXISTS completed_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER NOT NULL, metric_text TEXT NOT NULL, completed_date TEXT NOT NULL, UNIQUE(phase_index, metric_text));
        CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER, week INTEGER, day INTEGER, title TEXT NOT NULL, url TEXT, resource_type TEXT DEFAULT 'link', notes TEXT, is_completed INTEGER DEFAULT 0, is_favorite INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, source TEXT DEFAULT 'user', topic TEXT);
        CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT DEFAULT '#6366f1');
        CREATE TABLE IF NOT EXISTS resource_tags (resource_id INTEGER, tag_id INTEGER, PRIMARY KEY (resource_id, tag_id));
        """
    )
    conn.commit()
    conn.close()


def get_config(key, default=None):
    conn = get_db()
    cur = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


def set_config(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def init_if_needed():
    if get_config("start_date") is None:
        today = datetime.now().strftime("%Y-%m-%d")
        set_config("start_date", today)
        set_config("current_phase", "0")
        set_config("current_week", "1")


def load_curriculum():
    with open(CURRICULUM_PATH) as f:
        return yaml.safe_load(f)


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
    conn.close()
    return result["total"]


def get_total_hours():
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs")
    result = cur.fetchone()
    conn.close()
    return result["total"]


def get_hours_for_phase(phase_index, curriculum):
    # Query by phase_index column instead of date ranges
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE phase_index = ?", (phase_index,))
    result = cur.fetchone()
    conn.close()
    return result["total"]


def get_completed_metrics(phase_index=None):
    conn = get_db()
    if phase_index is not None:
        cur = conn.execute("SELECT * FROM completed_metrics WHERE phase_index = ?", (phase_index,))
    else:
        cur = conn.execute("SELECT * FROM completed_metrics")
    results = cur.fetchall()
    conn.close()
    return results


def get_recent_logs(days=7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_db()
    cur = conn.execute("SELECT date, hours, notes FROM time_logs WHERE date >= ? ORDER BY date DESC", (cutoff,))
    results = cur.fetchall()
    conn.close()
    return results


def get_resources(phase_index=None):
    conn = get_db()
    if phase_index is not None:
        cur = conn.execute("SELECT * FROM resources WHERE phase_index = ? OR phase_index IS NULL ORDER BY week, day, is_favorite DESC, created_at DESC", (phase_index,))
    else:
        cur = conn.execute("SELECT * FROM resources ORDER BY phase_index, week, day, is_favorite DESC, created_at DESC")
    rows = cur.fetchall()
    conn.close()

    resources = []
    for r in rows:
        item = dict(r)
        item["tags"] = []
        item["tag_colors"] = []
        conn2 = get_db()
        tag_rows = conn2.execute(
            """
            SELECT t.name, t.color FROM tags t
            JOIN resource_tags rt ON t.id = rt.tag_id
            WHERE rt.resource_id = ?
            """,
            (r["id"],)
        ).fetchall()
        conn2.close()
        for t in tag_rows:
            item["tags"].append(t["name"])
            item["tag_colors"].append(t["color"])
        resources.append(item)
    return resources


def get_all_resources():
    return get_resources()


def get_all_tags():
    conn = get_db()
    cur = conn.execute("SELECT * FROM tags ORDER BY name")
    results = cur.fetchall()
    conn.close()
    return results


def get_resources_by_week(phase_index, week):
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM resources WHERE phase_index = ? AND week = ? ORDER BY day, is_favorite DESC, created_at DESC",
        (phase_index, week),
    )
    rows = cur.fetchall()
    conn.close()
    grouped = {i: [] for i in range(1, 7)}
    ungrouped = []
    for r in rows:
        item = dict(r)
        item["tags"] = []
        item["tag_colors"] = []
        conn2 = get_db()
        tag_rows = conn2.execute(
            """
            SELECT t.name, t.color FROM tags t
            JOIN resource_tags rt ON t.id = rt.tag_id
            WHERE rt.resource_id = ?
            """,
            (r["id"],),
        ).fetchall()
        conn2.close()
        for t in tag_rows:
            item["tags"].append(t["name"])
            item["tag_colors"].append(t["color"])
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
    conn.close()
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
    conn.close()
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
    conn.close()
    total = row["total"] or 0
    completed = row["completed"] or 0
    percent = (completed / total * 100) if total > 0 else 0
    return (completed, total, percent)


@app.route("/")
@app.route("/view/<int:view_phase>/<int:view_week>")
def dashboard(view_phase=None, view_week=None):
    init_if_needed()
    curriculum = load_curriculum()
    current_phase = int(get_config("current_phase") or 0)
    current_week = int(get_config("current_week") or 1)
    
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
    
    # Get search query if present
    search_query = request.args.get("q", "").strip()
    if search_query:
        # Filter resources by search query (case-insensitive)
        search_lower = search_query.lower()
        filtered_grouped = {}
        for day, day_resources in grouped_week.items():
            filtered_day = [
                r for r in day_resources
                if search_lower in (r.get("title", "") or "").lower()
                or search_lower in (r.get("notes", "") or "").lower()
                or search_lower in (r.get("topic", "") or "").lower()
            ]
            if filtered_day:
                filtered_grouped[day] = filtered_day
        grouped_week = filtered_grouped
        filtered_ungrouped = [
            r for r in ungrouped_week
            if search_lower in (r.get("title", "") or "").lower()
            or search_lower in (r.get("notes", "") or "").lower()
            or search_lower in (r.get("topic", "") or "").lower()
        ]
        ungrouped_week = filtered_ungrouped
    
    # Calculate completion rollups
    phase_completed, phase_total, phase_percent = get_phase_completion(display_phase)
    week_completed, week_total, week_percent = get_week_completion(display_phase, display_week)
    day_completions = {}
    for day in range(1, 7):
        day_completed, day_total = get_day_completion(display_phase, display_week, day)
        day_completions[day] = {"completed": day_completed, "total": day_total}
    
    return render_template("dashboard.html", phase=phase, phase_index=display_phase, current_week=display_week,
        current_phase=current_phase, current_week_state=current_week, view_phase=view_phase, view_week=view_week,
        week_hours=week_hours, expected_weekly=expected_weekly, total_hours=total_hours,
        curriculum_total=curriculum_total, overall_progress=min(overall_progress, 100),
        completed_texts=completed_texts, recent_logs=recent_logs, phases=phases_data,
        resources=resources, grouped_week_resources=grouped_week, ungrouped_week_resources=ungrouped_week, all_tags=all_tags, today=datetime.now().strftime("%Y-%m-%d"),
        current_absolute_week=current_absolute_week, total_weeks=total_weeks, search_query=search_query,
        phase_completed=phase_completed, phase_total=phase_total, phase_percent=phase_percent,
        week_completed=week_completed, week_total=week_total, week_percent=week_percent,
        day_completions=day_completions)


@app.route("/resources")
def resources_page():
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
    
    return render_template("resources.html", 
        resources=filtered_resources,
        phases=curriculum["phases"],
        all_tags=get_all_tags(),
        search_query=search_query,
        filter_type=filter_type,
        filter_phase=filter_phase,
        filter_tag=filter_tag,
        filter_status=filter_status)


@app.route("/log", methods=["POST"])
def log_hours():
    hours = float(request.form.get("hours", 0))
    log_date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()
    if hours <= 0:
        return redirect(url_for("dashboard"))
    # Get current phase_index for this log entry
    current_phase = int(get_config("current_phase") or 0)
    conn = get_db()
    existing = conn.execute("SELECT id, hours FROM time_logs WHERE date = ?", (log_date,)).fetchone()
    if existing:
        conn.execute("UPDATE time_logs SET hours = ?, notes = ?, phase_index = ? WHERE id = ?", (existing["hours"] + hours, notes, current_phase, existing["id"]))
    else:
        conn.execute("INSERT INTO time_logs (date, hours, notes, phase_index) VALUES (?, ?, ?, ?)", (log_date, hours, notes, current_phase))
    conn.commit()
    conn.close()
    flash(f"Logged {hours} hours!", "success")
    return redirect(url_for("dashboard"))


@app.route("/complete-metric", methods=["POST"])
def complete_metric():
    phase_index = int(request.form.get("phase_index", 0))
    metric_text = request.form.get("metric_text", "")
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO completed_metrics (phase_index, metric_text, completed_date) VALUES (?, ?, ?)",
        (phase_index, metric_text, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/uncomplete-metric", methods=["POST"])
def uncomplete_metric():
    phase_index = int(request.form.get("phase_index", 0))
    metric_text = request.form.get("metric_text", "")
    conn = get_db()
    conn.execute("DELETE FROM completed_metrics WHERE phase_index = ? AND metric_text = ?", (phase_index, metric_text))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/next-week", methods=["POST"])
def next_week():
    curriculum = load_curriculum()
    current_phase = int(get_config("current_phase") or 0)
    current_week = int(get_config("current_week") or 1)
    if current_phase >= len(curriculum["phases"]):
        return redirect(url_for("dashboard"))
    phase = curriculum["phases"][current_phase]
    if current_week < phase["weeks"]:
        set_config("current_week", current_week + 1)
    elif current_phase + 1 < len(curriculum["phases"]):
        set_config("current_phase", current_phase + 1)
        set_config("current_week", 1)
    return redirect(url_for("dashboard"))


@app.route("/prev-week", methods=["POST"])
def prev_week():
    curriculum = load_curriculum()
    current_phase = int(get_config("current_phase") or 0)
    current_week = int(get_config("current_week") or 1)
    if current_week > 1:
        set_config("current_week", current_week - 1)
    elif current_phase > 0:
        set_config("current_phase", current_phase - 1)
        set_config("current_week", curriculum["phases"][current_phase - 1]["weeks"])
    return redirect(url_for("dashboard"))


@app.route("/jump-to-phase/<int:phase_index>", methods=["POST"])
def jump_to_phase(phase_index):
    curriculum = load_curriculum()
    if 0 <= phase_index < len(curriculum["phases"]):
        set_config("current_phase", phase_index)
        set_config("current_week", 1)
    return redirect(url_for("dashboard"))


@app.route("/add-resource", methods=["POST"])
def add_resource():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    resource_type = request.form.get("resource_type", "link")
    notes = request.form.get("notes", "").strip()
    topic = request.form.get("topic", "").strip()
    phase_index = request.form.get("phase_index", "")
    week_str = request.form.get("week", "").strip()
    day_str = request.form.get("day", "").strip()
    if not title:
        flash("Title required", "error")
        return redirect(request.referrer or url_for("dashboard"))
    phase_idx = int(phase_index) if phase_index.isdigit() else None
    week_val = int(week_str) if week_str.isdigit() else None
    day_val = int(day_str) if day_str.isdigit() else None
    conn = get_db()
    conn.execute("INSERT INTO resources (phase_index, week, day, title, topic, url, resource_type, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user')",
        (phase_idx, week_val, day_val, title, topic or None, url or None, resource_type, notes or None))
    conn.commit()
    conn.close()
    flash(f"Added: {title}", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-resource/<int:resource_id>", methods=["POST"])
def toggle_resource(resource_id):
    conn = get_db()
    # Get current state and resource details
    resource = conn.execute("SELECT phase_index, week, day, is_completed FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not resource:
        conn.close()
        return redirect(request.referrer or url_for("dashboard"))
    
    phase_index = resource["phase_index"]
    week = resource["week"]
    day = resource["day"]
    was_completed = resource["is_completed"]
    
    # Toggle the resource
    conn.execute("UPDATE resources SET is_completed = NOT is_completed WHERE id = ?", (resource_id,))
    
    # If this is Day 6 (BUILD DAY), link to metrics
    if day == 6 and phase_index is not None and week is not None:
        curriculum = load_curriculum()
        if phase_index < len(curriculum["phases"]):
            phase = curriculum["phases"][phase_index]
            metrics = phase.get("metrics", [])
            # Map week to metric index: Week 1 → metrics[0], Week 2 → metrics[1], etc.
            metric_index = week - 1  # week is 1-indexed, metrics are 0-indexed
            if 0 <= metric_index < len(metrics):
                metric_text = metrics[metric_index]
                now_completed = not was_completed
                
                if now_completed:
                    # Auto-complete the metric
                    conn.execute(
                        "INSERT OR IGNORE INTO completed_metrics (phase_index, metric_text, completed_date) VALUES (?, ?, ?)",
                        (phase_index, metric_text, datetime.now().strftime("%Y-%m-%d"))
                    )
                else:
                    # Auto-delete the metric
                    conn.execute(
                        "DELETE FROM completed_metrics WHERE phase_index = ? AND metric_text = ?",
                        (phase_index, metric_text)
                    )
    
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-favorite/<int:resource_id>", methods=["POST"])
def toggle_favorite(resource_id):
    conn = get_db()
    conn.execute("UPDATE resources SET is_favorite = NOT is_favorite WHERE id = ?", (resource_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    conn = get_db()
    conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-log/<date>", methods=["POST"])
def delete_log(date):
    conn = get_db()
    conn.execute("DELETE FROM time_logs WHERE date = ?", (date,))
    conn.commit()
    conn.close()
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
    conn.close()
    flash(f"Tag '{name}' created", "success")
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/delete-tag/<int:tag_id>", methods=["POST"])
def delete_tag(tag_id):
    conn = get_db()
    conn.execute("DELETE FROM resource_tags WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/export")
def export_data():
    conn = get_db()
    config = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM config").fetchall()}
    time_logs = [dict(r) for r in conn.execute("SELECT date, hours, notes, phase_index FROM time_logs ORDER BY date").fetchall()]
    metrics = [dict(r) for r in conn.execute("SELECT phase_index, metric_text, completed_date FROM completed_metrics").fetchall()]
    resources = [dict(r) for r in conn.execute("SELECT phase_index, week, day, title, topic, url, resource_type, notes, is_completed, is_favorite, source FROM resources").fetchall()]
    tags = [dict(r) for r in conn.execute("SELECT name, color FROM tags").fetchall()]
    conn.close()
    data = {"exported_at": datetime.now().isoformat(), "config": config, "time_logs": time_logs,
            "completed_metrics": metrics, "resources": resources, "tags": tags}
    return Response(json.dumps(data, indent=2), mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=curriculum_export.json"})


@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    conn.execute("DELETE FROM config")
    conn.execute("DELETE FROM time_logs")
    conn.execute("DELETE FROM completed_metrics")
    conn.execute("UPDATE resources SET is_completed = 0")
    conn.execute("UPDATE resources SET is_favorite = 0")
    conn.commit()
    conn.close()
    init_if_needed()
    flash("Progress reset!", "info")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    print("\n🎓 Curriculum Tracker")
    print("=" * 40)
    print("Initializing database...")
    init_db()
    print("✓ Database ready!")
    print("\nOpen: http://localhost:5000")
    print("Ctrl+C to stop\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
