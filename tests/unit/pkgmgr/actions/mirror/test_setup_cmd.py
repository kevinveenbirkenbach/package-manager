from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.setup_cmd import setup_mirrors
from pkgmgr.actions.mirror.types import RepoMirrorContext


class TestMirrorSetupCmd(unittest.TestCase):
    def _ctx(
        self,
        *,
        repo_dir: str = "/tmp/repo",
        resolved: dict[str, str] | None = None,
    ) -> RepoMirrorContext:
        # RepoMirrorContext derives resolved via property (config + file)
        # We feed mirrors via file_mirrors to keep insertion order realistic.
        return RepoMirrorContext(
            identifier="repo-id",
            repo_dir=repo_dir,
            config_mirrors={},
            file_mirrors=resolved or {},
        )

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_origin_remote")
    def test_setup_mirrors_local_calls_ensure_origin_remote(self, m_ensure, m_ctx) -> None:
        m_ctx.return_value = self._ctx(repo_dir="/tmp/repo", resolved={"primary": "git@x/y.git"})

        repos = [{"provider": "github.com", "account": "alice", "repository": "repo"}]
        setup_mirrors(
            selected_repos=repos,
            repositories_base_dir="/tmp",
            all_repos=repos,
            preview=True,
            local=True,
            remote=False,
            ensure_remote=False,
        )

        self.assertEqual(m_ensure.call_count, 1)
        args, kwargs = m_ensure.call_args

        # ensure_origin_remote(repo, ctx, preview) may be positional or kw.
        # Accept both to avoid coupling tests to call style.
        if "preview" in kwargs:
            self.assertTrue(kwargs["preview"])
        else:
            # args: (repo, ctx, preview)
            self.assertTrue(args[2])

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_mirror")
    @patch("pkgmgr.actions.mirror.setup_cmd.determine_primary_remote_url")
    def test_setup_mirrors_remote_no_mirrors_probes_primary(self, m_primary, m_probe, m_ctx) -> None:
        m_ctx.return_value = self._ctx(repo_dir="/tmp/repo", resolved={})
        m_primary.return_value = "git@github.com:alice/repo.git"
        m_probe.return_value = (True, "")

        repos = [{"provider": "github.com", "account": "alice", "repository": "repo"}]
        setup_mirrors(
            selected_repos=repos,
            repositories_base_dir="/tmp",
            all_repos=repos,
            preview=True,
            local=False,
            remote=True,
            ensure_remote=False,
        )

        m_primary.assert_called()
        m_probe.assert_called_with("git@github.com:alice/repo.git", "/tmp/repo")

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_mirror")
    def test_setup_mirrors_remote_with_mirrors_probes_each(self, m_probe, m_ctx) -> None:
        m_ctx.return_value = self._ctx(
            repo_dir="/tmp/repo",
            resolved={
                "origin": "git@github.com:alice/repo.git",
                "backup": "ssh://git@git.veen.world:2201/alice/repo.git",
            },
        )
        m_probe.return_value = (True, "")

        repos = [{"provider": "github.com", "account": "alice", "repository": "repo"}]
        setup_mirrors(
            selected_repos=repos,
            repositories_base_dir="/tmp",
            all_repos=repos,
            preview=True,
            local=False,
            remote=True,
            ensure_remote=False,
        )

        self.assertEqual(m_probe.call_count, 2)


if __name__ == "__main__":
    unittest.main()
