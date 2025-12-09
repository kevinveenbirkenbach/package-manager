#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the "tools" commands:

  - pkgmgr code
  - pkgmgr explore
  - pkgmgr terminal

These commands spawn external GUI tools (VS Code, Nautilus,
GNOME Terminal) which are usually not available in a headless CI
container. Therefore, the entire test class is skipped by default.

If you run the tests on a local desktop environment where these
commands exist and can be spawned, you can remove or modify the
@skip decorator.
"""

from __future__ import annotations

import os
import runpy
import sys
import unittest

from test_version_commands import _load_pkgmgr_repo_dir


@unittest.skip(
    "Requires GUI tools (code, nautilus, gnome-terminal) inside the "
    "test environment; skipped by default in CI."
)
class TestIntegrationToolsCommands(unittest.TestCase):
    """
    E2E tests for pkgmgr 'code', 'explore', and 'terminal' commands.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pkgmgr_repo_dir = _load_pkgmgr_repo_dir()

    def _run_pkgmgr_tools_command(self, extra_args: list[str]) -> None:
        """
        Run a 'tools' style command (code/explore/terminal) for pkgmgr.

        Any non-zero exit code is treated as a test failure.
        """
        cmd_repr = "pkgmgr " + " ".join(extra_args)
        original_argv = list(sys.argv)
        original_cwd = os.getcwd()

        try:
            os.chdir(self.pkgmgr_repo_dir)
            sys.argv = ["pkgmgr"] + extra_args

            try:
                runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                if code != 0:
                    print("[TEST] SystemExit caught while running", cmd_repr)
                    print(f"[TEST] Working directory: {os.getcwd()}")
                    print(f"[TEST] Exit code: {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {code}. "
                        "Scroll up to inspect the output printed before failure."
                    ) from exc
                # exit code 0 is success

        finally:
            os.chdir(original_cwd)
            sys.argv = original_argv

    def test_code_workspace_for_pkgmgr(self) -> None:
        """
        Run: pkgmgr code pkgmgr
        """
        self._run_pkgmgr_tools_command(["code", "pkgmgr"])

    def test_explore_pkgmgr(self) -> None:
        """
        Run: pkgmgr explore pkgmgr
        """
        self._run_pkgmgr_tools_command(["explore", "pkgmgr"])

    def test_terminal_pkgmgr(self) -> None:
        """
        Run: pkgmgr terminal pkgmgr
        """
        self._run_pkgmgr_tools_command(["terminal", "pkgmgr"])


if __name__ == "__main__":
    unittest.main()
