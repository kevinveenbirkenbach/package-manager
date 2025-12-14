from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.git_remote import (
    build_default_ssh_url,
    determine_primary_remote_url,
    has_origin_remote,
)
from pkgmgr.actions.mirror.types import RepoMirrorContext


class TestMirrorGitRemote(unittest.TestCase):
    def _ctx(self, *, file=None, config=None) -> RepoMirrorContext:
        return RepoMirrorContext(
            identifier="repo",
            repo_dir="/tmp/repo",
            config_mirrors=config or {},
            file_mirrors=file or {},
        )

    def test_build_default_ssh_url(self) -> None:
        repo = {
            "provider": "github.com",
            "account": "alice",
            "repository": "repo",
        }
        self.assertEqual(
            build_default_ssh_url(repo),
            "git@github.com:alice/repo.git",
        )

    def test_determine_primary_prefers_origin(self) -> None:
        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}
        ctx = self._ctx(config={"origin": "git@github.com:alice/repo.git"})
        self.assertEqual(
            determine_primary_remote_url(repo, ctx),
            "git@github.com:alice/repo.git",
        )

    def test_determine_primary_uses_file_order(self) -> None:
        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}
        ctx = self._ctx(
            file={
                "first": "git@a/first.git",
                "second": "git@a/second.git",
            }
        )
        self.assertEqual(
            determine_primary_remote_url(repo, ctx),
            "git@a/first.git",
        )

    def test_determine_primary_fallback_default(self) -> None:
        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}
        ctx = self._ctx()
        self.assertEqual(
            determine_primary_remote_url(repo, ctx),
            "git@github.com:alice/repo.git",
        )

    @patch("pkgmgr.actions.mirror.git_remote._safe_git_output")
    def test_has_origin_remote(self, m_out) -> None:
        m_out.return_value = "origin\nupstream\n"
        self.assertTrue(has_origin_remote("/tmp/repo"))
