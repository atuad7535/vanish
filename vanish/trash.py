"""OS trash integration for vanish.

Uses send2trash (optional) for native Recycle Bin / Trash support on all platforms.
Falls back to archive mode if send2trash is not installed.
"""

import os
from rich.console import Console

console = Console()

_HAS_SEND2TRASH = False
try:
    from send2trash import send2trash as _send2trash
    _HAS_SEND2TRASH = True
except ImportError:
    pass


def is_trash_available() -> bool:
    """Check if OS trash integration is available."""
    return _HAS_SEND2TRASH


def send_to_trash(path: str) -> bool:
    """Send a file or directory to the OS trash.

    Returns True on success, False if send2trash is not installed or on error.
    """
    if not _HAS_SEND2TRASH:
        return False

    try:
        _send2trash(path)
        return True
    except Exception as e:
        console.print(f"[yellow]⚠ Could not trash {path}: {e}[/yellow]")
        return False


def trash_or_delete(path: str, force_delete: bool = False) -> bool:
    """Try to send to OS trash. Fall back to permanent deletion if unavailable."""
    if not force_delete and _HAS_SEND2TRASH:
        return send_to_trash(path)

    import shutil
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception:
        return False
