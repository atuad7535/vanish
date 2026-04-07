"""Desktop notification utilities for vanish."""

import platform
import subprocess
from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"
_SKULL_IMG = _ASSETS_DIR / "0x1900-000000-80-0-0.jpg"


def send_notification(title: str, message: str, sound: bool = False, speak_aloud: bool = False):
    """Send a desktop notification (cross-platform).

    Args:
        speak_aloud: If True, also play FAHHH + speak the message via TTS.
    """
    system = platform.system().lower()

    try:
        if system == "darwin":
            _send_macos_notification(title, message, sound)
        elif system == "windows":
            _send_windows_notification(title, message)
        elif system == "linux":
            _send_linux_notification(title, message)
    except Exception:
        pass

    if speak_aloud:
        try:
            from .sounds import speak, play_fahhh
            play_fahhh()
            speak(message)
        except Exception:
            pass


def _send_macos_notification(title: str, message: str, sound: bool = False):
    """Send native macOS notification with skull image via PyObjC, with fallbacks."""
    if _try_pyobjc_notification(title, message, sound):
        return
    _try_osascript_notification(title, message, sound)


def _try_pyobjc_notification(title: str, message: str, sound: bool) -> bool:
    try:
        from Foundation import NSUserNotification, NSUserNotificationCenter
        from AppKit import NSImage

        notification = NSUserNotification.alloc().init()
        notification.setTitle_(f"✨ {title}")
        notification.setSubtitle_("poof. your dev junk vanished.")
        notification.setInformativeText_(message)

        if _SKULL_IMG.exists():
            img = NSImage.alloc().initWithContentsOfFile_(str(_SKULL_IMG))
            if img:
                notification.setContentImage_(img)

        if sound:
            notification.setSoundName_("default")

        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        center.deliverNotification_(notification)
        return True
    except Exception:
        return False


def _try_osascript_notification(title: str, message: str, sound: bool):
    import re
    _strip = lambda t: re.sub(r'[^\x00-\x7F]+', '', t).strip()
    safe_title = _strip(title).replace('\\', '\\\\').replace('"', '\\"') or "vanish"
    safe_msg = _strip(message).replace('\\', '\\\\').replace('"', '\\"') or "Cleanup complete"
    sound_param = ' sound name "default"' if sound else ""
    script = f'display notification "{safe_msg}" with title "{safe_title}"{sound_param}'
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _send_windows_notification(title: str, message: str):
    """Send notification on Windows with skull icon using winotify or win10toast."""
    icon = str(_SKULL_IMG) if _SKULL_IMG.exists() else ""

    try:
        from winotify import Notification
        toast = Notification(
            app_id="vanish",
            title=f"✨ {title}",
            msg=message,
        )
        if icon:
            toast.set_audio(None, suppress=True)
            toast.icon = icon
        toast.show()
        return
    except (ImportError, Exception):
        pass

    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            f"✨ {title}", message,
            icon_path=icon if icon else None,
            duration=5, threaded=True,
        )
        return
    except (ImportError, Exception):
        pass

    print(f"Notification: {title} - {message}")


def _send_linux_notification(title: str, message: str):
    """Send notification on Linux with skull icon using notify-send."""
    cmd = ["notify-send", f"✨ {title}", message]
    if _SKULL_IMG.exists():
        cmd += ["-i", str(_SKULL_IMG)]
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def notify_completion(total_size_mb: float, items_deleted: int, speak_aloud: bool = False):
    """Send completion notification."""
    from .messages import get_completion_message
    msg = get_completion_message(total_size_mb, items_deleted)
    send_notification("vanish", msg, sound=True, speak_aloud=speak_aloud)


def notify_error(error_message: str, speak_aloud: bool = False):
    """Send error notification."""
    from .messages import get_error_message
    send_notification("vanish", get_error_message(error_message), sound=False, speak_aloud=speak_aloud)


def notify_dry_run_complete(items_count: int, estimated_size_mb: float, speak_aloud: bool = False):
    """Send dry-run completion notification."""
    from .messages import get_dry_run_message
    msg = get_dry_run_message(estimated_size_mb, items_count)
    send_notification("vanish", msg, sound=False, speak_aloud=speak_aloud)
