#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-end style integration tests for the `pkgmgr release` CLI command.

These tests exercise the real top-level entry point (main.py) and mock
the high-level helper used by the CLI wiring
(pkgmgr.cli.commands.release.run_release) to ensure that argument
parsing and dispatch behave as expected, in particular the new `close`
flag.

The tests simulate real CLI calls like:

    pkgmgr release minor --preview --close

by manipulating sys.argv and executing main.py as __main__ via runpy.
"""

from __future__ import annotations

import runpy
import sys
import unittest
from unittest.mock import patch


class TestIntegrationReleaseCommand(unittest.TestCase):
    """Integration tests for `pkgmgr release` wiring."""

    def _run_pkgmgr(self, extra_args: list[str]) -> None:
        """
        Helper to invoke the `pkgmgr` console script via the real
        entry point (main.py).

        This simulates a real CLI call like:

            pkgmgr <extra_args...>

        by setting sys.argv accordingly and executing main.py as
        __main__ using runpy.run_module.
        """
        original_argv = list(sys.argv)
        try:
            # argv[0] is the program name; the rest are CLI arguments.
            sys.argv = ["pkgmgr"] + list(extra_args)
            runpy.run_module("main", run_name="__main__")
        finally:
            sys.argv = original_argv

    # ------------------------------------------------------------------
    # Behaviour without --close
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.release.run_release")
    @patch("pkgmgr.cli.dispatch._select_repo_for_current_directory")
    def test_release_without_close_flag(
        self,
        mock_select_repo,
        mock_run_release,
    ) -> None:
        """
        Calling `pkgmgr release patch --preview` should *not* enable
        the `close` flag by default.
        """
        # Ensure that the dispatch layer always selects a repository,
        # independent of any real config in the test environment.
        mock_select_repo.return_value = [
            {
                "directory": ".",
                "provider": "local",
                "account": "test",
                "repository": "dummy",
            }
        ]

        self._run_pkgmgr(["release", "patch", "--preview"])

        mock_run_release.assert_called_once()
        _args, kwargs = mock_run_release.call_args

        # CLI wiring
        self.assertEqual(kwargs.get("release_type"), "patch")
        self.assertTrue(
            kwargs.get("preview"),
            "preview should be True when --preview is used",
        )
        # Default: no --close → close=False
        self.assertFalse(
            kwargs.get("close"),
            "close must be False when --close is not given",
        )

    # ------------------------------------------------------------------
    # Behaviour with --close
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.release.run_release")
    @patch("pkgmgr.cli.dispatch._select_repo_for_current_directory")
    def test_release_with_close_flag(
        self,
        mock_select_repo,
        mock_run_release,
    ) -> None:
        """
        Calling `pkgmgr release minor --preview --close` should pass
        close=True into the helper used by the CLI wiring.
        """
        # Again: make sure there is always a selected repository.
        mock_select_repo.return_value = [
            {
                "directory": ".",
                "provider": "local",
                "account": "test",
                "repository": "dummy",
            }
        ]

        self._run_pkgmgr(["release", "minor", "--preview", "--close"])

        mock_run_release.assert_called_once()
        _args, kwargs = mock_run_release.call_args

        # CLI wiring
        self.assertEqual(kwargs.get("release_type"), "minor")
        self.assertTrue(
            kwargs.get("preview"),
            "preview should be True when --preview is used",
        )
        # With --close → close=True
        self.assertTrue(
            kwargs.get("close"),
            "close must be True when --close is given",
        )

    def test_release_help_runs_without_error(self) -> None:
        """
        Running `pkgmgr release --help` should succeed without touching the
        release helper and print a usage message for the release subcommand.

        This test intentionally does not mock anything to exercise the real
        CLI parser wiring in main.py.
        """
        import io
        import contextlib

        original_argv = list(sys.argv)
        buf = io.StringIO()

        try:
            sys.argv = ["pkgmgr", "release", "--help"]
            # argparse will call sys.exit(), so we expect a SystemExit here.
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_module("main", run_name="__main__")
        finally:
            sys.argv = original_argv

        # Help exit code is usually 0 (or sometimes None, which also means "no error")
        self.assertIn(cm.exception.code, (0, None))

        output = buf.getvalue()
        # Sanity checks: release help text should be present
        self.assertIn("usage:", output)
        self.assertIn("pkgmgr release", output)

if __name__ == "__main__":
    unittest.main()
