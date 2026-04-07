"""Interactive TUI mode for vanish using Textual.

This module is optional — only loaded when vanish[all] is installed.
"""

import os
from typing import List, Dict, Any

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, DataTable, Static
    from textual.containers import Container
    from textual.binding import Binding

    _HAS_TEXTUAL = True
except ImportError:
    _HAS_TEXTUAL = False


def is_tui_available() -> bool:
    return _HAS_TEXTUAL


if _HAS_TEXTUAL:
    from vanish.utils.safety import bytes_to_human_readable

    class VanishTUI(App):
        """Interactive cleanup TUI for vanish."""

        CSS = """
        Screen {
            layout: vertical;
        }
        #summary {
            height: 3;
            content-align: center middle;
            background: $primary-background;
            color: $text;
            text-style: bold;
        }
        DataTable {
            height: 1fr;
        }
        """

        BINDINGS = [
            Binding("space", "toggle_select", "Select/Deselect"),
            Binding("a", "select_all", "Select All"),
            Binding("enter", "confirm", "delete", priority=True),
            Binding("d", "confirm", "Delete Selected"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self, candidates: List[Dict[str, Any]], dry_run: bool = False, **kwargs):
            super().__init__(**kwargs)
            self.candidates = candidates
            self.selected: set = set()
            self.dry_run = dry_run
            self.confirmed_items: List[Dict[str, Any]] = []

        def compose(self) -> ComposeResult:
            yield Header()
            total = sum(c["size"] for c in self.candidates)
            yield Static(
                f"vanish — {len(self.candidates)} items found | "
                f"Total: {bytes_to_human_readable(total)} | "
                f"[Space] toggle  [A] all  [Enter] delete  [Q] quit",
                id="summary",
            )
            table = DataTable()
            table.add_columns("Sel", "Path", "Size", "Type", "Stale Since")
            for i, c in enumerate(self.candidates):
                table.add_row(
                    "[ ]",
                    c["path"],
                    bytes_to_human_readable(c["size"]),
                    c.get("target_name", "?"),
                    c.get("last_modified", "?"),
                    key=str(i),
                )
            yield table
            yield Footer()

        def action_toggle_select(self) -> None:
            table = self.query_one(DataTable)
            row_key = table.cursor_row
            if row_key is None:
                return
            idx = int(table.get_row_at(row_key)[1]) if False else row_key
            if idx in self.selected:
                self.selected.discard(idx)
                table.update_cell_at((row_key, 0), "[ ]")
            else:
                self.selected.add(idx)
                table.update_cell_at((row_key, 0), "[x]")
            self._update_summary()

        def action_select_all(self) -> None:
            table = self.query_one(DataTable)
            if len(self.selected) == len(self.candidates):
                self.selected.clear()
                for i in range(len(self.candidates)):
                    table.update_cell_at((i, 0), "[ ]")
            else:
                self.selected = set(range(len(self.candidates)))
                for i in range(len(self.candidates)):
                    table.update_cell_at((i, 0), "[x]")
            self._update_summary()

        def _update_summary(self) -> None:
            total = sum(self.candidates[i]["size"] for i in self.selected)
            summary = self.query_one("#summary", Static)
            summary.update(
                f"vanish — {len(self.selected)}/{len(self.candidates)} selected | "
                f"Selected: {bytes_to_human_readable(total)} | "
                f"[Space] toggle  [A] all  [Enter] delete  [Q] quit"
            )

        def action_confirm(self) -> None:
            self.confirmed_items = [self.candidates[i] for i in sorted(self.selected)]
            self.exit()

        def action_quit(self) -> None:
            self.confirmed_items = []
            self.exit()


def run_interactive(candidates: List[Dict[str, Any]], dry_run: bool = False) -> List[Dict[str, Any]]:
    """Run the interactive TUI and return user-selected items."""
    if not _HAS_TEXTUAL:
        from rich.console import Console
        Console().print(
            "[yellow]Textual not installed. Install with:[/yellow] "
            "[bold]pip install vanish\\[all][/bold]"
        )
        return []

    tui_app = VanishTUI(candidates, dry_run=dry_run)
    tui_app.run()
    return tui_app.confirmed_items
