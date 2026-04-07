"""Rich-powered progress indicators for vanish."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


class ProgressBar:
    """Rich progress bar for terminal display."""

    def __init__(self, total: int, prefix: str = "", width: int = 50):
        self.total = total
        self.prefix = prefix
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=width),
            TaskProgressColumn(),
            console=console,
        )
        self.task = None
        self.progress.start()
        self.task = self.progress.add_task(prefix, total=total)

    def update(self, count: int = 1, suffix: str = ""):
        self.progress.update(self.task, advance=count,
                             description=f"{self.prefix} {suffix}" if suffix else self.prefix)

    def finish(self):
        self.progress.update(self.task, completed=self.total)
        self.progress.stop()


class Spinner:
    """Rich spinner for indeterminate progress."""

    def __init__(self, message: str = "Working..."):
        self.message = message
        self._count = 0

    def spin(self):
        self._count += 1

    def finish(self, final_message: str | None = None):
        msg = final_message or self.message
        console.print(f"[green]✓[/green] {msg}")
