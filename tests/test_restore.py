"""Tests for restore functionality."""

import os
import json
import tempfile
import shutil
import pytest
from vanish.restore import JobRestorer


@pytest.fixture
def mock_restore_env():
    """Create a mock environment with archive and manifest."""
    root = tempfile.mkdtemp()
    archive_dir = os.path.join(root, "archive")
    os.makedirs(archive_dir)

    # Create archived item
    archived_item = os.path.join(archive_dir, "node_modules")
    os.makedirs(archived_item)
    with open(os.path.join(archived_item, "pkg.json"), 'w') as f:
        f.write("{}")

    original_path = os.path.join(root, "project", "node_modules")

    # Create manifest
    manifest_file = os.path.join(root, "manifest.json")
    manifest = {
        "timestamp": "2026-01-01T00:00:00",
        "items": [{
            "path": original_path,
            "size": 1024,
            "last_modified": "2025-12-01",
            "type": "folder",
            "archived_to": archived_item,
        }],
    }
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f)

    config = {
        "logging": {"manifest_file": manifest_file},
        "safety": {"archive_folder": archive_dir},
    }

    yield config, root, original_path

    if os.path.exists(root):
        shutil.rmtree(root)


def test_list_restorable(mock_restore_env):
    config, root, _ = mock_restore_env
    restorer = JobRestorer(config)
    items = restorer.list_restorable_items()
    assert len(items) == 1


def test_restore_item(mock_restore_env):
    config, root, original_path = mock_restore_env
    restorer = JobRestorer(config)
    items = restorer.list_restorable_items()
    assert len(items) == 1

    success = restorer.restore_item(items[0])
    assert success is True
    assert os.path.exists(original_path)


def test_no_manifest():
    config = {"logging": {"manifest_file": "/nonexistent/manifest.json"},
              "safety": {"archive_folder": "/tmp"}}
    restorer = JobRestorer(config)
    assert restorer.list_restorable_items() == []
