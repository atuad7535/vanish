"""Project health report for vanish doctor command.

Provides a comprehensive health view: disk, git, docker, and dependency staleness.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .utils.safety import bytes_to_human_readable
from .git_tools import GitAnalyzer
from .junk_score import TARGET_FOLDERS, PROJECT_INDICATORS, _dir_size

console = Console()

LOCKFILE_MAP = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "Pipfile.lock": "pipenv",
    "poetry.lock": "poetry",
    "Cargo.lock": "cargo",
    "go.sum": "go",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
}


def _lockfile_age_days(project_path: str) -> List[Dict[str, Any]]:
    """Find lockfiles and their age in days."""
    results = []
    now = datetime.now()
    for fname, manager in LOCKFILE_MAP.items():
        fpath = os.path.join(project_path, fname)
        if os.path.exists(fpath):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                age = (now - mtime).days
                results.append({"file": fname, "manager": manager, "age_days": age})
            except Exception:
                pass
    return results


def generate_health_report(root: str, max_depth: int = 3):
    """Generate full project health report."""
    console.print(Panel("[bold]vanish doctor[/bold] — project health report",
                        border_style="green"))

    root_depth = root.rstrip(os.sep).count(os.sep)
    reports = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
        if current_depth >= max_depth:
            dirnames.clear()
            continue

        dirnames[:] = [d for d in dirnames
                       if d not in {'.git', '.hg', 'Library', 'AppData',
                                    '$RECYCLE.BIN', '.Trash', '.cache'}
                       and not d.startswith('.')]

        has_indicator = any(f in PROJECT_INDICATORS for f in filenames)
        has_git = '.git' in os.listdir(dirpath) if os.path.isdir(dirpath) else False

        if not (has_indicator or has_git):
            continue

        report: Dict[str, Any] = {"path": dirpath, "issues": []}

        # Disk analysis
        junk_dirs = [d for d in os.listdir(dirpath)
                     if d in TARGET_FOLDERS and os.path.isdir(os.path.join(dirpath, d))]
        for jd in junk_dirs:
            jpath = os.path.join(dirpath, jd)
            size = _dir_size(jpath)
            if size > 1024 * 1024:  # > 1MB
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(jpath))
                    age = (datetime.now() - mtime).days
                except Exception:
                    age = 0
                report["issues"].append(
                    f"[red]Disk:[/red] {jd} ({bytes_to_human_readable(size)}, stale {age}d)"
                )

        # Git analysis
        if has_git:
            try:
                analyzer = GitAnalyzer(dirpath)
                if analyzer.is_git_repo():
                    stale = analyzer.find_stale_branches()
                    if stale:
                        report["issues"].append(
                            f"[yellow]Git:[/yellow] {len(stale)} merged stale branch(es)"
                        )
                    large = analyzer.find_large_files()
                    if large:
                        total_mb = sum(f['size_mb'] for f in large)
                        report["issues"].append(
                            f"[yellow]Git:[/yellow] {len(large)} large file(s) ({total_mb:.0f} MB)"
                        )
            except Exception:
                pass

        # Dependency staleness
        lockfiles = _lockfile_age_days(dirpath)
        for lf in lockfiles:
            if lf["age_days"] > 180:
                report["issues"].append(
                    f"[cyan]Deps:[/cyan] {lf['file']} ({lf['manager']}) is {lf['age_days']}d old"
                )

        if report["issues"]:
            reports.append(report)

        # Don't descend into this project further
        dirnames[:] = [d for d in dirnames if d not in TARGET_FOLDERS]

    if not reports:
        console.print("[green]All projects look healthy! Nothing to report.[/green]")
        return

    for r in reports[:15]:
        rel = os.path.relpath(r["path"], root)
        console.print(f"\n[bold]{rel}[/bold]")
        for issue in r["issues"]:
            console.print(f"  {issue}")

    console.print(f"\n[dim]{len(reports)} project(s) need attention.[/dim]")
