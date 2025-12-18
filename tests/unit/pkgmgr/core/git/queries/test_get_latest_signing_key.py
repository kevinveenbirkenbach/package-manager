import unittest
from unittest.mock import patch

from pkgmgr.core.git.errors import GitNotRepositoryError, GitRunError
from pkgmgr.core.git.queries.get_latest_signing_key import (
    GitLatestSigningKeyQueryError,
    get_latest_signing_key,
)


class TestGetLatestSigningKey(unittest.TestCase):
    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.run",
        return_value="ABCDEF1234567890\n",
    )
    def test_strips_output(self, _mock_run) -> None:
        out = get_latest_signing_key(cwd="/tmp/repo")
        self.assertEqual(out, "ABCDEF1234567890")

    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.run",
        side_effect=GitRunError("boom"),
    )
    def test_wraps_git_run_error(self, _mock_run) -> None:
        with self.assertRaises(GitLatestSigningKeyQueryError):
            get_latest_signing_key(cwd="/tmp/repo")

    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.run",
        side_effect=GitNotRepositoryError("no repo"),
    )
    def test_does_not_catch_not_repository_error(self, _mock_run) -> None:
        with self.assertRaises(GitNotRepositoryError):
            get_latest_signing_key(cwd="/tmp/no-repo")
