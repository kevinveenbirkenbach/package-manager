#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for NixFlakeInstaller using unittest (no pytest).

Covers:
- Successful installation (returncode == 0)
- Mandatory failure → SystemExit with correct code
- Optional failure (pkgmgr default) → no raise, but warning
- supports() behavior incl. PKGMGR_DISABLE_NIX_FLAKE_INSTALLER
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.install.installers.nix import NixFlakeInstaller


class DummyCtx:
    """Minimal context object to satisfy NixFlakeInstaller.run() / supports()."""

    def __init__(
        self,
        identifier: str,
        repo_dir: str,
        preview: bool = False,
        quiet: bool = False,
        force_update: bool = False,
    ):
        self.identifier = identifier
        self.repo_dir = repo_dir
        self.preview = preview
        self.quiet = quiet
        self.force_update = force_update


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
        if os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    @staticmethod
    def _cp(code: int) -> subprocess.CompletedProcess:
        # stdout/stderr are irrelevant here, but keep shape realistic
        return subprocess.CompletedProcess(args=["nix"], returncode=code, stdout="", stderr="")

    @staticmethod
    def _enable_nix_in_module(which_patch) -> None:
        """Ensure shutil.which('nix') in nix module returns a path."""
        which_patch.return_value = "/usr/bin/nix"

    def test_nix_flake_run_success(self) -> None:
        """
        When run_command returns success (returncode 0), installer
        should report success and not raise.
        """
        ctx = DummyCtx(identifier="some-lib", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        buf = io.StringIO()
        with patch("pkgmgr.actions.install.installers.nix.installer.shutil.which") as which_mock, patch(
            "pkgmgr.actions.install.installers.nix.installer.os.path.exists", return_value=True
        ), patch(
            "pkgmgr.actions.install.installers.nix.runner.subprocess.run"
        ) as subproc_mock, redirect_stdout(buf):

            self._enable_nix_in_module(which_mock)

            subproc_mock.return_value = subprocess.CompletedProcess(
                args=["nix", "profile", "list", "--json"],
                returncode=0,
                stdout='{"elements": []}',
                stderr="",
            )

            # Install succeeds
            run_cmd_mock.return_value = self._cp(0)

            self.assertTrue(installer.supports(ctx))
            installer.run(ctx)

        out = buf.getvalue()
        self.assertIn("[nix] install: nix profile install", out)
        self.assertIn("[nix] output 'default' successfully installed.", out)

        run_cmd_mock.assert_called_with(
            f"nix profile install {self.repo_dir}#default",
            cwd=self.repo_dir,
            preview=False,
            allow_failure=True,
        )

    def test_nix_flake_run_mandatory_failure_raises(self) -> None:
        """
        For a generic repository, 'default' is mandatory.
        A non-zero return code must raise SystemExit with that code.
        """
        ctx = DummyCtx(identifier="some-lib", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        buf = io.StringIO()
        with patch("pkgmgr.actions.install.installers.nix.installer.shutil.which") as which_mock, patch(
            "pkgmgr.actions.install.installers.nix.installer.os.path.exists", return_value=True
        ), patch(
            "pkgmgr.actions.install.installers.nix.runner.subprocess.run"
        ) as subproc_mock, redirect_stdout(buf):

            self._enable_nix_in_module(which_mock)

            subproc_mock.return_value = subprocess.CompletedProcess(
                args=["nix", "profile", "list", "--json"],
                returncode=0,
                stdout='{"elements": []}',
                stderr="",
            )

            # First install fails, retry fails -> should raise SystemExit(1)
            run_cmd_mock.side_effect = [self._cp(1), self._cp(1)]

            self.assertTrue(installer.supports(ctx))
            with self.assertRaises(SystemExit) as cm:
                installer.run(ctx)

        self.assertEqual(cm.exception.code, 1)
        out = buf.getvalue()
        self.assertIn("[nix] install: nix profile install", out)
        self.assertIn("[ERROR] Failed to install Nix flake output 'default' (exit 1)", out)

    def test_nix_flake_run_optional_failure_does_not_raise(self) -> None:
        """
        For pkgmgr/package-manager repositories:
          - 'pkgmgr' output is mandatory
          - 'default' output is optional
        Failure of optional output must not raise.
        """
        ctx = DummyCtx(identifier="pkgmgr", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        buf = io.StringIO()
        with patch("pkgmgr.actions.install.installers.nix.installer.shutil.which") as which_mock, patch(
            "pkgmgr.actions.install.installers.nix.installer.os.path.exists", return_value=True
        ), patch(
            "pkgmgr.actions.install.installers.nix.runner.subprocess.run"
        ) as subproc_mock, redirect_stdout(buf):

            self._enable_nix_in_module(which_mock)

            subproc_mock.return_value = subprocess.CompletedProcess(
                args=["nix", "profile", "list", "--json"],
                returncode=0,
                stdout='{"elements": []}',
                stderr="",
            )

            # pkgmgr install ok; default fails twice (initial + retry)
            run_cmd_mock.side_effect = [self._cp(0), self._cp(1), self._cp(1)]

            self.assertTrue(installer.supports(ctx))

            # Must NOT raise despite optional failure
            installer.run(ctx)

        out = buf.getvalue()

        # Should announce both outputs
        self.assertIn("ensuring outputs: pkgmgr, default", out)

        # First output ok
        self.assertIn("[nix] output 'pkgmgr' successfully installed.", out)

        # Second output failed but no raise
        self.assertIn("[ERROR] Failed to install Nix flake output 'default' (exit 1)", out)
        self.assertIn("[WARNING] Continuing despite failure of optional output 'default'.", out)

        # Verify run_command was called for both outputs (default twice due to retry)
        expected_calls = [
            (f"nix profile install {self.repo_dir}#pkgmgr",),
            (f"nix profile install {self.repo_dir}#default",),
            (f"nix profile install {self.repo_dir}#default",),
        ]
        actual_cmds = [c.args[0] for c in run_cmd_mock.call_args_list]
        self.assertEqual(actual_cmds, [e[0] for e in expected_calls])

    def test_nix_flake_supports_respects_disable_env(self) -> None:
        """
        PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 must disable the installer,
        even if flake.nix exists and nix is available.
        """
        ctx = DummyCtx(identifier="pkgmgr", repo_dir=self.repo_dir, quiet=False)
        installer = NixFlakeInstaller()

        with patch("pkgmgr.actions.install.installers.nix.installer.shutil.which") as which_mock, patch(
            "pkgmgr.actions.install.installers.nix.installer.os.path.exists", return_value=True
        ):
            self._enable_nix_in_module(which_mock)
            os.environ["PKGMGR_DISABLE_NIX_FLAKE_INSTALLER"] = "1"
            self.assertFalse(installer.supports(ctx))

if __name__ == "__main__":
    unittest.main()
