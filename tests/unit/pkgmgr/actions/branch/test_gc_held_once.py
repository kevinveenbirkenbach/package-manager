from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.branch import gc

AUTHOR = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
MERGED = 12
REGISTRATIONS = 40
GIT = shutil.which("git")


@unittest.skipUnless(GIT, "git builds the repository under test")
class TestHeldBranchesReadOnce(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        home = os.path.join(self.root, "home")
        os.makedirs(home)
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        patcher = patch.dict(os.environ, {**clean, "HOME": home}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = os.path.join(self.root, "repo")
        self._shape()

    def git(self, *args: str) -> str:
        return subprocess.run(
            [GIT, "-c", "commit.gpgsign=false", *args],
            cwd=self.repo,
            env={**os.environ, **AUTHOR},
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _write(self, path: str, text: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _shape(self) -> None:
        origin = os.path.join(self.root, "origin.git")
        subprocess.run([GIT, "init", "-q", "--bare", "-b", "main", origin], check=True)
        subprocess.run([GIT, "init", "-q", "-b", "main", self.repo], check=True)
        self.git("remote", "add", "origin", origin)
        self._write(os.path.join(self.repo, "c1"), "c1")
        self.git("add", "c1")
        self.git("commit", "-q", "-m", "c1")
        self.git("checkout", "-q", "-b", "side")
        self._write(os.path.join(self.repo, "f1"), "f1")
        self.git("add", "f1")
        self.git("commit", "-q", "-m", "f1")
        f1 = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "m1", "side")
        self.git("branch", "-q", "-D", "side")
        self.git("push", "-q", "origin", "main")
        self.git("fetch", "-q", "origin")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        for index in range(MERGED):
            self.git("branch", f"merged-{index:03d}", f1)
        self.git("symbolic-ref", "refs/heads/alias", "refs/heads/merged-001")
        base = os.path.join(self.repo, ".git", "worktrees")
        for index in range(REGISTRATIONS):
            reg = os.path.join(base, f"wt{index:03d}")
            head = "ref: refs/heads/merged-002\n" if index == 7 else f"{f1}\n"
            self._write(os.path.join(reg, "HEAD"), head)
            self._write(os.path.join(reg, "commondir"), "../..\n")
            self._write(
                os.path.join(reg, "gitdir"), f"{self.root}/gone/wt{index:03d}/.git\n"
            )
        self._write(
            os.path.join(base, "wt011", "rebase-merge", "head-name"),
            "refs/heads/merged-003\n",
        )
        self._write(os.path.join(self.repo, ".git", "BISECT_START"), "merged-004\n")

    def _run(self, *, cached: bool, apply: bool) -> tuple[dict, int]:
        out = io.StringIO()
        with ExitStack() as stack:
            held = stack.enter_context(
                patch.object(gc, "_held_branches", wraps=gc._held_branches)
            )
            if not cached:
                stack.enter_context(
                    patch.object(gc, "cache", side_effect=lambda func: func)
                )
            stack.enter_context(
                patch.object(gc, "host_pid_namespace", return_value=True)
            )
            stack.enter_context(patch.object(gc, "_process_cwds", return_value={}))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(io.StringIO()))
            code = gc.cleanup(
                [self.repo],
                scope="local",
                apply=apply,
                as_json=True,
                include=[],
                exclude=[],
                merged_into=[],
                sizes=False,
                min_age=None,
                hooks={},
            )
        self.assertEqual(code, 0)
        return json.loads(out.getvalue()), held.call_count

    def _items(self, plan: dict) -> dict:
        return {i["branch"]: i for i in plan["repos"][0]["items"]}

    def test_one_read_gives_the_plan_of_one_read_per_branch(self) -> None:
        per_branch, old_reads = self._run(cached=False, apply=False)
        once, new_reads = self._run(cached=True, apply=False)

        self.assertEqual(once, per_branch)
        self.assertEqual(new_reads, 1)
        self.assertGreaterEqual(old_reads, MERGED - 1)
        items = self._items(once)
        self.assertIn("symbolic ref", items["alias"]["skip"])
        self.assertIn("target of symbolic ref", items["merged-001"]["skip"])
        self.assertIn("checked out in", items["merged-002"]["skip"])
        self.assertIn("rebase in progress", items["merged-003"]["skip"])
        self.assertIn("bisect in progress", items["merged-004"]["skip"])
        deletable = sorted(n for n, i in items.items() if i["actions"])
        free = [0, *range(5, MERGED)]
        self.assertEqual(deletable, [f"merged-{i:03d}" for i in free])

    def test_branch_held_after_the_plan_is_not_deleted(self) -> None:
        rebuilt: list[str] = []
        rebuild = gc._rebuild

        def pin_before_first_recheck(*args: object) -> object:
            if not rebuilt:
                rebuilt.append(
                    self.git("symbolic-ref", "refs/tags/pin", "refs/heads/merged-005")
                )
            return rebuild(*args)

        with patch.object(gc, "_rebuild", side_effect=pin_before_first_recheck):
            plan, reads = self._run(cached=True, apply=True)

        items = self._items(plan)
        self.assertGreater(reads, 1)
        self.assertEqual(
            items["merged-005"]["result"],
            "skipped: changed since plan (target of symbolic ref refs/tags/pin)",
        )
        self.assertIn("merged-005", self.git("for-each-ref", "refs/heads"))


if __name__ == "__main__":
    unittest.main()
