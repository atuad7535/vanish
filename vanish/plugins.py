"""Plugin / ecosystem system for user-defined cleanup targets.

Users can drop JSON files into ~/.vanish/plugins/ to define custom targets.
Each plugin defines folder names to scan, optional indicator files that
identify a project, and staleness thresholds.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console

console = Console()

PLUGIN_DIR = os.path.join(os.path.expanduser("~"), ".vanish", "plugins")

SAMPLE_PLUGIN = {
    "name": "flutter_build",
    "description": "Clean Flutter build artifacts",
    "folders": ["build", ".dart_tool"],
    "indicator_files": ["pubspec.yaml"],
    "stale_days": 14,
    "enabled": True,
}


def get_plugin_dir() -> str:
    return PLUGIN_DIR


def ensure_plugin_dir():
    os.makedirs(PLUGIN_DIR, exist_ok=True)


def load_plugins() -> List[Dict[str, Any]]:
    """Load all plugin JSON files from the plugin directory."""
    plugins = []
    if not os.path.isdir(PLUGIN_DIR):
        return plugins

    for fname in os.listdir(PLUGIN_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(PLUGIN_DIR, fname)
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict) and "folders" in data:
                data.setdefault("name", fname.replace(".json", ""))
                data.setdefault("stale_days", 14)
                data.setdefault("enabled", True)
                plugins.append(data)
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to load plugin {fname}: {e}[/yellow]")

    return plugins


def plugins_to_targets(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert plugin definitions to the target format used by Config."""
    targets = []
    for plugin in plugins:
        if not plugin.get("enabled", True):
            continue
        for folder in plugin.get("folders", []):
            targets.append({
                "name": folder,
                "days_threshold": plugin.get("stale_days", 14),
                "enabled": True,
                "source": f"plugin:{plugin['name']}",
            })
    return targets


def create_sample_plugin():
    """Create a sample plugin file for users to customize."""
    ensure_plugin_dir()
    sample_path = os.path.join(PLUGIN_DIR, "example_flutter.json")
    if os.path.exists(sample_path):
        console.print(f"[dim]Sample plugin already exists: {sample_path}[/dim]")
        return sample_path

    with open(sample_path, 'w') as f:
        json.dump(SAMPLE_PLUGIN, f, indent=2)
    console.print(f"[green]Sample plugin created: {sample_path}[/green]")
    return sample_path


def list_plugins():
    """Display loaded plugins."""
    plugins = load_plugins()
    if not plugins:
        console.print("[dim]No plugins found.[/dim]")
        console.print(f"[dim]Add .json files to {PLUGIN_DIR}[/dim]")
        return

    from rich.table import Table
    table = Table(title="Loaded Plugins", border_style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Folders")
    table.add_column("Stale Days", justify="right")
    table.add_column("Enabled")

    for p in plugins:
        table.add_row(
            p.get("name", "?"),
            ", ".join(p.get("folders", [])),
            str(p.get("stale_days", 14)),
            "[green]yes[/green]" if p.get("enabled", True) else "[red]no[/red]",
        )
    console.print(table)
