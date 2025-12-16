import unittest
from unittest.mock import patch

from pkgmgr.actions.branch.drop_branch import drop_branch
from pkgmgr.core.git.errors import GitError
from pkgmgr.core.git.commands import GitDeleteRemoteBranchError


class TestDropBranch(unittest.TestCase):
    @patch("builtins.input", return_value="y")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.delete_local_branch")
    @patch("pkgmgr.actions.branch.drop_branch.delete_remote_branch")
    def test_drop_branch_happy_path(self, delete_remote, delete_local, _resolve, _current, _input_mock) -> None:
        drop_branch(None, cwd=".")
        delete_local.assert_called_once_with("feature-x", cwd=".", force=False)
        delete_remote.assert_called_once_with("origin", "feature-x", cwd=".")

    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.resolve_base_branch", return_value="main")
    def test_refuses_to_drop_base_branch(self, _resolve, _current) -> None:
        with self.assertRaises(RuntimeError):
            drop_branch(None)

    @patch("builtins.input", return_value="n")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.delete_local_branch")
    def test_drop_branch_aborts_on_no(self, delete_local, _resolve, _current, _input_mock) -> None:
        drop_branch(None, cwd=".")
        delete_local.assert_not_called()

    @patch("builtins.input")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.delete_local_branch")
    @patch("pkgmgr.actions.branch.drop_branch.delete_remote_branch")
    def test_drop_branch_force_skips_prompt(
        self,
        delete_remote,
        delete_local,
        _resolve,
        _current,
        input_mock,
    ) -> None:
        drop_branch(None, cwd=".", force=True)

        input_mock.assert_not_called()
        delete_local.assert_called_once_with("feature-x", cwd=".", force=False)
        delete_remote.assert_called_once_with("origin", "feature-x", cwd=".")

    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", side_effect=GitError("fail"))
    def test_drop_branch_errors_if_no_branch_detected(self, _current) -> None:
        with self.assertRaises(RuntimeError):
            drop_branch(None)

    @patch("builtins.input", return_value="y")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.delete_local_branch")
    @patch(
        "pkgmgr.actions.branch.drop_branch.delete_remote_branch",
        side_effect=GitDeleteRemoteBranchError("boom", cwd="."),
    )
    def test_drop_branch_remote_delete_failure_is_wrapped(
        self,
        _delete_remote,
        _delete_local,
        _resolve,
        _current,
        _input_mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            drop_branch(None, cwd=".")
        self.assertIn("remote deletion failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
