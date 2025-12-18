import unittest
from unittest.mock import patch

from pkgmgr.core.git.errors import GitNotRepositoryError
from pkgmgr.core.git.queries.get_latest_signing_key import GitLatestSigningKeyQueryError
from pkgmgr.core.git.queries.get_remote_head_commit import GitRemoteHeadCommitQueryError
from pkgmgr.core.repository.verify import verify_repository


class TestVerifyRepository(unittest.TestCase):
    def test_no_verified_info_returns_ok_and_best_effort_values(self) -> None:
        repo = {"id": "demo"}  # no "verified"
        with (
            patch(
                "pkgmgr.core.repository.verify.get_head_commit", return_value="deadbeef"
            ),
            patch(
                "pkgmgr.core.repository.verify.get_latest_signing_key",
                return_value="KEYID",
            ),
        ):
            ok, errors, commit, key = verify_repository(repo, "/tmp/repo", mode="local")
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(commit, "deadbeef")
        self.assertEqual(key, "KEYID")

    def test_best_effort_swallows_query_errors_when_no_verified_info(self) -> None:
        repo = {"id": "demo"}
        with (
            patch(
                "pkgmgr.core.repository.verify.get_head_commit",
                return_value=None,
            ),
            patch(
                "pkgmgr.core.repository.verify.get_latest_signing_key",
                side_effect=GitLatestSigningKeyQueryError("fail signing key"),
            ),
        ):
            ok, errors, commit, key = verify_repository(repo, "/tmp/repo", mode="local")
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(commit, "")
        self.assertEqual(key, "")

    def test_verified_commit_mismatch_fails(self) -> None:
        repo = {"verified": {"commit": "expected", "gpg_keys": None}}
        with (
            patch(
                "pkgmgr.core.repository.verify.get_head_commit", return_value="actual"
            ),
            patch(
                "pkgmgr.core.repository.verify.get_latest_signing_key",
                return_value="",
            ),
        ):
            ok, errors, commit, key = verify_repository(repo, "/tmp/repo", mode="local")

        self.assertFalse(ok)
        self.assertIn("Expected commit: expected, found: actual", errors)
        self.assertEqual(commit, "actual")
        self.assertEqual(key, "")

    def test_verified_gpg_key_missing_fails(self) -> None:
        repo = {"verified": {"commit": None, "gpg_keys": ["ABC"]}}
        with (
            patch("pkgmgr.core.repository.verify.get_head_commit", return_value=""),
            patch(
                "pkgmgr.core.repository.verify.get_latest_signing_key",
                return_value="",
            ),
        ):
            ok, errors, commit, key = verify_repository(repo, "/tmp/repo", mode="local")

        self.assertFalse(ok)
        self.assertTrue(any("no signing key was found" in e for e in errors))
        self.assertEqual(commit, "")
        self.assertEqual(key, "")

    def test_strict_pull_collects_remote_error_message(self) -> None:
        repo = {"verified": {"commit": "expected", "gpg_keys": None}}
        with (
            patch(
                "pkgmgr.core.repository.verify.get_remote_head_commit",
                side_effect=GitRemoteHeadCommitQueryError("remote fail"),
            ),
            patch(
                "pkgmgr.core.repository.verify.get_latest_signing_key",
                return_value="",
            ),
        ):
            ok, errors, commit, key = verify_repository(repo, "/tmp/repo", mode="pull")

        self.assertFalse(ok)
        self.assertIn("remote fail", " ".join(errors))
        self.assertEqual(commit, "")
        self.assertEqual(key, "")

    def test_not_repository_error_is_not_caught(self) -> None:
        repo = {"verified": {"commit": "expected", "gpg_keys": None}}
        with patch(
            "pkgmgr.core.repository.verify.get_head_commit",
            side_effect=GitNotRepositoryError("no repo"),
        ):
            with self.assertRaises(GitNotRepositoryError):
                verify_repository(repo, "/tmp/no-repo", mode="local")
