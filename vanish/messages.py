"""Gen-z meme notification messages for vanish.

Messages rotate randomly each run. Parameterized with {size}, {count}, {time}
placeholders filled at runtime.
"""

import random
from .utils.safety import bytes_to_human_readable

COMPLETION_MESSAGES = [
    "vanish just made {size} disappear like ur ex no cap 💀",
    "sheesh {size} of node_modules got sent to the shadow realm 💀",
    "poof ✨ {size} gone. ur disk is thriving rn fr fr",
    "vanish ate {size} of dead code for breakfast. bussin. 🔥",
    "{size} of dev junk? never heard of her. vanished. 💅",
    "ur disk just lost {size} and it's never looked better tbh",
    "{size} of artifacts just got ratio'd by vanish no cap 💀",
    "vanish said '{size} of junk? not on my watch' and obliterated it",
    "{count} folders totaling {size} just got absolutely rekt 💀",
    "disk went from mid to slay in {time}s. {size} freed. period. 💅",
]

DRY_RUN_MESSAGES = [
    "vanish WOULD obliterate {size} but u said dry run. coward. 💀",
    "{size} of junk detected. say the word and it's gone no cap 🫡",
    "ur disk is hoarding {size} of artifacts. that's not the vibe. 😬",
    "found {count} folders ({size}) just vibing there doing nothing. sus. 🤨",
    "dry run complete: {size} of junk spotted. vanish is ready when u are bestie 💅",
    "{size} of dead weight found across {count} folders. say less fam 🫡",
]

ERROR_MESSAGES = [
    "vanish tried its best but something went wrong ong 😭",
    "skill issue: vanish hit an error. check the logs bestie 💀",
    "not gonna lie, something broke. vanish is crying rn 😢",
    "L + ratio + something went wrong. error: {error} 💀",
    "vanish encountered a plot twist nobody asked for 😭",
]

ZERO_RESULT_MESSAGES = [
    "ur disk is actually clean?? main character energy fr ✨",
    "nothing to vanish. disk is immaculate. slay. 💅",
    "vanish found zero junk. who even are you. 🤯",
    "literally nothing to clean. disk said 'i woke up like this' 💅",
    "0 items found. ur disk is giving minimalist queen vibes ✨",
    "vanish scanned everything and found... nothing. respect. 🫡",
]

DESKTOP_COMPLETION = [
    "{size} vanished. ur disk is vibing. ✨",
    "poof. {size} gone no cap 💀",
    "{size} freed. disk is bussin rn 🔥",
    "{size} obliterated in {time}s. slay. 💅",
]

DESKTOP_DRY_RUN = [
    "{size} of junk found. dry run tho 👀",
    "spotted {size} of artifacts. say the word 🫡",
]

DESKTOP_ERROR = [
    "something broke bestie. check logs 😭",
    "error encountered ong. check logs 💀",
]


def _format(template: str, size_bytes: float = 0, count: int = 0,
            time_seconds: float = 0, error: str = "") -> str:
    size = bytes_to_human_readable(size_bytes) if size_bytes else "0 B"
    return template.format(
        size=size,
        count=count,
        time=f"{time_seconds:.1f}" if time_seconds else "0",
        error=error[:80] if error else "",
    )


def get_completion_message(total_size_mb: float, items_deleted: int,
                           duration_seconds: float = 0) -> str:
    template = random.choice(COMPLETION_MESSAGES)
    return _format(template, size_bytes=total_size_mb * 1024 * 1024,
                   count=items_deleted, time_seconds=duration_seconds)


def get_dry_run_message(estimated_size_mb: float, items_count: int) -> str:
    template = random.choice(DRY_RUN_MESSAGES)
    return _format(template, size_bytes=estimated_size_mb * 1024 * 1024,
                   count=items_count)


def get_error_message(error: str = "") -> str:
    template = random.choice(ERROR_MESSAGES)
    return _format(template, error=error)


def get_zero_result_message() -> str:
    return random.choice(ZERO_RESULT_MESSAGES)


def get_desktop_completion(total_size_mb: float, duration_seconds: float = 0) -> str:
    template = random.choice(DESKTOP_COMPLETION)
    return _format(template, size_bytes=total_size_mb * 1024 * 1024,
                   time_seconds=duration_seconds)


def get_desktop_dry_run(estimated_size_mb: float) -> str:
    template = random.choice(DESKTOP_DRY_RUN)
    return _format(template, size_bytes=estimated_size_mb * 1024 * 1024)


def get_desktop_error() -> str:
    return random.choice(DESKTOP_ERROR)
