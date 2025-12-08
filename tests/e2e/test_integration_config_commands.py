#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the `pkgmgr config` command.

We only exercise non-interactive, read-only subcommands here:
  - pkgmgr config show --all
  - pkgmgr config show pkgmgr

Interactive or mutating subcommands like `add`, `edit`, `init`,
`delete`, `ignore` are intentionally not covered in E2E tests to keep
the CI environment non-interactive and side-effect free.
"""

from __future__ import annotations

import runpy
import sys
import unittest


def _run_pkgmgr_config(extra_args: list[str]) -> None:
    """
    Run `pkgmgr config ...` with the given extra args.

    Any non-zero SystemExit is treated as a test failure and turned into
    an AssertionError with diagnostics.
    """
    cmd_repr = "pkgmgr " + " ".join(extra_args)
    original_argv = list(sys.argv)

    try:
        sys.argv = ["pkgmgr"] + extra_args

        try:
            runpy.run_module("main", run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else str(exc.code)
            if code != 0:
                print("[TEST] SystemExit caught while running", cmd_repr)
                print(f"[TEST] Exit code: {code}")
                raise AssertionError(
                    f"{cmd_repr!r} failed with exit code {code}. "
                    "Scroll up to inspect the output printed before failure."
                ) from exc
            # exit code 0 is success

    finally:
        sys.argv = original_argv


class TestIntegrationConfigCommands(unittest.TestCase):
    """
    E2E tests for `pkgmgr config` subcommands.
    """

    def test_config_show_all(self) -> None:
        """
        Run: pkgmgr config show --all
        """
        _run_pkgmgr_config(["config", "show", "--all"])

    def test_config_show_pkgmgr(self) -> None:
        """
        Run: pkgmgr config show pkgmgr

        Uses 'pkgmgr' as the standard repository identifier.
        """
        _run_pkgmgr_config(["config", "show", "pkgmgr"])


if __name__ == "__main__":
    unittest.main()
