from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.git import GitError
from pkgmgr.actions.release.git_ops import (
    run_git_command,
    sync_branch_with_remote,
    update_latest_tag,
)


class TestRunGitCommand(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_run_git_command_success(self, mock_run) -> None:
        # No exception means success
        run_git_command("git status")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("git status", args[0])
        self.assertTrue(kwargs.get("check"))

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_run_git_command_failure_raises_git_error(self, mock_run) -> None:
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(
            returncode=1,
            cmd="git status",
            output="stdout",
            stderr="stderr",
        )

        with self.assertRaises(GitError):
            run_git_command("git status")


class TestSyncBranchWithRemote(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_sync_branch_with_remote_skips_non_main_master(
        self,
        mock_run_git_command,
    ) -> None:
        sync_branch_with_remote("feature/my-branch", preview=False)
        mock_run_git_command.assert_not_called()

    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_sync_branch_with_remote_preview_on_main_does_not_run_git(
        self,
        mock_run_git_command,
    ) -> None:
        sync_branch_with_remote("main", preview=True)
        mock_run_git_command.assert_not_called()

    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_sync_branch_with_remote_main_runs_fetch_and_pull(
        self,
        mock_run_git_command,
    ) -> None:
        sync_branch_with_remote("main", preview=False)

        calls = [c.args[0] for c in mock_run_git_command.call_args_list]
        self.assertIn("git fetch origin", calls)
        self.assertIn("git pull origin main", calls)


class TestUpdateLatestTag(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_update_latest_tag_preview_does_not_call_git(
        self,
        mock_run_git_command,
    ) -> None:
        update_latest_tag("v1.2.3", preview=True)
        mock_run_git_command.assert_not_called()

    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_update_latest_tag_real_calls_git_with_dereference_and_message(
        self,
        mock_run_git_command,
    ) -> None:
        update_latest_tag("v1.2.3", preview=False)

        calls = [c.args[0] for c in mock_run_git_command.call_args_list]
        # Must dereference the tag object and create an annotated tag with message
        self.assertIn(
            'git tag -f -a latest v1.2.3^{} -m "Floating latest tag for v1.2.3"',
            calls,
        )
        self.assertIn("git push origin latest --force", calls)

if __name__ == "__main__":
    unittest.main()
