"""Watch mode / auto-clean daemon for vanish.

Periodically scans and cleans stale artifacts. Uses simple polling loop
for cross-platform compatibility (no systemd/launchd dependency).
"""

import time
import signal
import sys
from typing import Optional
from rich.console import Console

from .config import Config
from .core import CleanupEngine
from .notifications import send_notification

console = Console()

_RUNNING = True


def _handle_signal(sig, frame):
    global _RUNNING
    _RUNNING = False
    console.print("\n[yellow]vanish watch stopped.[/yellow]")


def watch(
    interval_seconds: int = 86400,
    config_path: Optional[str] = None,
    auto_clean: bool = False,
    min_stale_days: Optional[int] = None,
):
    """Run vanish in watch/daemon mode with periodic scanning.

    Args:
        interval_seconds: Seconds between scans (default 24h).
        config_path: Optional path to config JSON.
        auto_clean: If True, delete without prompting. If False, dry-run only.
        min_stale_days: Override staleness threshold for all targets.
    """
    global _RUNNING
    _RUNNING = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    console.print(f"[bold cyan]vanish watch[/bold cyan] — scanning every "
                  f"{interval_seconds // 3600}h {(interval_seconds % 3600) // 60}m")
    if auto_clean:
        console.print("[yellow]Auto-clean is ON — items will be deleted automatically.[/yellow]")
    else:
        console.print("[dim]Dry-run mode — use --auto-clean to enable deletion.[/dim]")

    run_count = 0
    while _RUNNING:
        run_count += 1
        console.print(f"\n[bold]Watch run #{run_count}[/bold] — {time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            cfg = Config(config_path)

            if min_stale_days is not None:
                targets = cfg.config.get("targets", [])
                for t in targets:
                    t["days_threshold"] = min_stale_days

            engine = CleanupEngine(config=cfg, dry_run=not auto_clean)
            result = engine.run()

            if auto_clean and result.get("success"):
                total_bytes = result["stats"]["folders_size"] + result["stats"]["bin_size"]
                if total_bytes > 0:
                    from .utils.safety import bytes_to_human_readable
                    size_str = bytes_to_human_readable(total_bytes)
                    send_notification("vanish watch", f"Auto-cleaned {size_str}")

        except Exception as e:
            console.print(f"[red]Watch run failed: {e}[/red]")

        if not _RUNNING:
            break

        console.print(f"[dim]Next scan in {interval_seconds}s. Press Ctrl+C to stop.[/dim]")
        waited = 0
        while waited < interval_seconds and _RUNNING:
            time.sleep(min(5, interval_seconds - waited))
            waited += 5

    console.print("[green]vanish watch exited cleanly.[/green]")
