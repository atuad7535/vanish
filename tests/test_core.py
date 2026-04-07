"""Tests for core cleanup engine."""

import os
import tempfile
import shutil
import pytest
from vanish.config import Config
from vanish.core import CleanupEngine


@pytest.fixture
def temp_project():
    """Create a temporary project with stale artifacts."""
    root = tempfile.mkdtemp()
    project = os.path.join(root, "test_project")
    os.makedirs(project)

    # Create a "node_modules" directory with some content
    nm = os.path.join(project, "node_modules")
    os.makedirs(nm)
    with open(os.path.join(nm, "package.json"), 'w') as f:
        f.write('{"name": "test"}')

    # Create a fake source file (old) to make the project seem stale
    src = os.path.join(project, "index.js")
    with open(src, 'w') as f:
        f.write("console.log('hi')")
    # Set mtime to 30 days ago
    import time
    old_time = time.time() - (30 * 86400)
    os.utime(src, (old_time, old_time))

    yield root

    if os.path.exists(root):
        shutil.rmtree(root)


def test_engine_dry_run(temp_project):
    """Test that dry run doesn't delete anything."""
    config = Config()
    config.set("main_folder", temp_project)

    engine = CleanupEngine(config=config, dry_run=True)
    result = engine.run()

    assert result["success"] is True
    nm_path = os.path.join(temp_project, "test_project", "node_modules")
    assert os.path.exists(nm_path)


def test_get_size(temp_project):
    """Test size calculation."""
    config = Config()
    engine = CleanupEngine(config=config, dry_run=True)
    nm_path = os.path.join(temp_project, "test_project", "node_modules")
    size = engine.get_size(nm_path)
    assert size > 0


def test_get_last_modified_time():
    """Test staleness detection ignores .DS_Store."""
    with tempfile.TemporaryDirectory() as d:
        ds = os.path.join(d, ".DS_Store")
        with open(ds, 'w') as f:
            f.write("x")
        result = CleanupEngine.get_last_modified_time(d)
        # .DS_Store should be ignored, so mtime should be epoch (no real files)
        from datetime import datetime
        assert result == datetime.fromtimestamp(0)


def test_engine_stats_initialized():
    """Test that engine stats are properly initialized."""
    config = Config()
    engine = CleanupEngine(config=config, dry_run=True)
    assert engine.stats["folders_deleted"] == 0
    assert engine.stats["folders_size"] == 0
    assert engine.stats["bin_deleted"] == 0
    assert engine.stats["errors"] == []
