#!/usr/bin/env python3
import csv
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"
CSV_PATH = Path(__file__).parent / "curriculum_data.csv"

TYPE_MAP = {
    "course": "course",
    "course (free)": "course",
    "docs": "docs",
    "project": "project",
    "article": "article",
    "video": "video",
    "tutorial": "docs",
    "lab": "course",
    "action": "note",
    "deliverable": "project",
    "review": "note",
}

def normalize_type(raw: str) -> str:
    if not raw:
        return "note"
    raw = raw.strip().lower()
    # Mixed types like "Docs/Course" -> take first token
    first = re.split(r"[\\/|,]", raw)[0].strip()
    return TYPE_MAP.get(first, "note")

def week_to_phase_and_rel(week_label: str):
    # week_label like 'W1', 'W10'
    m = re.match(r"w(\d+)", week_label.strip().lower())
    if not m:
        return None, None
    w = int(m.group(1))
    if 1 <= w <= 4:
        return 0, w
    if 5 <= w <= 8:
        return 1, w - 4
    if 9 <= w <= 12:
        return 2, w - 8
    if 13 <= w <= 17:
        return 3, w - 12
    return None, None

def upsert_resource(conn, phase_index, week, day, title, url, resource_type, notes):
    # Idempotency by (phase_index, week, day)
    existing = conn.execute(
        "SELECT id FROM resources WHERE phase_index = ? AND week = ? AND day = ?",
        (phase_index, week, day),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE resources SET title = ?, url = ?, resource_type = ?, notes = ? WHERE id = ?",
            (title, url or None, resource_type, notes or None, existing[0]),
        )
    else:
        conn.execute(
            "INSERT INTO resources (phase_index, week, day, title, url, resource_type, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (phase_index, week, day, title, url or None, resource_type, notes or None),
        )

def import_csv():
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        for r in rows:
            focus = (r.get("Focus") or "").strip()
            week_label = (r.get("Week") or "").strip()
            day_str = (r.get("Day") or "").strip()
            res_link = (r.get("Resource Link") or "").strip()
            res_type_raw = (r.get("Resource Type") or "").strip()
            spec = (r.get("Specific Tasks / Context") or "").strip()
            why = (r.get("Why this resource?") or "").strip()
            rec = (r.get("Recommended Resource") or "").strip()

            if not focus or not week_label or not day_str:
                # skip incomplete rows
                continue

            phase_index, rel_week = week_to_phase_and_rel(week_label)
            try:
                day = int(day_str)
            except ValueError:
                continue
            if phase_index is None or rel_week is None or not (1 <= day <= 6):
                continue

            title = focus
            url = res_link
            resource_type = normalize_type(res_type_raw)
            notes = " | ".join(
                [s for s in [spec, why, ("Resource: " + rec if rec else "")] if s]
            )

            upsert_resource(conn, phase_index, rel_week, day, title, url, resource_type, notes)
        conn.commit()
        print(f"Imported {len(rows)} rows from {CSV_PATH.name} (skipped invalid).")
    finally:
        conn.close()

if __name__ == "__main__":
    import_csv()
