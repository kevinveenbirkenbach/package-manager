# tests/unit/pkgmgr/test_install_repos.py

import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.context import RepoContext
import pkgmgr.install_repos as install_module
from pkgmgr.installers.base import BaseInstaller


class DummyInstaller(BaseInstaller):
    """Simple installer for testing orchestration."""

    layer = None  # no specific capabilities

    def __init__(self):
        self.calls = []

    def supports(self, ctx: RepoContext) -> bool:
        # Always support to verify that the pipeline runs
        return True

    def run(self, ctx: RepoContext) -> None:
        self.calls.append(ctx.identifier)


class TestInstallReposOrchestration(unittest.TestCase):
    @patch("pkgmgr.install_repos.create_ink")
    @patch("pkgmgr.install_repos.resolve_command_for_repo")
    @patch("pkgmgr.install_repos.verify_repository")
    @patch("pkgmgr.install_repos.get_repo_dir")
    @patch("pkgmgr.install_repos.get_repo_identifier")
    @patch("pkgmgr.install_repos.clone_repos")
    def test_install_repos_runs_pipeline_for_each_repo(
        self,
        mock_clone_repos,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_verify_repository,
        mock_resolve_command_for_repo,
        mock_create_ink,
    ):
        repo1 = {"name": "repo1"}
        repo2 = {"name": "repo2"}
        selected_repos = [repo1, repo2]
        all_repos = selected_repos

        # Return identifiers and directories
        mock_get_repo_identifier.side_effect = ["id1", "id2"]
        mock_get_repo_dir.side_effect = ["/tmp/repo1", "/tmp/repo2"]

        # Simulate verification success: (ok, errors, commit, key)
        mock_verify_repository.return_value = (True, [], "commit", "key")

        # Resolve commands for both repos so create_ink will be called
        mock_resolve_command_for_repo.side_effect = ["/bin/cmd1", "/bin/cmd2"]

        # Ensure directories exist (no cloning)
        with patch("os.path.exists", return_value=True):
            dummy_installer = DummyInstaller()
            # Monkeypatch INSTALLERS for this test
            old_installers = install_module.INSTALLERS
            install_module.INSTALLERS = [dummy_installer]
            try:
                install_module.install_repos(
                    selected_repos=selected_repos,
                    repositories_base_dir="/tmp",
                    bin_dir="/bin",
                    all_repos=all_repos,
                    no_verification=False,
                    preview=False,
                    quiet=False,
                    clone_mode="ssh",
                    update_dependencies=False,
                )
            finally:
                install_module.INSTALLERS = old_installers

        # Check that installers ran with both identifiers
        self.assertEqual(dummy_installer.calls, ["id1", "id2"])
        self.assertEqual(mock_create_ink.call_count, 2)
        self.assertEqual(mock_verify_repository.call_count, 2)
        self.assertEqual(mock_resolve_command_for_repo.call_count, 2)

    @patch("pkgmgr.install_repos.verify_repository")
    @patch("pkgmgr.install_repos.get_repo_dir")
    @patch("pkgmgr.install_repos.get_repo_identifier")
    @patch("pkgmgr.install_repos.clone_repos")
    def test_install_repos_skips_on_failed_verification(
        self,
        mock_clone_repos,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_verify_repository,
    ):
        repo = {"name": "repo1", "verified": True}
        selected_repos = [repo]
        all_repos = selected_repos

        mock_get_repo_identifier.return_value = "id1"
        mock_get_repo_dir.return_value = "/tmp/repo1"

        # Verification fails: ok=False, with error list
        mock_verify_repository.return_value = (False, ["sig error"], None, None)

        dummy_installer = DummyInstaller()
        with patch("os.path.exists", return_value=True), \
             patch("pkgmgr.install_repos.create_ink") as mock_create_ink, \
             patch("pkgmgr.install_repos.resolve_command_for_repo") as mock_resolve_cmd, \
             patch("builtins.input", return_value="n"):
            old_installers = install_module.INSTALLERS
            install_module.INSTALLERS = [dummy_installer]
            try:
                install_module.install_repos(
                    selected_repos=selected_repos,
                    repositories_base_dir="/tmp",
                    bin_dir="/bin",
                    all_repos=all_repos,
                    no_verification=False,
                    preview=False,
                    quiet=False,
                    clone_mode="ssh",
                    update_dependencies=False,
                )
            finally:
                install_module.INSTALLERS = old_installers

        # No installer run and no create_ink when user declines
        self.assertEqual(dummy_installer.calls, [])
        mock_create_ink.assert_not_called()
        mock_resolve_cmd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
