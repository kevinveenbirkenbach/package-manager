from __future__ import annotations

import runpy
import sys
import unittest
from unittest.mock import patch


class TestIntegrationBranchCommands(unittest.TestCase):
    """
    E2E-style tests for the 'pkgmgr branch' CLI wiring.

    We do NOT call real git; instead we patch pkgmgr.branch_commands.open_branch
    and verify that the CLI invokes it with the correct parameters.
    """

    def _run_pkgmgr(self, argv: list[str]) -> None:
        """
        Helper to run 'pkgmgr' via its entry module with a given argv.
        """
        original_argv = list(sys.argv)
        try:
            # argv typically looks like: ["pkgmgr", "branch", ...]
            sys.argv = argv
            # Run the CLI entry point
            runpy.run_module("pkgmgr.cli", run_name="__main__")
        finally:
            sys.argv = original_argv

    @patch("pkgmgr.branch_commands.open_branch")
    def test_branch_open_with_name_and_base(self, mock_open_branch) -> None:
        """
        pkgmgr branch open feature/test --base develop
        should invoke open_branch(name='feature/test', base_branch='develop', cwd='.')
        """
        self._run_pkgmgr(
            ["pkgmgr", "branch", "open", "feature/test", "--base", "develop"]
        )

        mock_open_branch.assert_called_once()
        _, kwargs = mock_open_branch.call_args
        self.assertEqual(kwargs.get("name"), "feature/test")
        self.assertEqual(kwargs.get("base_branch"), "develop")
        self.assertEqual(kwargs.get("cwd"), ".")

    @patch("pkgmgr.branch_commands.open_branch")
    def test_branch_open_without_name_uses_default_base(self, mock_open_branch) -> None:
        """
        pkgmgr branch open
        should invoke open_branch(name=None, base_branch='main', cwd='.')
        (the branch name will be asked interactively inside open_branch).
        """
        self._run_pkgmgr(["pkgmgr", "branch", "open"])

        mock_open_branch.assert_called_once()
        _, kwargs = mock_open_branch.call_args
        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")


if __name__ == "__main__":
    unittest.main()
