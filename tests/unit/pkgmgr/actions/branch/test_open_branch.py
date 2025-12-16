import unittest
from unittest.mock import patch

from pkgmgr.actions.branch.open_branch import open_branch


class TestOpenBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.open_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.open_branch.fetch")
    @patch("pkgmgr.actions.branch.open_branch.checkout")
    @patch("pkgmgr.actions.branch.open_branch.pull")
    @patch("pkgmgr.actions.branch.open_branch.create_branch")
    @patch("pkgmgr.actions.branch.open_branch.push_upstream")
    def test_open_branch_executes_git_commands(
        self,
        push_upstream,
        create_branch,
        pull,
        checkout,
        fetch,
        _resolve,
    ) -> None:
        open_branch("feature-x", base_branch="main", cwd=".")

        fetch.assert_called_once_with("origin", cwd=".")
        checkout.assert_called_once_with("main", cwd=".")
        pull.assert_called_once_with("origin", "main", cwd=".")
        create_branch.assert_called_once_with("feature-x", "main", cwd=".")
        push_upstream.assert_called_once_with("origin", "feature-x", cwd=".")

    @patch("builtins.input", return_value="auto-branch")
    @patch("pkgmgr.actions.branch.open_branch.resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.open_branch.fetch")
    @patch("pkgmgr.actions.branch.open_branch.checkout")
    @patch("pkgmgr.actions.branch.open_branch.pull")
    @patch("pkgmgr.actions.branch.open_branch.create_branch")
    @patch("pkgmgr.actions.branch.open_branch.push_upstream")
    def test_open_branch_prompts_for_name(
        self,
        push_upstream,
        create_branch,
        pull,
        checkout,
        fetch,
        _resolve,
        _input_mock,
    ) -> None:
        open_branch(None)

        fetch.assert_called_once_with("origin", cwd=".")
        checkout.assert_called_once_with("main", cwd=".")
        pull.assert_called_once_with("origin", "main", cwd=".")
        create_branch.assert_called_once_with("auto-branch", "main", cwd=".")
        push_upstream.assert_called_once_with("origin", "auto-branch", cwd=".")

    def test_open_branch_rejects_empty_name(self) -> None:
        with patch("builtins.input", return_value=""):
            with self.assertRaises(RuntimeError):
                open_branch(None)


if __name__ == "__main__":
    unittest.main()
