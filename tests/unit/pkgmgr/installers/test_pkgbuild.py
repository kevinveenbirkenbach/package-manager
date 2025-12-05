# tests/unit/pkgmgr/installers/test_pkgbuild.py

import os
import unittest
from unittest.mock import patch

from pkgmgr.context import RepoContext
from pkgmgr.installers.pkgbuild import PkgbuildInstaller


class TestPkgbuildInstaller(unittest.TestCase):
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
        self.installer = PkgbuildInstaller()

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/pacman")
    def test_supports_true_when_pacman_and_pkgbuild_exist(self, mock_which, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_which.assert_called_with("pacman")
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "PKGBUILD"))

    @patch("os.path.exists", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/pacman")
    def test_supports_false_when_pkgbuild_missing(self, mock_which, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.pkgbuild.run_command")
    @patch("subprocess.check_output", return_value="python\ngit\n")
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/pacman")
    def test_run_installs_all_packages_and_uses_clean_bash(
        self, mock_which, mock_exists, mock_check_output, mock_run_command
    ):
        self.installer.run(self.ctx)

        # Check subprocess.check_output arguments (clean shell)
        args, kwargs = mock_check_output.call_args
        cmd_list = args[0]
        self.assertEqual(cmd_list[0], "bash")
        self.assertIn("--noprofile", cmd_list)
        self.assertIn("--norc", cmd_list)

        # Check that pacman is called with the extracted packages
        cmd = mock_run_command.call_args[0][0]
        self.assertTrue(cmd.startswith("sudo pacman -S --noconfirm "))
        self.assertIn("python", cmd)
        self.assertIn("git", cmd)


if __name__ == "__main__":
    unittest.main()
