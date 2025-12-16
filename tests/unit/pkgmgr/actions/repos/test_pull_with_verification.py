import io
import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.pull import pull_with_verification


class TestPullWithVerification(unittest.TestCase):
    """
    Comprehensive unit tests for pull_with_verification().

    These tests verify:
      - Preview mode behaviour
      - Verification logic (prompting, bypassing, skipping)
      - pull_args invocation (instead of subprocess.run)
      - Repository directory existence checks
      - Handling of extra git pull arguments
    """

    def _setup_mocks(
        self,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        *,
        exists: bool = True,
        verified_ok: bool = True,
        errors=None,
        verified_info: bool = True,
    ):
        """Helper to configure repetitive mock behavior."""
        repo = {
            "name": "pkgmgr",
            "verified": {"gpg_keys": ["ABCDEF"]} if verified_info else None,
        }
        mock_exists.return_value = exists
        mock_get_repo_id.return_value = "pkgmgr"
        mock_get_repo_dir.return_value = "/fake/base/pkgmgr"
        mock_verify.return_value = (
            verified_ok,
            errors or [],
            "deadbeef",  # commit hash
            "ABCDEF",  # signing key
        )
        return repo

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_preview_mode_non_interactive(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        Preview mode must NEVER request user input and must still call pull_args
        in preview mode (which prints the preview command via core.git.run()).
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            exists=True,
            verified_ok=False,
            errors=["bad signature"],
            verified_info=True,
        )

        buf = io.StringIO()
        with patch("sys.stdout", new=buf):
            pull_with_verification(
                selected_repos=[repo],
                repositories_base_dir="/fake/base",
                all_repos=[repo],
                extra_args=["--ff-only"],
                no_verification=False,
                preview=True,
            )

        mock_input.assert_not_called()
        mock_pull_args.assert_called_once_with(
            ["--ff-only"],
            cwd="/fake/base/pkgmgr",
            preview=True,
        )

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_verification_failure_user_declines(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        If verification fails and preview=False, the user is prompted.
        If the user declines ('n'), no git command is executed.
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            verified_ok=False,
            errors=["signature invalid"],
        )

        mock_input.return_value = "n"

        pull_with_verification(
            selected_repos=[repo],
            repositories_base_dir="/fake/base",
            all_repos=[repo],
            extra_args=[],
            no_verification=False,
            preview=False,
        )

        mock_input.assert_called_once()
        mock_pull_args.assert_not_called()

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_verification_failure_user_accepts_runs_git(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        If verification fails and the user accepts ('y'),
        then the git pull should be executed via pull_args.
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            verified_ok=False,
            errors=["invalid"],
        )

        mock_input.return_value = "y"

        pull_with_verification(
            selected_repos=[repo],
            repositories_base_dir="/fake/base",
            all_repos=[repo],
            extra_args=[],
            no_verification=False,
            preview=False,
        )

        mock_input.assert_called_once()
        mock_pull_args.assert_called_once_with(
            [],
            cwd="/fake/base/pkgmgr",
            preview=False,
        )

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_verification_success_no_prompt(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        If verification is successful, the user should NOT be prompted,
        and git pull should run immediately.
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            verified_ok=True,
        )

        pull_with_verification(
            selected_repos=[repo],
            repositories_base_dir="/fake/base",
            all_repos=[repo],
            extra_args=["--rebase"],
            no_verification=False,
            preview=False,
        )

        mock_input.assert_not_called()
        mock_pull_args.assert_called_once_with(
            ["--rebase"],
            cwd="/fake/base/pkgmgr",
            preview=False,
        )

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_directory_missing_skips_repo(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        If the repository directory does not exist, the repo must be skipped
        and no git command executed.
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            exists=False,
        )

        buf = io.StringIO()
        with patch("sys.stdout", new=buf):
            pull_with_verification(
                selected_repos=[repo],
                repositories_base_dir="/fake/base",
                all_repos=[repo],
                extra_args=[],
                no_verification=False,
                preview=False,
            )

        output = buf.getvalue()
        self.assertIn("not found", output)

        mock_input.assert_not_called()
        mock_pull_args.assert_not_called()

    # ---------------------------------------------------------------------
    @patch("pkgmgr.actions.repository.pull.pull_args")
    @patch("pkgmgr.actions.repository.pull.verify_repository")
    @patch("pkgmgr.actions.repository.pull.get_repo_dir")
    @patch("pkgmgr.actions.repository.pull.get_repo_identifier")
    @patch("pkgmgr.actions.repository.pull.os.path.exists")
    @patch("builtins.input")
    def test_no_verification_flag_skips_prompt(
        self,
        mock_input,
        mock_exists,
        mock_get_repo_id,
        mock_get_repo_dir,
        mock_verify,
        mock_pull_args,
    ):
        """
        If no_verification=True, verification failures must NOT prompt.
        Git pull should run directly.
        """
        repo = self._setup_mocks(
            mock_exists,
            mock_get_repo_id,
            mock_get_repo_dir,
            mock_verify,
            verified_ok=False,
            errors=["invalid"],
        )

        pull_with_verification(
            selected_repos=[repo],
            repositories_base_dir="/fake/base",
            all_repos=[repo],
            extra_args=[],
            no_verification=True,
            preview=False,
        )

        mock_input.assert_not_called()
        mock_pull_args.assert_called_once_with(
            [],
            cwd="/fake/base/pkgmgr",
            preview=False,
        )
