"""Gamification — streaks, milestones, and cumulative stats for vanish."""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .utils.safety import bytes_to_human_readable

console = Console()

STATS_FILE = os.path.join(os.path.expanduser("~"), ".vanish", "gamification.json")

MILESTONES = [
    (1 * 1024**3, "Tidy Intern", "Freed 1 GB total"),
    (5 * 1024**3, "Clean Coder", "Freed 5 GB total"),
    (10 * 1024**3, "Disk Whisperer", "Freed 10 GB total"),
    (25 * 1024**3, "Storage Senpai", "Freed 25 GB total"),
    (50 * 1024**3, "Disk Wizard", "Freed 50 GB total"),
    (100 * 1024**3, "Vanishing Legend", "Freed 100 GB total"),
    (500 * 1024**3, "Terabyte Terminator", "Freed 500 GB total"),
]

STREAK_TITLES = [
    (1, "First Sweep"),
    (4, "Monthly Regular"),
    (12, "Quarterly Champion"),
    (26, "Half-Year Hero"),
    (52, "Annual Ace"),
]


def _load_stats() -> Dict[str, Any]:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_bytes_freed": 0,
        "total_runs": 0,
        "streak_weeks": 0,
        "last_run_date": None,
        "milestones_reached": [],
    }


def _save_stats(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def record_run(bytes_freed: int):
    """Record a cleanup run for gamification tracking."""
    data = _load_stats()
    data["total_bytes_freed"] = data.get("total_bytes_freed", 0) + bytes_freed
    data["total_runs"] = data.get("total_runs", 0) + 1

    now = datetime.now()
    last_run = data.get("last_run_date")
    if last_run:
        try:
            last_dt = datetime.fromisoformat(last_run)
            days_since = (now - last_dt).days
            if days_since <= 10:
                data["streak_weeks"] = data.get("streak_weeks", 0) + 1
            elif days_since > 14:
                data["streak_weeks"] = 1
        except Exception:
            data["streak_weeks"] = 1
    else:
        data["streak_weeks"] = 1

    data["last_run_date"] = now.isoformat()

    total = data["total_bytes_freed"]
    reached = data.get("milestones_reached", [])
    for threshold, title, desc in MILESTONES:
        if total >= threshold and title not in reached:
            reached.append(title)
            console.print(f"\n[bold yellow]🏆 NEW MILESTONE:[/bold yellow] "
                          f"[bold]{title}[/bold] — {desc} no cap 💀")
    data["milestones_reached"] = reached

    _save_stats(data)


def show_profile():
    """Display the gamification profile."""
    data = _load_stats()
    total = data.get("total_bytes_freed", 0)
    runs = data.get("total_runs", 0)
    streak = data.get("streak_weeks", 0)
    reached = data.get("milestones_reached", [])

    current_title = "Newbie"
    for threshold, title, _ in MILESTONES:
        if total >= threshold:
            current_title = title

    streak_title = "Just Started"
    for weeks, title in STREAK_TITLES:
        if streak >= weeks:
            streak_title = title

    next_milestone = None
    for threshold, title, desc in MILESTONES:
        if total < threshold:
            next_milestone = (threshold, title, desc)
            break

    table = Table(title="vanish Profile", border_style="magenta")
    table.add_column("", style="bold")
    table.add_column("")

    table.add_row("Total reclaimed", bytes_to_human_readable(total))
    table.add_row("Total runs", str(runs))
    table.add_row("Level", f"[bold magenta]{current_title}[/bold magenta]")
    table.add_row("Streak", f"{streak} weeks ({streak_title})")
    table.add_row("Milestones", ", ".join(reached) if reached else "None yet")

    if next_milestone:
        remaining = next_milestone[0] - total
        pct = (total / next_milestone[0]) * 100 if next_milestone[0] > 0 else 100
        table.add_row("Next milestone",
                       f"{next_milestone[1]} ({bytes_to_human_readable(remaining)} to go, {pct:.0f}%)")

    console.print(table)
