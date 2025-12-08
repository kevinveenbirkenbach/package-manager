#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-end style integration tests for the `pkgmgr release` CLI command.

These tests exercise the top-level `pkgmgr` entry point by invoking
the module as `__main__` and verifying that the underlying
`pkgmgr.release.release()` function is called with the expected
arguments, in particular the new `close` flag.
"""

from __future__ import annotations

import runpy
import sys
import unittest
from unittest.mock import patch


class TestIntegrationReleaseCommand(unittest.TestCase):
    """Integration tests for `pkgmgr release` wiring."""

    def _run_pkgmgr(self, argv: list[str]) -> None:
        """
        Helper to invoke the `pkgmgr` console script via `run_module`.

        This simulates a real CLI call like:

            pkgmgr release minor --preview --close
        """
        original_argv = list(sys.argv)
        try:
            sys.argv = argv
            # Entry point: the `pkgmgr` module is the console script.
            runpy.run_module("pkgmgr", run_name="__main__")
        finally:
            sys.argv = original_argv

    @patch("pkgmgr.release.release")
    def test_release_without_close_flag(self, mock_release) -> None:
        """
        Calling `pkgmgr release patch --preview` should *not* enable
        the `close` flag by default.
        """
        self._run_pkgmgr(["pkgmgr", "release", "patch", "--preview"])

        mock_release.assert_called_once()
        _args, kwargs = mock_release.call_args

        # CLI wiring
        self.assertEqual(kwargs.get("release_type"), "patch")
        self.assertTrue(kwargs.get("preview"), "preview should be True when --preview is used")
        # Default: no --close → close=False
        self.assertFalse(kwargs.get("close"), "close must be False when --close is not given")

    @patch("pkgmgr.release.release")
    def test_release_with_close_flag(self, mock_release) -> None:
        """
        Calling `pkgmgr release minor --preview --close` should pass
        close=True into pkgmgr.release.release().
        """
        self._run_pkgmgr(["pkgmgr", "release", "minor", "--preview", "--close"])

        mock_release.assert_called_once()
        _args, kwargs = mock_release.call_args

        # CLI wiring
        self.assertEqual(kwargs.get("release_type"), "minor")
        self.assertTrue(kwargs.get("preview"), "preview should be True when --preview is used")
        # With --close → close=True
        self.assertTrue(kwargs.get("close"), "close must be True when --close is given")


if __name__ == "__main__":
    unittest.main()
