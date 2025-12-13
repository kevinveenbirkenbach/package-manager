#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E integration tests for the `pkgmgr mirror` command family.

Covered commands:

  - pkgmgr mirror --help
  - pkgmgr mirror list --preview --all
  - pkgmgr mirror diff --preview --all
  - pkgmgr mirror merge config file --preview --all
  - pkgmgr mirror setup --preview --all
  - pkgmgr mirror check --preview --all
  - pkgmgr mirror provision --preview --all

All commands are executed via the real CLI entry point (main module).
With --preview enabled, all operations are non-destructive and safe
to run inside CI containers.
"""

import io
import runpy
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr


class TestIntegrationMirrorCommands(unittest.TestCase):
    """
    End-to-end tests for `pkgmgr mirror` commands.
    """

    # ------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------
    def _run_pkgmgr(self, args):
        """
        Execute pkgmgr with the given arguments and return captured output.

        - Treat SystemExit(0) or SystemExit(None) as success.
        - Any other exit code is considered a test failure.
        """
        original_argv = list(sys.argv)
        buffer = io.StringIO()
        cmd_repr = "pkgmgr " + " ".join(args)

        try:
            sys.argv = ["pkgmgr"] + list(args)

            try:
                with redirect_stdout(buffer), redirect_stderr(buffer):
                    runpy.run_module("pkgmgr", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else None
                if code not in (0, None):
                    raise AssertionError(
                        "%r failed with exit code %r.\n\nOutput:\n%s"
                        % (cmd_repr, exc.code, buffer.getvalue())
                    )

            return buffer.getvalue()

        finally:
            sys.argv = original_argv

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_mirror_help(self):
        """
        `pkgmgr mirror --help` should run without error and print usage info.
        """
        output = self._run_pkgmgr(["mirror", "--help"])
        self.assertIn("usage:", output)
        self.assertIn("pkgmgr mirror", output)

    def test_mirror_list_preview_all(self):
        """
        `pkgmgr mirror list --preview --all`
        """
        output = self._run_pkgmgr(
            ["mirror", "list", "--preview", "--all"]
        )
        self.assertTrue(
            output.strip(),
            "Expected output from mirror list",
        )

    def test_mirror_diff_preview_all(self):
        """
        `pkgmgr mirror diff --preview --all`
        """
        output = self._run_pkgmgr(
            ["mirror", "diff", "--preview", "--all"]
        )
        self.assertTrue(
            output.strip(),
            "Expected output from mirror diff",
        )

    def test_mirror_merge_config_to_file_preview_all(self):
        """
        `pkgmgr mirror merge config file --preview --all`
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
            "Expected output from mirror merge (config -> file)",
        )

    def test_mirror_setup_preview_all(self):
        """
        `pkgmgr mirror setup --preview --all`
        """
        output = self._run_pkgmgr(
            ["mirror", "setup", "--preview", "--all"]
        )
        self.assertTrue(
            output.strip(),
            "Expected output from mirror setup",
        )

    def test_mirror_check_preview_all(self):
        """
        `pkgmgr mirror check --preview --all`

        Performs non-destructive remote checks (git ls-remote).
        """
        output = self._run_pkgmgr(
            ["mirror", "check", "--preview", "--all"]
        )
        self.assertTrue(
            output.strip(),
            "Expected output from mirror check",
        )

    def test_mirror_provision_preview_all(self):
        """
        `pkgmgr mirror provision --preview --all`

        In preview mode this MUST NOT create remote repositories.
        """
        output = self._run_pkgmgr(
            ["mirror", "provision", "--preview", "--all"]
        )
        self.assertTrue(
            output.strip(),
            "Expected output from mirror provision (preview)",
        )


if __name__ == "__main__":
    unittest.main()
