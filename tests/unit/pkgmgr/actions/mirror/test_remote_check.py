#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.remote_check import probe_mirror
from pkgmgr.core.git import GitError


class TestRemoteCheck(unittest.TestCase):
    """
    Unit tests for non-destructive remote probing (git ls-remote).
    """

    @patch("pkgmgr.actions.mirror.remote_check.run_git")
    def test_probe_mirror_success_returns_true_and_empty_message(self, mock_run_git) -> None:
        mock_run_git.return_value = "dummy-output"

        ok, message = probe_mirror(
            "ssh://git@code.example.org:2201/alice/repo.git",
            "/tmp/some-repo",
        )

        self.assertTrue(ok)
        self.assertEqual(message, "")
        mock_run_git.assert_called_once_with(
            ["ls-remote", "ssh://git@code.example.org:2201/alice/repo.git"],
            cwd="/tmp/some-repo",
        )

    @patch("pkgmgr.actions.mirror.remote_check.run_git")
    def test_probe_mirror_failure_returns_false_and_error_message(self, mock_run_git) -> None:
        mock_run_git.side_effect = GitError("Git command failed (simulated)")

        ok, message = probe_mirror(
            "ssh://git@code.example.org:2201/alice/repo.git",
            "/tmp/some-repo",
        )

        self.assertFalse(ok)
        self.assertIn("Git command failed", message)
        mock_run_git.assert_called_once_with(
            ["ls-remote", "ssh://git@code.example.org:2201/alice/repo.git"],
            cwd="/tmp/some-repo",
        )


if __name__ == "__main__":
    unittest.main()
