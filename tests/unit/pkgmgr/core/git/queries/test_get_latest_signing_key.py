import unittest
import subprocess
from unittest.mock import patch

from pkgmgr.core.git.errors import GitNotRepositoryError
from pkgmgr.core.git.queries.get_latest_signing_key import (
    GitLatestSigningKeyQueryError,
    get_latest_signing_key,
)


class TestGetLatestSigningKey(unittest.TestCase):
    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["git", "log", "-1", "--format=%GK"],
            returncode=0,
            stdout="ABCDEF1234567890\n",
            stderr="",
        ),
    )
    def test_strips_output(self, _mock_run) -> None:
        out = get_latest_signing_key(cwd="/tmp/repo")
        self.assertEqual(out, "ABCDEF1234567890")

    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["git", "log", "-1", "--format=%GK"],
            returncode=1,
            stdout="",
            stderr="boom",
        ),
    )
    def test_wraps_git_run_error(self, _mock_run) -> None:
        with self.assertRaisesRegex(GitLatestSigningKeyQueryError, "boom"):
            get_latest_signing_key(cwd="/tmp/repo")

    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["git", "log", "-1", "--format=%GK"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        ),
    )
    def test_does_not_catch_not_repository_error(self, _mock_run) -> None:
        with self.assertRaises(GitNotRepositoryError):
            get_latest_signing_key(cwd="/tmp/no-repo")

    @patch(
        "pkgmgr.core.git.queries.get_latest_signing_key.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["git", "log", "-1", "--format=%GK"],
            returncode=0,
            stdout="",
            stderr="error: cannot run gpg: No such file or directory",
        ),
    )
    def test_raises_when_git_reports_gpg_runtime_error(self, _mock_run) -> None:
        with self.assertRaisesRegex(GitLatestSigningKeyQueryError, "cannot run gpg"):
            get_latest_signing_key(cwd="/tmp/repo")
