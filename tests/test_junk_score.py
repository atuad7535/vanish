"""Tests for junk score analysis."""

import os
import tempfile
import shutil
import pytest
from vanish.junk_score import find_projects, _dir_size


@pytest.fixture
def fake_project_tree():
    root = tempfile.mkdtemp()
    project = os.path.join(root, "my_app")
    os.makedirs(project)

    # Source file
    with open(os.path.join(project, "package.json"), 'w') as f:
        f.write('{"name": "my_app"}')
    with open(os.path.join(project, "index.js"), 'w') as f:
        f.write("console.log('hello')")

    # Junk directory
    nm = os.path.join(project, "node_modules")
    os.makedirs(nm)
    with open(os.path.join(nm, "big_file.js"), 'w') as f:
        f.write("x" * 10000)

    yield root
    shutil.rmtree(root)


def test_find_projects(fake_project_tree):
    projects = find_projects(fake_project_tree, max_depth=3)
    assert len(projects) >= 1
    p = projects[0]
    assert p["junk_size"] > 0
    assert p["source_size"] >= 0
    assert 0 <= p["junk_pct"] <= 100


def test_dir_size():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "file.txt"), 'w') as f:
            f.write("hello world")
        size = _dir_size(d)
        assert size > 0


def test_empty_root():
    with tempfile.TemporaryDirectory() as d:
        projects = find_projects(d, max_depth=3)
        assert projects == []
