# tests/unit/pkgmgr/installers/os_packages/test_debian_control.py

import unittest
from unittest.mock import patch, mock_open

from pkgmgr.context import RepoContext
from pkgmgr.installers.os_packages.debian_control import DebianControlInstaller


class TestDebianControlInstaller(unittest.TestCase):
    def setUp(self):
        self.repo = {"name": "repo"}
        self.ctx = RepoContext(
            repo=self.repo,
            identifier="id",
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
        self.installer = DebianControlInstaller()

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/apt-get")
    def test_supports_true(self, mock_which, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value=None)
    def test_supports_false_without_apt(self, mock_which, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.os_packages.debian_control.run_command")
    @patch("builtins.open", new_callable=mock_open, read_data="""
Build-Depends: python3, git (>= 2.0)
Depends: curl | wget
""")
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/apt-get")
    def test_run_installs_parsed_packages(
        self,
        mock_which,
        mock_exists,
        mock_file,
        mock_run_command
    ):
        self.installer.run(self.ctx)

        # First call: apt-get update
        self.assertIn("apt-get update", mock_run_command.call_args_list[0][0][0])

        # Second call: install packages
        install_cmd = mock_run_command.call_args_list[1][0][0]
        self.assertIn("apt-get install -y", install_cmd)
        self.assertIn("python3", install_cmd)
        self.assertIn("git", install_cmd)
        self.assertIn("curl", install_cmd)


if __name__ == "__main__":
    unittest.main()
