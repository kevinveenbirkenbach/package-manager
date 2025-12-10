"""
E2E/Integration tests for the tool-related subcommands' --help output.

We assert that calling:
  - pkgmgr explore --help
  - pkgmgr terminal --help
  - pkgmgr code --help

completes successfully. For --help, argparse exits with SystemExit(0),
which we treat as success and suppress in the helper.
"""

from __future__ import annotations

import os
import runpy
import sys
import unittest
from typing import List


# Resolve project root (the repo where main.py lives, e.g. /src)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
MAIN_PATH = os.path.join(PROJECT_ROOT, "main.py")


def _run_main(argv: List[str]) -> None:
    """
    Helper to run main.py with the given argv.

    This mimics a "pkgmgr ..." invocation in the E2E container.

    For --help invocations, argparse will call sys.exit(0), which raises
    SystemExit(0). We treat this as success and only re-raise non-zero
    exit codes.
    """
    old_argv = sys.argv
    try:
        sys.argv = ["pkgmgr"] + argv
        try:
            runpy.run_path(MAIN_PATH, run_name="__main__")
        except SystemExit as exc:  # argparse uses this for --help
            # SystemExit.code can be int, str or None; for our purposes:
            code = exc.code
            if code not in (0, None):
                # Non-zero exit code -> real error.
                raise
            # For 0/None: treat as success and swallow the exception.
    finally:
        sys.argv = old_argv


class TestToolsHelp(unittest.TestCase):
    """
    E2E/Integration tests for tool commands' --help screens.
    """

    def test_explore_help(self) -> None:
        """Ensure `pkgmgr explore --help` runs successfully."""
        _run_main(["explore", "--help"])

    def test_terminal_help(self) -> None:
        """Ensure `pkgmgr terminal --help` runs successfully."""
        _run_main(["terminal", "--help"])

    def test_code_help(self) -> None:
        """Ensure `pkgmgr code --help` runs successfully."""
        _run_main(["code", "--help"])


if __name__ == "__main__":
    unittest.main()