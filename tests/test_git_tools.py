"""Tests for Git tools."""

import unittest
from unittest.mock import patch, MagicMock
from vanish.git_tools import GitAnalyzer


class TestGitAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = GitAnalyzer(".")

    @patch('subprocess.run')
    def test_is_git_repo(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(self.analyzer.is_git_repo())

        mock_run.return_value.returncode = 128
        self.assertFalse(self.analyzer.is_git_repo())

    @patch('subprocess.run')
    def test_find_stale_branches(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="  feature-merged\n* main"),
            MagicMock(returncode=0, stdout="2023-01-01"),
        ]

        stale = self.analyzer.find_stale_branches()
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]['name'], 'feature-merged')

    @patch('os.walk')
    @patch('os.path.getsize')
    def test_find_large_files(self, mock_getsize, mock_walk):
        mock_walk.return_value = [
            ('.', [], ['big_file.bin', 'small_file.txt'])
        ]

        def get_size_side_effect(path):
            if 'big_file' in path:
                return 60 * 1024 * 1024
            return 1024

        mock_getsize.side_effect = get_size_side_effect

        large = self.analyzer.find_large_files(size_mb=50)
        self.assertEqual(len(large), 1)
        self.assertIn('big_file.bin', large[0]['path'])
