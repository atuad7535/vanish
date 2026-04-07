"""Tests for gen-z meme messages module."""

from vanish.messages import (
    get_completion_message,
    get_dry_run_message,
    get_error_message,
    get_zero_result_message,
    get_desktop_completion,
    get_desktop_dry_run,
    get_desktop_error,
)


def test_completion_message_has_size():
    msg = get_completion_message(500.0, 10, 3.5)
    assert len(msg) > 0


def test_dry_run_message():
    msg = get_dry_run_message(200.0, 5)
    assert len(msg) > 0


def test_error_message():
    msg = get_error_message("test error")
    assert len(msg) > 0


def test_zero_result_message():
    msg = get_zero_result_message()
    assert len(msg) > 0


def test_desktop_messages():
    assert len(get_desktop_completion(100.0, 2.5)) > 0
    assert len(get_desktop_dry_run(50.0)) > 0
    assert len(get_desktop_error()) > 0


def test_messages_are_random():
    """Verify messages rotate (not always the same)."""
    msgs = set()
    for _ in range(20):
        msgs.add(get_zero_result_message())
    # With 6 options and 20 draws, extremely unlikely to get only 1
    assert len(msgs) >= 2
