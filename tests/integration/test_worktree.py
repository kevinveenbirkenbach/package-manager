from __future__ import annotations

import io
import json
import os
import shlex
import shutil
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from pkgmgr.actions.branch import gc
from pkgmgr.actions.worktree import hooks, orphans, up
from pkgmgr.cli.commands.worktree import handle_gc, handle_worktree
from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.dispatch import dispatch_command
from pkgmgr.cli.parser import create_parser
from pkgmgr.core.config.load import load_config
from tests.integration.test_branch_gc import GcFixture, git


class WorktreeFixture(GcFixture):
    def _pushed_worktree(self, name: str, makefile: str | None) -> str:
        git(self.repo, "checkout", "-b", name, "main")
        if makefile is None:
            self._commit(name)
        else:
            with open(os.path.join(self.repo, "Makefile"), "w") as fh:
                fh.write(makefile)
            git(self.repo, "add", "Makefile")
            git(self.repo, "commit", "-m", f"{name} makefile")
        git(self.repo, "push", "origin", name)
        git(self.repo, "checkout", "main")
        path = os.path.join(self.root, f"wt-{name}")
        git(self.repo, "worktree", "add", path, name)
        return path

    def _execute(self, plan: gc.Repo, item: gc.Item) -> None:
        with patch.object(gc, "_process_cwds", return_value={}):
            gc.execute(plan, item)

    def _pinned(self, hook: str, argv: list[str]) -> dict:
        return {os.path.realpath(self.repo): {hook: argv}}


class TestCleanupScopes(WorktreeFixture, unittest.TestCase):
    def test_worktree_scope_removes_pushed_worktree_and_keeps_branch(self) -> None:
        path = self._pushed_worktree("pushed", None)
        plan = self._plan(host_ns=True, cwds={}, scope="worktree")
        items = self._items(plan)

        self.assertNotIn("squashed", items)
        item = items["pushed"]
        self.assertEqual(item.state, "unmerged")
        self.assertEqual(item.unpushed, 0)
        self.assertEqual(item.actions, ["worktree"])
        self.assertEqual(gc._label(item), "REMOVE")
        self._execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertFalse(os.path.exists(path))
        self.assertNotEqual(git(self.repo, "branch", "--list", "pushed"), "")
        self.assertNotEqual(git(self.origin, "branch", "--list", "pushed"), "")

    def test_worktree_scope_keeps_unpushed_worktree(self) -> None:
        path = self._pushed_worktree("ahead", None)
        with open(os.path.join(path, "more.txt"), "w") as fh:
            fh.write("more")
        git(path, "add", "more.txt")
        git(path, "commit", "-m", "more")
        item = self._items(self._plan(host_ns=True, cwds={}, scope="worktree"))["ahead"]

        self.assertEqual(item.unpushed, 1)
        self.assertEqual(item.actions, [])
        self.assertFalse(item.eligible)

    def test_branch_scope_skips_checked_out_and_takes_free_branches(self) -> None:
        items = self._items(self._plan(host_ns=True, cwds={}, scope="branch"))

        self.assertTrue(items["merged"].skip.startswith("checked out in worktree"))
        self.assertEqual(items["merged"].actions, [])
        self.assertEqual(gc._label(items["merged"]), "SKIP")
        self.assertEqual(
            items["squashed"].actions, ["local-branch", "remote-branch:origin"]
        )
        self.assertTrue(items["squashed"].eligible)

    def test_patch_equivalent_branch_counts_as_merged(self) -> None:
        git(self.repo, "checkout", "-b", "picked", "main")
        self._commit("picked")
        git(self.repo, "push", "origin", "picked")
        sha = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "main")
        self._commit("main-moved")
        git(self.repo, "cherry-pick", sha)
        git(self.repo, "push", "origin", "main")
        item = self._items(self._plan(host_ns=True, cwds={}))["picked"]

        self.assertEqual(item.merged_by, "patch")
        self.assertEqual(item.state, "merged-clean")

    def test_dotdot_behind_a_symlink_never_reaches_another_checkout(self) -> None:
        victim = os.path.join(self.root, "victim")
        os.makedirs(victim)
        git(victim, "init", "--quiet", "-b", "main")
        git(victim, "commit", "--quiet", "--allow-empty", "-m", "unpushed work")
        git(self.repo, "branch", "evil", "main")
        hop = os.path.join(self.repo, "A")
        os.makedirs(os.path.join(hop, "victim"))
        os.symlink(victim, os.path.join(hop, "L"))
        meta = os.path.join(self.repo, ".git", "worktrees", "evil")
        os.makedirs(meta)
        files = {
            os.path.join(hop, "victim", ".git"): f"gitdir: {meta}\n",
            os.path.join(meta, "gitdir"): os.path.join(
                hop, "L", "..", "victim", ".git"
            ),
            os.path.join(meta, "HEAD"): "ref: refs/heads/evil\n",
            os.path.join(meta, "commondir"): "../..\n",
        }
        for name, text in files.items():
            with open(name, "w") as fh:
                fh.write(text + ("" if text.endswith("\n") else "\n"))
        plan = self._plan(host_ns=True, cwds={}, scope="worktree")
        item = self._items(plan)["evil"]

        self._execute(plan, item)

        self.assertNotIn("worktree", item.actions)
        self.assertTrue(os.path.isdir(os.path.join(victim, ".git")))

    def test_pinned_fini_hook_runs_before_removal(self) -> None:
        marker = os.path.join(self.root, "fini-ran")
        path = self._pushed_worktree("hooked", None)
        pins = self._fini_pins(["touch", marker])
        plan = self._plan(host_ns=True, cwds={}, scope="worktree", hooks=pins)
        item = self._items(plan)["hooked"]

        self.assertEqual(item.actions, ["hook:worktree-fini", "worktree"])
        self._execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertTrue(os.path.exists(marker))
        self.assertFalse(os.path.exists(path))

    def _fini_pins(self, argv: list[str]) -> dict:
        return self._pinned("worktree-fini", argv)

    def _cleanup_merged_forged_to(self, target: str) -> dict:
        meta = os.path.join(self.repo, ".git", "worktrees", "wt-merged")
        with open(os.path.join(meta, "gitdir"), "w") as fh:
            fh.write(os.path.join(target, ".git") + "\n")
        pins = self._fini_pins(["touch", "{path}/fini-ran"])
        out = io.StringIO()
        with (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value={}),
            redirect_stdout(out),
            redirect_stderr(io.StringIO()),
        ):
            gc.cleanup(
                [self.repo],
                scope="worktree",
                apply=True,
                as_json=True,
                include=["merged"],
                exclude=[],
                merged_into=[],
                sizes=False,
                min_age=None,
                hooks=pins,
            )
        return json.loads(out.getvalue())["repos"][0]["items"][0]

    def test_forged_gitdir_runs_nothing_in_another_checkout(self) -> None:
        other = os.path.join(self.root, "other")
        git(self.root, "clone", "--quiet", self.repo, other)

        item = self._cleanup_merged_forged_to(other)

        self.assertFalse(os.path.exists(os.path.join(other, "fini-ran")))
        self.assertEqual(item["worktree"], other)
        self.assertEqual(item["skip"], gc.NOT_LINKED)
        self.assertEqual(item["actions"], [])
        self.assertTrue(os.path.isdir(os.path.join(other, ".git")))

    def test_gitdir_forged_to_a_sibling_worktree_runs_nothing_there(self) -> None:
        sibling = self._pushed_worktree("sibling", None)

        item = self._cleanup_merged_forged_to(sibling)

        self.assertFalse(os.path.exists(os.path.join(sibling, "fini-ran")))
        self.assertEqual(item["worktree"], sibling)
        self.assertEqual(item["skip"], gc.NOT_LINKED)
        self.assertEqual(item["actions"], [])
        self.assertTrue(os.path.isdir(sibling))

    def test_fini_hook_commit_keeps_worktree_and_branch(self) -> None:
        commit = [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.org",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "hook",
        ]
        plan = self._plan(host_ns=True, cwds={}, hooks=self._fini_pins(commit))
        item = self._items(plan)["merged"]
        self.assertIn("local-branch", item.actions)

        self._execute(plan, item)

        self.assertEqual(
            item.result, "skipped: changed during worktree-fini (HEAD moved)"
        )
        self.assertTrue(os.path.isdir(self.merged_wt))
        self.assertNotEqual(git(self.repo, "rev-parse", "merged"), item.local_sha)

    def test_fini_hook_timeout_kills_its_process_group(self) -> None:
        self._pushed_worktree("spawner", None)
        marker = os.path.join(self.root, "grandchild-ran")
        script = f"(sleep 1; touch {shlex.quote(marker)}) & sleep 30"
        pins = self._fini_pins(["sh", "-c", script])
        plan = self._plan(host_ns=True, cwds={}, scope="worktree", hooks=pins)
        item = self._items(plan)["spawner"]

        with patch.object(hooks, "HOOK_TIMEOUT", 0.3):
            self._execute(plan, item)
        time.sleep(1.5)

        self.assertEqual(item.result, "failed: worktree-fini timed out after 0.3 s")
        self.assertFalse(os.path.exists(marker))

    def test_fini_hook_timeout_fails_without_removal(self) -> None:
        path = self._pushed_worktree("slow", None)
        sleep = [sys.executable, "-c", "import time; time.sleep(30)"]
        pins = self._fini_pins(sleep)
        plan = self._plan(host_ns=True, cwds={}, scope="worktree", hooks=pins)
        item = self._items(plan)["slow"]

        with patch.object(hooks, "HOOK_TIMEOUT", 0.5):
            self._execute(plan, item)

        self.assertEqual(item.result, "failed: worktree-fini timed out after 0.5 s")
        self.assertTrue(os.path.isdir(path))

    def test_fini_hook_output_keeps_the_worktree(self) -> None:
        path = self._pushed_worktree("dumps", None)
        pins = self._fini_pins(["touch", "{path}/dump.sql"])
        plan = self._plan(host_ns=True, cwds={}, scope="worktree", hooks=pins)
        item = self._items(plan)["dumps"]

        self._execute(plan, item)

        self.assertEqual(
            item.result, "skipped: changed during worktree-fini (dirty: 1 paths)"
        )
        self.assertTrue(os.path.isfile(os.path.join(path, "dump.sql")))

    @unittest.skipUnless(shutil.which("make"), "make is not available")
    def test_makefile_hooks_never_run_unpinned(self) -> None:
        marker = os.path.join(self.root, "fini-ran")
        planted = f"worktree-fini:\n\ttouch {marker}\n"
        path = self._pushed_worktree("planted", makefile=planted)
        with open(os.path.join(self.repo, ".git", "info", "exclude"), "a") as fh:
            fh.write("GNUmakefile\n")
        with open(os.path.join(path, "GNUmakefile"), "w") as fh:
            fh.write(planted)
        plan = self._plan(host_ns=True, cwds={}, scope="worktree")
        item = self._items(plan)["planted"]

        self.assertEqual(item.actions, ["worktree"])
        self._execute(plan, item)

        self.assertEqual(item.result, "done")
        self.assertFalse(os.path.exists(marker))

    def test_activity_is_recorded_on_request(self) -> None:
        quiet = self._items(self._plan(host_ns=True, cwds={}))
        loud = self._items(self._plan(host_ns=True, cwds={}, activity=True))

        self.assertIsNone(quiet["merged"].last_activity)
        self.assertLessEqual(loud["merged"].last_activity, time.time())


class TestWorktreeUp(WorktreeFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.worktrees = os.path.join(self.root, "wts")

    def _up(
        self, branch: str, path: str | None, hooks: dict | None = None
    ) -> tuple[int, dict]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = up.worktree_up(
                self.repo,
                branch,
                base=None,
                worktrees_dir=self.worktrees,
                path=path,
                hooks=hooks or {},
                as_json=True,
            )
        return code, json.loads(out.getvalue()) if code != 2 else {}

    def _commit_file(self, name: str, text: str) -> None:
        with open(os.path.join(self.repo, name), "w") as fh:
            fh.write(text)
        git(self.repo, "add", name)
        git(self.repo, "commit", "-m", name)
        git(self.repo, "push", "origin", "main")

    def _commit_script(self, name: str) -> str:
        marker = os.path.join(self.root, f"{name}-ran")
        script = os.path.join(self.repo, name)
        with open(script, "w") as fh:
            fh.write(f"#!/bin/sh\ntouch {marker}\n")
        os.chmod(script, 0o755)
        git(self.repo, "add", name)
        git(self.repo, "commit", "-m", name)
        git(self.repo, "push", "origin", "main")
        return marker

    def _pins(self, argv: list[str]) -> dict:
        return self._pinned("worktree-init", argv)

    def test_slot_in_branch_name_stays_literal(self) -> None:
        write_path = "import sys; open('path.txt', 'w').write(sys.argv[1])"
        pins = self._pins([sys.executable, "-c", write_path, "{path}"])

        code, result = self._up("feature/x{slot}", None, pins)

        self.assertEqual(code, 0)
        self.assertTrue(result["path"].endswith("/feature/x{slot}"))
        with open(os.path.join(result["path"], "path.txt")) as fh:
            self.assertEqual(fh.read(), result["path"])

    @unittest.skipUnless(shutil.which("make"), "make is not available")
    def test_empty_path_entry_never_runs_a_planted_command(self) -> None:
        marker = self._commit_script("make")
        search = os.pathsep + os.environ["PATH"]

        with patch.dict(os.environ, {"PATH": search}):
            code, result = self._up("feature/p", None, self._pins(["make", "-v"]))

        self.assertEqual(code, 0)
        self.assertEqual(result["hook"], "worktree-init")
        self.assertFalse(os.path.exists(marker))

    def test_bare_pin_skips_a_path_entry_another_user_can_write(self) -> None:
        planted = os.path.join(self.root, "planted-bin")
        os.makedirs(planted)
        marker = os.path.join(self.root, "planted-ran")
        fake = os.path.join(planted, "true")
        with open(fake, "w") as fh:
            fh.write(f"#!/bin/sh\ntouch {marker}\n")
        os.chmod(fake, 0o755)
        if os.getuid() == 0:
            os.chown(planted, 65534, 65534)
            os.chown(fake, 65534, 65534)
        search = planted + os.pathsep + os.environ["PATH"]

        with patch.dict(os.environ, {"PATH": search}):
            code, result = self._up("feature/t", None, self._pins(["true"]))

        self.assertEqual((code, result["hook"]), (0, "worktree-init"))
        self.assertFalse(os.path.exists(marker))

    def test_relative_pin_is_refused_before_checkout(self) -> None:
        marker = self._commit_script("init.sh")

        code, _ = self._up("feature/r", None, self._pins(["./init.sh"]))

        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(os.path.exists(self.worktrees))

    def test_init_hook_timeout_fails_and_keeps_worktree(self) -> None:
        pins = self._pins([sys.executable, "-c", "import time; time.sleep(30)"])

        with patch.object(hooks, "HOOK_TIMEOUT", 0.5):
            code, result = self._up("feature/t", None, pins)

        self.assertEqual(code, 1)
        self.assertEqual(
            result["hook"],
            "worktree-init failed (worktree-init timed out after 0.5 s)",
        )
        self.assertTrue(os.path.isdir(result["path"]))

    def test_location_of_remote_urls(self) -> None:
        cases = {
            "git@github.com:owner/repo.git": "github.com/owner/repo",
            "https://github.com/owner/repo": "github.com/owner/repo",
            "ssh://git@host:2201/owner/repo.git": "host/owner/repo",
            "/tmp/x/origin.git": "tmp/x/origin",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(up.worktree_location(url), expected)

    def test_new_branches_get_path_slots_and_pinned_init_hook(self) -> None:
        write_slot = "import sys; open('slot.txt', 'w').write(sys.argv[1])"
        hooks = self._pins([sys.executable, "-c", write_slot, "{slot}"])

        code, first = self._up("feature/x", None, hooks)
        expected = os.path.join(
            self.worktrees, up.worktree_location(self.origin), "feature/x"
        )
        self.assertEqual(code, 0)
        self.assertEqual(first["path"], expected)
        self.assertEqual(first["slot"], 1)
        self.assertEqual(first["hook"], "worktree-init")
        self.assertTrue(first["origin"].startswith("new from origin/main"))
        with open(os.path.join(expected, "slot.txt")) as fh:
            self.assertEqual(fh.read().strip(), "1")

        _, second = self._up("feature/y", None, hooks)
        self.assertEqual(second["slot"], 2)
        self.assertEqual(self._up("feature/x", None, hooks)[0], 2)

    @unittest.skipUnless(shutil.which("make"), "make is not available")
    def test_unpinned_makefile_is_never_run_or_probed(self) -> None:
        parsed = os.path.join(self.root, "parsed")
        ran = os.path.join(self.root, "ran")
        self._commit_file(
            "Makefile", f"X := $(shell touch {parsed})\nworktree-init:\n\ttouch {ran}\n"
        )

        code, result = self._up("feature/m", None)

        self.assertEqual(code, 0)
        self.assertEqual(result["hook"], "not pinned: worktree-init in Makefile")
        self.assertFalse(os.path.exists(parsed))
        self.assertFalse(os.path.exists(ran))

    def test_origin_url_cannot_escape_the_worktrees_dir(self) -> None:
        git(self.repo, "remote", "set-url", "origin", "https://host/../../escape")

        self.assertEqual(self._up("feature/e", None)[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "escape")))

    def test_default_base_named_like_an_option_is_a_ref(self) -> None:
        git(self.repo, "checkout", "-b", "side", "main")
        self._commit("side")
        sha = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "main")
        git(self.repo, "update-ref", "refs/heads/-f", sha)
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/heads/-f")

        code, result = self._up("feature/o", None)

        self.assertEqual(code, 0)
        self.assertEqual(git(result["path"], "rev-parse", "HEAD"), sha)

    def test_local_filter_config_blocks_the_checkout(self) -> None:
        marker = os.path.join(self.root, "smudged")
        self._commit_file(".gitattributes", "* filter=evil\n")
        git(self.repo, "config", "filter.evil.smudge", f"touch {marker}; cat")

        self.assertEqual(self._up("feature/s", None)[0], 2)
        self.assertFalse(os.path.exists(marker))

    def test_local_ssh_command_skips_the_fetch(self) -> None:
        marker = os.path.join(self.root, "ssh-ran")
        git(self.repo, "config", "core.sshCommand", f"touch {marker}; false")
        git(self.repo, "config", "remote.origin.pushurl", self.origin)
        git(self.repo, "remote", "set-url", "origin", "ssh://example.invalid/r.git")

        code, result = self._up("feature/f", None)

        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(marker))
        self.assertIn("core.sshcommand", " ".join(result["warnings"]))

    def test_remote_branch_is_tracked(self) -> None:
        git(self.repo, "checkout", "-b", "remote-only", "main")
        self._commit("remote-only")
        git(self.repo, "push", "origin", "remote-only")
        git(self.repo, "checkout", "main")
        git(self.repo, "branch", "-D", "remote-only")

        code, result = self._up("remote-only", None)

        self.assertEqual(code, 0)
        self.assertEqual(result["origin"], "tracking origin/remote-only")
        self.assertEqual(result["hook"], "none")
        self.assertEqual(
            git(result["path"], "rev-parse", "--abbrev-ref", "@{u}"),
            "origin/remote-only",
        )

    def test_explicit_path_replaces_standard_path(self) -> None:
        released = os.path.join(self.root, "released", "feature-z")

        code, result = self._up("feature/z", released)

        self.assertEqual(code, 0)
        self.assertEqual(result["path"], released)
        self.assertEqual(
            git(released, "rev-parse", "--abbrev-ref", "HEAD"), "feature/z"
        )
        self.assertFalse(os.path.exists(self.worktrees))

    def test_invalid_branch_is_refused(self) -> None:
        self.assertEqual(self._up("../evil", None)[0], 2)
        self.assertFalse(os.path.exists(self.worktrees))


class TestWorktreeOrphans(WorktreeFixture, unittest.TestCase):
    def _report(self, cwds: dict[int, str]) -> dict[str, dict]:
        out = io.StringIO()
        with (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value=cwds),
            redirect_stdout(out),
        ):
            code = orphans.worktree_orphans(
                [self.repo],
                stale_days=0,
                top=5,
                as_json=True,
                include=[],
                exclude=[],
                merged_into=[],
                sizes=False,
            )
        self.assertEqual(code, 0)
        rows = json.loads(out.getvalue())["repos"][0]["rows"]
        return {row["branch"]: row for row in rows if row["branch"]}

    def test_classes_and_proposals(self) -> None:
        git(self.repo, "checkout", "-b", "lonely", "main")
        self._commit("lonely")
        git(self.repo, "checkout", "main")
        time.sleep(1.1)
        rows = self._report({})

        self.assertEqual(rows["main"]["class"], "active")
        self.assertEqual(rows["merged"]["class"], "merged-clean")
        self.assertEqual(rows["merged"]["proposal"], "pkgmgr gc")
        self.assertEqual(rows["dirty"]["class"], "merged-dirty")
        self.assertEqual(rows["lonely"]["class"], "stale-open")
        self.assertEqual(rows["lonely"]["unpushed"], 1)
        self.assertEqual(rows["wip"]["class"], "active")

    def test_busy_worktree_is_kept(self) -> None:
        rows = self._report({4242: self.merged_wt})

        self.assertEqual(rows["merged"]["class"], "merged-clean")
        self.assertTrue(
            rows["merged"]["proposal"].startswith("keep (process: pid 4242")
        )


class TestLoadedConfigCli(WorktreeFixture, unittest.TestCase):
    HOOKS = ("worktree-init", "worktree-fini")

    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(os.chdir, os.getcwd())
        self.markers = {h: os.path.join(self.root, f"{h}-ran") for h in self.HOOKS}

    def _ctx(self, directory: str, pinned: bool) -> CLIContext:
        location = up.worktree_location(self.origin)
        provider, _, rest = location.partition("/")
        account, _, repository = rest.rpartition("/")
        config: dict = {
            "directories": {"worktrees": os.path.join(self.root, "wts")},
            "repositories": [
                {
                    "provider": provider,
                    "account": account,
                    "repository": repository,
                    "directory": directory,
                }
            ],
        }
        if pinned:
            config["worktree_hooks"] = {
                location: {h: ["touch", m] for h, m in self.markers.items()}
            }
        config_dir = os.path.join(self.root, "config")
        os.makedirs(config_dir, exist_ok=True)
        user_config = os.path.join(config_dir, "config.yaml")
        with open(user_config, "w") as fh:
            yaml.safe_dump(config, fh)
        merged = load_config(user_config)
        return CLIContext(
            config_merged=merged,
            repositories_base_dir=os.path.join(self.root, "repos"),
            all_repositories=merged["repositories"],
            binaries_dir=os.path.join(self.root, "bin"),
            user_config_path=user_config,
        )

    def _run(self, argv: list[str], ctx: CLIContext) -> tuple[int, str]:
        os.chdir(self.repo)
        out = io.StringIO()
        with (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "fetch_forge_facts", return_value=self.forge),
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(gc, "_docker", return_value=""),
            patch("pkgmgr.cli.commands.branch.refresh_tree"),
            patch("pkgmgr.cli.commands.worktree.refresh_tree"),
            redirect_stdout(out),
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            dispatch_command(create_parser("test").parse_args(argv), ctx)
        return exit_ctx.exception.code, out.getvalue()

    def test_gc_dry_run_with_config_lacking_worktree_hooks(self) -> None:
        code, out = self._run(["gc", "--json"], self._ctx(self.repo, pinned=False))

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["repos"][0]["repo"], self.repo)

    def test_origin_url_of_a_managed_repository_selects_no_pin(self) -> None:
        managed = os.path.join(self.root, "managed")
        git(self.root, "clone", "--quiet", self.repo, managed)
        ctx = self._ctx(managed, pinned=True)

        code, out = self._run(["worktree", "up", "feature/a", "--json"], ctx)
        self.assertEqual((code, json.loads(out)["hook"]), (0, "none"))
        self.assertEqual(self._run(["gc", "--apply", "--branch", "merged"], ctx)[0], 0)

        self.assertFalse(os.path.exists(self.markers["worktree-init"]))
        self.assertFalse(os.path.exists(self.markers["worktree-fini"]))
        self.assertFalse(os.path.exists(self.merged_wt))

    def test_pinned_directory_borrowing_another_git_dir_runs_no_pin(self) -> None:
        borrower = os.path.join(self.root, "borrower")
        git(self.root, "init", "--quiet", "-b", "main", borrower)
        with open(os.path.join(borrower, ".git", "commondir"), "w") as fh:
            fh.write(os.path.join(self.repo, ".git") + "\n")
        ctx = self._ctx(borrower, pinned=True)

        code, out = self._run(
            ["gc", "--all", "--apply", "--json", "--branch", "merged"], ctx
        )

        warnings = json.loads(out)["repos"][0]["warnings"]
        self.assertEqual(code, 0)
        self.assertTrue(any("pinned hooks skipped" in w for w in warnings))
        self.assertFalse(os.path.exists(self.markers["worktree-fini"]))

    def test_managed_repository_runs_its_pins(self) -> None:
        ctx = self._ctx(self.repo, pinned=True)

        code, out = self._run(["worktree", "up", "feature/b", "--json"], ctx)
        self.assertEqual((code, json.loads(out)["hook"]), (0, "worktree-init"))
        self.assertEqual(self._run(["gc", "--apply", "--branch", "merged"], ctx)[0], 0)

        self.assertTrue(os.path.exists(self.markers["worktree-init"]))
        self.assertTrue(os.path.exists(self.markers["worktree-fini"]))
        self.assertFalse(os.path.exists(self.merged_wt))


class TestWorktreeCli(unittest.TestCase):
    def test_branch_gc_is_gone(self) -> None:
        with self.assertRaises(SystemExit):
            create_parser("test").parse_args(["branch", "gc"])

    def test_up_forwards_to_worktree_up(self) -> None:
        args = create_parser("test").parse_args(
            [
                "worktree",
                "up",
                "feature/x",
                "--base",
                "origin/main",
                "--path",
                "/srv/wt/x",
                "--json",
            ]
        )
        pins = {"worktree-init": ["true"]}
        ctx = SimpleNamespace(
            repositories_base_dir="/srv",
            config_merged={
                "directories": {"worktrees": "~/wt"},
                "repositories": [
                    {"provider": "host", "account": "o", "repository": "r"}
                ],
                "worktree_hooks": {"host/o/r": pins, "host/o/unmanaged": pins},
            },
        )
        with (
            patch("pkgmgr.cli.commands.worktree.worktree_up", return_value=0) as run_up,
            patch("pkgmgr.cli.commands.worktree.refresh_tree") as refresh,
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            handle_worktree(args, ctx)

        self.assertEqual(exit_ctx.exception.code, 0)
        run_up.assert_called_once_with(
            ".",
            "feature/x",
            base="origin/main",
            worktrees_dir="~/wt",
            path="/srv/wt/x",
            hooks={os.path.realpath("/srv/host/o/r"): pins},
            as_json=True,
        )
        refresh.assert_called_once()

    def test_cleanup_and_gc_pick_their_scope(self) -> None:
        for argv, handler, scope in (
            (["worktree", "cleanup", "--apply"], handle_worktree, "worktree"),
            (["gc", "--apply"], handle_gc, "all"),
        ):
            with self.subTest(scope=scope):
                args = create_parser("test").parse_args(argv)
                ctx = SimpleNamespace(
                    config_merged={"worktree_hooks": {}, "repositories": []}
                )
                with (
                    patch(
                        "pkgmgr.cli.commands.branch.main_repo_root", return_value="/r"
                    ),
                    patch(
                        "pkgmgr.cli.commands.branch.cleanup", return_value=0
                    ) as run_cleanup,
                    patch("pkgmgr.cli.commands.branch.refresh_tree") as refresh,
                    self.assertRaises(SystemExit),
                ):
                    handler(args, ctx)
                self.assertEqual(run_cleanup.call_args.kwargs["scope"], scope)
                self.assertTrue(run_cleanup.call_args.kwargs["apply"])
                self.assertEqual(run_cleanup.call_args.kwargs["hooks"], {})
                refresh.assert_called_once_with(["/r"])

    def test_orphans_requires_explicit_limits(self) -> None:
        with self.assertRaises(SystemExit):
            create_parser("test").parse_args(["worktree", "orphans"])
        args = create_parser("test").parse_args(
            ["worktree", "orphans", "--stale-days", "7", "--top", "5"]
        )
        self.assertEqual((args.stale_days, args.top), (7, 5))


if __name__ == "__main__":
    unittest.main()
