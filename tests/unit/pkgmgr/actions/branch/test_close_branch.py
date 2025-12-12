import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.actions.branch.close_branch import close_branch
from pkgmgr.core.git import GitError


class TestCloseBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.close_branch.input", return_value="y")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.run_git")
    def test_close_branch_happy_path(self, run_git, resolve, current, input_mock):
        close_branch(None, cwd=".")
        expected = [
            (["fetch", "origin"],),
            (["checkout", "main"],),
            (["pull", "origin", "main"],),
            (["merge", "--no-ff", "feature-x"],),
            (["push", "origin", "main"],),
            (["branch", "-d", "feature-x"],),
            (["push", "origin", "--delete", "feature-x"],),
        ]
        actual = [call.args for call in run_git.call_args_list]
        self.assertEqual(actual, expected)

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch._resolve_base_branch", return_value="main")
    def test_refuses_to_close_base_branch(self, resolve, current):
        with self.assertRaises(RuntimeError):
            close_branch(None)

    @patch("pkgmgr.actions.branch.close_branch.input", return_value="n")
    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.run_git")
    def test_close_branch_aborts_on_no(self, run_git, resolve, current, input_mock):
        close_branch(None, cwd=".")
        run_git.assert_not_called()

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.close_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.close_branch.run_git")
    def test_close_branch_force_skips_prompt(self, run_git, resolve, current):
        close_branch(None, cwd=".", force=True)
        self.assertGreater(len(run_git.call_args_list), 0)

    @patch("pkgmgr.actions.branch.close_branch.get_current_branch", side_effect=GitError("fail"))
    def test_close_branch_errors_if_cannot_detect_branch(self, current):
        with self.assertRaises(RuntimeError):
            close_branch(None)


if __name__ == "__main__":
    unittest.main()
