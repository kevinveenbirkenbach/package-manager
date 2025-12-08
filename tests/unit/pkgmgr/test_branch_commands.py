from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.branch_commands import open_branch
from pkgmgr.git_utils import GitError


class TestOpenBranch(unittest.TestCase):
    @patch("pkgmgr.branch_commands.run_git")
    def test_open_branch_with_explicit_name_and_default_base(self, mock_run_git) -> None:
        """
        open_branch(name, base='main') should:
        - fetch origin
        - checkout base
        - pull base
        - create new branch
        - push with upstream
        """
        mock_run_git.return_value = ""

        open_branch(name="feature/test", base_branch="main", cwd="/repo")

        # We expect a specific sequence of Git calls.
        expected_calls = [
            (["fetch", "origin"], "/repo"),
            (["checkout", "main"], "/repo"),
            (["pull", "origin", "main"], "/repo"),
            (["checkout", "-b", "feature/test"], "/repo"),
            (["push", "-u", "origin", "feature/test"], "/repo"),
        ]

        self.assertEqual(mock_run_git.call_count, len(expected_calls))

        for call, (args_expected, cwd_expected) in zip(
            mock_run_git.call_args_list, expected_calls
        ):
            args, kwargs = call
            self.assertEqual(args[0], args_expected)
            self.assertEqual(kwargs.get("cwd"), cwd_expected)

    @patch("builtins.input", return_value="feature/interactive")
    @patch("pkgmgr.branch_commands.run_git")
    def test_open_branch_prompts_for_name_if_missing(
        self,
        mock_run_git,
        mock_input,
    ) -> None:
        """
        If name is None/empty, open_branch should prompt via input()
        and still perform the full Git sequence.
        """
        mock_run_git.return_value = ""

        open_branch(name=None, base_branch="develop", cwd="/repo")

        # Ensure we asked for input exactly once
        mock_input.assert_called_once()

        expected_calls = [
            (["fetch", "origin"], "/repo"),
            (["checkout", "develop"], "/repo"),
            (["pull", "origin", "develop"], "/repo"),
            (["checkout", "-b", "feature/interactive"], "/repo"),
            (["push", "-u", "origin", "feature/interactive"], "/repo"),
        ]

        self.assertEqual(mock_run_git.call_count, len(expected_calls))
        for call, (args_expected, cwd_expected) in zip(
            mock_run_git.call_args_list, expected_calls
        ):
            args, kwargs = call
            self.assertEqual(args[0], args_expected)
            self.assertEqual(kwargs.get("cwd"), cwd_expected)

    @patch("pkgmgr.branch_commands.run_git")
    def test_open_branch_raises_runtimeerror_on_git_failure(self, mock_run_git) -> None:
        """
        If a GitError occurs (e.g. fetch fails), open_branch should
        raise a RuntimeError with a helpful message.
        """

        def side_effect(args, cwd="."):
            # Simulate a failure on the first call (fetch)
            raise GitError("simulated fetch failure")

        mock_run_git.side_effect = side_effect

        with self.assertRaises(RuntimeError) as cm:
            open_branch(name="feature/fail", base_branch="main", cwd="/repo")

        msg = str(cm.exception)
        self.assertIn("Failed to fetch from origin", msg)
        self.assertIn("simulated fetch failure", msg)


if __name__ == "__main__":
    unittest.main()
