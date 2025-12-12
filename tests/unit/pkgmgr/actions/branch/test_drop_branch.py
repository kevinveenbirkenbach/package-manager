import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.actions.branch.drop_branch import drop_branch
from pkgmgr.core.git import GitError


class TestDropBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.drop_branch.input", return_value="y")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.run_git")
    def test_drop_branch_happy_path(self, run_git, resolve, current, input_mock):
        drop_branch(None, cwd=".")
        expected = [
            (["branch", "-d", "feature-x"],),
            (["push", "origin", "--delete", "feature-x"],),
        ]
        actual = [call.args for call in run_git.call_args_list]
        self.assertEqual(actual, expected)

    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch._resolve_base_branch", return_value="main")
    def test_refuses_to_drop_base_branch(self, resolve, current):
        with self.assertRaises(RuntimeError):
            drop_branch(None)

    @patch("pkgmgr.actions.branch.drop_branch.input", return_value="n")
    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.run_git")
    def test_drop_branch_aborts_on_no(self, run_git, resolve, current, input_mock):
        drop_branch(None, cwd=".")
        run_git.assert_not_called()

    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", return_value="feature-x")
    @patch("pkgmgr.actions.branch.drop_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.drop_branch.run_git")
    def test_drop_branch_force_skips_prompt(self, run_git, resolve, current):
        drop_branch(None, cwd=".", force=True)
        self.assertGreater(len(run_git.call_args_list), 0)

    @patch("pkgmgr.actions.branch.drop_branch.get_current_branch", side_effect=GitError("fail"))
    def test_drop_branch_errors_if_no_branch_detected(self, current):
        with self.assertRaises(RuntimeError):
            drop_branch(None)


if __name__ == "__main__":
    unittest.main()
