"""Tests for plugin system."""

import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch
from vanish.plugins import load_plugins, plugins_to_targets, SAMPLE_PLUGIN


@pytest.fixture
def plugin_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


def test_load_plugins_empty(plugin_dir):
    with patch("vanish.plugins.PLUGIN_DIR", plugin_dir):
        plugins = load_plugins()
        assert plugins == []


def test_load_plugins_with_file(plugin_dir):
    plugin_data = {
        "name": "test_plugin",
        "folders": ["build_output"],
        "stale_days": 7,
        "enabled": True,
    }
    with open(os.path.join(plugin_dir, "test.json"), 'w') as f:
        json.dump(plugin_data, f)

    with patch("vanish.plugins.PLUGIN_DIR", plugin_dir):
        plugins = load_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "test_plugin"


def test_plugins_to_targets():
    plugins = [SAMPLE_PLUGIN]
    targets = plugins_to_targets(plugins)
    assert len(targets) == 2
    assert targets[0]["name"] == "build"
    assert targets[1]["name"] == ".dart_tool"
    assert targets[0]["days_threshold"] == 14


def test_disabled_plugin_ignored():
    plugin = {**SAMPLE_PLUGIN, "enabled": False}
    targets = plugins_to_targets([plugin])
    assert targets == []
