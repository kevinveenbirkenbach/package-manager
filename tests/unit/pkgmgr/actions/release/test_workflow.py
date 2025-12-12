from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.workflow import release


class TestWorkflowReleaseEntryPoint(unittest.TestCase):
    @patch("pkgmgr.actions.release.workflow._release_impl")
    def test_release_preview_calls_impl_preview_only(self, mock_impl) -> None:
        release(preview=True, force=False, close=False)

        mock_impl.assert_called_once()
        kwargs = mock_impl.call_args.kwargs
        self.assertTrue(kwargs["preview"])
        self.assertFalse(kwargs["force"])

    @patch("pkgmgr.actions.release.workflow._release_impl")
    @patch("pkgmgr.actions.release.workflow.sys.stdin.isatty", return_value=False)
    def test_release_non_interactive_runs_real_without_confirmation(self, _mock_isatty, mock_impl) -> None:
        release(preview=False, force=False, close=False)

        mock_impl.assert_called_once()
        kwargs = mock_impl.call_args.kwargs
        self.assertFalse(kwargs["preview"])

    @patch("pkgmgr.actions.release.workflow._release_impl")
    def test_release_force_runs_real_without_confirmation(self, mock_impl) -> None:
        release(preview=False, force=True, close=False)

        mock_impl.assert_called_once()
        kwargs = mock_impl.call_args.kwargs
        self.assertFalse(kwargs["preview"])
        self.assertTrue(kwargs["force"])

    @patch("pkgmgr.actions.release.workflow._release_impl")
    @patch("pkgmgr.actions.release.workflow.confirm_proceed_release", return_value=False)
    @patch("pkgmgr.actions.release.workflow.sys.stdin.isatty", return_value=True)
    def test_release_interactive_decline_runs_only_preview(self, _mock_isatty, _mock_confirm, mock_impl) -> None:
        release(preview=False, force=False, close=False)

        # interactive path: preview first, then decline => only one call
        self.assertEqual(mock_impl.call_count, 1)
        self.assertTrue(mock_impl.call_args_list[0].kwargs["preview"])

    @patch("pkgmgr.actions.release.workflow._release_impl")
    @patch("pkgmgr.actions.release.workflow.confirm_proceed_release", return_value=True)
    @patch("pkgmgr.actions.release.workflow.sys.stdin.isatty", return_value=True)
    def test_release_interactive_accept_runs_preview_then_real(self, _mock_isatty, _mock_confirm, mock_impl) -> None:
        release(preview=False, force=False, close=False)

        self.assertEqual(mock_impl.call_count, 2)
        self.assertTrue(mock_impl.call_args_list[0].kwargs["preview"])
        self.assertFalse(mock_impl.call_args_list[1].kwargs["preview"])


if __name__ == "__main__":
    unittest.main()
