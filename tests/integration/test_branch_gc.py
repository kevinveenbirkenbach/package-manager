from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.actions.branch import gc, gc_forge
from pkgmgr.actions.branch.gc_forge import ForgeFacts
from pkgmgr.cli.commands.branch import handle_branch
from pkgmgr.cli.parser import create_parser
from pkgmgr.core.credentials.types import NoCredentialsError

GITHUB_URL = "https://github.com/example/demo.git"
AUTHOR = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env={**os.environ, **AUTHOR},
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


class GcFixture:
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        home = os.path.join(self.root, "home")
        os.makedirs(home)
        scratch = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        patcher = patch.dict(os.environ, {**scratch, "HOME": home}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def _plan(
        self,
        host_ns: bool,
        cwds: dict[int, str],
        merged_into: list[str] | None = None,
        sizes: bool = False,
        min_age: float | None = None,
        scope: str = "all",
        activity: bool = False,
        hooks: dict | None = None,
        containers: list[gc.Container] | None = None,
    ) -> gc.Repo:
        with (
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value=cwds),
        ):
            return gc.plan_repo(
                self.repo,
                containers or [],
                host_ns,
                merged_into=merged_into or [],
                sizes=sizes,
                min_age=min_age,
                scope=scope,
                activity=activity,
                hooks=hooks or {},
            )

    def _integration_line(self) -> str:
        git(self.repo, "checkout", "-b", "line", "main")
        self._commit("line-base")
        git(self.repo, "checkout", "-b", "feat", "line")
        self._commit("feat")
        git(self.repo, "checkout", "line")
        git(self.repo, "merge", "--no-ff", "-m", "merge feat", "feat")
        git(self.repo, "push", "origin", "line", "feat")
        git(self.repo, "branch", "start", "line")
        git(self.repo, "checkout", "main")
        feat_wt = os.path.join(self.root, "wt-feat")
        git(self.repo, "worktree", "add", feat_wt, "feat")
        return feat_wt

    def _items(self, plan: gc.Repo) -> dict[str, gc.Item]:
        return {item.branch: item for item in plan.items if item.branch}


class TestBranchGc(GcFixture, unittest.TestCase):
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

    def test_merged_into_counts_commits_in_an_integration_line(self) -> None:
        self._integration_line()
        before = self._items(self._plan(host_ns=True, cwds={}))
        self.assertEqual(before["feat"].state, "unmerged")
        self.assertIsNone(before["feat"].merged_into)

        for ref in ("line", "origin/line"):
            with self.subTest(ref=ref):
                items = self._items(
                    self._plan(host_ns=True, cwds={}, merged_into=[ref])
                )
                self.assertEqual(items["feat"].state, "merged-clean")
                self.assertEqual(items["feat"].merged_by, f"line:{ref}")
                self.assertEqual(items["feat"].merged_into, ref)
                self.assertTrue(items["feat"].eligible)
                self.assertEqual(items["line"].state, "protected")
                self.assertEqual(items["start"].state, "unmerged")
                self.assertEqual(items["merged"].merged_into, "origin/main")

    def test_unknown_merged_into_ref_is_a_warning(self) -> None:
        plan = self._plan(host_ns=True, cwds={}, merged_into=["no-such-line"])

        self.assertIn("merged-into ref no-such-line not found", plan.warnings)
        self.assertEqual(self._items(plan)["merged"].state, "merged-clean")

    def test_sizes_and_min_age(self) -> None:
        items = self._items(self._plan(host_ns=True, cwds={}, sizes=True))
        self.assertGreater(items["merged"].size_bytes, 0)
        self.assertIsNone(items["squashed"].size_bytes)
        self.assertIn("size ", gc._line(items["merged"]))

        young = self._items(self._plan(host_ns=True, cwds={}, min_age=1000))
        self.assertEqual(young["merged"].skip, "younger than 1000 h")
        self.assertFalse(young["merged"].eligible)
        old = self._items(self._plan(host_ns=True, cwds={}, min_age=0))
        self.assertIsNone(old["merged"].skip)

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

    def _github_without_token(self) -> None:
        git(self.repo, "branch", "local-done", "merged")
        git(self.repo, "checkout", "-b", "local-wip", "main")
        self._commit("local-wip")
        git(self.repo, "checkout", "main")
        git(self.repo, "branch", "--track", "tracked", "origin/merged")
        git(self.repo, "push", "origin", "merged:refs/heads/remote-done")
        git(self.repo, "remote", "set-url", "origin", GITHUB_URL)

    def _cleanup_without_token(self, apply: bool) -> tuple[int, dict]:
        out = io.StringIO()
        with (
            patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"}),
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(gc_forge, "TokenResolver") as resolver,
            patch.object(gc_forge, "HttpClient") as http,
            redirect_stdout(out),
            redirect_stderr(io.StringIO()),
        ):
            resolver.return_value.get_token.side_effect = NoCredentialsError("none")
            code = gc.cleanup(
                [self.repo],
                scope="branch",
                apply=apply,
                as_json=True,
                include=[],
                exclude=[],
                merged_into=[],
                sizes=False,
                min_age=None,
                hooks={},
            )
        resolver.return_value.get_token.assert_called_once()
        http.assert_not_called()
        return code, json.loads(out.getvalue())["repos"][0]

    def test_local_only_merged_branch_needs_no_forge(self) -> None:
        self._github_without_token()
        code, plan = self._cleanup_without_token(apply=False)
        items = {i["branch"]: i for i in plan["items"] if i["branch"]}

        self.assertEqual(code, 0)
        self.assertIn("forge unavailable: no GitHub token (none)", plan["warnings"])
        self.assertIsNone(items["local-done"]["skip"])
        self.assertEqual(items["local-done"]["merged_by"], "ancestor")
        self.assertEqual(items["local-done"]["actions"], ["local-branch"])
        self.assertEqual(items["remote-done"]["state"], "merged-clean")
        self.assertEqual(items["tracked"]["state"], "merged-clean")
        self.assertEqual(items["local-wip"]["state"], "unmerged")
        for name in ("merged", "remote-done", "tracked", "local-wip", "squashed"):
            with self.subTest(branch=name):
                self.assertEqual(items[name]["skip"], "forge unavailable")

    def test_apply_without_token_deletes_only_the_local_only_merged_branch(
        self,
    ) -> None:
        self._github_without_token()
        before = set(git(self.repo, "for-each-ref", "--format=%(refname)").split())
        code, plan = self._cleanup_without_token(apply=True)
        after = set(git(self.repo, "for-each-ref", "--format=%(refname)").split())

        self.assertEqual(code, 0)
        self.assertEqual(
            [(i["branch"], i["result"]) for i in plan["items"] if i["result"]],
            [("local-done", "done")],
        )
        self.assertEqual(before - after, {"refs/heads/local-done"})
        self.assertEqual(after - before, set())
        self.assertEqual(
            git(self.origin, "branch", "--list", "remote-done"), "remote-done"
        )

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

    def test_worktree_path_with_newlines_cannot_forge_a_record(self) -> None:
        forged = os.path.join(self.root, "a\n\nworktree -evil")
        git(self.repo, "worktree", "add", "-b", "forged", forged, "main")

        paths = {tree.path: tree.branch for tree in gc._worktrees(self.repo)}

        self.assertEqual(paths[forged], "forged")
        self.assertNotIn("-evil", paths)

    def test_ref_named_like_an_option_writes_no_file(self) -> None:
        target = os.path.join(self.root, "pwn")
        os.makedirs(target)
        remote = f"--output={target}"
        main = git(self.repo, "rev-parse", "main")
        git(self.repo, "remote", "remove", "origin")
        git(self.repo, "config", f"remote.{remote}.url", self.origin)
        git(self.repo, "update-ref", f"refs/remotes/{remote}/main", main)
        git(
            self.repo,
            "symbolic-ref",
            f"refs/remotes/{remote}/HEAD",
            f"refs/remotes/{remote}/main",
        )

        plan = self._plan(host_ns=True, cwds={})

        self.assertEqual(plan.default, f"{remote}/main")
        self.assertEqual(os.listdir(target), [])

    def test_execute_deletes_branches_named_like_options(self) -> None:
        sha = git(self.repo, "rev-parse", "merged")
        other = os.path.join(self.root, "other.git")
        git(self.root, "init", "--bare", other)
        git(self.repo, "push", other, "merged:refs/heads/-evil")
        git(self.repo, "config", "remote.-r.url", other)
        git(self.repo, "update-ref", "refs/heads/-evil", sha)
        git(self.repo, "update-ref", "refs/remotes/-r/-evil", sha)
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["-evil"]
        self.assertEqual(item.remotes, {"-r": sha})

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertEqual(git(self.repo, "for-each-ref", "refs/heads/-evil"), "")
        self.assertEqual(git(other, "for-each-ref", "refs/heads/-evil"), "")

    def _fetches(self) -> int:
        with patch.object(gc, "run", wraps=gc.run) as spy:
            self.plan = self._plan(host_ns=True, cwds={})
        return sum("fetch" in call.args[0] for call in spy.call_args_list)

    def test_unsafe_repository_config_skips_fetch_and_remote_deletes(self) -> None:
        self.assertEqual(self._fetches(), 1)
        git(self.repo, "config", "core.sshCommand", "false")

        self.assertEqual(self._fetches(), 0)
        plan = self.plan
        item = self._items(plan)["merged"]

        self.assertIn(
            "fetch and remote branch deletes skipped: the repository config sets "
            "core.sshcommand",
            plan.warnings,
        )
        self.assertIsNone(item.skip)
        self.assertEqual(item.actions, ["worktree", "local-branch"])

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertFalse(os.path.exists(self.merged_wt))
        self.assertEqual(git(self.origin, "branch", "--list", "merged"), "merged")

    def test_config_set_after_plan_stops_execute(self) -> None:
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]
        git(self.repo, "config", "credential.helper", "false")

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(
            item.result, "skipped: repository config sets credential.helper"
        )
        self.assertTrue(os.path.isdir(self.merged_wt))
        self.assertEqual(git(self.origin, "branch", "--list", "merged"), "merged")

    def test_compose_project_with_containers_elsewhere_is_skipped(self) -> None:
        inside = gc.Container("proj", os.path.join(self.merged_wt, "app"), "img")
        elsewhere = gc.Container("proj", os.path.join(self.root, "other"), "img")

        alone = self._items(self._plan(host_ns=True, cwds={}, containers=[inside]))
        shared = self._items(
            self._plan(host_ns=True, cwds={}, containers=[inside, elsewhere])
        )

        self.assertIsNone(alone["merged"].skip)
        self.assertIn("compose-down:proj", alone["merged"].actions)
        self.assertEqual(
            shared["merged"].skip,
            "compose project proj also has containers outside the worktree",
        )
        self.assertFalse(shared["merged"].eligible)

    def test_execute_runs_no_repository_hook(self) -> None:
        marker = os.path.join(self.root, "hooked")
        hook = os.path.join(self.repo, ".git", "hooks", "reference-transaction")
        with open(hook, "w") as fh:
            fh.write(f"#!/bin/sh\ntouch {marker}\n")
        os.chmod(hook, 0o755)
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["merged"]

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertEqual(git(self.origin, "branch", "--list", "merged"), "")
        self.assertFalse(os.path.exists(marker))

    def test_local_branch_delete_runs_no_config_hook(self) -> None:
        marker = os.path.join(self.root, "hooked")
        git(self.repo, "branch", "local-only", "merged")
        git(self.repo, "config", "hook.probe.command", f"touch {marker}")
        git(self.repo, "config", "hook.probe.event", "reference-transaction")
        plan = self._plan(host_ns=True, cwds={})
        item = self._items(plan)["local-only"]
        self.assertEqual(item.actions, ["local-branch"])

        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertEqual(git(self.repo, "branch", "--list", "local-only"), "")
        self.assertFalse(os.path.exists(marker))

    def test_cleanup_json_and_refusal(self) -> None:
        out = io.StringIO()
        with (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value={}),
            redirect_stdout(out),
        ):
            code = gc.cleanup(
                [self.repo],
                scope="all",
                apply=False,
                as_json=True,
                include=["merged"],
                exclude=[],
                merged_into=["origin/main"],
                sizes=True,
                min_age=None,
                hooks={},
            )
        data = json.loads(out.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(data["repos"][0]["merged_into"], ["origin/main"])
        items = data["repos"][0]["items"]
        self.assertEqual([i["branch"] for i in items], ["merged"])
        self.assertEqual(items[0]["merged_into"], "origin/main")
        self.assertGreater(items[0]["size_bytes"], 0)
        with patch.object(gc, "host_pid_namespace", return_value=False):
            self.assertEqual(
                gc.cleanup(
                    [self.repo],
                    scope="all",
                    apply=True,
                    as_json=False,
                    include=[],
                    exclude=[],
                    merged_into=[],
                    sizes=False,
                    min_age=None,
                    hooks={},
                ),
                2,
            )

    def test_cli_forwards_cleanup_flags(self) -> None:
        args = create_parser("test").parse_args(
            [
                "branch",
                "cleanup",
                "--apply",
                "--json",
                "--branch",
                "a",
                "--branch",
                "b",
                "--exclude",
                "c",
                "--merged-into",
                "origin/line",
                "--merged-into",
                "fork/line",
                "--sizes",
                "--min-age",
                "24",
            ]
        )
        pins = {"worktree-fini": ["true"]}
        managed = {
            "provider": "host",
            "account": "o",
            "repository": "r",
            "directory": self.repo,
        }
        ctx = SimpleNamespace(
            config_merged={
                "worktree_hooks": {"host/o/r": pins},
                "repositories": [managed],
            }
        )
        with (
            patch("pkgmgr.cli.commands.branch.main_repo_root", return_value=self.repo),
            patch("pkgmgr.cli.commands.branch.cleanup", return_value=1) as run_gc,
            patch("pkgmgr.cli.commands.branch.refresh_tree") as refresh,
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            handle_branch(args, ctx=ctx)

        self.assertEqual(exit_ctx.exception.code, 1)
        run_gc.assert_called_once_with(
            [self.repo],
            scope="branch",
            apply=True,
            as_json=True,
            include=["a", "b"],
            exclude=["c"],
            merged_into=["origin/line", "fork/line"],
            sizes=True,
            min_age=24.0,
            hooks={os.path.realpath(self.repo): pins},
        )
        refresh.assert_called_once_with([self.repo])


if __name__ == "__main__":
    unittest.main()
