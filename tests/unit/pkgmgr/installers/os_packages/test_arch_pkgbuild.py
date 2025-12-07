# tests/unit/pkgmgr/installers/os_packages/test_arch_pkgbuild.py

import os
import unittest
from unittest.mock import patch

from pkgmgr.context import RepoContext
from pkgmgr.installers.os_packages.arch_pkgbuild import ArchPkgbuildInstaller


class TestArchPkgbuildInstaller(unittest.TestCase):
    def setUp(self):
        self.repo = {"name": "test-repo"}
        self.ctx = RepoContext(
            repo=self.repo,
            identifier="test-id",
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
        self.installer = ArchPkgbuildInstaller()

    @patch("pkgmgr.installers.os_packages.arch_pkgbuild.os.geteuid", return_value=1000)
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which")
    def test_supports_true_when_tools_and_pkgbuild_exist(
        self, mock_which, mock_exists, mock_geteuid
    ):
        def which_side_effect(name):
            if name in ("pacman", "makepkg"):
                return f"/usr/bin/{name}"
            return None

        mock_which.side_effect = which_side_effect

        self.assertTrue(self.installer.supports(self.ctx))

        calls = [c.args[0] for c in mock_which.call_args_list]
        self.assertIn("pacman", calls)
        self.assertIn("makepkg", calls)
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "PKGBUILD"))

    @patch("pkgmgr.installers.os_packages.arch_pkgbuild.os.geteuid", return_value=0)
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which")
    def test_supports_false_when_running_as_root(
        self, mock_which, mock_exists, mock_geteuid
    ):
        mock_which.return_value = "/usr/bin/pacman"
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.os_packages.arch_pkgbuild.os.geteuid", return_value=1000)
    @patch("os.path.exists", return_value=False)
    @patch("shutil.which")
    def test_supports_false_when_pkgbuild_missing(
        self, mock_which, mock_exists, mock_geteuid
    ):
        mock_which.return_value = "/usr/bin/pacman"
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.os_packages.arch_pkgbuild.run_command")
    @patch("pkgmgr.installers.os_packages.arch_pkgbuild.os.geteuid", return_value=1000)
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which")
    def test_run_builds_and_installs_with_makepkg(
        self, mock_which, mock_exists, mock_geteuid, mock_run_command
    ):
        def which_side_effect(name):
            if name in ("pacman", "makepkg"):
                return f"/usr/bin/{name}"
            return None

        mock_which.side_effect = which_side_effect

        self.installer.run(self.ctx)

        cmd = mock_run_command.call_args[0][0]
        self.assertEqual(
            cmd,
            "makepkg --syncdeps --cleanbuild --install --noconfirm",
        )
        self.assertEqual(
            mock_run_command.call_args[1].get("cwd"),
            self.ctx.repo_dir,
        )


if __name__ == "__main__":
    unittest.main()
