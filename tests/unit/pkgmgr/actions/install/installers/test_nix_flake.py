#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
from unittest import mock
from unittest.mock import MagicMock, patch

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.nix_flake import NixFlakeInstaller


class TestNixFlakeInstaller(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = {"repository": "package-manager"}
        # Important: identifier "pkgmgr" triggers both "pkgmgr" and "default"
        self.ctx = RepoContext(
            repo=self.repo,
            identifier="pkgmgr",
            repo_dir="/tmp/repo",
            repositories_base_dir="/tmp",
            bin_dir="/bin",
            all_repos=[self.repo],
            no_verification=False,
            preview=False,
            quiet=False,
            clone_mode="ssh",
            update_dependencies=False,
        )
        self.installer = NixFlakeInstaller()

    @patch("pkgmgr.actions.repository.install.installers.nix_flake.os.path.exists")
    @patch("pkgmgr.actions.repository.install.installers.nix_flake.shutil.which")
    def test_supports_true_when_nix_and_flake_exist(
        self,
        mock_which: MagicMock,
        mock_exists: MagicMock,
    ) -> None:
        mock_which.return_value = "/usr/bin/nix"
        mock_exists.return_value = True

        with patch.dict(os.environ, {"PKGMGR_DISABLE_NIX_FLAKE_INSTALLER": ""}, clear=False):
            self.assertTrue(self.installer.supports(self.ctx))

        mock_which.assert_called_once_with("nix")
        mock_exists.assert_called_once_with(
            os.path.join(self.ctx.repo_dir, self.installer.FLAKE_FILE)
        )

    @patch("pkgmgr.actions.repository.install.installers.nix_flake.os.path.exists")
    @patch("pkgmgr.actions.repository.install.installers.nix_flake.shutil.which")
    def test_supports_false_when_nix_missing(
        self,
        mock_which: MagicMock,
        mock_exists: MagicMock,
    ) -> None:
        mock_which.return_value = None
        mock_exists.return_value = True  # flake exists but nix is missing

        with patch.dict(os.environ, {"PKGMGR_DISABLE_NIX_FLAKE_INSTALLER": ""}, clear=False):
            self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.actions.repository.install.installers.nix_flake.os.path.exists")
    @patch("pkgmgr.actions.repository.install.installers.nix_flake.shutil.which")
    def test_supports_false_when_disabled_via_env(
        self,
        mock_which: MagicMock,
        mock_exists: MagicMock,
    ) -> None:
        mock_which.return_value = "/usr/bin/nix"
        mock_exists.return_value = True

        with patch.dict(
            os.environ,
            {"PKGMGR_DISABLE_NIX_FLAKE_INSTALLER": "1"},
            clear=False,
        ):
            self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.actions.repository.install.installers.nix_flake.NixFlakeInstaller.supports")
    @patch("pkgmgr.actions.repository.install.installers.nix_flake.run_command")
    def test_run_removes_old_profile_and_installs_outputs(
        self,
        mock_run_command: MagicMock,
        mock_supports: MagicMock,
    ) -> None:
        """
        run() should:
        - remove the old profile
        - install both 'pkgmgr' and 'default' outputs for identifier 'pkgmgr'
        - call commands in the correct order
        """
        mock_supports.return_value = True

        commands: list[str] = []

        def side_effect(cmd: str, cwd: str | None = None, preview: bool = False, **_: object) -> None:
            commands.append(cmd)

        mock_run_command.side_effect = side_effect

        with patch.dict(os.environ, {"PKGMGR_DISABLE_NIX_FLAKE_INSTALLER": ""}, clear=False):
            self.installer.run(self.ctx)

        remove_cmd = f"nix profile remove {self.installer.PROFILE_NAME} || true"
        install_pkgmgr_cmd = f"nix profile install {self.ctx.repo_dir}#pkgmgr"
        install_default_cmd = f"nix profile install {self.ctx.repo_dir}#default"

        self.assertIn(remove_cmd, commands)
        self.assertIn(install_pkgmgr_cmd, commands)
        self.assertIn(install_default_cmd, commands)

        self.assertEqual(commands[0], remove_cmd)

    @patch("pkgmgr.actions.repository.install.installers.nix_flake.shutil.which")
    @patch("pkgmgr.actions.repository.install.installers.nix_flake.run_command")
    def test_ensure_old_profile_removed_ignores_systemexit(
        self,
        mock_run_command: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        mock_which.return_value = "/usr/bin/nix"

        def side_effect(cmd: str, cwd: str | None = None, preview: bool = False, **_: object) -> None:
            raise SystemExit(1)

        mock_run_command.side_effect = side_effect

        self.installer._ensure_old_profile_removed(self.ctx)

        remove_cmd = f"nix profile remove {self.installer.PROFILE_NAME} || true"
        mock_run_command.assert_called_with(
            remove_cmd,
            cwd=self.ctx.repo_dir,
            preview=self.ctx.preview,
        )


if __name__ == "__main__":
    unittest.main()
