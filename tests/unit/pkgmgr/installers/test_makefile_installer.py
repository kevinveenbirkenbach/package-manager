# tests/unit/pkgmgr/installers/test_makefile_installer.py

import os
import unittest
from unittest.mock import patch

from pkgmgr.context import RepoContext
from pkgmgr.installers.makefile import MakefileInstaller


class TestMakefileInstaller(unittest.TestCase):
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
        self.installer = MakefileInstaller()

    @patch("os.path.exists", return_value=True)
    def test_supports_true_when_makefile_exists(self, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "Makefile"))

    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_makefile_missing(self, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.makefile.run_command")
    @patch("os.path.exists", return_value=True)
    def test_run_executes_make_install(self, mock_exists, mock_run_command):
        self.installer.run(self.ctx)
        cmd = mock_run_command.call_args[0][0]
        self.assertEqual(cmd, "make install")
        self.assertEqual(
            mock_run_command.call_args[1].get("cwd"),
            self.ctx.repo_dir,
        )


if __name__ == "__main__":
    unittest.main()
