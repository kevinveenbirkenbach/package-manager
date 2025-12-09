import os
import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.python import PythonInstaller


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
        """
        supports() should return True when a pyproject.toml exists in the repo
        and we are not inside a Nix dev shell.
        """
        with patch.dict(os.environ, {"IN_NIX_SHELL": ""}, clear=False):
            self.assertTrue(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_no_pyproject(self, mock_exists):
        """
        supports() should return False when no pyproject.toml exists.
        """
        with patch.dict(os.environ, {"IN_NIX_SHELL": ""}, clear=False):
            self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.actions.repository.install.installers.python.run_command")
    @patch("os.path.exists", side_effect=lambda path: path.endswith("pyproject.toml"))
    def test_run_installs_project_from_pyproject(self, mock_exists, mock_run_command):
        """
        run() should invoke pip to install the project from pyproject.toml
        when we are not inside a Nix dev shell.
        """
        # Simulate a normal environment (not inside nix develop).
        with patch.dict(os.environ, {"IN_NIX_SHELL": ""}, clear=False):
            self.installer.run(self.ctx)

        # Ensure run_command was actually called.
        mock_run_command.assert_called()

        # Extract the command string.
        cmd = mock_run_command.call_args[0][0]
        self.assertIn("pip install .", cmd)

        # Ensure the working directory is the repo dir.
        self.assertEqual(
            mock_run_command.call_args[1].get("cwd"),
            self.ctx.repo_dir,
        )


if __name__ == "__main__":
    unittest.main()
