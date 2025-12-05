import os
import unittest
from unittest import mock
from unittest.mock import patch

from pkgmgr.context import RepoContext
from pkgmgr.installers.nix_flake import NixFlakeInstaller


class TestNixFlakeInstaller(unittest.TestCase):
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
        self.installer = NixFlakeInstaller()

    @patch("shutil.which", return_value="/usr/bin/nix")
    @patch("os.path.exists", return_value=True)
    def test_supports_true_when_nix_and_flake_exist(self, mock_exists, mock_which):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_which.assert_called_with("nix")
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "flake.nix"))

    @patch("shutil.which", return_value=None)
    @patch("os.path.exists", return_value=True)
    def test_supports_false_when_nix_missing(self, mock_exists, mock_which):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/nix")
    @mock.patch("pkgmgr.installers.nix_flake.run_command")
    def test_run_tries_pkgmgr_then_default(self, mock_run_command, mock_which, mock_exists):
        cmds = []

        def side_effect(cmd, cwd=None, preview=False, *args, **kwargs):
            cmds.append(cmd)
            return None

        mock_run_command.side_effect = side_effect

        self.installer.run(self.ctx)

        self.assertIn(
            f"nix profile install {self.ctx.repo_dir}#pkgmgr",
            cmds,
        )
        self.assertIn(
            f"nix profile install {self.ctx.repo_dir}#default",
            cmds,
        )

if __name__ == "__main__":
    unittest.main()
