from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.git_remote import ensure_origin_remote
from pkgmgr.actions.mirror.types import RepoMirrorContext


class TestGitRemotePrimaryPush(unittest.TestCase):
    def test_origin_created_and_extra_push_added(self) -> None:
        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}
        ctx = RepoMirrorContext(
            identifier="repo",
            repo_dir="/tmp/repo",
            config_mirrors={},
            file_mirrors={
                "primary": "git@github.com:alice/repo.git",
                "backup": "git@github.com:alice/repo-backup.git",
            },
        )

        executed: list[str] = []

        def fake_run(cmd: str, cwd: str, preview: bool) -> None:
            executed.append(cmd)

        def fake_git(args, cwd):
            if args == ["remote"]:
                return ""
            if args == ["remote", "get-url", "--push", "--all", "origin"]:
                return "git@github.com:alice/repo.git\n"
            return ""

        with patch("os.path.isdir", return_value=True), patch(
            "pkgmgr.actions.mirror.git_remote.run_command", side_effect=fake_run
        ), patch(
            "pkgmgr.actions.mirror.git_remote._safe_git_output", side_effect=fake_git
        ):
            ensure_origin_remote(repo, ctx, preview=False)

        self.assertEqual(
            executed,
            [
                "git remote add origin git@github.com:alice/repo.git",
                "git remote set-url origin git@github.com:alice/repo.git",
                "git remote set-url --push origin git@github.com:alice/repo.git",
                "git remote set-url --add --push origin git@github.com:alice/repo-backup.git",
            ],
        )
