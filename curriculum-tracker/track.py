#!/usr/bin/env python3
"""
Curriculum Tracker CLI - Track your learning progress through a structured curriculum.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from difflib import SequenceMatcher

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich import box

# === Configuration ===
APP_DIR = Path.home() / ".curriculum-tracker"
DB_PATH = APP_DIR / "progress.db"
# Look for curriculum.yaml in current dir, then app dir, then package dir
CURRICULUM_SEARCH_PATHS = [
    Path.cwd() / "curriculum.yaml",
    APP_DIR / "curriculum.yaml",
    Path(__file__).parent / "curriculum.yaml",
]

console = Console()


# === Database Functions ===
def get_db():
    """Get database connection, creating tables if needed."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY,
            date TEXT,
            hours REAL
        );
        CREATE TABLE IF NOT EXISTS completed_metrics (
            id INTEGER PRIMARY KEY,
            phase_index INTEGER,
            metric_text TEXT,
            completed_date TEXT
        );
    """)
    conn.commit()
    return conn


def get_config(conn, key, default=None):
    """Get a config value."""
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_config(conn, key, value):
    """Set a config value."""
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()


def init_if_needed(conn):
    """Initialize config on first run."""
    if get_config(conn, "start_date") is None:
        today = datetime.now().strftime("%Y-%m-%d")
        set_config(conn, "start_date", today)
        set_config(conn, "current_phase", "0")
        set_config(conn, "current_week", "1")
        console.print("[green]✓ Initialized tracker![/green] Start date set to today.")


# === Curriculum Functions ===
def find_curriculum_path():
    """Find curriculum.yaml in search paths."""
    for path in CURRICULUM_SEARCH_PATHS:
        if path.exists():
            return path
    return None


def load_curriculum():
    """Load curriculum from YAML file."""
    path = find_curriculum_path()
    if not path:
        console.print("[red]Error:[/red] curriculum.yaml not found!")
        console.print("Searched in:")
        for p in CURRICULUM_SEARCH_PATHS:
            console.print(f"  - {p}")
        raise SystemExit(1)
    
    with open(path) as f:
        return yaml.safe_load(f), path


def save_curriculum(data, path):
    """Save curriculum to YAML file."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# === Helper Functions ===
def get_week_dates(date_str):
    """Get start and end of the week containing the given date."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fuzzy_match(query, candidates):
    """Find best fuzzy match for query in candidates."""
    best_match = None
    best_ratio = 0
    for i, candidate in enumerate(candidates):
        ratio = SequenceMatcher(None, query.lower(), candidate.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = (i, candidate)
    return best_match if best_ratio > 0.4 else None


def calculate_total_weeks(curriculum):
    """Calculate total weeks in curriculum."""
    return sum(p["weeks"] for p in curriculum["phases"])


def calculate_total_hours(curriculum):
    """Calculate total hours in curriculum."""
    return sum(p["hours"] for p in curriculum["phases"])


def get_hours_for_phase(conn, phase_index, curriculum):
    """Get total hours logged during a phase's weeks."""
    # Calculate which weeks belong to this phase
    weeks_before = sum(p["weeks"] for p in curriculum["phases"][:phase_index])
    phase_weeks = curriculum["phases"][phase_index]["weeks"]
    
    start_date = get_config(conn, "start_date")
    if not start_date:
        return 0
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    phase_start = start + timedelta(weeks=weeks_before)
    phase_end = phase_start + timedelta(weeks=phase_weeks)
    
    result = conn.execute(
        "SELECT SUM(hours) as total FROM time_logs WHERE date >= ? AND date < ?",
        (phase_start.strftime("%Y-%m-%d"), phase_end.strftime("%Y-%m-%d"))
    ).fetchone()
    return result["total"] or 0


def get_current_week_hours(conn):
    """Get hours logged in the current week."""
    today = datetime.now().strftime("%Y-%m-%d")
    week_start, week_end = get_week_dates(today)
    result = conn.execute(
        "SELECT SUM(hours) as total FROM time_logs WHERE date >= ? AND date <= ?",
        (week_start, week_end)
    ).fetchone()
    return result["total"] or 0


def get_total_hours(conn):
    """Get total hours logged."""
    result = conn.execute("SELECT SUM(hours) as total FROM time_logs").fetchone()
    return result["total"] or 0


def get_completed_metrics(conn, phase_index=None):
    """Get completed metrics, optionally filtered by phase."""
    if phase_index is not None:
        return conn.execute(
            "SELECT * FROM completed_metrics WHERE phase_index = ?", (phase_index,)
        ).fetchall()
    return conn.execute("SELECT * FROM completed_metrics").fetchall()


# === CLI Commands ===
@click.group()
@click.pass_context
def cli(ctx):
    """Curriculum Tracker - Track your learning progress through a structured curriculum."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = get_db()
    init_if_needed(ctx.obj["db"])


# --- Curriculum Commands ---
@cli.group()
def curriculum():
    """Manage curriculum phases and metrics."""
    pass


@curriculum.command("show")
@click.pass_context
def curriculum_show(ctx):
    """Display the full curriculum with phases, weeks, hours, and metrics."""
    data, path = load_curriculum()
    
    console.print(Panel(f"[bold]Curriculum[/bold] (from {path})", style="blue"))
    
    for i, phase in enumerate(data["phases"]):
        table = Table(
            title=f"[bold cyan]Phase {i}: {phase['name']}[/bold cyan]",
            box=box.ROUNDED,
            show_header=False,
            title_justify="left"
        )
        table.add_column("Property", style="dim")
        table.add_column("Value")
        
        table.add_row("Weeks", str(phase["weeks"]))
        table.add_row("Hours", str(phase["hours"]))
        table.add_row("", "")
        table.add_row("[bold]Metrics[/bold]", "")
        
        for j, metric in enumerate(phase.get("metrics", [])):
            table.add_row(f"  [{j}]", metric)
        
        console.print(table)
        console.print()


@curriculum.command("add-phase")
@click.argument("name")
@click.option("--weeks", required=True, type=int, help="Number of weeks for this phase")
@click.option("--hours", required=True, type=int, help="Target hours for this phase")
@click.pass_context
def curriculum_add_phase(ctx, name, weeks, hours):
    """Add a new phase to the curriculum."""
    data, path = load_curriculum()
    
    new_phase = {
        "name": name,
        "weeks": weeks,
        "hours": hours,
        "metrics": []
    }
    data["phases"].append(new_phase)
    save_curriculum(data, path)
    
    console.print(f"[green]✓ Added phase {len(data['phases']) - 1}: {name}[/green]")


@curriculum.command("add-metric")
@click.argument("phase_index", type=int)
@click.argument("metric_text")
@click.pass_context
def curriculum_add_metric(ctx, phase_index, metric_text):
    """Add a metric to a phase."""
    data, path = load_curriculum()
    
    if phase_index < 0 or phase_index >= len(data["phases"]):
        console.print(f"[red]Error:[/red] Invalid phase index {phase_index}. Valid range: 0-{len(data['phases'])-1}")
        raise SystemExit(1)
    
    data["phases"][phase_index]["metrics"].append(metric_text)
    save_curriculum(data, path)
    
    phase_name = data["phases"][phase_index]["name"]
    console.print(f"[green]✓ Added metric to {phase_name}[/green]")


@curriculum.command("edit-phase")
@click.argument("phase_index", type=int)
@click.option("--name", help="New name for the phase")
@click.option("--weeks", type=int, help="New number of weeks")
@click.option("--hours", type=int, help="New target hours")
@click.pass_context
def curriculum_edit_phase(ctx, phase_index, name, weeks, hours):
    """Edit a phase's properties."""
    data, path = load_curriculum()
    
    if phase_index < 0 or phase_index >= len(data["phases"]):
        console.print(f"[red]Error:[/red] Invalid phase index {phase_index}. Valid range: 0-{len(data['phases'])-1}")
        raise SystemExit(1)
    
    phase = data["phases"][phase_index]
    if name:
        phase["name"] = name
    if weeks:
        phase["weeks"] = weeks
    if hours:
        phase["hours"] = hours
    
    save_curriculum(data, path)
    console.print(f"[green]✓ Updated phase {phase_index}[/green]")


@curriculum.command("remove-metric")
@click.argument("phase_index", type=int)
@click.argument("metric_index", type=int)
@click.pass_context
def curriculum_remove_metric(ctx, phase_index, metric_index):
    """Remove a metric from a phase."""
    data, path = load_curriculum()
    
    if phase_index < 0 or phase_index >= len(data["phases"]):
        console.print(f"[red]Error:[/red] Invalid phase index {phase_index}")
        raise SystemExit(1)
    
    metrics = data["phases"][phase_index].get("metrics", [])
    if metric_index < 0 or metric_index >= len(metrics):
        console.print(f"[red]Error:[/red] Invalid metric index {metric_index}")
        raise SystemExit(1)
    
    removed = metrics.pop(metric_index)
    save_curriculum(data, path)
    console.print(f"[green]✓ Removed metric:[/green] {removed}")


# --- Progress Commands ---
@cli.command("log")
@click.argument("hours", type=float)
@click.option("--date", "log_date", default=None, help="Date to log hours for (YYYY-MM-DD)")
@click.pass_context
def log_hours(ctx, hours, log_date):
    """Log hours for today or a specific date."""
    conn = ctx.obj["db"]
    
    if log_date is None:
        log_date = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(log_date, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Error:[/red] Invalid date format. Use YYYY-MM-DD")
            raise SystemExit(1)
    
    # Check if entry exists for this date
    existing = conn.execute("SELECT id, hours FROM time_logs WHERE date = ?", (log_date,)).fetchone()
    
    if existing:
        new_total = existing["hours"] + hours
        conn.execute("UPDATE time_logs SET hours = ? WHERE id = ?", (new_total, existing["id"]))
        conn.commit()
        console.print(f"[green]✓ Updated {log_date}:[/green] {existing['hours']} → {new_total} hours")
    else:
        conn.execute("INSERT INTO time_logs (date, hours) VALUES (?, ?)", (log_date, hours))
        conn.commit()
        console.print(f"[green]✓ Logged {hours} hours for {log_date}[/green]")


@cli.command("status")
@click.pass_context
def status(ctx):
    """Show current progress status."""
    conn = ctx.obj["db"]
    curriculum_data, _ = load_curriculum()
    
    current_phase = int(get_config(conn, "current_phase", 0))
    current_week = int(get_config(conn, "current_week", 1))
    
    if current_phase >= len(curriculum_data["phases"]):
        console.print("[bold green]🎉 Congratulations! You've completed the curriculum![/bold green]")
        return
    
    phase = curriculum_data["phases"][current_phase]
    
    # Calculate stats
    week_hours = get_current_week_hours(conn)
    total_hours = get_total_hours(conn)
    curriculum_total = calculate_total_hours(curriculum_data)
    expected_weekly = phase["hours"] / phase["weeks"]
    
    # Get completed metrics for current phase
    completed = get_completed_metrics(conn, current_phase)
    completed_texts = {m["metric_text"] for m in completed}
    
    # Calculate overall progress
    total_weeks = calculate_total_weeks(curriculum_data)
    weeks_before = sum(p["weeks"] for p in curriculum_data["phases"][:current_phase])
    current_absolute_week = weeks_before + current_week
    week_progress = (current_absolute_week / total_weeks) * 100
    hour_progress = (total_hours / curriculum_total) * 100 if curriculum_total > 0 else 0
    
    # Display
    console.print(Panel(
        f"[bold]{phase['name']}[/bold]\n"
        f"Week {current_week} of {phase['weeks']}",
        title="📚 Current Phase",
        style="cyan"
    ))
    
    # Hours table
    hours_table = Table(box=box.SIMPLE)
    hours_table.add_column("Metric", style="dim")
    hours_table.add_column("Value", justify="right")
    
    week_status = "🟢" if week_hours >= expected_weekly else "🟡" if week_hours >= expected_weekly * 0.5 else "🔴"
    hours_table.add_row("This week", f"{week_hours:.1f} / {expected_weekly:.1f} hrs {week_status}")
    hours_table.add_row("Phase total", f"{get_hours_for_phase(conn, current_phase, curriculum_data):.1f} / {phase['hours']} hrs")
    hours_table.add_row("Overall", f"{total_hours:.1f} / {curriculum_total} hrs")
    
    console.print(hours_table)
    
    # Progress bar
    console.print()
    with Progress(
        TextColumn("[bold blue]Overall Progress"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("progress", total=100)
        progress.update(task, completed=hour_progress)
    
    # Metrics
    console.print()
    console.print("[bold]Success Metrics:[/bold]")
    for metric in phase.get("metrics", []):
        if metric in completed_texts:
            console.print(f"  [green]✓[/green] {metric}")
        else:
            console.print(f"  [dim]○[/dim] {metric}")


@cli.command("done")
@click.argument("metric_text")
@click.pass_context
def mark_done(ctx, metric_text):
    """Mark a metric as complete (uses fuzzy matching)."""
    conn = ctx.obj["db"]
    curriculum_data, _ = load_curriculum()
    
    current_phase = int(get_config(conn, "current_phase", 0))
    
    if current_phase >= len(curriculum_data["phases"]):
        console.print("[red]Error:[/red] No active phase")
        raise SystemExit(1)
    
    phase = curriculum_data["phases"][current_phase]
    metrics = phase.get("metrics", [])
    
    # Try fuzzy match
    match = fuzzy_match(metric_text, metrics)
    if not match:
        console.print(f"[red]Error:[/red] No matching metric found for '{metric_text}'")
        console.print("Available metrics:")
        for i, m in enumerate(metrics):
            console.print(f"  [{i}] {m}")
        raise SystemExit(1)
    
    metric_index, matched_text = match
    
    # Check if already completed
    existing = conn.execute(
        "SELECT id FROM completed_metrics WHERE phase_index = ? AND metric_text = ?",
        (current_phase, matched_text)
    ).fetchone()
    
    if existing:
        console.print(f"[yellow]Already completed:[/yellow] {matched_text}")
        return
    
    # Mark complete
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO completed_metrics (phase_index, metric_text, completed_date) VALUES (?, ?, ?)",
        (current_phase, matched_text, today)
    )
    conn.commit()
    
    console.print(f"[green]✓ Completed:[/green] {matched_text}")


@cli.command("next")
@click.pass_context
def next_week(ctx):
    """Advance to the next week (or next phase if current phase is complete)."""
    conn = ctx.obj["db"]
    curriculum_data, _ = load_curriculum()
    
    current_phase = int(get_config(conn, "current_phase", 0))
    current_week = int(get_config(conn, "current_week", 1))
    
    if current_phase >= len(curriculum_data["phases"]):
        console.print("[bold green]🎉 You've already completed the curriculum![/bold green]")
        return
    
    phase = curriculum_data["phases"][current_phase]
    
    if current_week < phase["weeks"]:
        # Advance week
        set_config(conn, "current_week", current_week + 1)
        console.print(f"[green]✓ Advanced to week {current_week + 1} of {phase['name']}[/green]")
    else:
        # Advance phase
        if current_phase + 1 < len(curriculum_data["phases"]):
            set_config(conn, "current_phase", current_phase + 1)
            set_config(conn, "current_week", 1)
            next_phase = curriculum_data["phases"][current_phase + 1]
            console.print(f"[green]✓ Advanced to {next_phase['name']}![/green]")
        else:
            set_config(conn, "current_phase", current_phase + 1)
            console.print("[bold green]🎉 Congratulations! You've completed the curriculum![/bold green]")


@cli.command("summary")
@click.pass_context
def summary(ctx):
    """Show summary of all phases and overall progress."""
    conn = ctx.obj["db"]
    curriculum_data, _ = load_curriculum()
    
    current_phase = int(get_config(conn, "current_phase", 0))
    current_week = int(get_config(conn, "current_week", 1))
    start_date = get_config(conn, "start_date")
    
    # Phase table
    table = Table(title="📊 Curriculum Summary", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Phase", style="bold")
    table.add_column("Weeks", justify="center")
    table.add_column("Hours", justify="right")
    table.add_column("Logged", justify="right")
    table.add_column("Status", justify="center")
    
    total_expected = 0
    total_logged = 0
    
    for i, phase in enumerate(curriculum_data["phases"]):
        logged = get_hours_for_phase(conn, i, curriculum_data)
        total_expected += phase["hours"]
        total_logged += logged
        
        if i < current_phase:
            status = "[green]✓ Done[/green]"
        elif i == current_phase:
            status = f"[cyan]→ Week {current_week}[/cyan]"
        else:
            status = "[dim]Pending[/dim]"
        
        table.add_row(
            str(i),
            phase["name"],
            str(phase["weeks"]),
            f"{phase['hours']}h",
            f"{logged:.1f}h",
            status
        )
    
    table.add_row("", "[bold]Total[/bold]", "", f"[bold]{total_expected}h[/bold]", f"[bold]{total_logged:.1f}h[/bold]", "")
    
    console.print(table)
    
    # Completed metrics
    all_completed = get_completed_metrics(conn)
    if all_completed:
        console.print()
        console.print("[bold]✓ Completed Metrics:[/bold]")
        for m in all_completed:
            phase_name = curriculum_data["phases"][m["phase_index"]]["name"] if m["phase_index"] < len(curriculum_data["phases"]) else "Unknown"
            console.print(f"  [green]✓[/green] {m['metric_text']} [dim]({phase_name})[/dim]")
    
    # On-track status
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        weeks_elapsed = (datetime.now() - start).days // 7 + 1
        weeks_before = sum(p["weeks"] for p in curriculum_data["phases"][:current_phase])
        current_absolute_week = weeks_before + current_week
        
        console.print()
        if current_absolute_week >= weeks_elapsed:
            console.print(f"[green]✓ On track![/green] Week {current_absolute_week} (elapsed: {weeks_elapsed})")
        else:
            behind = weeks_elapsed - current_absolute_week
            console.print(f"[yellow]⚠ Behind by {behind} week(s)[/yellow] (Current: week {current_absolute_week}, Elapsed: {weeks_elapsed})")


@cli.command("reset")
@click.confirmation_option(prompt="This will clear all progress data. Continue?")
@click.pass_context
def reset(ctx):
    """Reset all progress data (keeps curriculum)."""
    conn = ctx.obj["db"]
    
    conn.executescript("""
        DELETE FROM config;
        DELETE FROM time_logs;
        DELETE FROM completed_metrics;
    """)
    conn.commit()
    
    init_if_needed(conn)
    console.print("[green]✓ Progress reset![/green]")


def main():
    cli()


if __name__ == "__main__":
    main()
