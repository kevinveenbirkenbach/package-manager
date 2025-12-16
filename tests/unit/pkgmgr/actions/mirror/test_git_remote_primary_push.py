from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.git_remote import ensure_origin_remote
from pkgmgr.actions.mirror.types import RepoMirrorContext


class TestGitRemotePrimaryPush(unittest.TestCase):
    def test_origin_created_and_extra_push_added(self) -> None:
        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}

        # Use file_mirrors so ctx.resolved_mirrors contains both, no setattr (frozen dataclass!)
        ctx = RepoMirrorContext(
            identifier="repo",
            repo_dir="/tmp/repo",
            config_mirrors={},
            file_mirrors={
                "primary": "git@github.com:alice/repo.git",
                "backup": "git@github.com:alice/repo-backup.git",
            },
        )

        with patch("os.path.isdir", return_value=True):
            with patch("pkgmgr.actions.mirror.git_remote.has_origin_remote", return_value=False), patch(
                "pkgmgr.actions.mirror.git_remote.add_remote"
            ) as m_add_remote, patch(
                "pkgmgr.actions.mirror.git_remote.set_remote_url"
            ) as m_set_remote_url, patch(
                "pkgmgr.actions.mirror.git_remote.get_remote_push_urls", return_value=set()
            ), patch(
                "pkgmgr.actions.mirror.git_remote.add_remote_push_url"
            ) as m_add_push:
                ensure_origin_remote(repo, ctx, preview=False)

        # determine_primary_remote_url falls back to file order (primary first)
        m_add_remote.assert_called_once_with(
            "origin",
            "git@github.com:alice/repo.git",
            cwd="/tmp/repo",
            preview=False,
        )

        m_set_remote_url.assert_any_call(
            "origin",
            "git@github.com:alice/repo.git",
            cwd="/tmp/repo",
            push=False,
            preview=False,
        )
        m_set_remote_url.assert_any_call(
            "origin",
            "git@github.com:alice/repo.git",
            cwd="/tmp/repo",
            push=True,
            preview=False,
        )

        m_add_push.assert_called_once_with(
            "origin",
            "git@github.com:alice/repo-backup.git",
            cwd="/tmp/repo",
            preview=False,
        )
