from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.actions.branch import gc, gc_forge, tree
from pkgmgr.cli.commands.branch import handle_branch, scan_repo_roots
from pkgmgr.cli.parser import create_parser
from pkgmgr.core.credentials.types import NoCredentialsError
from pkgmgr.core.git.errors import GitBaseError, GitRunError
from pkgmgr.core.git.run import CALLER_CONFIG, DEFAULT_CONFIG

GITHUB_URL = "https://github.com/example/demo.git"
AUTHOR = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
FAILING_DOCKER = """#!{python}
import json, os, sys
with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
sys.exit(1)
"""
MARKING_HOOK = """#!/bin/sh
echo "$@" >> "{marker}"
"""
BRANCH_CLI = """import sys
from types import SimpleNamespace
from pkgmgr.cli.commands.branch import handle_branch
from pkgmgr.cli.parser import create_parser
ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
handle_branch(create_parser("test").parse_args(sys.argv[1:]), ctx=ctx)
"""


def clean_env() -> dict[str, str]:
    """
    Build the environment of every git the tests run.

    Returns:
        The current environment without any `GIT_*` variable, plus a fixed
        author and committer.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, **AUTHOR}


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=clean_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestBranchCleanupLocal(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        for patcher in (
            patch.dict(os.environ, {"HOME": self.home}),
            patch("pkgmgr.core.git.run._passwd_home", return_value=self.home),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.origin = os.path.join(self.root, "origin.git")
        self.repo = os.path.join(self.root, "repo")
        git(self.root, "init", "--bare", "-b", "main", self.origin)
        git(self.root, "init", "-b", "main", self.repo)
        git(self.repo, "remote", "add", "origin", f"file://{self.origin}")
        self._commit("init")
        git(self.repo, "push", "-u", "origin", "main")

        git(self.repo, "checkout", "-b", "done", "main")
        self._commit("done")
        git(self.repo, "push", "-u", "origin", "done")
        git(self.repo, "push", "origin", "done:refs/heads/remote-done")
        git(self.repo, "checkout", "-b", "picked", "main")
        self._commit("picked")
        git(self.repo, "checkout", "main")
        git(self.repo, "merge", "--no-ff", "-m", "merge done", "done")
        git(self.repo, "cherry-pick", "picked")
        git(self.repo, "push", "origin", "main")
        git(self.repo, "checkout", "-b", "wip", "main")
        self._commit("wip")
        git(self.repo, "checkout", "main")
        git(self.repo, "fetch", "origin")
        git(self.repo, "update-ref", "--no-deref", "-d", "refs/remotes/origin/HEAD")
        git(self.repo, "branch", "local-done", "done")
        git(self.repo, "branch", "held-done", "done")
        self.held = os.path.join(self.root, "wt-held")
        git(self.repo, "worktree", "add", self.held, "held-done")
        git(self.repo, "remote", "add", "hub", GITHUB_URL)

        self.bin = os.path.join(self.root, "bin")
        os.makedirs(self.bin)
        docker = os.path.join(self.bin, "docker")
        with open(docker, "w", encoding="utf-8") as fh:
            fh.write(FAILING_DOCKER.format(python=sys.executable))
        os.chmod(docker, 0o755)
        self.docker_log = os.path.join(self.root, "docker.log")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _set_head(self) -> None:
        git(self.repo, "remote", "set-head", "origin", "main")

    def _commit(self, name: str) -> None:
        with open(os.path.join(self.repo, f"{name}.txt"), "w") as fh:
            fh.write(name)
        git(self.repo, "add", f"{name}.txt")
        git(self.repo, "commit", "-m", name)

    def _refs(self, cwd: str, prefix: str) -> dict[str, str]:
        out = git(cwd, "for-each-ref", "--format=%(refname) %(objectname)", prefix)
        return dict(line.split(" ") for line in out.splitlines())

    @contextmanager
    def _guarded(self) -> Iterator[SimpleNamespace]:
        """
        Patch the host checks, drop every `GIT_*` variable from the
        environment and watch every token, forge and docker access.

        Returns:
            The git run spy, the token resolver, HTTP client and Secret
            Service mocks, as attributes git, token, http and secret.
        """
        env = {
            **clean_env(),
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": self.docker_log,
            "GIT_ALLOW_PROTOCOL": "file",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(gc, "run", wraps=gc.run) as git_run,
            patch.object(gc_forge, "TokenResolver") as resolver,
            patch.object(gc_forge, "HttpClient") as http,
            patch.object(
                tree, "secret_service_token", return_value=(None, "test")
            ) as secret,
        ):
            resolver.return_value.get_token.side_effect = NoCredentialsError("none")
            yield SimpleNamespace(git=git_run, token=resolver, http=http, secret=secret)

    def _cleanup(
        self,
        scope: str,
        apply: bool,
        merged_into: tuple[str, ...] = (),
        roots: tuple[str, ...] = (),
        leak: dict[str, str] | None = None,
        include: tuple[str, ...] = (),
        exclude: tuple[str, ...] = (),
    ) -> SimpleNamespace:
        """
        Run gc.cleanup on the fixture under _guarded.

        Args:
            scope: the cleanup scope.
            apply: execute the plan.
            merged_into: integration lines that also count as merged.
            roots: the repositories to scan; the fixture repository if empty.
            leak: variables set in the environment gc.cleanup sees, after
                _guarded dropped every `GIT_*` one.
            include: the --branch filter.
            exclude: the --exclude filter.

        Returns:
            The exit code, the first repository's items by branch and
            warnings, every repository record, the stderr text and the
            _guarded spies, as attributes code, items, warnings, repos, stderr
            and guard; no repositories when nothing was printed.
        """
        out, err = io.StringIO(), io.StringIO()
        with (
            self._guarded() as guard,
            patch.dict(os.environ, leak or {}),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            code = gc.cleanup(
                list(roots) or [self.repo],
                scope=scope,
                apply=apply,
                as_json=True,
                include=list(include),
                exclude=list(exclude),
                merged_into=list(merged_into),
                sizes=False,
                min_age=None,
                hooks={},
            )
        repos = json.loads(out.getvalue())["repos"] if out.getvalue() else []
        first = repos[0] if repos else {"items": [], "warnings": []}
        return SimpleNamespace(
            code=code,
            items={i["branch"]: i for i in first["items"]},
            warnings=first["warnings"],
            repos=repos,
            stderr=err.getvalue(),
            guard=guard,
        )

    def _branch_config(self, name: str) -> list[str]:
        return subprocess.run(
            ["git", "config", "--get-regexp", f"^branch\\.{name}\\."],
            cwd=self.repo,
            env=clean_env(),
            check=False,
            capture_output=True,
            text=True,
        ).stdout.split()[::2]

    def _results(self, run: SimpleNamespace) -> dict[str, str]:
        return {name: i["result"] for name, i in run.items.items() if i["result"]}

    def assertLocalOnly(self, guard: SimpleNamespace) -> None:
        self.assertFalse(os.path.exists(self.docker_log))
        guard.token.assert_not_called()
        guard.http.assert_not_called()
        guard.secret.assert_not_called()
        for call in guard.git.call_args_list:
            with self.subTest(argv=call.args[0]):
                self.assertNotIn("push", call.args[0])
                self.assertNotIn("fetch", call.args[0])

    def test_dry_run_plans_only_ancestor_tips(self) -> None:
        self._set_head()
        run = self._cleanup("local", apply=False)
        items = run.items

        self.assertEqual(run.code, 0)
        self.assertEqual(run.warnings, [])
        self.assertEqual(
            set(items), {"main", "done", "local-done", "held-done", "picked", "wip"}
        )
        self.assertEqual(items["done"]["upstream"], "origin/done")
        self.assertEqual(list(items["done"]["remotes"]), ["origin"])
        for name in ("done", "local-done"):
            with self.subTest(deletes=name):
                self.assertIsNone(items[name]["skip"])
                self.assertEqual(items[name]["actions"], ["local-branch"])
        self.assertEqual(
            items["held-done"]["skip"], f"checked out in worktree {self.held}"
        )
        self.assertEqual(
            items["picked"]["skip"],
            "merged by patch, tip is no ancestor of refs/remotes/origin/main",
        )
        self.assertEqual(items["wip"]["state"], "unmerged")
        self.assertEqual(items["main"]["state"], "protected")
        for name in ("held-done", "picked", "wip", "main"):
            with self.subTest(keeps=name):
                self.assertEqual(items[name]["actions"], [])
        self.assertLocalOnly(run.guard)

    def test_apply_deletes_only_local_refs_against_the_planned_sha(self) -> None:
        self._set_head()
        heads = self._refs(self.repo, "refs/heads")
        tracking = self._refs(self.repo, "refs/remotes")
        origin = self._refs(self.origin, "refs")
        trees = git(self.repo, "worktree", "list", "--porcelain")
        self.assertEqual(
            self._branch_config("done"), ["branch.done.remote", "branch.done.merge"]
        )
        self.assertEqual(self._branch_config("local-done"), [])

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 0)
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(self._branch_config("done"), [])
        self.assertEqual(
            self._branch_config("main"), ["branch.main.remote", "branch.main.merge"]
        )
        after = self._refs(self.repo, "refs/heads")
        self.assertEqual(
            set(heads) - set(after), {"refs/heads/done", "refs/heads/local-done"}
        )
        self.assertEqual(set(after) - set(heads), set())
        self.assertEqual(self._refs(self.repo, "refs/remotes"), tracking)
        self.assertEqual(self._refs(self.origin, "refs"), origin)
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain"), trees)
        deletes = [c.args[0] for c in run.guard.git.call_args_list if "-d" in c.args[0]]
        self.assertEqual(
            deletes,
            [
                [
                    "update-ref",
                    "--no-deref",
                    "-d",
                    f"refs/heads/{name}",
                    heads[f"refs/heads/{name}"],
                ]
                for name in ("done", "local-done")
            ],
        )
        self.assertLocalOnly(run.guard)

    def test_branch_moved_after_the_check_is_not_deleted(self) -> None:
        planned = git(self.repo, "rev-parse", "done")
        moved = git(
            self.repo,
            "commit-tree",
            "-p",
            planned,
            "-m",
            "moved",
            f"{planned}^{{tree}}",
        )

        def race(_repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "done":
                git(self.repo, "update-ref", "refs/heads/done", moved)
            return item

        with patch.object(gc, "_rebuild", side_effect=race):
            run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 1)
        self.assertTrue(run.items["done"]["result"].startswith("failed: "))
        self.assertEqual(run.items["local-done"]["result"], "done")
        self.assertEqual(git(self.repo, "rev-parse", "refs/heads/done"), moved)

    def test_cherry_picked_branch_stays_with_only_a_file_remote(self) -> None:
        git(self.repo, "remote", "remove", "hub")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.items["picked"]["state"], "merged-clean")
        self.assertEqual(run.items["picked"]["merged_by"], "patch")
        self.assertEqual(
            run.items["picked"]["skip"],
            "merged by patch, tip is no ancestor of refs/remotes/origin/main",
        )
        self.assertNotIn("picked", self._results(run))
        self.assertIn("refs/heads/picked", self._refs(self.repo, "refs/heads"))

    def test_target_is_the_default_ref_not_head(self) -> None:
        init = git(self.repo, "rev-list", "--max-parents=0", "main")
        git(self.repo, "checkout", "-b", "head-only", init)
        self._commit("head-only")
        git(self.repo, "checkout", "--detach", init)
        git(self.repo, "merge", "--no-ff", "-m", "merge head-only", "head-only")
        self.assertNotEqual(
            git(self.repo, "rev-parse", "HEAD"),
            git(self.repo, "rev-parse", "origin/main"),
        )

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(run.items["head-only"]["state"], "unmerged")
        self.assertIn("refs/heads/head-only", self._refs(self.repo, "refs/heads"))

    def test_merged_into_line_counts_only_when_given(self) -> None:
        git(self.repo, "checkout", "-b", "line-only", "main")
        self._commit("line-only")
        git(self.repo, "checkout", "-b", "staging", "main")
        git(self.repo, "merge", "--no-ff", "-m", "merge line-only", "line-only")
        git(self.repo, "push", "origin", "staging")
        git(self.repo, "checkout", "main")
        git(self.repo, "branch", "-D", "staging")

        without = self._cleanup("local", apply=False)
        run = self._cleanup("local", apply=True, merged_into=("origin/staging",))

        self.assertEqual(without.items["line-only"]["state"], "unmerged")
        self.assertEqual(without.items["line-only"]["actions"], [])
        self.assertEqual(run.items["line-only"]["merged_by"], "line:origin/staging")
        self.assertEqual(run.items["line-only"]["result"], "done")
        self.assertNotIn("refs/heads/line-only", self._refs(self.repo, "refs/heads"))
        self.assertLocalOnly(run.guard)

    def test_without_remote_head_a_local_main_merge_counts_for_nothing(self) -> None:
        git(self.repo, "checkout", "-b", "feat", "main")
        self._commit("feat")
        git(self.repo, "checkout", "main")
        git(self.repo, "merge", "--no-ff", "-m", "merge feat", "feat")
        head = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=self.repo,
            env=clean_env(),
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(head.returncode, 0)

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 0)
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(run.items["feat"]["state"], "unmerged")
        self.assertIn("refs/heads/feat", self._refs(self.repo, "refs/heads"))

    def test_without_remote_default_the_repository_is_refused(self) -> None:
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")
        git(self.repo, "branch", "-m", "main", "trunk")
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True, merged_into=("origin/done",))

        self.assertEqual(run.code, 2)
        self.assertEqual(run.warnings, [gc.NO_REMOTE_DEFAULT])
        self.assertEqual(run.items, {})
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)
        self.assertLocalOnly(run.guard)

    def test_rebase_and_bisect_hold_their_branches(self) -> None:
        init = git(self.repo, "rev-list", "--max-parents=0", "main")
        rebasing = os.path.join(self.root, "wt-rebase")
        git(self.repo, "worktree", "add", rebasing, "local-done")
        subprocess.run(
            ["git", "rebase", "-f", "--exec", "false", "HEAD~1"],
            cwd=rebasing,
            env=clean_env(),
            check=False,
            capture_output=True,
        )
        bisecting = os.path.join(self.root, "wt-bisect")
        git(self.repo, "worktree", "add", bisecting, "done")
        git(bisecting, "bisect", "start", "done", init)
        git(bisecting, "checkout", "--detach")
        for path, state in ((rebasing, "rebase-merge"), (bisecting, "BISECT_START")):
            with self.subTest(precondition=state):
                state_path = git(path, "rev-parse", "--git-path", state)
                self.assertTrue(os.path.exists(os.path.join(path, state_path)))
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 0)
        self.assertEqual(self._results(run), {})
        for name, operation in (("local-done", "rebase"), ("done", "bisect")):
            with self.subTest(held=name):
                self.assertIsNone(run.items[name]["worktree"])
                self.assertTrue(
                    run.items[name]["skip"].startswith(f"{operation} in progress in ")
                )
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def _local_merge(self, branch: str) -> None:
        git(self.repo, "checkout", "-b", branch, "main")
        self._commit(branch)
        git(self.repo, "checkout", "main")
        git(self.repo, "merge", "--no-ff", "-m", f"merge {branch}", branch)

    def test_symbolic_ref_and_its_target_are_held(self) -> None:
        git(self.repo, "symbolic-ref", "refs/heads/alias", "refs/heads/local-done")
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done"})
        self.assertEqual(
            run.items["alias"]["skip"], "symbolic ref to refs/heads/local-done"
        )
        self.assertEqual(
            run.items["local-done"]["skip"], "target of symbolic ref refs/heads/alias"
        )
        self.assertEqual(
            git(self.repo, "symbolic-ref", "refs/heads/alias"), "refs/heads/local-done"
        )
        self.assertEqual(
            self._refs(self.repo, "refs/heads")["refs/heads/local-done"],
            heads["refs/heads/local-done"],
        )

    def test_delete_never_follows_a_symref_made_after_the_check(self) -> None:
        planned = git(self.repo, "rev-parse", "held-done")

        def race(_repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "done":
                git(self.repo, "update-ref", "-d", "refs/heads/done")
                git(
                    self.repo, "symbolic-ref", "refs/heads/done", "refs/heads/held-done"
                )
            return item

        with patch.object(gc, "_rebuild", side_effect=race):
            self._cleanup("local", apply=True)

        self.assertEqual(git(self.repo, "rev-parse", "refs/heads/held-done"), planned)
        self.assertEqual(git(self.held, "symbolic-ref", "HEAD"), "refs/heads/held-done")

    def test_registration_and_state_files_hold_their_branches(self) -> None:
        git(self.repo, "branch", "stacked", "done")
        ghost = os.path.join(self.root, "wt-ghost")
        git(self.repo, "worktree", "add", ghost, "local-done")
        with open(os.path.join(ghost, "uncommitted.txt"), "w") as fh:
            fh.write("work")
        meta = os.path.join(self.repo, ".git", "worktrees")
        os.remove(os.path.join(meta, "wt-ghost", "gitdir"))
        sha = git(self.repo, "rev-parse", "stacked")
        states = {
            "rebase-apply/head-name": "refs/heads/done\n",
            "rebase-merge/update-refs": f"refs/heads/stacked\n{sha}\n{sha}\n",
        }
        for name, content in states.items():
            path = os.path.join(meta, "wt-held", name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {})
        self.assertIsNone(run.items["local-done"]["worktree"])
        for name, reason in (
            ("local-done", "checked out in "),
            ("done", "rebase in progress in "),
            ("stacked", "rebase in progress in "),
        ):
            with self.subTest(held=name):
                self.assertTrue(run.items[name]["skip"].startswith(reason))
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)
        self.assertTrue(os.path.isfile(os.path.join(ghost, "uncommitted.txt")))

    def test_remote_head_selects_the_default_over_main(self) -> None:
        init = git(self.repo, "rev-list", "--max-parents=0", "main")
        git(self.repo, "checkout", "-b", "on-trunk", init)
        self._commit("on-trunk")
        git(self.repo, "checkout", "-b", "trunk", init)
        git(self.repo, "merge", "--no-ff", "-m", "merge on-trunk", "on-trunk")
        git(self.repo, "push", "origin", "trunk")
        git(self.repo, "checkout", "main")
        git(self.repo, "branch", "-D", "trunk")
        git(
            self.repo,
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/trunk",
        )

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"on-trunk": "done"})
        self.assertEqual(run.items["done"]["state"], "unmerged")

    def test_remote_head_into_a_local_branch_is_ignored(self) -> None:
        self._local_merge("feat")
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/heads/main")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(run.items["feat"]["state"], "unmerged")
        self.assertIn("refs/heads/feat", self._refs(self.repo, "refs/heads"))

    def test_remote_main_into_a_local_branch_is_refused(self) -> None:
        self._local_merge("feat")
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")
        git(self.repo, "symbolic-ref", "refs/remotes/origin/main", "refs/heads/main")
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertEqual(run.warnings, [gc.NO_REMOTE_DEFAULT])
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def _fork_main(self, merged: str) -> None:
        init = git(self.repo, "rev-list", "--max-parents=0", "main")
        git(self.repo, "checkout", "-b", merged, init)
        self._commit(merged)
        git(self.repo, "checkout", "--detach", init)
        git(self.repo, "merge", "--no-ff", "-m", f"merge {merged}", merged)
        sha = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "main")
        git(self.repo, "remote", "add", "fork", "file:///nonexistent/fork.git")
        git(self.repo, "update-ref", "refs/remotes/fork/main", sha)
        git(
            self.repo,
            "symbolic-ref",
            "refs/remotes/fork/HEAD",
            "refs/remotes/fork/main",
        )

    def test_origin_wins_over_another_remote_head(self) -> None:
        self._fork_main("feat4")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(run.items["feat4"]["state"], "unmerged")

    def test_several_remotes_without_origin_are_refused(self) -> None:
        self._fork_main("feat4")
        git(self.repo, "remote", "remove", "hub")
        git(self.repo, "remote", "rename", "origin", "up")
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertEqual(run.warnings, [gc.NO_REMOTE_DEFAULT])
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def _raw_heads(self, cwd: str) -> bytes:
        return subprocess.run(
            ["git", "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"],
            cwd=cwd,
            env=clean_env(),
            check=True,
            capture_output=True,
        ).stdout

    def test_submodule_cleanup_stays_in_the_submodule(self) -> None:
        sub_origin = os.path.join(self.root, "sub-origin.git")
        seed = os.path.join(self.root, "seed")
        git(self.root, "init", "--bare", "-b", "main", sub_origin)
        git(self.root, "init", "-b", "main", seed)
        with open(os.path.join(seed, "s.txt"), "w") as fh:
            fh.write("s")
        git(seed, "add", "s.txt")
        git(seed, "commit", "-m", "s")
        git(seed, "push", f"file://{sub_origin}", "main")
        git(
            self.repo,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            f"file://{sub_origin}",
            "sub",
        )
        sub = os.path.join(self.repo, "sub")
        heads = self._refs(self.repo, "refs/heads")
        args = create_parser("test").parse_args(
            ["branch", "cleanup", "--local", "--apply", "--json"]
        )
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        os.chdir(sub)
        out = io.StringIO()
        with (
            self._guarded(),
            redirect_stdout(out),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            handle_branch(args, ctx=ctx)

        self.assertEqual(gc.local_repo_root(sub), sub)
        self.assertEqual(json.loads(out.getvalue())["repos"][0]["repo"], sub)
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_main_worktree_of_another_repository_is_refused(self) -> None:
        other = os.path.join(self.root, "other")
        git(self.root, "init", "-b", "main", other)
        git(other, "config", "core.worktree", self.repo)

        with self.assertRaises(GitBaseError):
            gc.local_repo_root(other)

    def test_core_worktree_shape_keeps_the_head_root_outside_local(self) -> None:
        parent = os.path.join(self.root, "cwt-a")
        plain = os.path.join(self.root, "cwt-b")
        git(self.root, "init", "-b", "main", parent)
        os.makedirs(plain)
        git(parent, "config", "core.worktree", plain)
        parse = create_parser("test").parse_args
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        os.chdir(parent)

        self.assertEqual(gc.main_repo_root("."), parent)
        self.assertEqual(scan_repo_roots(parse(["branch", "cleanup"]), ctx), [parent])
        local = parse(["branch", "cleanup", "--local"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stop:
            scan_repo_roots(local, ctx, local=True)
        self.assertEqual(stop.exception.code, 2)

    def test_non_utf8_repository_path_is_refused(self) -> None:
        bad = os.fsdecode(os.path.join(os.fsencode(self.root), b"bad\xffdir"))
        subprocess.run(
            ["git", "clone", f"file://{self.origin}", bad],
            env=clean_env(),
            check=True,
            capture_output=True,
        )
        before = self._raw_heads(bad)
        args = create_parser("test").parse_args(
            ["branch", "cleanup", "--local", "--apply", "--json"]
        )
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        os.chdir(bad)
        err = io.StringIO()
        with (
            self._guarded(),
            redirect_stdout(io.StringIO()),
            redirect_stderr(err),
            self.assertRaises(SystemExit) as stop,
        ):
            handle_branch(args, ctx=ctx)

        self.assertEqual(stop.exception.code, 2)
        self.assertIn(gc.NOT_UTF8, err.getvalue())
        self.assertEqual(self._raw_heads(bad), before)

    def test_reftable_registration_head_holds_its_branch(self) -> None:
        rt = os.path.join(self.root, "rt")
        made = subprocess.run(
            ["git", "init", "-b", "main", "--ref-format=reftable", rt],
            env=clean_env(),
            check=False,
            capture_output=True,
        )
        if made.returncode:
            self.skipTest("git without reftable support")
        git(rt, "remote", "add", "origin", f"file://{self.origin}")
        git(rt, "fetch", "origin")
        git(rt, "branch", "feat", "origin/done")
        ghost = os.path.join(self.root, "rt-ghost")
        git(rt, "worktree", "add", ghost, "feat")
        os.remove(os.path.join(rt, ".git", "worktrees", "rt-ghost", "gitdir"))

        run = self._cleanup("local", apply=True, roots=(rt,))

        self.assertIsNone(run.items["feat"]["worktree"])
        self.assertTrue(run.items["feat"]["skip"].startswith("checked out in "))
        self.assertIn("refs/heads/feat", self._refs(rt, "refs/heads"))

    def test_merged_into_branch_target_is_never_deleted(self) -> None:
        git(self.repo, "branch", "a-line", "done")

        run = self._cleanup("local", apply=True, merged_into=("refs/heads/a-line",))

        self.assertEqual(run.items["a-line"]["state"], "protected")
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertIn("refs/heads/a-line", self._refs(self.repo, "refs/heads"))

    def test_vanished_target_skips_the_rest_and_still_reports(self) -> None:
        git(self.repo, "checkout", "-b", "line-only", "main")
        self._commit("line-only")
        git(self.repo, "checkout", "-b", "staging", "main")
        git(self.repo, "merge", "--no-ff", "-m", "merge line-only", "line-only")
        git(self.repo, "push", "origin", "staging")
        git(self.repo, "checkout", "main")
        git(self.repo, "branch", "-D", "staging")
        rebuild = gc._rebuild

        def vanish(repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "line-only":
                git(self.repo, "update-ref", "-d", "refs/remotes/origin/staging")
            return rebuild(repo, item)

        with patch.object(gc, "_rebuild", side_effect=vanish):
            run = self._cleanup("local", apply=True, merged_into=("origin/staging",))

        self.assertEqual(run.code, 1)
        self.assertEqual(run.items["done"]["result"], "done")
        self.assertTrue(run.items["line-only"]["result"].startswith("failed: "))
        self.assertEqual(
            run.items["local-done"]["result"],
            "skipped: target origin/staging is gone",
        )
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/line-only", heads)
        self.assertIn("refs/heads/local-done", heads)

    def test_failed_item_outranks_a_refused_repository(self) -> None:
        other = os.path.join(self.root, "other")
        git(self.root, "init", "-b", "main", other)
        moved = git(
            self.repo, "commit-tree", "-p", "done", "-m", "moved", "done^{tree}"
        )

        def race(_repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "done":
                git(self.repo, "update-ref", "refs/heads/done", moved)
            return item

        with patch.object(gc, "_rebuild", side_effect=race):
            run = self._cleanup("local", apply=True, roots=(self.repo, other))

        self.assertEqual(run.code, 1)
        self.assertTrue(run.items["done"]["result"].startswith("failed: "))
        self.assertEqual(run.items["local-done"]["result"], "done")
        self.assertEqual(run.repos[1]["warnings"], [gc.NO_REMOTE_DEFAULT])

    def test_non_utf8_ref_name_refuses_the_repository(self) -> None:
        git(self.repo, "branch", os.fsdecode(b"bad\xff"), "done")
        before = self._raw_heads(self.repo)

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertEqual(run.warnings, [gc.NOT_UTF8])
        self.assertEqual(run.items, {})
        self.assertEqual(self._raw_heads(self.repo), before)

    def test_refs_shared_through_a_symlink_refuse_the_repository(self) -> None:
        git(self.repo, "checkout", "local-done")
        shared = os.path.join(self.root, "new")
        os.makedirs(os.path.join(shared, ".git", "logs"))
        for name in ("config", "refs", "objects", "info", "hooks", "packed-refs"):
            source = os.path.join(self.repo, ".git", name)
            if os.path.exists(source):
                os.symlink(source, os.path.join(shared, ".git", name))
        os.symlink(
            os.path.join(self.repo, ".git", "logs", "refs"),
            os.path.join(shared, ".git", "logs", "refs"),
        )
        with open(os.path.join(shared, ".git", "HEAD"), "w", encoding="utf-8") as fh:
            fh.write("ref: refs/heads/main\n")
        git(shared, "checkout", "-f", "main")
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True, roots=(shared,))

        self.assertEqual(run.code, 2)
        self.assertTrue(run.warnings[-1].startswith("refused: refs"))
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)
        self.assertEqual(
            git(self.repo, "symbolic-ref", "HEAD"), "refs/heads/local-done"
        )

    def test_symrefs_outside_heads_hold_their_targets(self) -> None:
        git(self.repo, "symbolic-ref", "refs/tags/latest", "refs/heads/done")
        git(
            self.repo,
            "symbolic-ref",
            "refs/remotes/origin/alias",
            "refs/heads/local-done",
        )

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {})
        self.assertEqual(
            run.items["done"]["skip"], "target of symbolic ref refs/tags/latest"
        )
        self.assertEqual(
            run.items["local-done"]["skip"],
            "target of symbolic ref refs/remotes/origin/alias",
        )
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/done", heads)
        self.assertIn("refs/heads/local-done", heads)

    def _clone_with(self, path: str, *branches: str) -> None:
        git(self.root, "clone", f"file://{self.origin}", path)
        for name in branches:
            git(path, "branch", name, "origin/done")

    def test_vanished_repository_skips_its_rest_and_still_prints(self) -> None:
        other = os.path.join(self.root, "other")
        self._clone_with(other, "a-first", "local-done")
        rebuild = gc._rebuild

        def vanish(repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "a-first":
                os.rename(other, f"{other}-moved")
            return rebuild(repo, item)

        with patch.object(gc, "_rebuild", side_effect=vanish):
            run = self._cleanup("local", apply=True, roots=(other, self.repo))

        self.assertEqual(run.code, 1)
        self.assertTrue(run.items["a-first"]["result"].startswith("failed: "))
        self.assertTrue(
            run.items["local-done"]["result"].startswith(
                f"skipped: repository {other} unreadable: "
            )
        )
        mine = {i["branch"]: i["result"] for i in run.repos[1]["items"]}
        self.assertEqual(mine["done"], "done")
        self.assertIn(
            "refs/heads/local-done", self._refs(f"{other}-moved", "refs/heads")
        )

    def test_repository_replaced_mid_run_is_never_touched(self) -> None:
        nested = os.path.join(self.repo, "nested")
        self._clone_with(nested, "a-first", "local-done")
        rebuild = gc._rebuild

        def replace(repo: gc.Repo, item: gc.Item) -> gc.Item:
            if item.branch == "a-first":
                shutil.rmtree(os.path.join(nested, ".git"))
            return rebuild(repo, item)

        with patch.object(gc, "_rebuild", side_effect=replace):
            run = self._cleanup("local", apply=True, roots=(nested,))

        self.assertEqual(
            run.items["local-done"]["result"],
            f"skipped: repository {nested} is no longer the planned one",
        )
        self.assertIn("refs/heads/local-done", self._refs(self.repo, "refs/heads"))

    def test_non_local_plan_keeps_a_merged_into_branch_unprotected(self) -> None:
        run = self._cleanup(
            "branch", apply=False, merged_into=("refs/heads/local-done",)
        )

        self.assertEqual(run.items["local-done"]["state"], "merged-clean")
        self.assertEqual(run.items["local-done"]["actions"], ["local-branch"])

    def test_worktree_symref_holds_its_target(self) -> None:
        pinned = os.path.join(self.root, "wt-pin")
        git(self.repo, "worktree", "add", "-b", "pin-base", pinned, "main")
        git(pinned, "symbolic-ref", "refs/worktree/pin", "refs/heads/local-done")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done"})
        self.assertEqual(
            run.items["local-done"]["skip"],
            "target of symbolic ref worktrees/wt-pin/refs/worktree/pin",
        )
        self.assertIn("refs/heads/local-done", self._refs(self.repo, "refs/heads"))

    def test_unreadable_repository_is_refused_and_the_run_goes_on(self) -> None:
        stale = os.path.join(self.root, "stale")
        os.makedirs(stale)
        with open(os.path.join(stale, ".git"), "w", encoding="utf-8") as fh:
            fh.write(f"gitdir: {self.root}/gone/.git/worktrees/stale\n")

        run = self._cleanup("local", apply=True, roots=(self.repo, stale))

        self.assertEqual(run.code, 2)
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(run.repos[1]["items"], [])
        self.assertTrue(run.repos[1]["warnings"][-1].startswith("refused: "))

    def _state(self, cwd: str) -> tuple[str, str, bytes]:
        with open(os.path.join(cwd, ".git", "config"), "rb") as fh:
            config = fh.read()
        refs = git(cwd, "for-each-ref", "--format=%(refname) %(objectname)")
        return refs, git(cwd, "remote", "-v"), config

    def test_git_dir_in_the_environment_never_reaches_a_repository(self) -> None:
        sentinel = os.path.join(self.root, "sentinel")
        git(self.root, "init", "-b", "trunk", sentinel)
        git(sentinel, "commit", "--allow-empty", "-m", "sentinel")
        before = self._state(sentinel)
        dot_git = os.path.join(sentinel, ".git")
        leak = {
            "GIT_DIR": dot_git,
            "GIT_COMMON_DIR": dot_git,
            "GIT_WORK_TREE": sentinel,
        }

        with patch.dict(os.environ, leak):
            git(self.repo, "branch", "leak-done", "done")
            self._commit("leak")
            run = self._cleanup("local", apply=True)

        self.assertEqual(self._state(sentinel), before)
        self.assertEqual(run.items["leak-done"]["result"], "done")

    def test_the_only_remote_gives_the_default_without_origin(self) -> None:
        git(self.repo, "remote", "remove", "hub")
        git(self.repo, "remote", "rename", "origin", "up")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.repos[0]["default"], "refs/remotes/up/main")
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})

    def test_merged_into_remote_tracking_ref_protects_its_branch(self) -> None:
        git(self.repo, "branch", "a-line", "done")
        git(self.repo, "push", "origin", "a-line")

        run = self._cleanup(
            "local", apply=True, merged_into=("refs/remotes/origin/a-line",)
        )

        self.assertEqual(run.items["a-line"]["state"], "protected")
        self.assertIn("refs/heads/a-line", self._refs(self.repo, "refs/heads"))

    def test_reftable_shared_through_a_symlink_refuses_the_repository(self) -> None:
        rt = os.path.join(self.root, "rt-shared")
        made = subprocess.run(
            ["git", "init", "-b", "main", "--ref-format=reftable", rt],
            env=clean_env(),
            check=False,
            capture_output=True,
        )
        if made.returncode:
            self.skipTest("git without reftable support")
        git(rt, "remote", "add", "origin", f"file://{self.origin}")
        git(rt, "fetch", "origin")
        git(rt, "branch", "feat", "origin/done")
        store = os.path.join(self.root, "reftable-store")
        os.rename(os.path.join(rt, ".git", "reftable"), store)
        os.symlink(store, os.path.join(rt, ".git", "reftable"))

        run = self._cleanup("local", apply=True, roots=(rt,))

        self.assertEqual(run.code, 2)
        self.assertTrue(run.warnings[-1].startswith("refused: reftable"))
        self.assertIn("refs/heads/feat", self._refs(rt, "refs/heads"))

    def test_main_worktree_rebase_and_bisect_hold_their_branches(self) -> None:
        common = os.path.join(self.repo, ".git")
        os.makedirs(os.path.join(common, "rebase-merge"))
        with open(os.path.join(common, "rebase-merge", "head-name"), "w") as fh:
            fh.write("refs/heads/local-done\n")
        with open(os.path.join(common, "BISECT_START"), "w") as fh:
            fh.write("done\n")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {})
        self.assertEqual(
            run.items["local-done"]["skip"], f"rebase in progress in {common}"
        )
        self.assertEqual(run.items["done"]["skip"], f"bisect in progress in {common}")

    def test_remote_master_is_the_last_default(self) -> None:
        git(self.repo, "update-ref", "refs/remotes/origin/master", "origin/main")
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.repos[0]["default"], "refs/remotes/origin/master")
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})

    def test_bare_repository_head_holds_its_branch(self) -> None:
        bare = os.path.join(self.root, "bare.git")
        git(self.root, "clone", "--bare", f"file://{self.origin}", bare)
        git(
            bare, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"
        )
        git(bare, "fetch", "origin")
        git(bare, "symbolic-ref", "HEAD", "refs/heads/done")

        run = self._cleanup("local", apply=True, roots=(bare,))

        self.assertEqual(run.items["done"]["skip"], f"checked out in {bare}")
        self.assertIn("refs/heads/done", self._refs(bare, "refs/heads"))

    def test_linked_worktree_resolves_to_the_main_worktree(self) -> None:
        self.assertEqual(gc.local_repo_root(self.held), self.repo)

    def test_git_variables_never_reach_the_local_git_calls(self) -> None:
        sentinel = os.path.join(self.root, "sentinel")
        git(self.root, "init", "-b", "trunk", sentinel)
        git(sentinel, "commit", "--allow-empty", "-m", "sentinel")
        git(sentinel, "config", "branch.done.remote", "origin")
        git(sentinel, "config", "branch.local-done.description", "keep me")
        config = os.path.join(sentinel, ".git", "config")
        with open(config, "rb") as fh:
            before = fh.read()
        leak = {
            "GIT_CONFIG": config,
            "GIT_OBJECT_DIRECTORY": os.path.join(sentinel, ".git", "objects"),
            "GIT_NAMESPACE": "foo",
        }

        run = self._cleanup("local", apply=True, leak=leak)

        self.assertEqual(run.code, 0)
        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        with open(config, "rb") as fh:
            self.assertEqual(fh.read(), before)
        self.assertEqual(self._branch_config("done"), [])
        own = os.path.join(self.repo, ".git", "config")
        self.assertIn(
            ["config", "--file", own, "--remove-section", "branch.done"],
            [call.args[0] for call in run.guard.git.call_args_list],
        )

    def test_merged_into_must_name_exactly_one_branch(self) -> None:
        forms = (
            "picked~0",
            "picked^0",
            "picked@{0}",
            git(self.repo, "rev-parse", "picked"),
        )
        heads = self._refs(self.repo, "refs/heads")

        for form in forms:
            with self.subTest(form=form):
                run = self._cleanup("local", apply=True, merged_into=(form,))

                self.assertEqual(run.code, 2)
                self.assertEqual(run.repos, [])
                self.assertIn(f"--merged-into {form} ", run.stderr)
                self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_registration_with_any_id_holds_its_branch(self) -> None:
        ghost = os.path.join(self.root, "wt-ghost")
        git(self.repo, "worktree", "add", ghost, "local-done")
        with open(os.path.join(ghost, "work.txt"), "w") as fh:
            fh.write("uncommitted")
        meta = os.path.join(self.repo, ".git", "worktrees")
        os.rename(os.path.join(meta, "wt-ghost"), os.path.join(meta, "wt ghost"))
        os.remove(os.path.join(meta, "wt ghost", "gitdir"))
        with open(os.path.join(ghost, ".git"), "w", encoding="utf-8") as fh:
            fh.write(f"gitdir: {meta}/wt ghost\n")

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done"})
        self.assertEqual(
            run.items["local-done"]["skip"], f"checked out in {meta}/wt ghost"
        )
        self.assertIn("refs/heads/local-done", self._refs(self.repo, "refs/heads"))
        self.assertTrue(os.path.isfile(os.path.join(ghost, "work.txt")))

    def test_unreadable_registration_refuses_the_repository(self) -> None:
        broken = os.path.join(self.repo, ".git", "worktrees", "broken")
        os.makedirs(broken)
        for name, content in (("HEAD", "garbage\n"), ("commondir", "../..\n")):
            with open(os.path.join(broken, name), "w", encoding="utf-8") as fh:
                fh.write(content)
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertEqual(run.items, {})
        self.assertTrue(run.warnings[-1].startswith("refused: "))
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_unreadable_state_file_refuses_the_repository(self) -> None:
        os.makedirs(os.path.join(self.repo, ".git", "BISECT_START"))
        heads = self._refs(self.repo, "refs/heads")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertTrue(run.warnings[-1].startswith("refused: "))
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_main_worktree_symref_holds_with_a_linked_root(self) -> None:
        git(self.repo, "symbolic-ref", "refs/worktree/pin", "refs/heads/local-done")

        run = self._cleanup("local", apply=True, roots=(self.held,))

        self.assertEqual(
            run.items["local-done"]["skip"], "target of symbolic ref refs/worktree/pin"
        )
        self.assertIn("refs/heads/local-done", self._refs(self.repo, "refs/heads"))

    def _cli_apply(
        self, cwd: str, leak: dict[str, str] | None = None
    ) -> tuple[int, str, str]:
        """
        Run `branch cleanup --local --apply --json` in cwd under _guarded.

        Args:
            cwd: the directory to run in.
            leak: variables set in the environment the CLI sees, after
                _guarded dropped every `GIT_*` one.

        Returns:
            The exit code, stdout and stderr.
        """
        args = create_parser("test").parse_args(
            ["branch", "cleanup", "--local", "--apply", "--json"]
        )
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        os.chdir(cwd)
        out, err = io.StringIO(), io.StringIO()
        with (
            self._guarded(),
            patch.dict(os.environ, leak or {}),
            redirect_stdout(out),
            redirect_stderr(err),
            self.assertRaises(SystemExit) as stop,
        ):
            handle_branch(args, ctx=ctx)
        return stop.exception.code, out.getvalue(), err.getvalue()

    def test_ceiling_stops_discovery_of_the_repository_above(self) -> None:
        below = os.path.join(self.repo, "not-a-repo")
        os.makedirs(below)
        heads = self._refs(self.repo, "refs/heads")

        code, out, err = self._cli_apply(
            below, leak={"GIT_CEILING_DIRECTORIES": self.repo}
        )

        self.assertEqual(code, 2)
        self.assertIn("Not inside a git repository", err)
        self.assertEqual(out, "")
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_git_variables_reaching_the_cli_never_touch_another_repo(self) -> None:
        git(self.repo, "remote", "remove", "hub")
        sentinel = os.path.join(self.root, "sentinel")
        git(self.root, "init", "-b", "trunk", sentinel)
        git(sentinel, "commit", "--allow-empty", "-m", "sentinel")
        before = self._state(sentinel)
        dot_git = os.path.join(sentinel, ".git")
        env = {
            **clean_env(),
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": self.docker_log,
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_DIR": dot_git,
            "GIT_WORK_TREE": sentinel,
            "GIT_INDEX_FILE": os.path.join(dot_git, "index"),
        }

        for argv, extra in (
            (["--json"], {}),
            (["--local", "--json"], {"GIT_COMMON_DIR": dot_git}),
        ):
            with self.subTest(argv=argv):
                done = subprocess.run(
                    [sys.executable, "-c", BRANCH_CLI, "branch", "cleanup", *argv],
                    cwd=self.repo,
                    env={**env, **extra},
                    check=False,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout)["repos"][0]["repo"], self.repo)
        self.assertEqual(self._state(sentinel), before)

    def test_registration_outside_the_common_dir_refuses_the_repository(
        self,
    ) -> None:
        moved = os.path.join(self.root, "wt-moved")
        git(self.repo, "worktree", "add", moved, "local-done")
        with open(os.path.join(moved, "work.txt"), "w") as fh:
            fh.write("uncommitted")
        common = os.path.join(self.repo, ".git")
        reg = os.path.join(common, "worktrees", "wt-moved")
        heads = self._refs(self.repo, "refs/heads")

        for target in (
            os.path.join(self.root, "reg"),
            os.path.join(common, "worktrees", "nest", "wt-moved"),
        ):
            with self.subTest(target=target):
                os.renames(reg, target)
                reg = target
                with open(os.path.join(reg, "commondir"), "w", encoding="utf-8") as fh:
                    fh.write(common + "\n")
                with open(os.path.join(moved, ".git"), "w", encoding="utf-8") as fh:
                    fh.write(f"gitdir: {reg}\n")

                run = self._cleanup("local", apply=True, roots=(moved,))
                code, out, err = self._cli_apply(moved)

                self.assertEqual(run.code, 2)
                self.assertEqual(run.items, {})
                self.assertIn(f"git dir {reg} is neither", run.warnings[-1])
                self.assertEqual(code, 2)
                self.assertIn(f"git dir {reg} is neither", err)
                self.assertEqual(out, "")
                self.assertEqual(self._refs(self.repo, "refs/heads"), heads)
                self.assertEqual(
                    git(moved, "symbolic-ref", "HEAD"), "refs/heads/local-done"
                )

    def test_symlink_below_refs_refuses_the_repository(self) -> None:
        other = os.path.join(self.root, "other")
        self._clone_with(other, "shared-done")
        git(other, "checkout", "shared-done")
        theirs = os.path.join(other, ".git", "refs", "heads")
        own = os.path.join(self.repo, ".git")
        before = self._refs(other, "refs/heads")
        heads = self._refs(self.repo, "refs/heads")
        git(self.repo, "pack-refs", "--all")
        links = (
            ("refs/heads/team", theirs),
            ("logs/refs/heads/team", os.path.join(other, ".git", "logs", "refs")),
            ("refs/heads", theirs),
        )

        for link, target in links:
            with self.subTest(link=link):
                path = os.path.join(own, link)
                if link == "refs/heads":
                    shutil.rmtree(path, ignore_errors=True)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                os.symlink(target, path)

                run = self._cleanup("local", apply=True)

                os.remove(path)
                self.assertEqual(run.code, 2)
                self.assertTrue(run.warnings[-1].startswith(f"refused: {link} in "))
                self.assertEqual(self._refs(other, "refs/heads"), before)
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_delete_merged_opt_out_and_local_upstreams_are_kept(self) -> None:
        for name, start in (
            ("topic", "done"),
            ("inner", "done"),
            ("base", "done"),
            ("child", "wip"),
            ("stem", "done"),
            ("leaf", "done"),
        ):
            git(self.repo, "branch", name, start)
        for key, value in (
            ("branch.topic.deleteMerged", "false"),
            ("branch.child.remote", "."),
            ("branch.child.merge", "refs/heads/base"),
            ("branch.base.remote", "."),
            ("branch.base.merge", "refs/heads/inner"),
            ("branch.leaf.remote", "."),
            ("branch.leaf.merge", "refs/heads/stem"),
        ):
            git(self.repo, "config", key, value)

        run = self._cleanup("local", apply=True)

        self.assertEqual(
            self._results(run),
            {"done": "done", "local-done": "done", "leaf": "done", "stem": "done"},
        )
        self.assertEqual(
            {name: run.items[name]["skip"] for name in ("topic", "base", "inner")},
            {
                "topic": "kept: branch.topic.deleteMerged is false",
                "base": "kept: local upstream of child",
                "inner": "kept: local upstream of base",
            },
        )
        self.assertEqual(self._branch_config("topic"), ["branch.topic.deletemerged"])
        heads = self._refs(self.repo, "refs/heads")
        for name in ("topic", "inner", "base", "child"):
            self.assertIn(f"refs/heads/{name}", heads)

    def test_filtered_out_branch_keeps_its_local_upstream(self) -> None:
        git(self.repo, "branch", "x", "done")
        git(self.repo, "branch", "y", "done")
        git(self.repo, "config", "branch.x.remote", ".")
        git(self.repo, "config", "branch.x.merge", "refs/heads/y")

        for include, exclude in ((("y",), ()), ((), ("x",))):
            with self.subTest(include=include, exclude=exclude):
                run = self._cleanup(
                    "local", apply=True, include=include, exclude=exclude
                )

                self.assertEqual(run.items["y"]["skip"], "kept: local upstream of x")
                self.assertIsNone(run.items["y"]["result"])
                heads = self._refs(self.repo, "refs/heads")
                self.assertIn("refs/heads/x", heads)
                self.assertIn("refs/heads/y", heads)

    def test_local_upstream_is_resolved_as_git_does(self) -> None:
        forms = {"x1": "heads/y1", "x2": "y2", "x3": "refs/heads/y3"}
        for child, merge in forms.items():
            parent = f"y{child[1:]}"
            git(self.repo, "branch", parent, "done")
            git(self.repo, "branch", child, "wip")
            git(self.repo, "config", f"branch.{child}.remote", ".")
            git(self.repo, "config", f"branch.{child}.merge", merge)
            self.assertEqual(
                git(self.repo, "rev-parse", "--symbolic-full-name", f"{child}@{{u}}"),
                f"refs/heads/{parent}",
            )

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertEqual(
            {name: run.items[name]["skip"] for name in ("y1", "y2", "y3")},
            {
                "y1": "kept: local upstream of x1",
                "y2": "kept: local upstream of x2",
                "y3": "kept: local upstream of x3",
            },
        )

    def test_worktree_config_opt_out_keeps_the_branch_from_every_root(self) -> None:
        for name in ("y", "q"):
            git(self.repo, "branch", name, "done")
        w = os.path.join(self.root, "w")
        git(self.repo, "worktree", "add", "-b", "feat/w", w, "wip")
        git(self.repo, "config", "extensions.worktreeConfig", "true")
        git(w, "config", "--worktree", "branch.y.deleteMerged", "false")
        include = os.path.join(self.root, "keep.inc")
        with open(include, "w", encoding="utf-8") as fh:
            fh.write('[branch "q"]\n\tdeleteMerged = false\n')
        git(self.repo, "config", "includeIf.onbranch:feat/**.path", include)
        kept = {
            "y": "kept: branch.y.deleteMerged is false",
            "q": "kept: branch.q.deleteMerged is false",
        }

        for root in (self.repo, w):
            with self.subTest(root=root):
                run = self._cleanup("local", apply=False, roots=(root,))

                self.assertEqual({n: run.items[n]["skip"] for n in kept}, kept)
        code, out, _ = self._cli_apply(w)

        items = {i["branch"]: i for i in json.loads(out)["repos"][0]["items"]}
        self.assertEqual(code, 0)
        self.assertEqual({n: items[n]["skip"] for n in kept}, kept)
        self.assertEqual(
            {n: i["result"] for n, i in items.items() if i["result"]},
            {"done": "done", "local-done": "done"},
        )

    def test_system_config_opt_out_keeps_the_branch(self) -> None:
        system = os.path.join(self.root, "system.cfg")
        with open(system, "w", encoding="utf-8") as fh:
            fh.write('[branch "local-done"]\n\tdeleteMerged = false\n')

        run = self._cleanup("local", apply=True, leak={"GIT_CONFIG_SYSTEM": system})

        self.assertEqual(self._results(run), {"done": "done"})
        self.assertEqual(
            run.items["local-done"]["skip"],
            "kept: branch.local-done.deleteMerged is false",
        )

    def test_config_variables_reach_only_the_keep_reads(self) -> None:
        global_config = os.path.join(self.root, "global.cfg")
        with open(global_config, "w", encoding="utf-8") as fh:
            fh.write('[branch "local-done"]\n\tdeleteMerged = false\n')
        git(self.repo, "branch", "kid", "wip")
        shapes = (
            ({"GIT_CONFIG_GLOBAL": global_config}, "local-done", "deleteMerged"),
            (
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "branch.local-done.deleteMerged",
                    "GIT_CONFIG_VALUE_0": "false",
                },
                "local-done",
                "deleteMerged",
            ),
            (
                {
                    "GIT_CONFIG_COUNT": "2",
                    "GIT_CONFIG_KEY_0": "branch.kid.remote",
                    "GIT_CONFIG_VALUE_0": ".",
                    "GIT_CONFIG_KEY_1": "branch.kid.merge",
                    "GIT_CONFIG_VALUE_1": "refs/heads/done",
                },
                "done",
                "upstream",
            ),
        )
        reasons = {
            "deleteMerged": "kept: branch.local-done.deleteMerged is false",
            "upstream": "kept: local upstream of kid",
        }

        for leak, branch, rule in shapes:
            with self.subTest(names=sorted(leak), rule=rule):
                run = self._cleanup("local", apply=False, leak=leak)

                self.assertEqual(run.items[branch]["skip"], reasons[rule])
                self.assertEqual(run.items[branch]["actions"], [])
                views = {
                    (call.args[0][1], call.kwargs["config_view"])
                    for call in run.guard.git.call_args_list
                    if call.kwargs.get("config_view")
                }
                self.assertEqual(
                    views,
                    {
                        (command, view)
                        for command in ("config", "for-each-ref")
                        for view in (CALLER_CONFIG, DEFAULT_CONFIG)
                    },
                )

    def _kid_tracks_par(self) -> None:
        git(self.repo, "branch", "par", "done")
        git(self.repo, "branch", "kid", "wip")

    def test_system_config_upstream_keeps_its_parent(self) -> None:
        self._kid_tracks_par()
        system = os.path.join(self.root, "system.cfg")
        include = os.path.join(self.root, "inc.cfg")
        kid_up = '[branch "kid"]\n\tremote = .\n\tmerge = refs/heads/par\n'
        with open(include, "w", encoding="utf-8") as fh:
            fh.write(kid_up)
        shapes = {
            "s1_whole_upstream": kid_up,
            "s2_merge_line_only": '[branch "kid"]\n\tmerge = refs/heads/par\n',
            "s3_include": f"[include]\n\tpath = {include}\n",
            "s5_includeif_onbranch": f'[includeIf "onbranch:main"]\n\tpath = {include}\n',
        }

        for shape, text in shapes.items():
            with self.subTest(shape=shape):
                with open(system, "w", encoding="utf-8") as fh:
                    fh.write(text)
                if shape.startswith("s2"):
                    git(self.repo, "config", "branch.kid.remote", ".")

                run = self._cleanup(
                    "local", apply=False, leak={"GIT_CONFIG_SYSTEM": system}
                )

                self.assertEqual(
                    run.items["par"]["skip"], "kept: local upstream of kid"
                )
                self.assertEqual(run.items["par"]["actions"], [])

    def test_injected_config_never_removes_a_keep(self) -> None:
        self._kid_tracks_par()
        git(self.repo, "config", "branch.kid.remote", ".")
        git(self.repo, "config", "branch.kid.merge", "refs/heads/par")
        git(self.repo, "config", "branch.local-done.deleteMerged", "false")
        include = os.path.join(self.root, "inc.cfg")
        with open(include, "w", encoding="utf-8") as fh:
            fh.write('[branch "kid"]\n\tremote = /nonexistent/url\n')
        count = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "branch.kid.remote"}
        leaks = {
            "e1_count_remote": {**count, "GIT_CONFIG_VALUE_0": "origin"},
            "e2_params_remote": {
                "GIT_CONFIG_PARAMETERS": "'branch.kid.remote'='origin'"
            },
            "e3_params_include": {
                "GIT_CONFIG_PARAMETERS": f"'include.path'='{include}'"
            },
            "e4_count_url": {
                **count,
                "GIT_CONFIG_VALUE_0": "https://example.invalid/x.git",
            },
            "e5_params_delete_merged": {
                "GIT_CONFIG_PARAMETERS": "'branch.local-done.deletemerged'='true'"
            },
        }

        for shape, leak in leaks.items():
            with self.subTest(shape=shape):
                run = self._cleanup("local", apply=False, leak=leak)

                self.assertEqual(
                    run.items["par"]["skip"], "kept: local upstream of kid"
                )
                self.assertEqual(
                    run.items["local-done"]["skip"],
                    "kept: branch.local-done.deleteMerged is false",
                )
        run = self._cleanup("local", apply=True, leak=leaks["e1_count_remote"])

        self.assertEqual(self._results(run), {"done": "done"})
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/par", heads)
        self.assertIn("refs/heads/local-done", heads)

    def test_hostile_home_never_hides_the_passwd_home_keep(self) -> None:
        self._kid_tracks_par()
        home = os.path.join(self.root, "passwd-home")
        os.makedirs(home)
        with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as fh:
            fh.write(
                '[branch "kid"]\n\tremote = .\n\tmerge = refs/heads/par\n'
                '[branch "local-done"]\n\tdeleteMerged = false\n'
            )
        hostile = os.path.join(self.root, "hostile-home")
        os.makedirs(hostile)

        with patch("pkgmgr.core.git.run._passwd_home", return_value=home):
            run = self._cleanup(
                "local",
                apply=True,
                leak={
                    "HOME": hostile,
                    "XDG_CONFIG_HOME": hostile,
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_SYSTEM": os.devnull,
                },
            )

        self.assertEqual(self._results(run), {"done": "done"})
        self.assertEqual(run.items["par"]["skip"], "kept: local upstream of kid")
        self.assertEqual(
            run.items["local-done"]["skip"],
            "kept: branch.local-done.deleteMerged is false",
        )
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/par", heads)
        self.assertIn("refs/heads/local-done", heads)

    def test_local_upstream_from_a_worktree_config_keeps_its_parent(self) -> None:
        for name in ("par1", "par2", "par3"):
            git(self.repo, "branch", name, "done")
        for name in ("kid2", "kid3"):
            git(self.repo, "branch", name, "wip")
        w1 = os.path.join(self.root, "w1")
        w2 = os.path.join(self.root, "w2")
        git(self.repo, "worktree", "add", "-b", "kid1", w1, "wip")
        git(self.repo, "worktree", "add", "-b", "feat/w2", w2, "wip")
        git(self.repo, "config", "extensions.worktreeConfig", "true")
        for checkout, child, parent in ((w1, "kid1", "par1"), (w2, "kid2", "par2")):
            git(checkout, "config", "--worktree", f"branch.{child}.remote", ".")
            git(
                checkout,
                "config",
                "--worktree",
                f"branch.{child}.merge",
                f"refs/heads/{parent}",
            )
        include = os.path.join(self.root, "up.inc")
        with open(include, "w", encoding="utf-8") as fh:
            fh.write('[branch "kid3"]\n\tremote = .\n\tmerge = refs/heads/par3\n')
        git(self.repo, "config", "includeIf.onbranch:feat/**.path", include)
        kept = {f"par{n}": f"kept: local upstream of kid{n}" for n in (1, 2, 3)}

        run = self._cleanup("local", apply=False)
        code, out, _ = self._cli_apply(w2)

        self.assertEqual({n: run.items[n]["skip"] for n in kept}, kept)
        items = {i["branch"]: i for i in json.loads(out)["repos"][0]["items"]}
        self.assertEqual(code, 0)
        self.assertEqual({n: items[n]["skip"] for n in kept}, kept)
        self.assertEqual(
            {n: i["result"] for n, i in items.items() if i["result"]},
            {"done": "done", "local-done": "done"},
        )
        heads = self._refs(self.repo, "refs/heads")
        for name in kept:
            self.assertIn(f"refs/heads/{name}", heads)

    def test_inherited_git_variables_never_move_the_local_root(self) -> None:
        sentinel = os.path.join(self.root, "sentinel")
        git(self.root, "init", "-b", "trunk", sentinel)
        dot_git = os.path.join(sentinel, ".git")

        with patch.dict(os.environ, {"GIT_DIR": dot_git, "GIT_COMMON_DIR": dot_git}):
            self.assertEqual(gc.local_repo_root(self.held), self.repo)

    def test_failed_head_read_refuses_the_repository(self) -> None:
        heads = self._refs(self.repo, "refs/heads")
        real = gc._git

        def timed_out(args: list[str], cwd: str) -> str:
            if args[1:] == ["symbolic-ref", "--quiet", "HEAD"]:
                err = GitRunError("Git command timed out")
                err.returncode = -1
                raise err
            return real(args, cwd)

        with patch.object(gc, "_git", side_effect=timed_out):
            run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 2)
        self.assertEqual(run.items, {})
        self.assertEqual(run.warnings[-1], "refused: Git command timed out")
        self.assertEqual(self._refs(self.repo, "refs/heads"), heads)

    def test_locked_config_is_a_note_on_a_done_item(self) -> None:
        with open(os.path.join(self.repo, ".git", "config.lock"), "w") as fh:
            fh.write("")

        run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 0)
        self.assertTrue(
            run.items["done"]["result"].startswith("done; config branch.done kept: ")
        )
        self.assertTrue(run.items["local-done"]["result"].startswith("done"))
        self.assertNotIn("refs/heads/done", self._refs(self.repo, "refs/heads"))
        self.assertEqual(
            self._branch_config("done"), ["branch.done.remote", "branch.done.merge"]
        )

    def test_repository_hooks_never_run(self) -> None:
        marker = os.path.join(self.root, "hook.log")
        hooks = os.path.join(self.repo, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        for name in ("reference-transaction", "post-checkout"):
            path = os.path.join(hooks, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(MARKING_HOOK.format(marker=marker))
            os.chmod(path, 0o755)

        run = self._cleanup("local", apply=True)

        self.assertEqual(self._results(run), {"done": "done", "local-done": "done"})
        self.assertFalse(os.path.exists(marker))

    def test_config_keep_made_after_the_plan_skips_the_delete(self) -> None:
        real = gc._rebuild

        def late_keep(repo: gc.Repo, item: gc.Item) -> gc.Item:
            fresh = real(repo, item)
            if item.branch == "done":
                git(self.repo, "branch", "kid", "wip")
                git(self.repo, "config", "branch.kid.remote", ".")
                git(self.repo, "config", "branch.kid.merge", "refs/heads/done")
            if item.branch == "local-done":
                git(self.repo, "config", "branch.local-done.deleteMerged", "false")
            return fresh

        with patch.object(gc, "_rebuild", side_effect=late_keep):
            run = self._cleanup("local", apply=True)

        self.assertEqual(run.code, 0)
        self.assertEqual(
            self._results(run),
            {
                "done": "skipped: changed since plan (kept: local upstream of kid)",
                "local-done": (
                    "skipped: changed since plan "
                    "(kept: branch.local-done.deleteMerged is false)"
                ),
            },
        )
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/done", heads)
        self.assertIn("refs/heads/local-done", heads)
        self.assertEqual(
            self._branch_config("done"), ["branch.done.remote", "branch.done.merge"]
        )

    def _family(self) -> None:
        self._set_head()
        git(self.repo, "branch", "a-base", "done")
        git(self.repo, "branch", "z-kid", "done")
        git(self.repo, "config", "branch.z-kid.remote", ".")
        git(self.repo, "config", "branch.z-kid.merge", "refs/heads/a-base")

    def _apply_after(self, change: Callable[[], None]) -> SimpleNamespace:
        """
        Args:
            change: run once after the plan, before the first re-check of
                `--local --apply --branch a-base --branch z-kid`.

        Returns:
            As _cleanup returns it.
        """
        real = gc._rebuild
        changes = [change]

        def late(repo: gc.Repo, item: gc.Item) -> gc.Item:
            if changes:
                changes.pop()()
            return real(repo, item)

        with patch.object(gc, "_rebuild", side_effect=late):
            return self._cleanup("local", apply=True, include=("a-base", "z-kid"))

    def assertFamilyKept(self, run: SimpleNamespace) -> None:
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/a-base", heads)
        self.assertIn("refs/heads/z-kid", heads)
        self.assertFalse((run.items["a-base"]["result"] or "").startswith("done"))
        self.assertEqual(
            git(self.repo, "config", "--get", "branch.z-kid.merge"), "refs/heads/a-base"
        )

    def test_kid_held_before_the_plan_keeps_its_base(self) -> None:
        self._family()
        git(self.repo, "worktree", "add", os.path.join(self.root, "wt-kid"), "z-kid")

        run = self._cleanup("local", apply=True, include=("a-base", "z-kid"))

        self.assertEqual(run.items["a-base"]["skip"], "kept: local upstream of z-kid")
        self.assertFamilyKept(run)

    def test_kid_held_after_the_plan_keeps_its_base(self) -> None:
        self._family()
        kid = os.path.join(self.root, "wt-kid")

        run = self._apply_after(lambda: git(self.repo, "worktree", "add", kid, "z-kid"))

        self.assertEqual(run.code, 0)
        self.assertTrue(run.items["z-kid"]["result"].startswith("skipped: changed"))
        self.assertEqual(
            run.items["a-base"]["result"],
            "skipped: changed since plan (kept: local upstream of z-kid)",
        )
        self.assertFamilyKept(run)

    def test_kid_moved_after_the_plan_keeps_its_base(self) -> None:
        self._family()

        def move() -> None:
            tree = os.path.join(self.root, "wt-tmp")
            git(self.repo, "worktree", "add", "--detach", tree, "z-kid")
            with open(os.path.join(tree, "kid.txt"), "w", encoding="utf-8") as fh:
                fh.write("kid")
            git(tree, "add", "kid.txt")
            git(tree, "commit", "-m", "kid")
            moved = git(tree, "rev-parse", "HEAD")
            git(self.repo, "update-ref", "refs/heads/z-kid", moved)
            git(self.repo, "worktree", "remove", "--force", tree)

        run = self._apply_after(move)

        self.assertTrue(run.items["z-kid"]["result"].startswith("skipped: changed"))
        self.assertFamilyKept(run)

    def test_unchanged_kid_is_deleted_before_its_base(self) -> None:
        self._family()

        run = self._cleanup("local", apply=True, include=("a-base", "z-kid"))

        self.assertEqual(run.code, 0)
        self.assertEqual(self._results(run), {"a-base": "done", "z-kid": "done"})
        deleted = [
            c.args[0][3]
            for c in run.guard.git.call_args_list
            if c.args[0][:3] == ["update-ref", "--no-deref", "-d"]
        ]
        self.assertEqual(deleted, ["refs/heads/z-kid", "refs/heads/a-base"])

    def test_local_upstream_cycle_is_kept_on_apply(self) -> None:
        self._set_head()
        for name in ("c1", "c2"):
            git(self.repo, "branch", name, "done")
        for name, upstream in (("c1", "c2"), ("c2", "c1")):
            git(self.repo, "config", f"branch.{name}.remote", ".")
            git(self.repo, "config", f"branch.{name}.merge", f"refs/heads/{upstream}")

        run = self._cleanup("local", apply=True, include=("c1", "c2"))

        self.assertEqual(
            self._results(run),
            {
                name: f"skipped: changed since plan (kept: local upstream of {other})"
                for name, other in (("c1", "c2"), ("c2", "c1"))
            },
        )
        heads = self._refs(self.repo, "refs/heads")
        self.assertIn("refs/heads/c1", heads)
        self.assertIn("refs/heads/c2", heads)

    def _hub_call(self, *branches: str) -> SimpleNamespace:
        """
        Args:
            branches: the --branch values of `branch cleanup --local --apply
                --json`, run in the fixture repository under _guarded with a
                compose stack listed in the held worktree.

        Returns:
            The exit code, stdout, stderr, the _guarded spies and the
            container listing and docker mocks, as attributes code, out,
            err, guard, compose and docker.
        """
        argv = ["branch", "cleanup", "--local", "--apply", "--json"]
        args = create_parser("test").parse_args(
            [*argv, *(f"--branch={name}" for name in branches)]
        )
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        stack = [gc.Container("proj", os.path.join(self.held, "app"), "img")]
        os.chdir(self.repo)
        out, err = io.StringIO(), io.StringIO()
        with (
            self._guarded() as guard,
            patch.object(gc, "list_compose_containers", return_value=stack) as ps,
            patch.object(gc, "_docker", side_effect=AssertionError) as docker,
            redirect_stdout(out),
            redirect_stderr(err),
            self.assertRaises(SystemExit) as stop,
        ):
            handle_branch(args, ctx=ctx)
        return SimpleNamespace(
            code=stop.exception.code,
            out=out.getvalue(),
            err=err.getvalue(),
            guard=guard,
            compose=ps,
            docker=docker,
        )

    def test_hub_call_deletes_only_a_merged_branch_no_worktree_holds(self) -> None:
        self._set_head()
        heads = self._refs(self.repo, "refs/heads")
        tracking = self._refs(self.repo, "refs/remotes")
        origin = self._refs(self.origin, "refs")
        trees = git(self.repo, "worktree", "list", "--porcelain")

        refused = self._hub_call("remote-done")
        run = self._hub_call("held-done", "wip", "local-done")

        self.assertEqual(refused.code, 2)
        self.assertEqual(refused.out, "")
        self.assertIn("Unknown --branch: remote-done", refused.err)
        self.assertEqual(run.code, 0)
        items = {i["branch"]: i for i in json.loads(run.out)["repos"][0]["items"]}
        self.assertEqual(set(items), {"held-done", "wip", "local-done"})
        held = items["held-done"]
        self.assertEqual(held["skip"], f"checked out in worktree {self.held}")
        self.assertEqual(held["worktree"], self.held)
        self.assertEqual(held["compose_projects"], [])
        self.assertEqual(items["wip"]["state"], "unmerged")
        for name in ("held-done", "wip"):
            with self.subTest(keeps=name):
                self.assertEqual(items[name]["actions"], [])
                self.assertIsNone(items[name]["result"])
        self.assertEqual(items["local-done"]["result"], "done")
        after = self._refs(self.repo, "refs/heads")
        self.assertEqual(set(heads) - set(after), {"refs/heads/local-done"})
        self.assertEqual(self._refs(self.repo, "refs/remotes"), tracking)
        self.assertEqual(self._refs(self.origin, "refs"), origin)
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain"), trees)
        self.assertTrue(os.path.isfile(os.path.join(self.held, "done.txt")))
        for call in (refused, run):
            call.compose.assert_not_called()
            call.docker.assert_not_called()
            self.assertLocalOnly(call.guard)

    def test_branch_scope_still_needs_the_forge_for_a_remote_copy(self) -> None:
        run = self._cleanup("branch", apply=False)

        self.assertEqual(run.code, 0)
        self.assertIn("forge unavailable: no GitHub token (none)", run.warnings)
        self.assertEqual(run.items["done"]["skip"], "forge unavailable")
        self.assertEqual(run.items["remote-done"]["skip"], "forge unavailable")
        self.assertIsNone(run.items["local-done"]["skip"])
        self.assertEqual(run.items["local-done"]["actions"], ["local-branch"])

    def test_cli_local_apply_reads_no_token_and_keeps_the_tree_file(self) -> None:
        tree_path = os.path.join(self.root, "branch-tree.json")
        with open(tree_path, "w", encoding="utf-8") as fh:
            json.dump(
                {"repos": [{"path": self.repo, "known": True, "scanned_at": ""}]}, fh
            )
        with open(tree_path, "rb") as fh:
            before = fh.read()
        args = create_parser("test").parse_args(
            ["branch", "cleanup", "--local", "--apply", "--json"]
        )
        ctx = SimpleNamespace(config_merged={"worktree_hooks": {}, "repositories": []})
        out = io.StringIO()
        with (
            self._guarded() as guard,
            patch.dict(os.environ, {"PKGMGR_TREE_FILE": tree_path}),
            patch("pkgmgr.cli.commands.branch.local_repo_root", return_value=self.repo),
            redirect_stdout(out),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            handle_branch(args, ctx=ctx)

        self.assertEqual(exit_ctx.exception.code, 0)
        items = {
            i["branch"]: i for i in json.loads(out.getvalue())["repos"][0]["items"]
        }
        self.assertEqual(items["done"]["result"], "done")
        self.assertNotIn("refs/heads/done", self._refs(self.repo, "refs/heads"))
        with open(tree_path, "rb") as fh:
            self.assertEqual(fh.read(), before)
        self.assertLocalOnly(guard)


if __name__ == "__main__":
    unittest.main()
