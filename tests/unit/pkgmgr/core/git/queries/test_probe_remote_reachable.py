from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch

from pkgmgr.core.git.errors import GitRunError

# IMPORTANT:
# Import the MODULE, not the function exported by pkgmgr.core.git.queries.__init__.
pr = importlib.import_module("pkgmgr.core.git.queries.probe_remote_reachable")


def _git_error(
    *,
    returncode: int,
    stderr: str = "",
    stdout: str = "",
    message: str = "git failed",
) -> GitRunError:
    """
    Create a GitRunError that mimics what pkgmgr.core.git.run attaches.
    """
    exc = GitRunError(message)
    exc.returncode = returncode
    exc.stderr = stderr
    exc.stdout = stdout
    return exc


class TestProbeRemoteReachableHelpers(unittest.TestCase):
    def test_first_useful_line_prefers_keyword_lines(self) -> None:
        text = "\nerror:\n   \nFATAL: Could not read from remote repository.\nmore\n"
        self.assertEqual(
            pr._first_useful_line(text),
            "FATAL: Could not read from remote repository.",
        )

    def test_first_useful_line_skips_plain_error_if_possible(self) -> None:
        text = "error:\nsome other info\n"
        self.assertEqual(pr._first_useful_line(text), "some other info")

    def test_first_useful_line_returns_empty_for_empty(self) -> None:
        self.assertEqual(pr._first_useful_line("   \n\n"), "")

    def test_looks_like_real_transport_error_true(self) -> None:
        self.assertTrue(
            pr._looks_like_real_transport_error(
                "fatal: Could not read from remote repository."
            )
        )

    def test_looks_like_real_transport_error_false(self) -> None:
        self.assertFalse(pr._looks_like_real_transport_error("some harmless output"))


class TestProbeRemoteReachableDetail(unittest.TestCase):
    @patch.object(pr, "run", return_value="")
    def test_detail_success_returns_true_empty_reason(self, m_run) -> None:
        ok, reason = pr.probe_remote_reachable_detail(
            "git@github.com:alice/repo.git",
            cwd="/tmp",
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")
        m_run.assert_called_once()

    @patch.object(pr, "run")
    def test_detail_rc2_without_transport_indicators_treated_as_reachable(
        self, m_run
    ) -> None:
        # rc=2 but no transport/auth indicators => treat as reachable (empty repo)
        m_run.side_effect = _git_error(
            returncode=2,
            stderr="",
            stdout="",
            message="Git command failed (exit 2)",
        )

        ok, reason = pr.probe_remote_reachable_detail(
            "git@github.com:alice/empty.git",
            cwd="/tmp",
        )
        self.assertTrue(ok)
        self.assertIn("empty repository", reason.lower())

    @patch.object(pr, "run")
    def test_detail_rc2_with_transport_indicators_is_not_reachable(self, m_run) -> None:
        # rc=2 but stderr indicates transport/auth problem => NOT reachable
        m_run.side_effect = _git_error(
            returncode=2,
            stderr="ERROR: Repository not found.",
            stdout="",
            message="Git command failed (exit 2)",
        )

        ok, reason = pr.probe_remote_reachable_detail(
            "git@github.com:alice/missing.git",
            cwd="/tmp",
        )
        self.assertFalse(ok)
        self.assertIn("repository not found", reason.lower())

    @patch.object(pr, "run")
    def test_detail_rc128_reports_reason(self, m_run) -> None:
        m_run.side_effect = _git_error(
            returncode=128,
            stderr="fatal: Could not read from remote repository.",
            stdout="",
            message="Git command failed (exit 128)",
        )

        ok, reason = pr.probe_remote_reachable_detail(
            "ssh://git@host:2201/a/b.git",
            cwd="/tmp",
        )
        self.assertFalse(ok)
        self.assertIn("(exit 128)", reason.lower())
        self.assertIn("could not read from remote repository", reason.lower())

    @patch.object(pr, "run")
    def test_detail_adds_hint_if_reason_is_generic(self, m_run) -> None:
        # Generic failure: rc=128 but no stderr/stdout => should append hint
        m_run.side_effect = _git_error(
            returncode=128,
            stderr="",
            stdout="",
            message="",
        )

        url = "git@github.com:alice/repo.git"
        ok, reason = pr.probe_remote_reachable_detail(url, cwd="/tmp")

        self.assertFalse(ok)
        self.assertIn("hint:", reason.lower())
        self.assertIn("git ls-remote --exit-code", reason.lower())

    @patch.object(pr, "probe_remote_reachable_detail", return_value=(True, ""))
    def test_probe_remote_reachable_delegates_to_detail(self, m_detail) -> None:
        self.assertTrue(pr.probe_remote_reachable("x", cwd="/tmp"))
        m_detail.assert_called_once_with("x", cwd="/tmp")


if __name__ == "__main__":
    unittest.main()
