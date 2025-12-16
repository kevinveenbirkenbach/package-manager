# tests/unit/pkgmgr/actions/repos/test_clone.py
from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.clone import clone_repos


class TestCloneRepos(unittest.TestCase):
    def setUp(self) -> None:
        # Add `verified` so verify_repository() is actually exercised.
        self.repo = {
            "provider": "github.com",
            "account": "user",
            "repository": "repo",
            "verified": {"commit": "deadbeef"},
        }
        self.selected = [self.repo]
        self.base_dir = "/tmp/repos"
        self.all_repos = self.selected

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
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
        mock_git_clone,
        mock_verify,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False

        # verification called; and because no_verification=True, result doesn't matter
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="ssh",
        )

        mock_git_clone.assert_called_once()
        args, kwargs = mock_git_clone.call_args
        clone_args = args[0]
        self.assertEqual(
            clone_args,
            ["git@github.com:user/repo.git", "/tmp/repos/user/repo"],
        )
        self.assertEqual(kwargs["cwd"], "/tmp/repos/user")
        self.assertFalse(kwargs["preview"])

        # verify_repository should be called because repo has "verified"
        mock_verify.assert_called_once()
        v_args, v_kwargs = mock_verify.call_args
        self.assertEqual(v_args[0], self.repo)  # repo dict
        self.assertEqual(v_args[1], "/tmp/repos/user/repo")  # repo_dir
        self.assertEqual(v_kwargs["mode"], "local")
        self.assertTrue(v_kwargs["no_verification"])

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
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
        mock_git_clone,
        mock_verify,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="https",
        )

        mock_git_clone.assert_called_once()
        args, kwargs = mock_git_clone.call_args
        clone_args = args[0]
        self.assertEqual(
            clone_args,
            ["https://github.com/user/repo.git", "/tmp/repos/user/repo"],
        )
        self.assertEqual(kwargs["cwd"], "/tmp/repos/user")
        self.assertFalse(kwargs["preview"])

        mock_verify.assert_called_once()

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
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
        mock_git_clone,
        mock_verify,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_verify.return_value = (True, [], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="shallow",
        )

        mock_git_clone.assert_called_once()
        args, kwargs = mock_git_clone.call_args
        clone_args = args[0]
        self.assertEqual(
            clone_args,
            [
                "--depth",
                "1",
                "--single-branch",
                "https://github.com/user/repo.git",
                "/tmp/repos/user/repo",
            ],
        )
        self.assertEqual(kwargs["cwd"], "/tmp/repos/user")
        self.assertFalse(kwargs["preview"])

        mock_verify.assert_called_once()

    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_preview_mode_calls_git_clone_with_preview_true(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_git_clone,
        mock_verify,
    ) -> None:
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

        mock_git_clone.assert_called_once()
        _args, kwargs = mock_git_clone.call_args
        self.assertTrue(kwargs["preview"])

        # Even in preview, verification is reached (because repo has "verified"),
        # but no_verification=True makes it non-blocking.
        mock_verify.assert_called_once()

    @patch("builtins.input", return_value="y")
    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_ssh_clone_failure_prompts_and_falls_back_to_https_when_confirmed(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_git_clone,
        mock_verify,
        mock_input,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False
        mock_verify.return_value = (True, [], "hash", "key")

        # First call (ssh) fails, second call (https) succeeds
        from pkgmgr.core.git.commands.clone import GitCloneError

        mock_git_clone.side_effect = [
            GitCloneError("ssh failed", cwd="/tmp/repos/user"),
            None,
        ]

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="ssh",
        )

        self.assertEqual(mock_git_clone.call_count, 2)

        first_args, first_kwargs = mock_git_clone.call_args_list[0]
        self.assertEqual(
            first_args[0],
            ["git@github.com:user/repo.git", "/tmp/repos/user/repo"],
        )
        self.assertEqual(first_kwargs["cwd"], "/tmp/repos/user")
        self.assertFalse(first_kwargs["preview"])

        second_args, second_kwargs = mock_git_clone.call_args_list[1]
        self.assertEqual(
            second_args[0],
            ["https://github.com/user/repo.git", "/tmp/repos/user/repo"],
        )
        self.assertEqual(second_kwargs["cwd"], "/tmp/repos/user")
        self.assertFalse(second_kwargs["preview"])

        mock_input.assert_called_once()
        mock_verify.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_ssh_clone_failure_does_not_fallback_when_declined(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_git_clone,
        mock_verify,
        mock_input,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False

        from pkgmgr.core.git.commands.clone import GitCloneError

        mock_git_clone.side_effect = GitCloneError("ssh failed", cwd="/tmp/repos/user")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=True,
            clone_mode="ssh",
        )

        mock_git_clone.assert_called_once()
        mock_input.assert_called_once()

        # If fallback is declined, verification should NOT run (repo was not cloned)
        mock_verify.assert_not_called()

    @patch("builtins.input", return_value="n")
    @patch("pkgmgr.actions.repository.clone.verify_repository")
    @patch("pkgmgr.actions.repository.clone.git_clone")
    @patch("pkgmgr.actions.repository.clone.os.makedirs")
    @patch("pkgmgr.actions.repository.clone.os.path.exists")
    @patch("pkgmgr.actions.repository.clone.get_repo_dir")
    @patch("pkgmgr.actions.repository.clone.get_repo_identifier")
    def test_verification_failure_prompts_and_skips_when_user_declines(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_exists,
        mock_makedirs,
        mock_git_clone,
        mock_verify,
        mock_input,
    ) -> None:
        mock_get_repo_identifier.return_value = "github.com/user/repo"
        mock_get_repo_dir.return_value = "/tmp/repos/user/repo"
        mock_exists.return_value = False

        # Clone succeeds
        mock_git_clone.return_value = None

        # Verification fails, and user answers "n" to proceed anyway
        mock_verify.return_value = (False, ["bad signature"], "hash", "key")

        clone_repos(
            self.selected,
            self.base_dir,
            self.all_repos,
            preview=False,
            no_verification=False,
            clone_mode="https",
        )

        mock_git_clone.assert_called_once()
        mock_verify.assert_called_once()
        mock_input.assert_called_once()


if __name__ == "__main__":
    unittest.main()
