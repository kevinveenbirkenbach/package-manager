# tests/test_install_repos.py
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open

from pkgmgr.install_repos import install_repos


class TestInstallRepos(unittest.TestCase):
    def setUp(self):
        self.repo = {
            "provider": "github.com",
            "account": "user",
            "repository": "repo",
        }
        self.selected = [self.repo]
        self.base_dir = "/tmp/repos"
        self.bin_dir = "/tmp/bin"
        self.all_repos = self.selected

    @patch("pkgmgr.install_repos.clone_repos")
    @patch("pkgmgr.install_repos.os.path.exists")
    @patch("pkgmgr.install_repos.get_repo_dir")
    @patch("pkgmgr.install_repos.get_repo_identifier")
    def test_calls_clone_repos_with_clone_mode(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_clone_repos,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        # Repo-Verzeichnis existiert nicht -> soll geklont werden
        mock_exists.return_value = False

        install_repos(
            self.selected,
            self.base_dir,
            self.bin_dir,
            self.all_repos,
            no_verification=True,
            preview=False,
            quiet=True,
            clone_mode="shallow",
            update_dependencies=False,
        )

        mock_clone_repos.assert_called_once()
        args, kwargs = mock_clone_repos.call_args
        # clone_mode ist letztes Argument
        self.assertEqual(args[-1], "shallow")

    @patch("pkgmgr.install_repos.run_command")
    @patch("pkgmgr.install_repos.open", new_callable=mock_open, create=True)
    @patch("pkgmgr.install_repos.yaml.safe_load")
    @patch("pkgmgr.install_repos.os.path.exists")
    @patch("pkgmgr.install_repos.create_ink")
    @patch("pkgmgr.install_repos.verify_repository")
    @patch("pkgmgr.install_repos.get_repo_dir")
    @patch("pkgmgr.install_repos.get_repo_identifier")
    def test_pkgmgr_requirements_propagate_clone_mode(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_verify,
        mock_create_ink,
        mock_exists,
        mock_safe_load,
        mock_open_file,
        mock_run_command,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        repo_dir = "/tmp/repos/user/repo"
        mock_get_repo_dir.return_value = repo_dir

        # exists() muss True für repo_dir & requirements.yml liefern,
        # sonst werden die Anforderungen nie verarbeitet.
        def exists_side_effect(path):
            if path == repo_dir:
                return True
            if path == os.path.join(repo_dir, "requirements.yml"):
                return True
            # requirements.txt und Makefile sollen "nicht existieren"
            return False

        mock_exists.side_effect = exists_side_effect

        mock_verify.return_value = (True, [], "hash", "key")

        # requirements.yml enthält pkgmgr-Dependencies
        mock_safe_load.return_value = {
            "pkgmgr": ["github.com/other/account/dep"],
        }

        commands = []

        def run_command_side_effect(cmd, cwd=None, preview=False):
            commands.append((cmd, cwd, preview))

        mock_run_command.side_effect = run_command_side_effect

        install_repos(
            self.selected,
            self.base_dir,
            self.bin_dir,
            self.all_repos,
            no_verification=False,
            preview=False,
            quiet=True,
            clone_mode="shallow",
            update_dependencies=False,
        )

        # Prüfen, dass ein pkgmgr install Befehl mit --clone-mode shallow gebaut wurde
        pkgmgr_install_cmds = [
            c for (c, cwd, preview) in commands if "pkgmgr install" in c
        ]
        self.assertTrue(
            pkgmgr_install_cmds,
            f"No pkgmgr install command was executed. Commands seen: {commands}",
        )

        cmd = pkgmgr_install_cmds[0]
        self.assertIn("--clone-mode shallow", cmd)


if __name__ == "__main__":
    unittest.main()
