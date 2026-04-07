"""Tests for gamification module."""

import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch
from vanish.gamification import record_run, _load_stats, _save_stats, MILESTONES


@pytest.fixture
def temp_stats():
    d = tempfile.mkdtemp()
    stats_file = os.path.join(d, "gamification.json")
    yield stats_file
    shutil.rmtree(d)


def test_load_stats_fresh(temp_stats):
    with patch("vanish.gamification.STATS_FILE", temp_stats):
        data = _load_stats()
        assert data["total_bytes_freed"] == 0
        assert data["total_runs"] == 0


def test_record_run(temp_stats):
    with patch("vanish.gamification.STATS_FILE", temp_stats):
        record_run(1024 * 1024 * 100)  # 100 MB
        data = _load_stats()
        assert data["total_bytes_freed"] == 1024 * 1024 * 100
        assert data["total_runs"] == 1
        assert data["streak_weeks"] == 1


def test_milestone_detection(temp_stats):
    with patch("vanish.gamification.STATS_FILE", temp_stats):
        record_run(2 * 1024**3)  # 2 GB — should trigger "Tidy Intern" (1 GB)
        data = _load_stats()
        assert "Tidy Intern" in data.get("milestones_reached", [])
