# tests/unit/pkgmgr/installers/test_python_installer.py

import os
import unittest
from unittest.mock import patch

from pkgmgr.context import RepoContext
from pkgmgr.installers.python import PythonInstaller


class TestPythonInstaller(unittest.TestCase):
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
        self.installer = PythonInstaller()

    @patch("os.path.exists", side_effect=lambda path: path.endswith("pyproject.toml"))
    def test_supports_true_when_pyproject_exists(self, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_no_pyproject(self, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.python.run_command")
    @patch("os.path.exists", side_effect=lambda path: path.endswith("pyproject.toml"))
    def test_run_installs_project_from_pyproject(self, mock_exists, mock_run_command):
        self.installer.run(self.ctx)
        cmd = mock_run_command.call_args[0][0]
        self.assertIn("pip install .", cmd)
        self.assertEqual(
            mock_run_command.call_args[1].get("cwd"),
            self.ctx.repo_dir,
        )


if __name__ == "__main__":
    unittest.main()
