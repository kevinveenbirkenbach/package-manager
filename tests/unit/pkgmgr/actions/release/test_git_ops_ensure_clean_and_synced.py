from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.git_ops import ensure_clean_and_synced


class TestEnsureCleanAndSynced(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.pull_ff_only")
    @patch("pkgmgr.actions.release.git_ops.fetch")
    @patch("pkgmgr.actions.release.git_ops.get_upstream_ref")
    def test_no_upstream_skips(
        self,
        mock_get_upstream_ref,
        mock_fetch,
        mock_pull_ff_only,
    ) -> None:
        mock_get_upstream_ref.return_value = None

        ensure_clean_and_synced(preview=False)

        mock_fetch.assert_not_called()
        mock_pull_ff_only.assert_not_called()

    @patch("pkgmgr.actions.release.git_ops.pull_ff_only")
    @patch("pkgmgr.actions.release.git_ops.fetch")
    @patch("pkgmgr.actions.release.git_ops.get_upstream_ref")
    def test_preview_calls_commands_with_preview_true(
        self,
        mock_get_upstream_ref,
        mock_fetch,
        mock_pull_ff_only,
    ) -> None:
        mock_get_upstream_ref.return_value = "origin/main"

        ensure_clean_and_synced(preview=True)

        mock_fetch.assert_called_once_with(
            remote="origin",
            prune=True,
            tags=True,
            force=True,
            preview=True,
        )
        mock_pull_ff_only.assert_called_once_with(preview=True)

    @patch("pkgmgr.actions.release.git_ops.pull_ff_only")
    @patch("pkgmgr.actions.release.git_ops.fetch")
    @patch("pkgmgr.actions.release.git_ops.get_upstream_ref")
    def test_real_calls_commands_with_preview_false(
        self,
        mock_get_upstream_ref,
        mock_fetch,
        mock_pull_ff_only,
    ) -> None:
        mock_get_upstream_ref.return_value = "origin/main"

        ensure_clean_and_synced(preview=False)

        mock_fetch.assert_called_once_with(
            remote="origin",
            prune=True,
            tags=True,
            force=True,
            preview=False,
        )
        mock_pull_ff_only.assert_called_once_with(preview=False)
