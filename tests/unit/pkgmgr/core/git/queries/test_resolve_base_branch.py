from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.git import GitError
from pkgmgr.core.git.queries.resolve_base_branch import (
    GitBaseBranchNotFoundError,
    resolve_base_branch,
)


class TestResolveBaseBranch(unittest.TestCase):
    @patch("pkgmgr.core.git.queries.resolve_base_branch.run")
    def test_resolves_preferred(self, mock_run):
        mock_run.return_value = "dummy"
        result = resolve_base_branch("main", "master", cwd=".")
        self.assertEqual(result, "main")
        mock_run.assert_called_with(["rev-parse", "--verify", "main"], cwd=".")

    @patch("pkgmgr.core.git.queries.resolve_base_branch.run")
    def test_resolves_fallback(self, mock_run):
        mock_run.side_effect = [
            GitError("fatal: Needed a single revision"),  # treat as "missing"
            "dummy",
        ]
        result = resolve_base_branch("main", "master", cwd=".")
        self.assertEqual(result, "master")
        self.assertEqual(mock_run.call_args_list[0].kwargs["cwd"], ".")
        self.assertEqual(mock_run.call_args_list[1].kwargs["cwd"], ".")

    @patch("pkgmgr.core.git.queries.resolve_base_branch.run")
    def test_raises_when_no_branch_exists(self, mock_run):
        mock_run.side_effect = [
            GitError("fatal: Needed a single revision"),
            GitError("fatal: Needed a single revision"),
        ]
        with self.assertRaises(GitBaseBranchNotFoundError):
            resolve_base_branch("main", "master", cwd=".")


if __name__ == "__main__":
    unittest.main()
