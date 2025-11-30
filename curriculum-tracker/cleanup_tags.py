#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

KEEP_TAGS = [
    "Course",
    "Docs",
    "Article",
    "Video",
    "Project",
    "Lab",
    "Tutorial",
    "Action",
    "Note",
    "Deliverable",
]

def cleanup_tags():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Get all tags
        all_tags = conn.execute("SELECT id, name FROM tags").fetchall()
        
        tags_to_delete = []
        for tag in all_tags:
            if tag["name"] not in KEEP_TAGS:
                tags_to_delete.append(tag["id"])
                print(f"  Will delete tag: {tag['name']}")
        
        if tags_to_delete:
            # Delete resource_tags entries first (to avoid foreign key issues)
            placeholders = ",".join("?" * len(tags_to_delete))
            conn.execute(f"DELETE FROM resource_tags WHERE tag_id IN ({placeholders})", tags_to_delete)
            
            # Delete tags
            conn.execute(f"DELETE FROM tags WHERE id IN ({placeholders})", tags_to_delete)
            
            conn.commit()
            print(f"\n✓ Deleted {len(tags_to_delete)} junk tags")
        else:
            print("✓ No junk tags found")
        
        # Show remaining tags
        remaining = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
        print(f"\n✓ Remaining tags ({len(remaining)}): {[t['name'] for t in remaining]}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Cleaning up junk tags...\n")
    cleanup_tags()

