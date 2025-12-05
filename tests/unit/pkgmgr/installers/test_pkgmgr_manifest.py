# tests/unit/pkgmgr/installers/test_pkgmgr_manifest.py

import os
import unittest
from unittest.mock import patch, mock_open

from pkgmgr.context import RepoContext
from pkgmgr.installers.pkgmgr_manifest import PkgmgrManifestInstaller


class TestPkgmgrManifestInstaller(unittest.TestCase):
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
            update_dependencies=True,
        )
        self.installer = PkgmgrManifestInstaller()

    @patch("os.path.exists", return_value=True)
    def test_supports_true_when_manifest_exists(self, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))
        manifest_path = os.path.join(self.ctx.repo_dir, "pkgmgr.yml")
        mock_exists.assert_called_with(manifest_path)

    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_manifest_missing(self, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.pkgmgr_manifest.run_command")
    @patch("builtins.open", new_callable=mock_open, read_data="""
version: 1
author: "Kevin"
url: "https://example.com"
description: "Test repo"
dependencies:
  - repository: github:user/repo1
    version: main
    reason: "Core dependency"
  - repository: github:user/repo2
""")
    @patch("os.path.exists", return_value=True)
    def test_run_installs_dependencies_and_pulls_when_update_enabled(
        self, mock_exists, mock_file, mock_run_command
    ):
        self.installer.run(self.ctx)

        # First call: pkgmgr pull github:user/repo1 github:user/repo2
        # Then calls to pkgmgr install ...
        cmds = [call_args[0][0] for call_args in mock_run_command.call_args_list]

        self.assertIn(
            "pkgmgr pull github:user/repo1 github:user/repo2",
            cmds,
        )
        self.assertIn(
            "pkgmgr install github:user/repo1 --version main --dependencies --clone-mode ssh",
            cmds,
        )
        # For repo2: no version but dependencies + clone_mode
        self.assertIn(
            "pkgmgr install github:user/repo2 --dependencies --clone-mode ssh",
            cmds,
        )

    @patch("pkgmgr.installers.pkgmgr_manifest.run_command")
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("os.path.exists", return_value=True)
    def test_run_no_dependencies_no_command_called(
        self, mock_exists, mock_file, mock_run_command
    ):
        self.ctx.update_dependencies = True
        self.installer.run(self.ctx)
        mock_run_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
