#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for NixFlakeInstaller using unittest (no pytest).

Covers:
- Successful installation (exit_code == 0)
- Mandatory failure → SystemExit with correct code
- Optional failure (pkgmgr default) → no raise, but warning
- supports() behavior incl. PKGMGR_DISABLE_NIX_FLAKE_INSTALLER
"""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.install.installers.nix_flake import NixFlakeInstaller


class DummyCtx:
    """Minimal context object to satisfy NixFlakeInstaller.run() / supports()."""

    def __init__(self, identifier: str, repo_dir: str, preview: bool = False):
        self.identifier = identifier
        self.repo_dir = repo_dir
        self.preview = preview


class TestNixFlakeInstaller(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary repository directory with a flake.nix file
        self._tmpdir = tempfile.mkdtemp(prefix="nix_flake_test_")
        self.repo_dir = self._tmpdir
        flake_path = os.path.join(self.repo_dir, "flake.nix")
        with open(flake_path, "w", encoding="utf-8") as f:
            f.write("{}\n")

        # Ensure the disable env var is not set by default
        os.environ.pop("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER", None)

    def tearDown(self) -> None:
        # Cleanup temporary directory
        if os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _enable_nix_in_module(self, which_patch):
        """Ensure shutil.which('nix') in nix_flake module returns a path."""
        which_patch.return_value = "/usr/bin/nix"

    def test_nix_flake_run_success(self):
        """
        When os.system returns a successful exit code, the installer
        should report success and not raise.
        """
        ctx = DummyCtx(identifier="some-lib", repo_dir=self.repo_dir)

        installer = NixFlakeInstaller()

        buf = io.StringIO()
        with patch(
            "pkgmgr.actions.install.installers.nix_flake.shutil.which"
        ) as which_mock, patch(
            "pkgmgr.actions.install.installers.nix_flake.os.system"
        ) as system_mock, redirect_stdout(buf):
            self._enable_nix_in_module(which_mock)

            # Simulate os.system returning success (exit code 0)
            system_mock.return_value = 0

            # Sanity: supports() must be True
            self.assertTrue(installer.supports(ctx))

            installer.run(ctx)

        out = buf.getvalue()
        self.assertIn("[INFO] Running: nix profile install", out)
        self.assertIn("Nix flake output 'default' successfully installed.", out)

        # Ensure the nix command was actually invoked
        system_mock.assert_called_with(
            f"nix profile install {self.repo_dir}#default"
        )

    def test_nix_flake_run_mandatory_failure_raises(self):
        """
        For a generic repository (identifier not pkgmgr/package-manager),
        `default` is mandatory and a non-zero exit code should raise SystemExit
        with the real exit code (e.g. 1, not 256).
        """
        ctx = DummyCtx(identifier="some-lib", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        buf = io.StringIO()
        with patch(
            "pkgmgr.actions.install.installers.nix_flake.shutil.which"
        ) as which_mock, patch(
            "pkgmgr.actions.install.installers.nix_flake.os.system"
        ) as system_mock, redirect_stdout(buf):
            self._enable_nix_in_module(which_mock)

            # Simulate os.system returning encoded status for exit code 1
            # os.system encodes exit code as (exit_code << 8)
            system_mock.return_value = 1 << 8

            self.assertTrue(installer.supports(ctx))

            with self.assertRaises(SystemExit) as cm:
                installer.run(ctx)

        # The real exit code should be 1 (not 256)
        self.assertEqual(cm.exception.code, 1)

        out = buf.getvalue()
        self.assertIn("[INFO] Running: nix profile install", out)
        self.assertIn("[Error] Failed to install Nix flake output 'default'", out)
        self.assertIn("[Error] Command exited with code 1", out)

    def test_nix_flake_run_optional_failure_does_not_raise(self):
        """
        For the package-manager repository, the 'default' output is optional.
        Failure to install it must not raise, but should log a warning instead.
        """
        ctx = DummyCtx(identifier="pkgmgr", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        calls = []

        def fake_system(cmd: str) -> int:
            calls.append(cmd)
            # First call (pkgmgr) → success
            if len(calls) == 1:
                return 0
            # Second call (default) → failure (exit code 1 encoded)
            return 1 << 8

        buf = io.StringIO()
        with patch(
            "pkgmgr.actions.install.installers.nix_flake.shutil.which"
        ) as which_mock, patch(
            "pkgmgr.actions.install.installers.nix_flake.os.system",
            side_effect=fake_system,
        ), redirect_stdout(buf):
            self._enable_nix_in_module(which_mock)

            self.assertTrue(installer.supports(ctx))

            # Optional failure must NOT raise
            installer.run(ctx)

        out = buf.getvalue()

        # Both outputs should have been mentioned
        self.assertIn(
            "attempting to install profile outputs: pkgmgr, default", out
        )

        # First output ("pkgmgr") succeeded
        self.assertIn(
            "Nix flake output 'pkgmgr' successfully installed.", out
        )

        # Second output ("default") failed but did not raise
        self.assertIn(
            "[Error] Failed to install Nix flake output 'default'", out
        )
        self.assertIn("[Error] Command exited with code 1", out)
        self.assertIn(
            "Continuing despite failure to install optional output 'default'.",
            out,
        )

        # Ensure we actually called os.system twice (pkgmgr and default)
        self.assertEqual(len(calls), 2)
        self.assertIn(
            f"nix profile install {self.repo_dir}#pkgmgr",
            calls[0],
        )
        self.assertIn(
            f"nix profile install {self.repo_dir}#default",
            calls[1],
        )

    def test_nix_flake_supports_respects_disable_env(self):
        """
        PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 must disable the installer,
        even if flake.nix exists and nix is available.
        """
        ctx = DummyCtx(identifier="pkgmgr", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        with patch(
            "pkgmgr.actions.install.installers.nix_flake.shutil.which"
        ) as which_mock:
            self._enable_nix_in_module(which_mock)
            os.environ["PKGMGR_DISABLE_NIX_FLAKE_INSTALLER"] = "1"

            self.assertFalse(installer.supports(ctx))


if __name__ == "__main__":
    unittest.main()
