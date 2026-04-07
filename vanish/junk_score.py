"""Junk score analysis — show how much of each project is regenerable junk vs source code."""

import os
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table

from .utils.safety import bytes_to_human_readable

console = Console()

TARGET_FOLDERS = {
    "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist", "target", ".tox", ".nox",
    ".next", ".nuxt", ".eggs",
}

PROJECT_INDICATORS = {
    "package.json", "requirements.txt", "setup.py", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "Gemfile", "composer.json", "pubspec.yaml",
}


def _dir_size(path: str) -> int:
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except PermissionError:
        pass
    return total


def find_projects(root: str, max_depth: int = 3) -> List[Dict[str, Any]]:
    """Walk root up to max_depth and find directories that look like projects."""
    projects = []
    root_depth = root.rstrip(os.sep).count(os.sep)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
        if current_depth >= max_depth:
            dirnames.clear()
            continue

        # Prune heavy non-project dirs
        dirnames[:] = [d for d in dirnames
                       if d not in {'.git', '.hg', 'Library', 'AppData',
                                    '$RECYCLE.BIN', '.Trash', '.cache'}
                       and not d.startswith('.')]

        has_indicator = any(f in PROJECT_INDICATORS for f in filenames)
        has_junk_dir = any(d in TARGET_FOLDERS for d in dirnames)

        if has_indicator or has_junk_dir:
            junk_size = 0
            junk_dirs = []
            for d in dirnames:
                if d in TARGET_FOLDERS:
                    full = os.path.join(dirpath, d)
                    size = _dir_size(full)
                    junk_size += size
                    junk_dirs.append((d, size))

            total_size = _dir_size(dirpath)
            source_size = total_size - junk_size

            if total_size > 0:
                junk_pct = (junk_size / total_size) * 100
            else:
                junk_pct = 0

            if junk_size > 0:
                projects.append({
                    "path": dirpath,
                    "total_size": total_size,
                    "source_size": source_size,
                    "junk_size": junk_size,
                    "junk_pct": junk_pct,
                    "junk_dirs": junk_dirs,
                })

            # Don't descend into this project's children (already scanned)
            dirnames[:] = [d for d in dirnames if d not in TARGET_FOLDERS]

    return sorted(projects, key=lambda p: p["junk_size"], reverse=True)


def display_junk_score(root: str, max_depth: int = 3):
    """Scan and display junk score table."""
    console.print(f"\n[bold cyan]Junk Score Analysis[/bold cyan] — {root}\n")

    projects = find_projects(root, max_depth)

    if not projects:
        console.print("[dim]No projects with reclaimable junk found.[/dim]")
        return

    table = Table(title="Project Junk Scores", border_style="cyan")
    table.add_column("Project", style="bold", max_width=50)
    table.add_column("Source", justify="right")
    table.add_column("Junk", justify="right", style="red")
    table.add_column("Score", justify="right")

    total_junk = 0
    total_source = 0

    for p in projects[:20]:
        rel_path = os.path.relpath(p["path"], root)
        if len(rel_path) > 48:
            rel_path = "..." + rel_path[-45:]

        pct = p["junk_pct"]
        if pct >= 90:
            score_style = "bold red"
        elif pct >= 70:
            score_style = "yellow"
        else:
            score_style = "green"

        table.add_row(
            rel_path,
            bytes_to_human_readable(p["source_size"]),
            bytes_to_human_readable(p["junk_size"]),
            f"[{score_style}]{pct:.0f}% junk[/{score_style}]",
        )

        total_junk += p["junk_size"]
        total_source += p["source_size"]

    console.print(table)

    console.print(f"\n[bold]Total reclaimable:[/bold] "
                  f"[red]{bytes_to_human_readable(total_junk)}[/red] across {len(projects)} projects")
    if total_source + total_junk > 0:
        overall_pct = (total_junk / (total_source + total_junk)) * 100
        console.print(f"[dim]Overall junk ratio: {overall_pct:.0f}%[/dim]")
