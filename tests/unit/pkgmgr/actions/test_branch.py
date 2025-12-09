from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.branch import open_branch
from pkgmgr.core.git import GitError


class TestOpenBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.run_git")
    def test_open_branch_with_explicit_name_and_default_base(self, mock_run_git) -> None:
        """
        open_branch(name, base='main') should:
        - resolve base branch (prefers 'main', falls back to 'master')
        - fetch origin
        - checkout resolved base
        - pull resolved base
        - create new branch
        - push with upstream
        """
        mock_run_git.return_value = ""

        open_branch(name="feature/test", base_branch="main", cwd="/repo")

        # We expect a specific sequence of Git calls.
        expected_calls = [
            (["rev-parse", "--verify", "main"], "/repo"),
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
    @patch("pkgmgr.actions.branch.run_git")
    def test_open_branch_prompts_for_name_if_missing(
        self,
        mock_run_git,
        mock_input,
    ) -> None:
        """
        If name is None/empty, open_branch should prompt via input()
        and still perform the full Git sequence on the resolved base.
        """
        mock_run_git.return_value = ""

        open_branch(name=None, base_branch="develop", cwd="/repo")

        # Ensure we asked for input exactly once
        mock_input.assert_called_once()

        expected_calls = [
            (["rev-parse", "--verify", "develop"], "/repo"),
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

    @patch("pkgmgr.actions.branch.run_git")
    def test_open_branch_raises_runtimeerror_on_fetch_failure(self, mock_run_git) -> None:
        """
        If a GitError occurs on fetch, open_branch should raise a RuntimeError
        with a helpful message.
        """

        def side_effect(args, cwd="."):
            # First call: base resolution (rev-parse) should succeed
            if args == ["rev-parse", "--verify", "main"]:
                return ""
            # Second call: fetch should fail
            if args == ["fetch", "origin"]:
                raise GitError("simulated fetch failure")
            return ""

        mock_run_git.side_effect = side_effect

        with self.assertRaises(RuntimeError) as cm:
            open_branch(name="feature/fail", base_branch="main", cwd="/repo")

        msg = str(cm.exception)
        self.assertIn("Failed to fetch from origin", msg)
        self.assertIn("simulated fetch failure", msg)

    @patch("pkgmgr.actions.branch.run_git")
    def test_open_branch_uses_fallback_master_if_main_missing(self, mock_run_git) -> None:
        """
        If the preferred base (e.g. 'main') does not exist, open_branch should
        fall back to the fallback base (default: 'master').
        """

        def side_effect(args, cwd="."):
            # First: rev-parse main -> fails
            if args == ["rev-parse", "--verify", "main"]:
                raise GitError("main does not exist")
            # Second: rev-parse master -> succeeds
            if args == ["rev-parse", "--verify", "master"]:
                return ""
            # Then normal flow on master
            return ""

        mock_run_git.side_effect = side_effect

        open_branch(name="feature/fallback", base_branch="main", cwd="/repo")

        expected_calls = [
            (["rev-parse", "--verify", "main"], "/repo"),
            (["rev-parse", "--verify", "master"], "/repo"),
            (["fetch", "origin"], "/repo"),
            (["checkout", "master"], "/repo"),
            (["pull", "origin", "master"], "/repo"),
            (["checkout", "-b", "feature/fallback"], "/repo"),
            (["push", "-u", "origin", "feature/fallback"], "/repo"),
        ]

        self.assertEqual(mock_run_git.call_count, len(expected_calls))
        for call, (args_expected, cwd_expected) in zip(
            mock_run_git.call_args_list, expected_calls
        ):
            args, kwargs = call
            self.assertEqual(args[0], args_expected)
            self.assertEqual(kwargs.get("cwd"), cwd_expected)


if __name__ == "__main__":
    unittest.main()
