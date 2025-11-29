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
        CREATE TABLE IF NOT EXISTS time_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, hours REAL NOT NULL, notes TEXT);
        CREATE TABLE IF NOT EXISTS completed_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER NOT NULL, metric_text TEXT NOT NULL, completed_date TEXT NOT NULL, UNIQUE(phase_index, metric_text));
        CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, phase_index INTEGER, title TEXT NOT NULL, url TEXT, resource_type TEXT DEFAULT 'link', notes TEXT, is_completed INTEGER DEFAULT 0, is_favorite INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
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
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:phase_index])
    phase_weeks = curriculum["phases"][phase_index]["weeks"]
    start_date = get_config("start_date")
    if not start_date:
        return 0
    start = datetime.strptime(start_date, "%Y-%m-%d")
    phase_start = start + timedelta(weeks=weeks_before)
    phase_end = phase_start + timedelta(weeks=phase_weeks)
    conn = get_db()
    cur = conn.execute("SELECT COALESCE(SUM(hours), 0) as total FROM time_logs WHERE date >= ? AND date < ?", (phase_start.strftime("%Y-%m-%d"), phase_end.strftime("%Y-%m-%d")))
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
        cur = conn.execute("SELECT * FROM resources WHERE phase_index = ? OR phase_index IS NULL ORDER BY is_favorite DESC, created_at DESC", (phase_index,))
    else:
        cur = conn.execute("SELECT * FROM resources ORDER BY phase_index, is_favorite DESC, created_at DESC")
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
    all_resources = get_all_resources()
    grouped = {}
    for r in all_resources:
        phase_idx = r["phase_index"]
        if phase_idx is None:
            phase_name = "📌 General Resources"
        elif phase_idx < len(curriculum["phases"]):
            phase_name = curriculum["phases"][phase_idx]["name"]
        else:
            phase_name = f"Phase {phase_idx}"
        if phase_name not in grouped:
            grouped[phase_name] = []
        grouped[phase_name].append(r)
    return render_template("resources.html", grouped_resources=grouped, phases=curriculum["phases"],
        all_tags=get_all_tags(), search_query="", tag_filter=None,
        filter_type="", filter_phase="", filter_tag="", filter_status="")


@app.route("/log", methods=["POST"])
def log_hours():
    hours = float(request.form.get("hours", 0))
    log_date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()
    if hours <= 0:
        return redirect(url_for("dashboard"))
    conn = get_db()
    existing = conn.execute("SELECT id, hours FROM time_logs WHERE date = ?", (log_date,)).fetchone()
    if existing:
        conn.execute("UPDATE time_logs SET hours = ?, notes = ? WHERE id = ?", (existing["hours"] + hours, notes, existing["id"]))
    else:
        conn.execute("INSERT INTO time_logs (date, hours, notes) VALUES (?, ?, ?)", (log_date, hours, notes))
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
    phase_index = request.form.get("phase_index", "")
    if not title:
        flash("Title required", "error")
        return redirect(request.referrer or url_for("dashboard"))
    phase_idx = int(phase_index) if phase_index.isdigit() else None
    conn = get_db()
    conn.execute("INSERT INTO resources (phase_index, title, url, resource_type, notes) VALUES (?, ?, ?, ?, ?)",
        (phase_idx, title, url or None, resource_type, notes or None))
    conn.commit()
    conn.close()
    flash(f"Added: {title}", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/toggle-resource/<int:resource_id>", methods=["POST"])
def toggle_resource(resource_id):
    conn = get_db()
    conn.execute("UPDATE resources SET is_completed = NOT is_completed WHERE id = ?", (resource_id,))
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
    time_logs = [dict(r) for r in conn.execute("SELECT date, hours, notes FROM time_logs ORDER BY date").fetchall()]
    metrics = [dict(r) for r in conn.execute("SELECT phase_index, metric_text, completed_date FROM completed_metrics").fetchall()]
    resources = [dict(r) for r in conn.execute("SELECT phase_index, title, url, resource_type, notes, is_completed, is_favorite FROM resources").fetchall()]
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
