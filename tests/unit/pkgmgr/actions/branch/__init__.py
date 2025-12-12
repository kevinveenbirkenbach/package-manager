import unittest
from unittest.mock import patch, MagicMock

from pkgmgr.actions.branch.utils import _resolve_base_branch
from pkgmgr.core.git import GitError


class TestResolveBaseBranch(unittest.TestCase):
    @patch("pkgmgr.actions.branch.utils.run_git")
    def test_resolves_preferred(self, run_git):
        run_git.return_value = None
        result = _resolve_base_branch("main", "master", cwd=".")
        self.assertEqual(result, "main")
        run_git.assert_called_with(["rev-parse", "--verify", "main"], cwd=".")

    @patch("pkgmgr.actions.branch.utils.run_git")
    def test_resolves_fallback(self, run_git):
        run_git.side_effect = [
            GitError("main missing"),
            None,
        ]
        result = _resolve_base_branch("main", "master", cwd=".")
        self.assertEqual(result, "master")

    @patch("pkgmgr.actions.branch.utils.run_git")
    def test_raises_when_no_branch_exists(self, run_git):
        run_git.side_effect = GitError("missing")
        with self.assertRaises(RuntimeError):
            _resolve_base_branch("main", "master", cwd=".")


if __name__ == "__main__":
    unittest.main()
