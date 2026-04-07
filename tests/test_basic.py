"""Basic tests for vanish package."""

import pytest
from vanish import __version__, Config, CleanupEngine


def test_version():
    """Test version is defined."""
    assert __version__  # version string exists and is non-empty


def test_config_creation():
    """Test configuration can be created."""
    config = Config()
    assert config is not None
    assert config.get("main_folder") is not None


def test_cleanup_engine_creation():
    """Test cleanup engine can be instantiated."""
    config = Config()
    engine = CleanupEngine(config, dry_run=True)
    assert engine is not None
    assert engine.dry_run is True


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    targets = config.get_enabled_targets()
    assert isinstance(targets, list)
    assert len(targets) > 0
    assert targets[0]["name"] == "venv"
