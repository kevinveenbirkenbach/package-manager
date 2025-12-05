# tests/unit/pkgmgr/installers/test_aur.py

import os
import unittest
from unittest.mock import patch, mock_open

from pkgmgr.context import RepoContext
from pkgmgr.installers.aur import AurInstaller, AUR_CONFIG_FILENAME


class TestAurInstaller(unittest.TestCase):
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
        self.installer = AurInstaller()

    @patch("shutil.which", return_value="/usr/bin/pacman")
    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
helper: yay
packages:
  - aurutils
  - name: some-aur-only-tool
    reason: "Test tool"
""",
    )
    def test_supports_true_when_arch_and_aur_config_present(
        self, mock_file, mock_exists, mock_which
    ):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_which.assert_called_with("pacman")
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, AUR_CONFIG_FILENAME))

    @patch("shutil.which", return_value=None)
    def test_supports_false_when_not_arch(self, mock_which):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("shutil.which", return_value="/usr/bin/pacman")
    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_no_config(self, mock_exists, mock_which):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("shutil.which", side_effect=lambda name: "/usr/bin/pacman" if name == "pacman" else "/usr/bin/yay")
    @patch("pkgmgr.installers.aur.run_command")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
helper: yay
packages:
  - aurutils
  - some-aur-only-tool
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_installs_packages_with_helper(
        self, mock_exists, mock_file, mock_run_command, mock_which
    ):
        self.installer.run(self.ctx)

        cmd = mock_run_command.call_args[0][0]
        self.assertTrue(cmd.startswith("yay -S --noconfirm "))
        self.assertIn("aurutils", cmd)
        self.assertIn("some-aur-only-tool", cmd)

    @patch("shutil.which", return_value="/usr/bin/pacman")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="packages: []",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_skips_when_no_packages(
        self, mock_exists, mock_file, mock_which
    ):
        with patch("pkgmgr.installers.aur.run_command") as mock_run_command:
            self.installer.run(self.ctx)
            mock_run_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
