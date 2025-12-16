#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.git import GitError
from pkgmgr.core.git.queries.probe_remote_reachable import probe_remote_reachable


class TestProbeRemoteReachable(unittest.TestCase):
    """
    Unit tests for non-destructive remote probing (git ls-remote).
    """

    @patch("pkgmgr.core.git.queries.probe_remote_reachable.run")
    def test_probe_remote_reachable_success_returns_true(self, mock_run) -> None:
        mock_run.return_value = "dummy-output"

        ok = probe_remote_reachable(
            "ssh://git@code.example.org:2201/alice/repo.git",
            cwd="/tmp/some-repo",
        )

        self.assertTrue(ok)
        mock_run.assert_called_once_with(
            ["ls-remote", "--exit-code", "ssh://git@code.example.org:2201/alice/repo.git"],
            cwd="/tmp/some-repo",
        )

    @patch("pkgmgr.core.git.queries.probe_remote_reachable.run")
    def test_probe_remote_reachable_failure_returns_false(self, mock_run) -> None:
        mock_run.side_effect = GitError("Git command failed (simulated)")

        ok = probe_remote_reachable(
            "ssh://git@code.example.org:2201/alice/repo.git",
            cwd="/tmp/some-repo",
        )

        self.assertFalse(ok)
        mock_run.assert_called_once_with(
            ["ls-remote", "--exit-code", "ssh://git@code.example.org:2201/alice/repo.git"],
            cwd="/tmp/some-repo",
        )


if __name__ == "__main__":
    unittest.main()
