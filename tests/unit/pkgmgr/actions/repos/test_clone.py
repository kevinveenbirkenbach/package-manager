# tests/test_clone_repos.py
import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.actions.repository.clone import clone_repos


class TestCloneRepos(unittest.TestCase):
    def setUp(self):
        self.repo = {
            "provider": "github.com",
            "account": "user",
            "repository": "repo",
        }
        self.selected = [self.repo]
        self.base_dir = "/tmp/repos"
        self.all_repos = self.selected

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.subprocess.run")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_clone_ssh_mode_uses_ssh_url(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_run,
        mock_verify,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="ssh",
        )

        mock_run.assert_called_once()
        # subprocess.run wird mit positional args aufgerufen
        cmd = mock_run.call_args[0][0]
        cwd = mock_run.call_args[1]["cwd"]

        self.assertIn("git clone", cmd)
        self.assertIn("git@github.com:user/repo.git", cmd)
        self.assertEqual(cwd, "/tmp/repos/user")

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.subprocess.run")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_clone_https_mode_uses_https_url(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_run,
        mock_verify,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="https",
        )

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        cwd = mock_run.call_args[1]["cwd"]

        self.assertIn("git clone", cmd)
        self.assertIn("https://github.com/user/repo.git", cmd)
        self.assertEqual(cwd, "/tmp/repos/user")

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.subprocess.run")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_clone_shallow_mode_uses_https_with_depth(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_run,
        mock_verify,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="shallow",
        )

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        cwd = mock_run.call_args[1]["cwd"]

        self.assertIn("git clone --depth 1 --single-branch", cmd)
        self.assertIn("https://github.com/user/repo.git", cmd)
        self.assertEqual(cwd, "/tmp/repos/user")

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.subprocess.run")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_preview_mode_does_not_call_subprocess_run(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_run,
        mock_verify,
    ):
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=True,
            no_verification=True,
            clone_mode="shallow",
        )

        # Im Preview-Modus sollte subprocess.run nicht aufgerufen werden
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
