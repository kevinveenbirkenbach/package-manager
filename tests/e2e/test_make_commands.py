#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the `pkgmgr make` command.

We exercise the wrapper around `make` using the pkgmgr repository as
the standard target, but only in --preview mode to avoid side effects.
"""

from __future__ import annotations

import os
import runpy
import sys
import unittest

from test_version_commands import _load_pkgmgr_repo_dir


class TestIntegrationMakeCommands(unittest.TestCase):
    """
    E2E tests for the pkgmgr `make` wrapper.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Reuse the helper from the version tests to locate the pkgmgr repo
        cls.pkgmgr_repo_dir = _load_pkgmgr_repo_dir()

    def _run_pkgmgr_make(self, extra_args: list[str]) -> None:
        """
        Run `pkgmgr make ...` with the given extra args, from inside
        the pkgmgr repository.

        Any non-zero exit code is treated as test failure.
        """
        cmd_repr = "pkgmgr " + " ".join(extra_args)
        original_argv = list(sys.argv)
        original_cwd = os.getcwd()

        try:
            os.chdir(self.pkgmgr_repo_dir)
            sys.argv = ["pkgmgr"] + extra_args

            try:
                runpy.run_module("pkgmgr", run_name="__main__")
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

    def test_make_install_pkgmgr_preview(self) -> None:
        """
        Run: pkgmgr make pkgmgr install --preview

        - 'pkgmgr' is used as the standard repository identifier.
        - '--preview' ensures that no destructive make commands are
          actually executed inside the container.
        """
        self._run_pkgmgr_make(["make", "install", "--preview", "pkgmgr"])


if __name__ == "__main__":
    unittest.main()
