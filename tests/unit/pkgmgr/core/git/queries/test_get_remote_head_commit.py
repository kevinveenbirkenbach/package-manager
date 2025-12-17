import unittest
from unittest.mock import patch

from pkgmgr.core.git.errors import GitNotRepositoryError, GitRunError
from pkgmgr.core.git.queries.get_remote_head_commit import (
    GitRemoteHeadCommitQueryError,
    get_remote_head_commit,
)


class TestGetRemoteHeadCommit(unittest.TestCase):
    @patch("pkgmgr.core.git.queries.get_remote_head_commit.run", return_value="abc123\tHEAD\n")
    def test_parses_first_token_as_hash(self, mock_run) -> None:
        out = get_remote_head_commit(cwd="/tmp/repo")
        self.assertEqual(out, "abc123")
        mock_run.assert_called_once()

    @patch("pkgmgr.core.git.queries.get_remote_head_commit.run", return_value="")
    def test_returns_empty_string_on_empty_output(self, _mock_run) -> None:
        out = get_remote_head_commit(cwd="/tmp/repo")
        self.assertEqual(out, "")

    @patch("pkgmgr.core.git.queries.get_remote_head_commit.run", side_effect=GitRunError("boom"))
    def test_wraps_git_run_error(self, _mock_run) -> None:
        with self.assertRaises(GitRemoteHeadCommitQueryError) as ctx:
            get_remote_head_commit(cwd="/tmp/repo")
        self.assertIn("Failed to query remote head commit", str(ctx.exception))

    @patch("pkgmgr.core.git.queries.get_remote_head_commit.run", side_effect=GitNotRepositoryError("no repo"))
    def test_does_not_catch_not_repository_error(self, _mock_run) -> None:
        with self.assertRaises(GitNotRepositoryError):
            get_remote_head_commit(cwd="/tmp/no-repo")
