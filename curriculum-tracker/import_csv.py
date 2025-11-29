#!/usr/bin/env python3
import csv
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

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

def extract_domain(url):
    """Extract domain from URL and return a normalized tag name."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
        # Remove common TLDs for cleaner names
        domain = re.sub(r'\.(com|org|net|io|ai|edu)$', '', domain, flags=re.IGNORECASE)
        # Capitalize properly
        if domain == 'udemy':
            return 'Udemy'
        elif domain == 'codecademy':
            return 'Codecademy'
        elif domain == 'deeplearning':
            return 'DeepLearning.ai'
        elif domain == 'supabase':
            return 'Supabase'
        elif domain == 'github':
            return 'GitHub'
        elif domain == 'youtube':
            return 'YouTube'
        elif domain == 'mdn':
            return 'MDN'
        else:
            # Capitalize first letter
            return domain.capitalize() if domain else None
    except:
        return None


def get_or_create_tag(conn, name, color):
    """Get or create a tag, return its ID."""
    cur = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
    return cur.lastrowid


def link_tag_to_resource(conn, resource_id, tag_id):
    """Link a tag to a resource if not already linked."""
    cur = conn.execute(
        "SELECT 1 FROM resource_tags WHERE resource_id = ? AND tag_id = ?",
        (resource_id, tag_id)
    )
    if not cur.fetchone():
        conn.execute(
            "INSERT INTO resource_tags (resource_id, tag_id) VALUES (?, ?)",
            (resource_id, tag_id)
        )


TYPE_COLORS = {
    "course": "#3b82f6",
    "docs": "#22c55e",
    "project": "#f97316",
    "article": "#8b5cf6",
    "video": "#ef4444",
    "note": "#6b7280",
    "lab": "#14b8a6",
    "tutorial": "#84cc16",
    "action": "#f59e0b",
}

SOURCE_COLORS = {
    "Udemy": "#a855f7",
    "Codecademy": "#fbbf24",
    "DeepLearning.ai": "#06b6d4",
    "Supabase": "#10b981",
    "GitHub": "#1f2937",
    "YouTube": "#ef4444",
    "MDN": "#22c55e",
}


def upsert_resource(conn, phase_index, week, day, title, topic, url, resource_type, notes):
    # Match on (phase_index, week, day, title) for updates
    # Only update resources where source='curriculum'
    existing = conn.execute(
        "SELECT id, source FROM resources WHERE phase_index = ? AND week = ? AND day = ? AND title = ?",
        (phase_index, week, day, title),
    ).fetchone()
    
    if existing:
        # Only update if source is 'curriculum' (never overwrite user-added resources)
        if existing[1] == 'curriculum':
            conn.execute(
                "UPDATE resources SET url = ?, resource_type = ?, notes = ?, topic = ? WHERE id = ?",
                (url or None, resource_type, notes or None, topic or None, existing[0]),
            )
            resource_id = existing[0]
        else:
            # Skip updating user-added resources
            return existing[0]
    else:
        cur = conn.execute(
            "INSERT INTO resources (phase_index, week, day, title, topic, url, resource_type, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'curriculum')",
            (phase_index, week, day, title, topic or None, url or None, resource_type, notes or None),
        )
        resource_id = cur.lastrowid
    
    # Auto-tag: resource_type tag
    type_tag_name = resource_type.capitalize() if resource_type else "Note"
    type_color = TYPE_COLORS.get(resource_type, "#6b7280")
    type_tag_id = get_or_create_tag(conn, type_tag_name, type_color)
    link_tag_to_resource(conn, resource_id, type_tag_id)
    
    # Auto-tag: source tag from URL domain
    source_name = extract_domain(url)
    if source_name:
        source_color = SOURCE_COLORS.get(source_name, "#6366f1")
        source_tag_id = get_or_create_tag(conn, source_name, source_color)
        link_tag_to_resource(conn, resource_id, source_tag_id)
    
    return resource_id

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

            # title = "Recommended Resource" column (actual course/doc name)
            title = rec if rec else focus  # Fallback to focus if no recommended resource
            # topic = "Focus" column (the topic like "API Authentication")
            topic = focus
            url = res_link
            resource_type = normalize_type(res_type_raw)
            # Notes: "Tasks: {specific_tasks}" and "Why: {why_this_resource}"
            notes_parts = []
            if spec:
                notes_parts.append(f"Tasks: {spec}")
            if why:
                notes_parts.append(f"Why: {why}")
            notes = " | ".join(notes_parts) if notes_parts else None

            upsert_resource(conn, phase_index, rel_week, day, title, topic, url, resource_type, notes)
        conn.commit()
        print(f"Imported {len(rows)} rows from {CSV_PATH.name} (skipped invalid).")
    finally:
        conn.close()

if __name__ == "__main__":
    import_csv()
