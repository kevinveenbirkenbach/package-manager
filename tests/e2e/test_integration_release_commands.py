#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the `pkgmgr release` command.

We deliberately only test a *negative* path here, to avoid mutating
the real repositories (bumping versions, editing changelogs) during
CI runs.

The test verifies that:

  - Calling `pkgmgr release` with a non-existent repository identifier
    results in a non-zero exit code and a helpful error.
"""

from __future__ import annotations

import runpy
import sys
import unittest


class TestIntegrationReleaseCommand(unittest.TestCase):
    """
    E2E tests for `pkgmgr release`.
    """
    
    def _run_release_expect_failure(self) -> None:
        cmd_repr = "pkgmgr release patch does-not-exist-xyz"
        original_argv = list(sys.argv)

        try:
            sys.argv = [
                "pkgmgr",
                "release",
                "patch",
                "does-not-exist-xyz",
            ]
            try:
                runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                # Hier wirklich verifizieren:
                assert code != 0, f"{cmd_repr!r} unexpectedly succeeded with exit code 0"
                print("[TEST] pkgmgr release failed as expected")
                print(f"[TEST] Command   : {cmd_repr}")
                print(f"[TEST] Exit code : {code}")
            else:
                # Kein SystemExit -> auf jeden Fall falsch
                raise AssertionError(
                    f"{cmd_repr!r} returned normally (expected non-zero exit)."
                )
        finally:
            sys.argv = original_argv


    def test_release_for_unknown_repo_fails_cleanly(self) -> None:
        self._run_release_expect_failure()

if __name__ == "__main__":
    unittest.main()

