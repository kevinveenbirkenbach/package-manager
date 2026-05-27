"""Unit tests for the `release(retry=True)` re-deploy entry point.

`TestReleaseRetry` exercises the routing decision in `release()` —
that `--retry` skips the full `_release_impl` flow and dispatches to
`retry_release` instead.

`TestRetryRelease` exercises the standalone module `pkgmgr.actions.release.retry`:
HEAD-tag discovery, idempotent push, latest-tag re-alignment, and
fallback behaviour when the current branch cannot be detected.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.retry import retry_release
from pkgmgr.actions.release.workflow import release
from pkgmgr.core.git import GitRunError


class TestReleaseRetry(unittest.TestCase):
    @patch("pkgmgr.actions.release.workflow.retry_release")
    @patch("pkgmgr.actions.release.workflow._release_impl")
    def test_retry_routes_to_retry_release_only(
        self, mock_release_impl, mock_retry_release
    ) -> None:
        release(retry=True, preview=False)

        mock_retry_release.assert_called_once()
        mock_release_impl.assert_not_called()
        self.assertFalse(mock_retry_release.call_args.kwargs["preview"])

    @patch("pkgmgr.actions.release.workflow.retry_release")
    @patch("pkgmgr.actions.release.workflow._release_impl")
    def test_retry_preview_passthrough(
        self, mock_release_impl, mock_retry_release
    ) -> None:
        release(retry=True, preview=True)

        mock_retry_release.assert_called_once()
        mock_release_impl.assert_not_called()
        self.assertTrue(mock_retry_release.call_args.kwargs["preview"])

    @patch("pkgmgr.actions.release.workflow.retry_release")
    @patch("pkgmgr.actions.release.workflow._release_impl")
    def test_retry_ignores_release_args(
        self, mock_release_impl, mock_retry_release
    ) -> None:
        # release_type/message/close/force must NOT trigger the full release flow
        # when retry=True.
        release(
            retry=True,
            release_type="major",
            message="ignored body",
            preview=False,
            force=True,
            close=True,
        )

        mock_retry_release.assert_called_once()
        mock_release_impl.assert_not_called()


class TestRetryRelease(unittest.TestCase):
    @patch("pkgmgr.actions.release.retry.update_latest_tag")
    @patch("pkgmgr.actions.release.retry.is_highest_version_tag", return_value=True)
    @patch("pkgmgr.actions.release.retry.run")
    @patch("pkgmgr.actions.release.retry.head_semver_tags")
    @patch(
        "pkgmgr.actions.release.retry.get_current_branch",
        return_value="release-fix",
    )
    def test_retry_pushes_existing_tag_and_updates_latest(
        self,
        _mock_branch,
        mock_head_tags,
        mock_run,
        _mock_highest,
        mock_update_latest,
    ) -> None:
        mock_head_tags.return_value = ["v1.13.4"]

        retry_release(pyproject_path="pyproject.toml", preview=False)

        mock_run.assert_called_once_with(
            ["push", "origin", "release-fix", "v1.13.4"], preview=False
        )
        mock_update_latest.assert_called_once_with("v1.13.4", preview=False)

    @patch("pkgmgr.actions.release.retry.update_latest_tag")
    @patch("pkgmgr.actions.release.retry.is_highest_version_tag", return_value=False)
    @patch("pkgmgr.actions.release.retry.run")
    @patch("pkgmgr.actions.release.retry.head_semver_tags")
    @patch(
        "pkgmgr.actions.release.retry.get_current_branch",
        return_value="release-fix",
    )
    def test_retry_skips_latest_for_non_highest_tag(
        self,
        _mock_branch,
        mock_head_tags,
        _mock_run,
        _mock_highest,
        mock_update_latest,
    ) -> None:
        mock_head_tags.return_value = ["v1.0.0"]

        retry_release(pyproject_path="pyproject.toml", preview=False)

        mock_update_latest.assert_not_called()

    @patch(
        "pkgmgr.actions.release.retry.head_semver_tags",
        return_value=[],
    )
    @patch(
        "pkgmgr.actions.release.retry.get_current_branch",
        return_value="main",
    )
    def test_retry_raises_when_head_has_no_tag(
        self, _mock_branch, _mock_head_tags
    ) -> None:
        with self.assertRaises(RuntimeError) as cm:
            retry_release(pyproject_path="pyproject.toml", preview=False)
        self.assertIn("No version tag on HEAD", str(cm.exception))

    @patch("pkgmgr.actions.release.retry.update_latest_tag")
    @patch("pkgmgr.actions.release.retry.is_highest_version_tag", return_value=True)
    @patch("pkgmgr.actions.release.retry.run")
    @patch("pkgmgr.actions.release.retry.head_semver_tags")
    @patch(
        "pkgmgr.actions.release.retry.get_current_branch",
        side_effect=GitRunError("detached"),
    )
    def test_retry_falls_back_to_main_branch_when_detection_fails(
        self,
        _mock_branch,
        mock_head_tags,
        mock_run,
        _mock_highest,
        _mock_update_latest,
    ) -> None:
        mock_head_tags.return_value = ["v2.0.0"]

        retry_release(pyproject_path="pyproject.toml", preview=False)

        mock_run.assert_called_once_with(
            ["push", "origin", "main", "v2.0.0"], preview=False
        )


if __name__ == "__main__":
    unittest.main()
