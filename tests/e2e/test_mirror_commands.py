#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E integration tests for the `pkgmgr mirror` command family.

This test class covers:

  - pkgmgr mirror --help
  - pkgmgr mirror list --preview --all
  - pkgmgr mirror diff --preview --all
  - pkgmgr mirror merge config file --preview --all
  - pkgmgr mirror setup --preview --all

All of these subcommands are fully wired at CLI level and do not
require mocks. With --preview, merge and setup do not perform
destructive actions, making them safe for CI execution.
"""

from __future__ import annotations

import io
import runpy
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr


class TestIntegrationMirrorCommands(unittest.TestCase):
    """
    E2E tests for `pkgmgr mirror` commands.
    """

    # ------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------
    def _run_pkgmgr(self, args: list[str]) -> str:
        """
        Execute pkgmgr with the given arguments and return captured stdout+stderr.

        - Treat SystemExit(0) or SystemExit(None) as success.
        - Convert non-zero exit codes into AssertionError.
        """
        original_argv = list(sys.argv)
        buffer = io.StringIO()
        cmd_repr = "pkgmgr " + " ".join(args)

        try:
            sys.argv = ["pkgmgr"] + args

            try:
                with redirect_stdout(buffer), redirect_stderr(buffer):
                    runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else None
                if code not in (0, None):
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {exc.code}. "
                        "Scroll up to inspect the pkgmgr output."
                    ) from exc

            return buffer.getvalue()

        finally:
            sys.argv = original_argv

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_mirror_help(self) -> None:
        """
        Ensure `pkgmgr mirror --help` runs successfully
        and prints a usage message for the mirror command.
        """
        output = self._run_pkgmgr(["mirror", "--help"])
        self.assertIn("usage:", output)
        self.assertIn("pkgmgr mirror", output)

    def test_mirror_list_preview_all(self) -> None:
        """
        `pkgmgr mirror list --preview --all` should run without error
        and produce some output for the selected repositories.
        """
        output = self._run_pkgmgr(["mirror", "list", "--preview", "--all"])
        # Do not assert specific wording; just ensure something was printed.
        self.assertTrue(
            output.strip(),
            msg="Expected `pkgmgr mirror list --preview --all` to produce output.",
        )

    def test_mirror_diff_preview_all(self) -> None:
        """
        `pkgmgr mirror diff --preview --all` should run without error
        and produce some diagnostic output (diff header, etc.).
        """
        output = self._run_pkgmgr(["mirror", "diff", "--preview", "--all"])
        self.assertTrue(
            output.strip(),
            msg="Expected `pkgmgr mirror diff --preview --all` to produce output.",
        )

    def test_mirror_merge_config_to_file_preview_all(self) -> None:
        """
        `pkgmgr mirror merge config file --preview --all` should run without error.

        In preview mode this does not change either config or MIRRORS files;
        it only prints what would be merged.
        """
        output = self._run_pkgmgr(
            [
                "mirror",
                "merge",
                "config",
                "file",
                "--preview",
                "--all",
            ]
        )
        self.assertTrue(
            output.strip(),
            msg=(
                "Expected `pkgmgr mirror merge config file --preview --all` "
                "to produce output."
            ),
        )

    def test_mirror_setup_preview_all(self) -> None:
        """
        `pkgmgr mirror setup --preview --all` should run without error.

        In preview mode only the intended Git operations and remote
        suggestions are printed; no real changes are made.
        """
        output = self._run_pkgmgr(["mirror", "setup", "--preview", "--all"])
        self.assertTrue(
            output.strip(),
            msg="Expected `pkgmgr mirror setup --preview --all` to produce output.",
        )


if __name__ == "__main__":
    unittest.main()
