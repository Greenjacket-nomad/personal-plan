#!/usr/bin/env python3
"""
Curriculum Tracker - Web Dashboard with PostgreSQL
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/curriculum_tracker")
CURRICULUM_PATH = Path(__file__).parent / "curriculum.yaml"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS time_logs (id SERIAL PRIMARY KEY, date DATE NOT NULL, hours REAL NOT NULL, notes TEXT);
        CREATE TABLE IF NOT EXISTS completed_metrics (id SERIAL PRIMARY KEY, phase_index INTEGER NOT NULL, metric_text TEXT NOT NULL, completed_date DATE NOT NULL, UNIQUE(phase_index, metric_text));
        CREATE TABLE IF NOT EXISTS resources (id SERIAL PRIMARY KEY, phase_index INTEGER, title TEXT NOT NULL, url TEXT, resource_type TEXT DEFAULT 'link', notes TEXT, is_completed BOOLEAN DEFAULT FALSE, is_favorite BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tags (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, color TEXT DEFAULT '#6366f1');
        CREATE TABLE IF NOT EXISTS resource_tags (resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE, tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY (resource_id, tag_id));
    """)
    conn.commit()
    cur.close()
    conn.close()


def get_config(key, default=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["value"] if row else default


def set_config(key, value):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, str(value)))
    conn.commit()
    cur.close()
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
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date >= %s AND date <= %s", (week_start, week_end))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["total"]


def get_total_hours():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["total"]


def get_hours_for_phase(phase_index, curriculum):
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:phase_index])
    phase_weeks = curriculum["phases"][phase_index]["weeks"]
    start_date = get_config("start_date")
    if not start_date:
        return 0
    start = datetime.strptime(start_date, "%Y-%m-%d")
    phase_start = start + timedelta(weeks=weeks_before)
    phase_end = phase_start + timedelta(weeks=phase_weeks)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date >= %s AND date < %s", (phase_start.strftime("%Y-%m-%d"), phase_end.strftime("%Y-%m-%d")))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["total"]


def get_completed_metrics(phase_index=None):
    conn = get_db()
    cur = conn.cursor()
    if phase_index is not None:
        cur.execute("SELECT * FROM completed_metrics WHERE phase_index = %s", (phase_index,))
    else:
        cur.execute("SELECT * FROM completed_metrics")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_recent_logs(days=7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT date, hours, notes FROM time_logs WHERE date >= %s ORDER BY date DESC", (cutoff,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_resources(phase_index=None, search_query=None, tag_id=None):
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT r.*, array_agg(t.name) FILTER (WHERE t.name IS NOT NULL) as tags,
               array_agg(t.color) FILTER (WHERE t.color IS NOT NULL) as tag_colors
        FROM resources r
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE 1=1
    """
    params = []
    if phase_index is not None:
        query += " AND (r.phase_index = %s OR r.phase_index IS NULL)"
        params.append(phase_index)
    if search_query:
        query += " AND (r.title ILIKE %s OR r.notes ILIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if tag_id:
        query += " AND r.id IN (SELECT resource_id FROM resource_tags WHERE tag_id = %s)"
        params.append(tag_id)
    query += " GROUP BY r.id ORDER BY r.is_favorite DESC, r.created_at DESC"
    cur.execute(query, params)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_all_resources():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.*, array_agg(t.name) FILTER (WHERE t.name IS NOT NULL) as tags,
               array_agg(t.color) FILTER (WHERE t.color IS NOT NULL) as tag_colors
        FROM resources r
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        GROUP BY r.id ORDER BY r.phase_index NULLS FIRST, r.is_favorite DESC, r.created_at DESC
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_all_tags():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tags ORDER BY name")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


@app.route("/")
def dashboard():
    init_if_needed()
    curriculum = load_curriculum()
    current_phase = int(get_config("current_phase") or 0)
    current_week = int(get_config("current_week") or 1)
    if current_phase >= len(curriculum["phases"]):
        current_phase = len(curriculum["phases"]) - 1
    phase = curriculum["phases"][current_phase]
    week_hours = get_current_week_hours()
    total_hours = get_total_hours()
    curriculum_total = sum(p["hours"] for p in curriculum["phases"])
    expected_weekly = phase["hours"] / phase["weeks"] if phase["weeks"] > 0 else 0
    completed = get_completed_metrics(current_phase)
    completed_texts = {m["metric_text"] for m in completed}
    total_weeks = sum(p["weeks"] for p in curriculum["phases"])
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:current_phase])
    current_absolute_week = weeks_before + current_week
    overall_progress = (total_hours / curriculum_total * 100) if curriculum_total > 0 else 0
    recent_logs = get_recent_logs()
    resources = get_resources(current_phase)
    all_tags = get_all_tags()
    phases_data = []
    for i, p in enumerate(curriculum["phases"]):
        phase_completed = get_completed_metrics(i)
        phases_data.append({
            "index": i, "name": p["name"], "weeks": p["weeks"], "hours": p["hours"],
            "logged": get_hours_for_phase(i, curriculum), "is_current": i == current_phase,
            "is_complete": i < current_phase, "metrics_done": len(phase_completed),
            "metrics_total": len(p.get("metrics", []))
        })
    return render_template("dashboard.html", phase=phase, phase_index=current_phase, current_week=current_week,
        week_hours=week_hours, expected_weekly=expected_weekly, total_hours=total_hours,
        curriculum_total=curriculum_total, overall_progress=min(overall_progress, 100),
        completed_texts=completed_texts, recent_logs=recent_logs, phases=phases_data,
        resources=resources, all_tags=all_tags, today=datetime.now().strftime("%Y-%m-%d"),
        current_absolute_week=current_absolute_week, total_weeks=total_weeks)


@app.route("/resources")
def resources_page():
    curriculum = load_curriculum()
    search_query = request.args.get("q", "").strip()
    filter_type = request.args.get("type", "").strip()
    filter_phase = request.args.get("phase", "").strip()
    filter_tag = request.args.get("tag", "").strip()
    filter_status = request.args.get("status", "").strip()
    
    # Build query
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT r.*, array_agg(t.name) FILTER (WHERE t.name IS NOT NULL) as tags,
               array_agg(t.color) FILTER (WHERE t.color IS NOT NULL) as tag_colors
        FROM resources r
        LEFT JOIN resource_tags rt ON r.id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE 1=1
    """
    params = []
    if search_query:
        query += " AND (r.title ILIKE %s OR r.notes ILIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if filter_type:
        query += " AND r.resource_type = %s"
        params.append(filter_type)
    if filter_phase.isdigit():
        query += " AND r.phase_index = %s"
        params.append(int(filter_phase))
    if filter_tag:
        query += " AND r.id IN (SELECT resource_id FROM resource_tags rt2 JOIN tags t2 ON rt2.tag_id = t2.id WHERE t2.name = %s)"
        params.append(filter_tag)
    if filter_status == "completed":
        query += " AND r.is_completed = TRUE"
    elif filter_status == "pending":
        query += " AND r.is_completed = FALSE"
    elif filter_status == "favorites":
        query += " AND r.is_favorite = TRUE"
    query += " GROUP BY r.id ORDER BY r.is_favorite DESC, r.created_at DESC"
    cur.execute(query, params)
    resources = cur.fetchall()
    cur.close()
    conn.close()
    
    phases_data = [{"index": i, "name": p["name"]} for i, p in enumerate(curriculum["phases"])]
    return render_template("resources.html", resources=resources, phases=phases_data,
        all_tags=get_all_tags(), search_query=search_query, filter_type=filter_type,
        filter_phase=filter_phase, filter_tag=filter_tag, filter_status=filter_status)


@app.route("/log", methods=["POST"])
def log_hours():
    hours = float(request.form.get("hours", 0))
    log_date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()
    if hours <= 0:
        return redirect(url_for("dashboard"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, hours FROM time_logs WHERE date = %s", (log_date,))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE time_logs SET hours = %s, notes = %s WHERE id = %s", (existing["hours"] + hours, notes, existing["id"]))
    else:
        cur.execute("INSERT INTO time_logs (date, hours, notes) VALUES (%s, %s, %s)", (log_date, hours, notes))
    conn.commit()
    cur.close()
    conn.close()
    flash(f"Logged {hours} hours!", "success")
    return redirect(url_for("dashboard"))


@app.route("/complete-metric", methods=["POST"])
def complete_metric():
    phase_index = int(request.form.get("phase_index", 0))
    metric_text = request.form.get("metric_text", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO completed_metrics (phase_index, metric_text, completed_date) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (phase_index, metric_text, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/uncomplete-metric", methods=["POST"])
def uncomplete_metric():
    phase_index = int(request.form.get("phase_index", 0))
    metric_text = request.form.get("metric_text", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM completed_metrics WHERE phase_index = %s AND metric_text = %s", (phase_index, metric_text))
    conn.commit()
    cur.close()
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
    phase_index = request.form.get("phase_index", "")
    tags = request.form.getlist("tags")
    if not title:
        flash("Title required", "error")
        return redirect(request.referrer or url_for("dashboard"))
    phase_idx = int(phase_index) if phase_index.isdigit() else None
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO resources (phase_index, title, url, resource_type, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (phase_idx, title, url or None, resource_type, notes or None))
    resource_id = cur.fetchone()["id"]
    for tag_id in tags:
        cur.execute("INSERT INTO resource_tags (resource_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (resource_id, int(tag_id)))
    conn.commit()
    cur.close()
    conn.close()
    flash(f"Added: {title}", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-resource/<int:resource_id>", methods=["POST"])
def toggle_resource(resource_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE resources SET is_completed = NOT is_completed WHERE id = %s", (resource_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-favorite/<int:resource_id>", methods=["POST"])
def toggle_favorite(resource_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE resources SET is_favorite = NOT is_favorite WHERE id = %s", (resource_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete-log/<date>", methods=["POST"])
def delete_log(date):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM time_logs WHERE date = %s", (date,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/add-tag", methods=["POST"])
def add_tag():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#6366f1")
    if not name:
        return redirect(request.referrer or url_for("resources_page"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO tags (name, color) VALUES (%s, %s) ON CONFLICT DO NOTHING", (name, color))
    conn.commit()
    cur.close()
    conn.close()
    flash(f"Tag '{name}' created", "success")
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/delete-tag/<int:tag_id>", methods=["POST"])
def delete_tag(tag_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/add-tag-to-resource/<int:resource_id>", methods=["POST"])
def add_tag_to_resource(resource_id):
    tag_id = request.form.get("tag_id")
    if tag_id:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO resource_tags (resource_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (resource_id, int(tag_id)))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(request.referrer or url_for("resources_page"))


@app.route("/export")
def export_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM config")
    config = {r["key"]: r["value"] for r in cur.fetchall()}
    cur.execute("SELECT date::text, hours, notes FROM time_logs ORDER BY date")
    time_logs = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT phase_index, metric_text, completed_date::text FROM completed_metrics")
    metrics = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT phase_index, title, url, resource_type, notes, is_completed, is_favorite FROM resources")
    resources = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT name, color FROM tags")
    tags = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    data = {"exported_at": datetime.now().isoformat(), "config": config, "time_logs": time_logs,
            "completed_metrics": metrics, "resources": resources, "tags": tags}
    return Response(json.dumps(data, indent=2), mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=curriculum_export.json"})


@app.route("/import", methods=["POST"])
def import_data():
    if "file" not in request.files:
        flash("No file", "error")
        return redirect(url_for("resources_page"))
    file = request.files["file"]
    try:
        data = json.load(file)
    except:
        flash("Invalid JSON", "error")
        return redirect(url_for("resources_page"))
    conn = get_db()
    cur = conn.cursor()
    for tag in data.get("tags", []):
        cur.execute("INSERT INTO tags (name, color) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tag["name"], tag.get("color", "#6366f1")))
    for r in data.get("resources", []):
        cur.execute("INSERT INTO resources (phase_index, title, url, resource_type, notes, is_completed, is_favorite) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (r.get("phase_index"), r["title"], r.get("url"), r.get("resource_type", "link"), r.get("notes"), r.get("is_completed", False), r.get("is_favorite", False)))
    conn.commit()
    cur.close()
    conn.close()
    flash("Imported!", "success")
    return redirect(url_for("resources_page"))


@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM config; DELETE FROM time_logs; DELETE FROM completed_metrics;")
    conn.commit()
    cur.close()
    conn.close()
    init_if_needed()
    flash("Progress reset!", "info")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    print("\n🎓 Curriculum Tracker")
    print("=" * 40)
    print("Initializing database...")
    init_db()
    print("Open: http://localhost:5000")
    print("Ctrl+C to stop\n")
    app.run(debug=True, port=5000)
