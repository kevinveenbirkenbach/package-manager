import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.actions.branch.open_branch import open_branch


class TestOpenBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.open_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.open_branch.run_git")
    def test_open_branch_executes_git_commands(self, run_git, resolve):
        open_branch("feature-x", base_branch="main", cwd=".")
        expected_calls = [
            (["fetch", "origin"],),
            (["checkout", "main"],),
            (["pull", "origin", "main"],),
            (["checkout", "-b", "feature-x"],),
            (["push", "-u", "origin", "feature-x"],),
        ]
        actual = [call.args for call in run_git.call_args_list]
        self.assertEqual(actual, expected_calls)

    @patch("builtins.input", return_value="auto-branch")
    @patch("pkgmgr.actions.branch.open_branch._resolve_base_branch", return_value="main")
    @patch("pkgmgr.actions.branch.open_branch.run_git")
    def test_open_branch_prompts_for_name(self, run_git, resolve, input_mock):
        open_branch(None)
        calls = [call.args for call in run_git.call_args_list]
        self.assertEqual(calls[3][0][0], "checkout")  # verify git executed normally

    def test_open_branch_rejects_empty_name(self):
        with patch("builtins.input", return_value=""):
            with self.assertRaises(RuntimeError):
                open_branch(None)


if __name__ == "__main__":
    unittest.main()
