"""Tests for scheduler module."""

import pytest
from unittest.mock import patch, MagicMock
from vanish.scheduler import Scheduler


def test_get_vanish_path_found():
    with patch("shutil.which", return_value="/usr/local/bin/vanish"):
        s = Scheduler()
        assert s.vanish_path == "/usr/local/bin/vanish"


def test_get_vanish_path_fallback():
    with patch("shutil.which", return_value=None):
        s = Scheduler()
        assert "-m vanish" in s.vanish_path


def test_parse_frequency():
    s = Scheduler()
    assert s._parse_frequency("daily") == "0 2 * * *"
    assert s._parse_frequency("weekly") == "0 2 * * 0"
    assert s._parse_frequency("monthly") == "0 2 1 * *"
    assert s._parse_frequency("hourly") == "0 * * * *"
    assert s._parse_frequency("0 3 * * *") == "0 3 * * *"
