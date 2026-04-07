"""Tests for the Typer CLI interface."""

import re
from typer.testing import CliRunner
from vanish.cli import app
from vanish import __version__

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in _plain(result.stdout)


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = _plain(result.stdout)
    assert "vanish" in out
    assert "scan" in out
    assert "stats" in out
    assert "doctor" in out


def test_scan_help():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    out = _plain(result.stdout)
    assert "--dry-run" in out
    assert "--archive" in out
    assert "--trash" in out
    assert "--interactive" in out


def test_schedule_help():
    result = runner.invoke(app, ["schedule", "--help"])
    assert result.exit_code == 0
    out = _plain(result.stdout)
    assert "daily" in out
    assert "weekly" in out
    assert "list" in out
    assert "remove" in out


def test_config_generate():
    result = runner.invoke(app, ["config", "generate", "--output", "/tmp/vanish_test_config.json"])
    assert result.exit_code == 0
    import os
    assert os.path.exists("/tmp/vanish_test_config.json")
    os.remove("/tmp/vanish_test_config.json")


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "main_folder" in _plain(result.stdout)


def test_telemetry_status():
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Telemetry" in _plain(result.stdout)


def test_plugin_list():
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0


def test_profile():
    result = runner.invoke(app, ["profile"])
    assert result.exit_code == 0
    assert "vanish Profile" in _plain(result.stdout)
