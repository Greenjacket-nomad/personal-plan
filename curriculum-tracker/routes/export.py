#!/usr/bin/env python3
"""
Export routes for Curriculum Tracker.
Handles PDF, CSV, and image exports.
"""

import csv
import io
import json
from datetime import datetime
from flask import Blueprint, Response, jsonify, request, current_app
from flask_login import login_required, current_user
from database import get_db, get_db_cursor
from services.reporting import get_burndown_data
from services.progress import get_progress, get_total_hours, get_hours_for_phase

# Create blueprint
export_bp = Blueprint('export', __name__)


@export_bp.route("/reports/export/csv")
@login_required
def export_csv():
    """Export reports data as CSV."""
    try:
        # Get report data
        progress = get_progress()
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Get hours by phase
        cur.execute("""
            SELECT 
                phase_index,
                SUM(hours) as total_hours
            FROM activity_log
            WHERE user_id = %s AND action LIKE 'hours_logged%'
            GROUP BY phase_index
            ORDER BY phase_index
        """, (current_user.id,))
        phase_hours = cur.fetchall()
        
        # Get resource completions
        cur.execute("""
            SELECT 
                resource_type,
                COUNT(*) as count
            FROM resources
            WHERE user_id = %s AND status = 'complete'
            GROUP BY resource_type
        """, (current_user.id,))
        resource_completions = cur.fetchall()
        
        cur.close()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Report Type', 'Metric', 'Value'])
        writer.writerow(['Generated', 'Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Write phase hours
        writer.writerow(['Phase Hours'])
        writer.writerow(['Phase', 'Total Hours'])
        for row in phase_hours:
            writer.writerow([f"Phase {row['phase_index'] + 1}", row['total_hours']])
        writer.writerow([])
        
        # Write resource completions
        writer.writerow(['Resource Completions'])
        writer.writerow(['Type', 'Count'])
        for row in resource_completions:
            writer.writerow([row['resource_type'], row['count']])
        
        # Create response
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=curriculum-report-{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting CSV: {e}")
        return jsonify({"error": "Failed to export CSV"}), 500


@export_bp.route("/reports/export/pdf")
@login_required
def export_pdf():
    """Export reports as PDF."""
    try:
        # For now, return a simple text response
        # In production, use reportlab or weasyprint for PDF generation
        return jsonify({
            "message": "PDF export coming soon",
            "note": "Install reportlab or weasyprint for PDF generation"
        }), 501
        
    except Exception as e:
        current_app.logger.error(f"Error exporting PDF: {e}")
        return jsonify({"error": "Failed to export PDF"}), 500


@export_bp.route("/reports/export/png")
@login_required
def export_png():
    """Export charts as PNG."""
    try:
        # For now, return a simple response
        # In production, use canvas or server-side rendering
        return jsonify({
            "message": "PNG export coming soon",
            "note": "Use html2canvas or server-side chart rendering for PNG export"
        }), 501
        
    except Exception as e:
        current_app.logger.error(f"Error exporting PNG: {e}")
        return jsonify({"error": "Failed to export PNG"}), 500


@export_bp.route("/journal/export/markdown")
@login_required
def export_journal_markdown():
    """Export journal entries as Markdown."""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        tags = request.args.getlist('tags')
        
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Build query
        query = "SELECT * FROM journal_entries WHERE user_id = %s"
        params = [current_user.id]
        
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        
        query += " ORDER BY date DESC"
        
        cur.execute(query, params)
        entries = cur.fetchall()
        cur.close()
        
        # Generate Markdown
        markdown = f"# Journal Export\n\n"
        markdown += f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        markdown += f"---\n\n"
        
        for entry in entries:
            date_str = entry['date'].strftime('%Y-%m-%d') if hasattr(entry['date'], 'strftime') else str(entry['date'])
            markdown += f"## {date_str}\n\n"
            
            if entry.get('mood'):
                mood_emoji = {
                    'great': '😊',
                    'okay': '😐',
                    'struggling': '😔',
                    'fire': '🔥'
                }.get(entry['mood'], '')
                if mood_emoji:
                    markdown += f"**Mood:** {mood_emoji} {entry['mood'].title()}\n\n"
            
            if entry.get('content'):
                markdown += f"{entry['content']}\n\n"
            
            markdown += "---\n\n"
        
        # Create response
        response = Response(
            markdown,
            mimetype='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename=journal-export-{datetime.now().strftime("%Y%m%d")}.md'
            }
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting journal as Markdown: {e}")
        return jsonify({"error": "Failed to export journal"}), 500


@export_bp.route("/journal/export/json")
@login_required
def export_journal_json():
    """Export journal entries as JSON."""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Build query
        query = "SELECT * FROM journal_entries WHERE user_id = %s"
        params = [current_user.id]
        
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        
        query += " ORDER BY date DESC"
        
        cur.execute(query, params)
        entries = cur.fetchall()
        cur.close()
        
        # Convert to list of dicts
        entries_list = []
        for entry in entries:
            entry_dict = dict(entry)
            # Convert date to string
            if hasattr(entry_dict.get('date'), 'strftime'):
                entry_dict['date'] = entry_dict['date'].strftime('%Y-%m-%d')
            if hasattr(entry_dict.get('created_at'), 'isoformat'):
                entry_dict['created_at'] = entry_dict['created_at'].isoformat()
            if hasattr(entry_dict.get('updated_at'), 'isoformat'):
                entry_dict['updated_at'] = entry_dict['updated_at'].isoformat()
            entries_list.append(entry_dict)
        
        # Create response
        response = Response(
            json.dumps({
                'export_date': datetime.now().isoformat(),
                'entries': entries_list
            }, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=journal-export-{datetime.now().strftime("%Y%m%d")}.json'
            }
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting journal as JSON: {e}")
        return jsonify({"error": "Failed to export journal"}), 500

