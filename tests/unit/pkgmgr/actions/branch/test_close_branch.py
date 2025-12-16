import unittest
from unittest.mock import patch

from pkgmgr.actions.branch.close_branch import close_branch
from pkgmgr.core.git.errors import GitError
from pkgmgr.core.git.commands import GitDeleteRemoteBranchError


class TestCloseBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.close_branch.input", return_value="y")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    @patch("pkgmgr.actions.branch.close_branch.checkout")
    @patch("pkgmgr.actions.branch.close_branch.pull")
    @patch("pkgmgr.actions.branch.close_branch.merge_no_ff")
    @patch("pkgmgr.actions.branch.close_branch.push")
    @patch("pkgmgr.actions.branch.close_branch.delete_local_branch")
    @patch("pkgmgr.actions.branch.close_branch.delete_remote_branch")
    def test_close_branch_happy_path(
        self,
        delete_remote_branch,
        delete_local_branch,
        push,
        merge_no_ff,
        pull,
        checkout,
        fetch,
        resolve,
        current,
        input_mock,
    ):
        close_branch(None, cwd=".")
        fetch.assert_called_once_with("origin", cwd=".")
        checkout.assert_called_once_with("main", cwd=".")
        pull.assert_called_once_with("origin", "main", cwd=".")
        merge_no_ff.assert_called_once_with("feature-x", cwd=".")
        push.assert_called_once_with("origin", "main", cwd=".")
        delete_local_branch.assert_called_once_with("feature-x", cwd=".", force=False)
        delete_remote_branch.assert_called_once_with("origin", "feature-x", cwd=".")

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    def test_refuses_to_close_base_branch(self, resolve, current):
        with self.assertRaises(RuntimeError):
            close_branch(None)

    @patch("pkgmgr.actions.branch.close_branch.input", return_value="n")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    def test_close_branch_aborts_on_no(self, fetch, resolve, current, input_mock):
        close_branch(None, cwd=".")
        fetch.assert_not_called()

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    def test_close_branch_force_skips_prompt(self, fetch, resolve, current):
        close_branch(None, cwd=".", force=True)
        fetch.assert_called_once()

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", side_effect=GitError("fail"))
    def test_close_branch_errors_if_cannot_detect_branch(self, current):
        with self.assertRaises(RuntimeError):
            close_branch(None)

    @patch("pkgmgr.actions.branch.close_branch.input", return_value="y")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    @patch("pkgmgr.actions.branch.close_branch.checkout")
    @patch("pkgmgr.actions.branch.close_branch.pull")
    @patch("pkgmgr.actions.branch.close_branch.merge_no_ff")
    @patch("pkgmgr.actions.branch.close_branch.push")
    @patch("pkgmgr.actions.branch.close_branch.delete_local_branch")
    @patch(
        "pkgmgr.actions.branch.close_branch.delete_remote_branch",
        side_effect=GitDeleteRemoteBranchError("boom", cwd="."),
    )
    def test_close_branch_remote_delete_failure_is_wrapped(
        self,
        delete_remote_branch,
        delete_local_branch,
        push,
        merge_no_ff,
        pull,
        checkout,
        fetch,
        resolve,
        current,
        input_mock,
    ):
        with self.assertRaises(RuntimeError) as ctx:
            close_branch(None, cwd=".")
        self.assertIn("remote deletion failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
