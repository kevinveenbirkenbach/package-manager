#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-end tests for the `pkgmgr path` command.

We verify two usage patterns:

1) pkgmgr path --all
   - Should print the paths of all configured repositories.

2) pkgmgr path pkgmgr
   - Should print the path for the repository identified as "pkgmgr".

Both tests are considered successful if the command completes without
raising an exception and exits with code 0 (or no explicit exit code).
"""

from __future__ import annotations

import io
import runpy
import sys
import unittest
from contextlib import redirect_stdout


class TestPathCommandsE2E(unittest.TestCase):
    def _run_pkgmgr_path(self, argv_tail: list[str]) -> str:
        """
        Helper to run `pkgmgr path ...` via main.py and return stdout.

        Args:
            argv_tail: List of arguments that follow the "pkgmgr" executable,
                       e.g. ["path", "--all"] or ["path", "pkgmgr"].

        Returns:
            The captured stdout produced by the command.

        Raises:
            AssertionError if the command exits with a non-zero exit code.
        """
        original_argv = sys.argv
        cmd_repr = "pkgmgr " + " ".join(argv_tail)
        buffer = io.StringIO()

        try:
            sys.argv = ["pkgmgr"] + argv_tail

            try:
                # Capture stdout while running the CLI entry point.
                with redirect_stdout(buffer):
                    runpy.run_module("pkgmgr", run_name="__main__")
            except SystemExit as exc:
                # Determine the exit code (int or string)
                exit_code = exc.code
                if isinstance(exit_code, int):
                    numeric_code = exit_code
                else:
                    try:
                        numeric_code = int(exit_code)
                    except (TypeError, ValueError):
                        numeric_code = None

                # Treat SystemExit(0) as success.
                if numeric_code == 0 or numeric_code is None:
                    return buffer.getvalue()

                # Non-zero exit code → fail with helpful message.
                raise AssertionError(
                    f"{cmd_repr!r} failed with exit code {exit_code!r}. "
                    "Scroll up to see the full pkgmgr output inside the container."
                ) from exc

        finally:
            sys.argv = original_argv

        # No SystemExit raised → also treat as success.
        return buffer.getvalue()

    def test_path_all_repositories(self) -> None:
        """
        Run: pkgmgr path --all

        The test succeeds if the command exits successfully and prints
        at least one non-empty line.
        """
        output = self._run_pkgmgr_path(["path", "--all"])
        lines = [line for line in output.splitlines() if line.strip()]

        # We only assert that something was printed; we do not assume
        # that repositories are already cloned on disk.
        self.assertGreater(
            len(lines),
            0,
            msg="Expected `pkgmgr path --all` to print at least one path.",
        )

    def test_path_single_pkgmgr(self) -> None:
        """
        Run: pkgmgr path pkgmgr

        The test succeeds if the command exits successfully and prints
        at least one non-empty line (the resolved directory).
        """
        output = self._run_pkgmgr_path(["path", "pkgmgr"])
        lines = [line for line in output.splitlines() if line.strip()]

        self.assertGreater(
            len(lines),
            0,
            msg="Expected `pkgmgr path pkgmgr` to print at least one path.",
        )


if __name__ == "__main__":
    unittest.main()
