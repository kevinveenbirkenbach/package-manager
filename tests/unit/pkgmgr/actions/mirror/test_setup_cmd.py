from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.setup_cmd import setup_mirrors
from pkgmgr.actions.mirror.types import RepoMirrorContext


class TestMirrorSetupCmd(unittest.TestCase):
    def _ctx(self, *, repo_dir: str = "/tmp/repo", resolved: dict[str, str] | None = None) -> RepoMirrorContext:
        # resolved_mirrors is a @property combining config+file. Put it into file_mirrors.
        return RepoMirrorContext(
            identifier="repo",
            repo_dir=repo_dir,
            config_mirrors={},
            file_mirrors=resolved or {},
        )

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_origin_remote")
    def test_setup_mirrors_local_calls_ensure_origin_remote(self, m_ensure, m_ctx) -> None:
        ctx = self._ctx(repo_dir="/tmp/repo", resolved={"primary": "git@x/y.git"})
        m_ctx.return_value = ctx

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

        # ensure_origin_remote(repo, ctx, preview) is called positionally in your code
        m_ensure.assert_called_once()
        args, kwargs = m_ensure.call_args

        self.assertEqual(args[0], repos[0])
        self.assertIs(args[1], ctx)
        self.assertEqual(kwargs.get("preview", args[2] if len(args) >= 3 else None), True)

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.determine_primary_remote_url")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_remote_reachable")
    def test_setup_mirrors_remote_no_mirrors_probes_primary(self, m_probe, m_primary, m_ctx) -> None:
        m_ctx.return_value = self._ctx(repo_dir="/tmp/repo", resolved={})
        m_primary.return_value = "git@github.com:alice/repo.git"
        m_probe.return_value = True

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
        m_probe.assert_called_once_with("git@github.com:alice/repo.git", cwd="/tmp/repo")

    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_remote_reachable")
    def test_setup_mirrors_remote_with_mirrors_probes_each(self, m_probe, m_ctx) -> None:
        m_ctx.return_value = self._ctx(
            repo_dir="/tmp/repo",
            resolved={
                "origin": "git@github.com:alice/repo.git",
                "backup": "ssh://git@git.veen.world:2201/alice/repo.git",
            },
        )
        m_probe.return_value = True

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
        m_probe.assert_any_call("git@github.com:alice/repo.git", cwd="/tmp/repo")
        m_probe.assert_any_call("ssh://git@git.veen.world:2201/alice/repo.git", cwd="/tmp/repo")


if __name__ == "__main__":
    unittest.main()
