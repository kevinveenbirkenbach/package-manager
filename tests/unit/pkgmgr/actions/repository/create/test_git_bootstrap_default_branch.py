from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.create.git_bootstrap import GitBootstrapper
from pkgmgr.core.git.commands import GitPushUpstreamError


class TestGitBootstrapperDefaultBranch(unittest.TestCase):
    def test_init_repo_uses_main_as_initial_branch(self):
        with (
            patch("pkgmgr.actions.repository.create.git_bootstrap.init") as init,
            patch("pkgmgr.actions.repository.create.git_bootstrap.add_all"),
            patch("pkgmgr.actions.repository.create.git_bootstrap.commit"),
        ):
            GitBootstrapper().init_repo("/repo", preview=False)

        init.assert_called_once_with(
            initial_branch="main", cwd="/repo", preview=False
        )

    def test_push_default_branch_pushes_main(self):
        with (
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.branch_move"
            ) as branch_move,
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.push_upstream"
            ) as push_upstream,
        ):
            GitBootstrapper().push_default_branch("/repo", preview=False)

        branch_move.assert_called_once_with("main", cwd="/repo", preview=False)
        push_upstream.assert_called_once_with(
            "origin", "main", cwd="/repo", preview=False
        )

    def test_failed_push_does_not_fall_back_to_master(self):
        with (
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.branch_move"
            ) as branch_move,
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.push_upstream",
                side_effect=GitPushUpstreamError("boom"),
            ) as push_upstream,
        ):
            GitBootstrapper().push_default_branch("/repo", preview=False)

        self.assertEqual(
            [call.args[0] for call in branch_move.call_args_list], ["main"]
        )
        self.assertEqual(
            [call.args[1] for call in push_upstream.call_args_list], ["main"]
        )


if __name__ == "__main__":
    unittest.main()
