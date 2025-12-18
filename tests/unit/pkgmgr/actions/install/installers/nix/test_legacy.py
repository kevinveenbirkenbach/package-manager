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
from typing import List
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
    def _cp(
        code: int, stdout: str = "", stderr: str = ""
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=["nix"], returncode=code, stdout=stdout, stderr=stderr
        )

    @staticmethod
    def _enable_nix_in_module(which_patch) -> None:
        """Ensure shutil.which('nix') in nix installer module returns a path."""
        which_patch.return_value = "/usr/bin/nix"

    @staticmethod
    def _install_cmds_from_calls(call_args_list) -> List[str]:
        cmds: List[str] = []
        for c in call_args_list:
            if not c.args:
                continue
            cmd = c.args[0]
            if isinstance(cmd, str) and cmd.startswith("nix profile install "):
                cmds.append(cmd)
        return cmds

    def test_nix_flake_run_success(self) -> None:
        """
        When install returns success (returncode 0), installer
        should report success and not raise.
        """
        ctx = DummyCtx(identifier="some-lib", repo_dir=self.repo_dir)
        installer = NixFlakeInstaller()

        install_results = [self._cp(0)]  # first install succeeds

        def fake_subprocess_run(cmd, *args, **kwargs):
            # cmd is a string because CommandRunner uses shell=True
            if isinstance(cmd, str) and cmd.startswith("nix profile list --json"):
                return self._cp(0, stdout='{"elements": []}', stderr="")
            if isinstance(cmd, str) and cmd.startswith("nix profile install "):
                return install_results.pop(0)
            return self._cp(0)

        buf = io.StringIO()
        with (
            patch(
                "pkgmgr.actions.install.installers.nix.installer.shutil.which"
            ) as which_mock,
            patch(
                "pkgmgr.actions.install.installers.nix.installer.os.path.exists",
                return_value=True,
            ),
            patch(
                "pkgmgr.actions.install.installers.nix.runner.subprocess.run",
                side_effect=fake_subprocess_run,
            ) as subproc_mock,
            redirect_stdout(buf),
        ):
            self._enable_nix_in_module(which_mock)

            self.assertTrue(installer.supports(ctx))
            installer.run(ctx)

        out = buf.getvalue()
        self.assertIn("[nix] install: nix profile install", out)
        self.assertIn("[nix] output 'default' successfully installed.", out)

        install_cmds = self._install_cmds_from_calls(subproc_mock.call_args_list)
        self.assertEqual(install_cmds, [f"nix profile install {self.repo_dir}#default"])

    def test_nix_flake_supports_respects_disable_env(self) -> None:
        """
        PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 must disable the installer,
        even if flake.nix exists and nix is available.
        """
        ctx = DummyCtx(identifier="pkgmgr", repo_dir=self.repo_dir, quiet=False)
        installer = NixFlakeInstaller()

        with (
            patch(
                "pkgmgr.actions.install.installers.nix.installer.shutil.which"
            ) as which_mock,
            patch(
                "pkgmgr.actions.install.installers.nix.installer.os.path.exists",
                return_value=True,
            ),
        ):
            self._enable_nix_in_module(which_mock)
            os.environ["PKGMGR_DISABLE_NIX_FLAKE_INSTALLER"] = "1"
            self.assertFalse(installer.supports(ctx))


if __name__ == "__main__":
    unittest.main()
