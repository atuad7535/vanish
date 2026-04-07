"""Command-line interface for vanish — Typer subcommand architecture."""

import os
import sys
import csv
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import print as rprint

from .config import Config
from .core import CleanupEngine
from .scheduler import Scheduler
from .utils import bytes_to_human_readable
from .messages import get_zero_result_message
from . import __version__

console = Console()
app = typer.Typer(
    name="vanish",
    help="vanish — poof. your dev junk vanished.",
    no_args_is_help=False,
    invoke_without_command=True,
)

schedule_app = typer.Typer(help="Manage automated cleanup schedules.")
config_app = typer.Typer(help="Generate or view configuration.")
telemetry_app = typer.Typer(help="Manage anonymous usage statistics.")

app.add_typer(schedule_app, name="schedule")
app.add_typer(config_app, name="config")
app.add_typer(telemetry_app, name="telemetry")


def version_callback(value: bool):
    if value:
        rprint(f"vanish {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback,
                                 is_eager=True, help="Show version and exit."),
):
    """vanish — poof. your dev junk vanished.

    Run with no arguments to scan and clean stale dev artifacts.
    """
    if ctx.invoked_subcommand is None:
        _run_scan(dry_run=False, archive=False, config_path=None, sound=True)


@app.command()
def scan(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview deletions without actually deleting."),
    archive: bool = typer.Option(False, "--archive", "-a", help="Move to archive instead of permanent deletion."),
    trash: bool = typer.Option(False, "--trash", "-t", help="Send to OS Trash/Recycle Bin instead of deleting."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive TUI mode (requires vanish[all])."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Mute the completion chime and voice."),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config file (JSON)."),
    docker: bool = typer.Option(False, "--docker", help="Also clean unused Docker images."),
    git_check: bool = typer.Option(False, "--git-check", help="Also run Git repository health analysis."),
):
    """Scan and clean stale dev artifacts."""
    _run_scan(dry_run=dry_run, archive=archive, config_path=config,
              docker=docker, git_check=git_check, use_trash=trash,
              interactive=interactive, sound=not quiet)


def _run_scan(dry_run: bool, archive: bool, config_path: Optional[str],
              docker: bool = False, git_check: bool = False,
              use_trash: bool = False, interactive: bool = False,
              sound: bool = False):
    """Internal scan + clean logic shared by default invocation and `scan` subcommand."""
    import logging
    cfg = Config(config_path)
    logging.basicConfig(level=getattr(logging, cfg.get("logging", {}).get("level", "INFO")))

    if docker:
        cfg.set("docker", {"enabled": True})
    if git_check:
        cfg.set("git", {"enabled": True})

    engine = CleanupEngine(config=cfg, dry_run=dry_run, archive_mode=archive,
                           use_trash=use_trash, sound=sound)

    if interactive:
        from .tui import run_interactive, is_tui_available
        if not is_tui_available():
            console.print("[yellow]Textual not installed.[/yellow] "
                          "Install with: [bold]pip install vanish\\[all][/bold]")
            raise typer.Exit(1)

        targets = cfg.get_enabled_targets()
        candidates = engine._scan_all_targets(cfg.get("main_folder"), targets)
        if not candidates:
            console.print(get_zero_result_message())
            raise typer.Exit(0)

        selected = run_interactive(candidates, dry_run=dry_run)
        if not selected:
            console.print("[yellow]No items selected. Cancelled.[/yellow]")
            raise typer.Exit(0)

        for item in selected:
            engine.delete_or_archive_item(item)

        total_bytes = sum(i["size"] for i in selected)
        from . import messages
        msg = messages.get_completion_message(
            total_bytes / (1024 * 1024), len(selected))
        console.print(f"\n[green]{msg}[/green]")

        from .notifications import notify_completion
        notify_completion(total_bytes / (1024 * 1024), len(selected),
                          speak_aloud=sound)

        raise typer.Exit(0)

    result = engine.run()
    raise typer.Exit(0 if result["success"] else 1)


@app.command()
def restore(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config file."),
):
    """Restore items from the last archive run."""
    from .restore import JobRestorer
    cfg = Config(config)
    restorer = JobRestorer(cfg)
    count = restorer.restore_all()
    if count:
        console.print(f"[green]Restored {count} items.[/green]")
    else:
        console.print("[yellow]No restorable items found (did you use --archive previously?)[/yellow]")


@app.command("junk-score")
def junk_score(
    path: Optional[str] = typer.Argument(None, help="Root directory to analyze (default: home)."),
    depth: int = typer.Option(3, "--depth", "-d", help="Max directory depth to scan."),
):
    """Analyze projects and show junk vs. source code ratio."""
    from .junk_score import display_junk_score
    root = path or os.path.expanduser("~")
    display_junk_score(root, max_depth=depth)


@app.command()
def ci(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    max_junk_gb: float = typer.Option(5.0, "--max-junk", help="Max junk GB before non-zero exit."),
):
    """CI/CD mode: scan, output JSON, exit non-zero if junk exceeds threshold."""
    import json as json_mod
    cfg = Config(config)
    engine = CleanupEngine(config=cfg, dry_run=True)
    targets = cfg.get_enabled_targets()
    candidates = engine._scan_all_targets(cfg.get("main_folder"), targets)

    total_bytes = sum(c["size"] for c in candidates)
    total_gb = total_bytes / (1024 ** 3)

    data = {
        "total_junk_bytes": total_bytes,
        "total_junk_gb": round(total_gb, 2),
        "items": len(candidates),
        "threshold_gb": max_junk_gb,
        "exceeds_threshold": total_gb > max_junk_gb,
    }
    console.print_json(json_mod.dumps(data))

    if total_gb > max_junk_gb:
        raise typer.Exit(1)
    raise typer.Exit(0)


@app.command()
def stats(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config file."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """View cleanup dashboard, savings, and trends."""
    import json as json_mod
    cfg = Config(config)
    log_file = cfg.get("logging", {}).get("log_file")

    if not os.path.exists(log_file):
        console.print(Panel("No cleanup history found yet.\nRun [bold]vanish[/bold] to start!",
                            title="vanish Dashboard", border_style="cyan"))
        return

    try:
        with open(log_file, 'r') as f:
            reader = list(csv.DictReader(f))
    except Exception as e:
        console.print(f"[red]Error reading dashboard: {e}[/red]")
        return

    if not reader:
        console.print(Panel("No cleanup history found yet.", title="vanish Dashboard", border_style="cyan"))
        return

    total_runs = len(reader)
    last_row = reader[-1]
    cumulative_total_mb = float(last_row['cumulative_total_mb'])
    cumulative_folders_mb = float(last_row['cumulative_folders_mb'])
    cumulative_bin_mb = float(last_row['cumulative_bin_mb'])
    avg_per_run = cumulative_total_mb / total_runs if total_runs > 0 else 0

    if json_output:
        data = {
            "total_runs": total_runs,
            "cumulative_total_mb": round(cumulative_total_mb, 2),
            "cumulative_folders_mb": round(cumulative_folders_mb, 2),
            "cumulative_bin_mb": round(cumulative_bin_mb, 2),
            "avg_per_run_mb": round(avg_per_run, 2),
        }
        console.print_json(json_mod.dumps(data))
        return

    table = Table(title="vanish Dashboard — Space Savings", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total space freed", bytes_to_human_readable(cumulative_total_mb * 1024 * 1024))
    table.add_row("  From folders", bytes_to_human_readable(cumulative_folders_mb * 1024 * 1024))
    table.add_row("  From bin", bytes_to_human_readable(cumulative_bin_mb * 1024 * 1024))
    table.add_row("Total runs", str(total_runs))
    table.add_row("Average per run", bytes_to_human_readable(avg_per_run * 1024 * 1024))

    console.print(table)

    now = datetime.now()
    recent = [r for r in reader
              if (now - datetime.strptime(r['datetime'], '%Y-%m-%d %H:%M:%S')).days <= 7]
    if recent:
        console.print(f"\n[bold]Last 7 days:[/bold] {len(recent)} runs, "
                      f"{bytes_to_human_readable(sum(float(r['total_deleted_mb']) for r in recent) * 1024 * 1024)} freed")


@app.command()
def doctor(
    path: Optional[str] = typer.Argument(None, help="Root directory to analyze (default: home)."),
    depth: int = typer.Option(3, "--depth", "-d", help="Max directory depth to scan."),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config file."),
):
    """Run full project health report (disk, Git, Docker, dependency staleness)."""
    from .health import generate_health_report
    cfg = Config(config)
    root = path or cfg.get("main_folder") or os.path.expanduser("~")
    generate_health_report(root, max_depth=depth)


# --- schedule subcommands ---

@schedule_app.command("daily")
def schedule_daily(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    archive: bool = typer.Option(False, "--archive", "-a"),
):
    """Schedule vanish to run daily at 2 AM."""
    _do_schedule("daily", config, dry_run, archive)


@schedule_app.command("weekly")
def schedule_weekly(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    archive: bool = typer.Option(False, "--archive", "-a"),
):
    """Schedule vanish to run weekly (Sunday 2 AM)."""
    _do_schedule("weekly", config, dry_run, archive)


@schedule_app.command("monthly")
def schedule_monthly(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    archive: bool = typer.Option(False, "--archive", "-a"),
):
    """Schedule vanish to run monthly (1st of month, 2 AM)."""
    _do_schedule("monthly", config, dry_run, archive)


@schedule_app.command("list")
def schedule_list():
    """List all scheduled vanish tasks."""
    Scheduler().list_schedules()


@schedule_app.command("remove")
def schedule_remove():
    """Remove all scheduled vanish tasks."""
    Scheduler().remove_schedule()


def _do_schedule(freq: str, config: Optional[str], dry_run: bool, archive: bool):
    s = Scheduler()
    success = s.schedule(frequency=freq, config_path=config, dry_run=dry_run, archive=archive)
    raise typer.Exit(0 if success else 1)


# --- config subcommands ---

@config_app.command("generate")
def config_generate(
    output: str = typer.Option("vanish_config.json", "--output", "-o",
                               help="Output path for generated config."),
):
    """Generate a sample configuration file."""
    cfg = Config()
    cfg.save_to_file(output)
    console.print(f"[green]Sample configuration saved to: {output}[/green]")
    console.print("Edit this file to customize your cleanup settings.")


@config_app.command("show")
def config_show(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file."),
):
    """Show current configuration."""
    import json as json_mod
    cfg = Config(config)
    console.print_json(json_mod.dumps(cfg.config, indent=2))


# --- telemetry subcommands ---

@telemetry_app.command("status")
def telemetry_status(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
):
    """Check if anonymous telemetry is enabled."""
    cfg = Config(config)
    enabled = cfg.get("telemetry", {}).get("enabled", True)
    status = "[green]ENABLED[/green]" if enabled else "[red]DISABLED[/red]"
    console.print(f"Anonymous Telemetry: {status}")


@telemetry_app.command("on")
def telemetry_on(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
):
    """Enable anonymous usage statistics."""
    cfg = Config(config)
    cfg.set("telemetry", {"enabled": True})
    cfg.save_to_file(config or "vanish_config.json")
    console.print("[green]Anonymous telemetry enabled. Thank you for contributing![/green]")


@telemetry_app.command("off")
def telemetry_off(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
):
    """Disable anonymous usage statistics."""
    cfg = Config(config)
    cfg.set("telemetry", {"enabled": False})
    cfg.save_to_file(config or "vanish_config.json")
    console.print("[green]Anonymous telemetry disabled.[/green]")


# --- watch command ---

@app.command()
def watch(
    interval: int = typer.Option(86400, "--interval", help="Seconds between scans (default 86400 = 24h)."),
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    auto_clean: bool = typer.Option(False, "--auto-clean", help="Actually delete (default is dry-run)."),
    min_stale_days: Optional[int] = typer.Option(None, "--min-stale-days",
                                                  help="Override staleness threshold for all targets."),
):
    """Run vanish in watch/daemon mode with periodic scanning."""
    from .watch import watch as do_watch
    do_watch(interval_seconds=interval, config_path=config,
             auto_clean=auto_clean, min_stale_days=min_stale_days)


# --- plugin commands ---

plugin_app = typer.Typer(help="Manage cleanup target plugins.")
app.add_typer(plugin_app, name="plugin")


@plugin_app.command("list")
def plugin_list():
    """List loaded plugins."""
    from .plugins import list_plugins
    list_plugins()


@plugin_app.command("init")
def plugin_init():
    """Create sample plugin file in ~/.vanish/plugins/."""
    from .plugins import create_sample_plugin
    create_sample_plugin()


# --- profile / gamification command ---

@app.command()
def profile():
    """Show your vanish gamification profile (streaks, milestones, level)."""
    from .gamification import show_profile
    show_profile()


def main():
    """Legacy entry point for backward compatibility."""
    app()
