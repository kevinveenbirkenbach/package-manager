# tests/unit/pkgmgr/installers/os_packages/test_rpm_spec.py

import unittest
from unittest.mock import patch, mock_open

from pkgmgr.context import RepoContext
from pkgmgr.installers.os_packages.rpm_spec import RpmSpecInstaller


class TestRpmSpecInstaller(unittest.TestCase):
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
        self.installer = RpmSpecInstaller()

    @patch("glob.glob", return_value=["/tmp/repo/test.spec"])
    @patch("shutil.which", return_value="/usr/bin/dnf")
    def test_supports_true(self, mock_which, mock_glob):
        self.assertTrue(self.installer.supports(self.ctx))

    @patch("glob.glob", return_value=[])
    @patch("shutil.which", return_value="/usr/bin/dnf")
    def test_supports_false_missing_spec(self, mock_which, mock_glob):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.os_packages.rpm_spec.run_command")
    @patch("builtins.open", new_callable=mock_open, read_data="""
BuildRequires: python3-devel, git >= 2.0
Requires: curl
""")
    @patch("glob.glob", return_value=["/tmp/repo/test.spec"])
    @patch("shutil.which", return_value="/usr/bin/dnf")
    @patch("os.path.exists", return_value=True)
    def test_run_installs_parsed_dependencies(
        self, mock_exists, mock_which, mock_glob, mock_file, mock_run_command
    ):
        self.installer.run(self.ctx)

        install_cmd = mock_run_command.call_args_list[0][0][0]

        self.assertIn("dnf install -y", install_cmd)
        self.assertIn("python3-devel", install_cmd)
        self.assertIn("git", install_cmd)
        self.assertIn("curl", install_cmd)


if __name__ == "__main__":
    unittest.main()
