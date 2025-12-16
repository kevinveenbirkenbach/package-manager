import unittest
from unittest.mock import patch

from pkgmgr.actions.branch.close_branch import close_branch
from pkgmgr.core.git.errors import GitError
from pkgmgr.core.git.commands import GitDeleteRemoteBranchError


class TestCloseBranch(unittest.TestCase):
    @patch("builtins.input", return_value="y")
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
        _resolve,
        _current,
        _input_mock,
    ) -> None:
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
    def test_refuses_to_close_base_branch(self, _resolve, _current) -> None:
        with self.assertRaises(RuntimeError):
            close_branch(None)

    @patch("builtins.input", return_value="n")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    def test_close_branch_aborts_on_no(self, fetch, _resolve, _current, _input_mock) -> None:
        close_branch(None, cwd=".")
        fetch.assert_not_called()

    @patch("builtins.input")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.fetch")
    @patch("pkgmgr.actions.branch.close_branch.checkout")
    @patch("pkgmgr.actions.branch.close_branch.pull")
    @patch("pkgmgr.actions.branch.close_branch.merge_no_ff")
    @patch("pkgmgr.actions.branch.close_branch.push")
    @patch("pkgmgr.actions.branch.close_branch.delete_local_branch")
    @patch("pkgmgr.actions.branch.close_branch.delete_remote_branch")
    def test_close_branch_force_skips_prompt(
        self,
        delete_remote_branch,
        delete_local_branch,
        push,
        merge_no_ff,
        pull,
        checkout,
        fetch,
        _resolve,
        _current,
        input_mock,
    ) -> None:
        close_branch(None, cwd=".", force=True)

        # no interactive prompt when forced
        input_mock.assert_not_called()

        # workflow still runs (but is mocked)
        fetch.assert_called_once_with("origin", cwd=".")
        checkout.assert_called_once_with("main", cwd=".")
        pull.assert_called_once_with("origin", "main", cwd=".")
        merge_no_ff.assert_called_once_with("feature-x", cwd=".")
        push.assert_called_once_with("origin", "main", cwd=".")
        delete_local_branch.assert_called_once_with("feature-x", cwd=".", force=False)
        delete_remote_branch.assert_called_once_with("origin", "feature-x", cwd=".")

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", side_effect=GitError("fail"))
    def test_close_branch_errors_if_cannot_detect_branch(self, _current) -> None:
        with self.assertRaises(RuntimeError):
            close_branch(None)

    @patch("builtins.input", return_value="y")
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
        _delete_remote_branch,
        _delete_local_branch,
        _push,
        _merge_no_ff,
        _pull,
        _checkout,
        _fetch,
        _resolve,
        _current,
        _input_mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            close_branch(None, cwd=".")
        self.assertIn("remote deletion failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
