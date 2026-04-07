"""Tests for the Typer CLI interface."""

from typer.testing import CliRunner
from vanish.cli import app
from vanish import __version__

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vanish" in result.stdout
    assert "scan" in result.stdout
    assert "stats" in result.stdout
    assert "doctor" in result.stdout


def test_scan_help():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.stdout
    assert "--archive" in result.stdout
    assert "--trash" in result.stdout
    assert "--interactive" in result.stdout


def test_schedule_help():
    result = runner.invoke(app, ["schedule", "--help"])
    assert result.exit_code == 0
    assert "daily" in result.stdout
    assert "weekly" in result.stdout
    assert "list" in result.stdout
    assert "remove" in result.stdout


def test_config_generate():
    result = runner.invoke(app, ["config", "generate", "--output", "/tmp/vanish_test_config.json"])
    assert result.exit_code == 0
    import os
    assert os.path.exists("/tmp/vanish_test_config.json")
    os.remove("/tmp/vanish_test_config.json")


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "main_folder" in result.stdout


def test_telemetry_status():
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Telemetry" in result.stdout


def test_plugin_list():
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0


def test_profile():
    result = runner.invoke(app, ["profile"])
    assert result.exit_code == 0
    assert "vanish Profile" in result.stdout
