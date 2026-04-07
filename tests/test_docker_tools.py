"""Tests for Docker tools."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from vanish.docker_tools import DockerCleaner


class TestDockerCleaner(unittest.TestCase):

    def setUp(self):
        self.cleaner = DockerCleaner()
        self.cleaner.docker_cmd = "/usr/bin/docker"

    @patch('subprocess.run')
    def test_find_unused_images(self, mock_run):
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        output = f"sha256:123|my-repo|v1|{old_date} 10:00:00 +0000 UTC\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output)

        unused = self.cleaner.find_unused_images(days_threshold=60)
        self.assertEqual(len(unused), 1)
        self.assertEqual(unused[0]['id'], 'sha256:123')
        self.assertEqual(unused[0]['repo'], 'my-repo')

    @patch('subprocess.run')
    def test_prune_images(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        deleted = self.cleaner.prune_images([{'id': '123'}])
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0], '123')
