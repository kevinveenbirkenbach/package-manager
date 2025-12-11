#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.setup_cmd import _probe_mirror
from pkgmgr.core.git import GitError


class TestMirrorSetupCmd(unittest.TestCase):
    """
    Unit tests for the non-destructive remote probing logic in setup_cmd.
    """

    @patch("pkgmgr.actions.mirror.setup_cmd.run_git")
    def test_probe_mirror_success_returns_true_and_empty_message(
        self,
        mock_run_git,
    ) -> None:
        """
        If run_git returns successfully, _probe_mirror must report (True, "").
        """
        mock_run_git.return_value = "dummy-output"

        ok, message = _probe_mirror(
            "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git",
            "/tmp/some-repo",
        )

        self.assertTrue(ok)
        self.assertEqual(message, "")
        mock_run_git.assert_called_once()

    @patch("pkgmgr.actions.mirror.setup_cmd.run_git")
    def test_probe_mirror_failure_returns_false_and_error_message(
        self,
        mock_run_git,
    ) -> None:
        """
        If run_git raises GitError, _probe_mirror must report (False, <message>),
        and not re-raise the exception.
        """
        mock_run_git.side_effect = GitError("Git command failed (simulated)")

        ok, message = _probe_mirror(
            "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git",
            "/tmp/some-repo",
        )

        self.assertFalse(ok)
        self.assertIn("Git command failed", message)
        mock_run_git.assert_called_once()


if __name__ == "__main__":
    unittest.main()
