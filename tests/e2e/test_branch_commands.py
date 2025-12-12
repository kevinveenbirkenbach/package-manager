from __future__ import annotations

import runpy
import sys
import unittest
from unittest.mock import patch


class TestIntegrationBranchCommands(unittest.TestCase):
    """
    Integration tests for the `pkgmgr branch` CLI wiring.

    These tests execute the real entry point (main.py) and mock
    the high-level helpers to ensure that argument parsing and
    dispatch behave as expected.
    """

    def _run_pkgmgr(self, extra_args: list[str]) -> None:
        """
        Run the main entry point with the given extra args, as if called via:

            pkgmgr <extra_args...>

        We explicitly set sys.argv and execute main.py as __main__ using runpy.
        """
        original_argv = list(sys.argv)
        try:
            # argv[0] is the program name; the rest are CLI arguments.
            sys.argv = ["pkgmgr"] + list(extra_args)
            runpy.run_module("pkgmgr", run_name="__main__")
        finally:
            sys.argv = original_argv

    @patch("pkgmgr.cli.commands.branch.open_branch")
    def test_branch_open_with_name_and_base(self, mock_open_branch) -> None:
        """
        `pkgmgr branch open feature/test --base develop` must forward
        the name and base branch to open_branch() with cwd=".".
        """
        self._run_pkgmgr(
            ["branch", "open", "feature/test", "--base", "develop"]
        )

        mock_open_branch.assert_called_once()
        _, kwargs = mock_open_branch.call_args
        self.assertEqual(kwargs.get("name"), "feature/test")
        self.assertEqual(kwargs.get("base_branch"), "develop")
        self.assertEqual(kwargs.get("cwd"), ".")

    @patch("pkgmgr.cli.commands.branch.open_branch")
    def test_branch_open_without_name_uses_default_base(
        self,
        mock_open_branch,
    ) -> None:
        """
        `pkgmgr branch open` without a name must still call open_branch(),
        passing name=None and the default base branch 'main'.
        """
        self._run_pkgmgr(["branch", "open"])

        mock_open_branch.assert_called_once()
        _, kwargs = mock_open_branch.call_args
        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")

    # ------------------------------------------------------------------
    # close subcommand
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_branch_close_with_name_and_base(self, mock_close_branch) -> None:
        """
        `pkgmgr branch close feature/test --base develop` must forward
        the name and base branch to close_branch() with cwd=".".
        """
        self._run_pkgmgr(
            ["branch", "close", "feature/test", "--base", "develop"]
        )

        mock_close_branch.assert_called_once()
        _, kwargs = mock_close_branch.call_args
        self.assertEqual(kwargs.get("name"), "feature/test")
        self.assertEqual(kwargs.get("base_branch"), "develop")
        self.assertEqual(kwargs.get("cwd"), ".")

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_branch_close_without_name_uses_default_base(
        self,
        mock_close_branch,
    ) -> None:
        """
        `pkgmgr branch close` without a name must still call close_branch(),
        passing name=None and the default base branch 'main'.

        The branch helper will then resolve the actual base (main/master)
        internally.
        """
        self._run_pkgmgr(["branch", "close"])

        mock_close_branch.assert_called_once()
        _, kwargs = mock_close_branch.call_args
        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")


if __name__ == "__main__":
    unittest.main()
