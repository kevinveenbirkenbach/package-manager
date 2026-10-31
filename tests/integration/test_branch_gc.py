from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.branch import gc
from pkgmgr.actions.branch.gc_forge import ForgeFacts
from pkgmgr.cli.commands.branch import handle_branch
from pkgmgr.cli.parser import create_parser

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True


class TestBranchGc(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        self.origin = os.path.join(self.root, "origin.git")
        self.repo = os.path.join(self.root, "repo")
        git(self.root, "init", "--bare", "-b", "main", self.origin)
        git(self.root, "init", "-b", "main", self.repo)
        git(self.repo, "remote", "add", "origin", self.origin)
        self._commit("init")
        git(self.repo, "push", "-u", "origin", "main")

        self._branch_with_commit("merged")
        git(self.repo, "merge", "--no-ff", "-m", "merge merged", "merged")
        git(self.repo, "push", "origin", "main")
        git(self.repo, "branch", "fresh")
        git(self.repo, "push", "origin", "fresh")
        self._branch_with_commit("wip")
        self._branch_with_commit("squashed")
        self._branch_with_commit("locked")
        git(self.repo, "merge", "--no-ff", "-m", "merge locked", "locked")
        git(self.repo, "push", "origin", "main")
        git(self.repo, "remote", "set-head", "origin", "main")

        self.merged_wt = os.path.join(self.root, "wt-merged")
        git(self.repo, "worktree", "add", self.merged_wt, "merged")
        self.dirty_wt = os.path.join(self.root, "wt-dirty")
        git(self.repo, "worktree", "add", "-b", "dirty", self.dirty_wt, "merged")
        with open(os.path.join(self.dirty_wt, "scratch.txt"), "w") as fh:
            fh.write("x")
        self.locked_wt = os.path.join(self.root, "wt-locked")
        git(self.repo, "worktree", "add", self.locked_wt, "locked")

        self.squashed_sha = git(self.repo, "rev-parse", "squashed")
        self.forge = ForgeFacts(
            merged_heads={self.squashed_sha: 7}, open_heads={"wip": 3}
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _commit(self, name: str) -> None:
        with open(os.path.join(self.repo, f"{name}.txt"), "w") as fh:
            fh.write(name)
        git(self.repo, "add", f"{name}.txt")
        git(self.repo, "commit", "-m", name)

    def _branch_with_commit(self, name: str) -> None:
        git(self.repo, "checkout", "-b", name, "main")
        self._commit(name)
        git(self.repo, "push", "origin", name)
        git(self.repo, "checkout", "main")

    def _lock(self, reason: str) -> None:
        git(self.repo, "worktree", "lock", "--reason", reason, self.locked_wt)

    def _plan(self, host_ns: bool, cwds: dict[int, str]) -> gc.Repo:
        with (
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value=cwds),
        ):
            return gc.plan_repo(self.repo, [], host_ns)

    def _items(self, plan: gc.Repo) -> dict[str, gc.Item]:
        return {item.branch: item for item in plan.items if item.branch}

    def test_classifies_every_branch(self) -> None:
        items = self._items(self._plan(host_ns=True, cwds={}))

        self.assertEqual(items["main"].state, "protected")
        self.assertEqual(items["merged"].state, "merged-clean")
        self.assertEqual(items["merged"].merged_by, "ancestor")
        self.assertEqual(
            items["merged"].actions,
            ["worktree", "local-branch", "remote-branch:origin"],
        )
        self.assertTrue(items["merged"].eligible)
        self.assertEqual(items["squashed"].merged_by, "pr#7")
        self.assertTrue(items["squashed"].eligible)
        self.assertEqual(items["fresh"].state, "unmerged")
        self.assertEqual(items["fresh"].reason, "no own commits")
        self.assertEqual(items["wip"].state, "unmerged")
        self.assertEqual(items["wip"].skip, "open-pr #3")
        self.assertEqual(items["dirty"].state, "dirty")

    def test_busy_worktree_is_skipped(self) -> None:
        cwds = {4242: os.path.join(self.merged_wt, "sub")}
        items = self._items(self._plan(host_ns=True, cwds=cwds))

        self.assertTrue(items["merged"].skip.startswith("process: pid 4242"))
        self.assertFalse(items["merged"].eligible)

    def test_lock_with_live_pid_is_skipped(self) -> None:
        self._lock(f"claude agent x (pid {os.getpid()} on host)")
        items = self._items(self._plan(host_ns=True, cwds={}))

        self.assertEqual(items["locked"].skip, f"lock: pid {os.getpid()} alive")

    def test_lock_with_dead_pid_is_overridden(self) -> None:
        self._lock("claude agent x (pid 999999999 on host)")
        items = self._items(self._plan(host_ns=True, cwds={}))

        self.assertIsNone(items["locked"].skip)
        self.assertTrue(items["locked"].eligible)

    def test_lock_outside_host_namespace_is_unknown(self) -> None:
        self._lock("claude agent x (pid 999999999 on host)")
        items = self._items(self._plan(host_ns=False, cwds={}))

        self.assertEqual(items["locked"].skip, "lock: liveness unknown")

    def test_lock_without_pid_is_respected(self) -> None:
        self._lock("manual hold")
        items = self._items(self._plan(host_ns=True, cwds={}))

        self.assertEqual(items["locked"].skip, "lock: manual hold")

    def test_forge_unavailable_skips_everything(self) -> None:
        self.forge = ForgeFacts(unavailable="no GitHub token")
        items = self._items(self._plan(host_ns=True, cwds={}))

        self.assertEqual(items["merged"].skip, "forge unavailable")
        self.assertIsNone(items["squashed"].merged_by)

    def test_stale_metadata_is_listed_not_pruned(self) -> None:
        stub = os.path.join(self.repo, ".git", "worktrees", "stub")
        os.makedirs(stub)
        open(os.path.join(stub, "commondir"), "w").close()
        plan = self._plan(host_ns=True, cwds={})

        stale = [i for i in plan.items if i.state == "stale"]
        self.assertEqual([i.worktree for i in stale], [stub])
        self.assertTrue(os.path.isdir(stub))

    def test_execute_removes_worktree_and_branches(self) -> None:
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]
        meta = os.path.join(self.repo, ".git", "worktrees", "wt-merged")

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertFalse(os.path.exists(self.merged_wt))
        self.assertFalse(os.path.exists(meta))
        self.assertEqual(git(self.repo, "branch", "--list", "merged"), "")
        self.assertEqual(git(self.origin, "branch", "--list", "merged"), "")

    @unittest.skipUnless(docker_available(), "docker is not available")
    def test_execute_removes_foreign_owned_worktree_via_container(self) -> None:
        with open(os.path.join(self.repo, ".git", "info", "exclude"), "a") as fh:
            fh.write("node_modules/\n")
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{self.merged_wt}:/w",
                gc.CLEANUP_IMAGE,
                "sh",
                "-c",
                (
                    "mkdir -p /w/node_modules/pkg && touch /w/node_modules/pkg/index.js"
                    " && chown -R 65534:65534 /w/node_modules"
                ),
            ],
            check=True,
            capture_output=True,
        )
        self.assertTrue(gc._foreign_owned(self.merged_wt))
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]
        meta = os.path.join(self.repo, ".git", "worktrees", "wt-merged")

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertFalse(os.path.lexists(self.merged_wt))
        self.assertFalse(os.path.exists(meta))
        self.assertEqual(git(self.repo, "branch", "--list", "merged"), "")

    def test_metadata_kept_when_checkout_survives_removal(self) -> None:
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]
        meta = os.path.join(self.repo, ".git", "worktrees", "wt-merged")

        with (
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(gc, "_foreign_owned", return_value=True),
            patch.object(gc, "_docker", return_value="") as docker,
        ):
            gc.execute(plan, item)

        docker.assert_called_once_with(
            [
                "run",
                "--rm",
                "-v",
                f"{self.root}:/w",
                gc.CLEANUP_IMAGE,
                "rm",
                "-rf",
                "/w/wt-merged",
            ]
        )
        self.assertTrue(item.result.startswith("failed: worktree"))
        self.assertTrue(os.path.isdir(self.merged_wt))
        self.assertTrue(os.path.isdir(meta))
        self.assertNotEqual(git(self.repo, "branch", "--list", "merged"), "")

    def test_execute_skips_item_changed_since_plan(self) -> None:
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]
        with open(os.path.join(self.merged_wt, "late.txt"), "w") as fh:
            fh.write("late")

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertTrue(item.result.startswith("skipped: changed since plan"))
        self.assertTrue(os.path.isdir(self.merged_wt))

    def test_branch_gc_json_and_refusal(self) -> None:
        out = io.StringIO()
        with (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value={}),
            redirect_stdout(out),
        ):
            code = gc.branch_gc(
                [self.repo], apply=False, as_json=True, include=["merged"], exclude=[]
            )
        data = json.loads(out.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual([i["branch"] for i in data["repos"][0]["items"]], ["merged"])
        with patch.object(gc, "host_pid_namespace", return_value=False):
            self.assertEqual(
                gc.branch_gc(
                    [self.repo], apply=True, as_json=False, include=[], exclude=[]
                ),
                2,
            )

    def test_cli_forwards_gc_flags(self) -> None:
        args = create_parser("test").parse_args(
            [
                "branch",
                "gc",
                "--apply",
                "--json",
                "--branch",
                "a",
                "--branch",
                "b",
                "--exclude",
                "c",
            ]
        )
        with (
            patch("pkgmgr.cli.commands.branch.main_repo_root", return_value=self.repo),
            patch("pkgmgr.cli.commands.branch.branch_gc", return_value=1) as run_gc,
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            handle_branch(args, ctx=None)

        self.assertEqual(exit_ctx.exception.code, 1)
        run_gc.assert_called_once_with(
            [self.repo], apply=True, as_json=True, include=["a", "b"], exclude=["c"]
        )


if __name__ == "__main__":
    unittest.main()
