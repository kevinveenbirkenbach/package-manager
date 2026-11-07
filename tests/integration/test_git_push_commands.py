from __future__ import annotations

import os
import subprocess
import tempfile
import unittest

from pkgmgr.core.git.commands import delete_remote_branch, push, push_upstream

REMOTE = "-r"


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.org",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestPushCommandsEndOptions(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = os.path.realpath(self._tmp.name)
        self.origin = os.path.join(root, "origin.git")
        self.repo = os.path.join(root, "repo")
        git(root, "init", "-q", "--bare", "-b", "main", self.origin)
        git(root, "init", "-q", "-b", "main", self.repo)
        git(self.repo, "config", f"remote.{REMOTE}.url", self.origin)
        git(
            self.repo,
            "config",
            f"remote.{REMOTE}.fetch",
            f"+refs/heads/*:refs/remotes/{REMOTE}/*",
        )
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")

    def _branches(self) -> str:
        return git(self.origin, "for-each-ref", "--format=%(refname:short)")

    def test_remote_named_like_an_option(self) -> None:
        push_upstream(REMOTE, "main", cwd=self.repo)
        self.assertEqual(self._branches(), "main")
        self.assertEqual(
            git(self.repo, "rev-parse", "--abbrev-ref", "@{u}"), f"{REMOTE}/main"
        )

        git(self.repo, "commit", "-q", "--amend", "--allow-empty", "-m", "rewritten")
        push(REMOTE, "main:feature", cwd=self.repo)
        push(REMOTE, "main", force=True, cwd=self.repo)
        self.assertEqual(
            git(self.origin, "rev-parse", "main"), git(self.repo, "rev-parse", "HEAD")
        )

        delete_remote_branch(REMOTE, "feature", cwd=self.repo)
        self.assertEqual(self._branches(), "main")


if __name__ == "__main__":
    unittest.main()
