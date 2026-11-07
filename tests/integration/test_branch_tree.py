from __future__ import annotations

import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import yaml

from pkgmgr.actions.branch import gc, tree
from pkgmgr.actions.branch.gc_forge import ForgeFacts
from pkgmgr.cli.commands.branch import handle_branch
from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.parser import create_parser
from pkgmgr.core.git.run import run

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
VOLATILE = ("generated_at", "scanned_at")


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def stable(data):
    if isinstance(data, dict):
        return {
            key: stable(value) for key, value in data.items() if key not in VOLATILE
        }
    if isinstance(data, list):
        return [stable(value) for value in data]
    return data


class TestBranchTree(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)
        self.origin = os.path.join(self.root, "origin.git")
        self.repo = os.path.join(self.root, "repos", "repo")
        self.shared = os.path.join(self.root, "shared-worktrees")
        os.makedirs(self.shared)
        git(self.root, "init", "--bare", "-b", "main", self.origin)
        git(self.root, "init", "-b", "main", self.repo)
        git(self.repo, "remote", "add", "origin", self.origin)
        self._commit("init")
        git(self.repo, "push", "-u", "origin", "main")
        git(self.repo, "remote", "set-head", "origin", "main")
        self._write(os.path.join(self.repo, ".git", "info"), "exclude", ".worktrees/\n")

        self._pushed("merged")
        git(self.repo, "merge", "--no-ff", "-m", "merge merged", "merged")
        git(self.repo, "push", "origin", "main")
        self._pushed("ahead")
        git(self.repo, "checkout", "ahead")
        self._commit("ahead-local")
        git(self.repo, "checkout", "main")
        self._pushed("behind", commits=2)
        git(self.repo, "branch", "-f", "behind", "behind~1")
        self._pushed("gone")
        git(self.repo, "push", "origin", "--delete", "gone")

        self.changed = os.path.join(self.root, "repos", "repo", ".worktrees", "changed")
        git(self.repo, "worktree", "add", "-b", "changed", self.changed, "main")
        self._write(self.changed, "staged.txt", "s")
        git(self.changed, "add", "staged.txt")
        self._write(self.changed, "init.txt", "edited")
        self._write(self.changed, "loose.txt", "u")
        self.detached = os.path.join(self.shared, "repo", "detached")
        git(self.repo, "worktree", "add", "--detach", self.detached, "main")
        self.missing = os.path.join(self.root, "wt-missing")
        git(self.repo, "worktree", "add", "-b", "missing", self.missing, "main")
        shutil.rmtree(self.missing)

        self.facts = ForgeFacts(merged_heads={}, open_heads={})
        self.tree_file = os.path.join(self.root, "state", "tree", "branch-tree.json")
        self.env = patch.dict(
            os.environ,
            {
                "PKGMGR_TREE_FILE": self.tree_file,
                "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.patches = [
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(
                tree,
                "secret_service_token",
                return_value=(None, "Secret Service locked"),
            ),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _write(self, cwd: str, name: str, text: str) -> None:
        with open(os.path.join(cwd, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _commit(self, name: str, cwd: str | None = None) -> None:
        self._write(cwd or self.repo, f"{name}.txt", name)
        git(cwd or self.repo, "add", f"{name}.txt")
        git(cwd or self.repo, "commit", "-m", name)

    def _pushed(self, name: str, commits: int = 1) -> None:
        git(self.repo, "checkout", "-b", name, "main")
        for number in range(commits):
            self._commit(f"{name}-{number}")
        git(self.repo, "push", "-u", "origin", name)
        git(self.repo, "checkout", "main")

    def _tree(self, fmt: str = "json", repos: list[str] | None = None) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            code = tree.branch_tree(
                repos or [self.repo], fmt=fmt, output=None, worktrees_root=self.shared
            )
        self.assertEqual(code, 0)
        return out.getvalue()

    def _entry(self) -> dict:
        data = json.loads(self._tree())
        return next(repo for repo in data["repos"] if repo["path"] == self.repo)

    def _by_branch(self, entry: dict) -> dict[str, dict]:
        return {item["branch"]: item for item in entry["items"] if item["branch"]}

    def test_json_carries_repository_branch_and_worktree_fields(self) -> None:
        data = json.loads(self._tree())
        entry = next(repo for repo in data["repos"] if repo["path"] == self.repo)
        branches = self._by_branch(entry)

        self.assertIn("generated_at", data)
        self.assertEqual(
            (entry["remote"], entry["default"], entry["missing"]),
            (self.origin, "main", False),
        )
        self.assertEqual(
            (
                branches["ahead"]["upstream"],
                branches["ahead"]["ahead"],
                branches["ahead"]["behind"],
            ),
            ("origin/ahead", 1, 0),
        )
        self.assertEqual(
            (branches["behind"]["ahead"], branches["behind"]["behind"]), (0, 1)
        )
        self.assertTrue(branches["gone"]["gone"])
        self.assertFalse(branches["merged"]["gone"])
        changed = branches["changed"]
        self.assertEqual(
            (changed["worktree"], changed["worktree_state"]), (self.changed, "changed")
        )
        self.assertEqual(
            (changed["staged"], changed["unstaged"], changed["untracked"]), (1, 1, 1)
        )
        self.assertEqual(changed["head"], git(self.repo, "rev-parse", "main"))
        self.assertEqual(changed["state"], "dirty")
        self.assertEqual(branches["missing"]["worktree_state"], "missing")
        self.assertEqual(branches["main"]["worktree_state"], "clean")
        detached = [item for item in entry["items"] if item["detached"]]
        self.assertEqual(
            [(item["worktree"], item["worktree_state"]) for item in detached],
            [(self.detached, "clean")],
        )
        self.assertEqual(branches["merged"]["merged_by"], "ancestor")
        self.assertEqual(entry["forge"], "none")
        self.assertEqual(
            (data["delete_ready"], data["delete_reason"]),
            (False, "Secret Service locked"),
        )

    def test_yaml_prints_the_same_data(self) -> None:
        self.assertEqual(
            stable(yaml.safe_load(self._tree("yaml"))),
            stable(json.loads(self._tree("json"))),
        )

    def test_tree_and_gc_share_every_state(self) -> None:
        out = io.StringIO()
        with (
            patch.object(gc, "fetch_forge_facts", return_value=ForgeFacts()),
            redirect_stdout(out),
        ):
            gc.cleanup(
                [self.repo],
                scope="all",
                apply=False,
                as_json=True,
                include=[],
                exclude=[],
                merged_into=[],
                sizes=False,
                min_age=None,
                hooks={},
            )
        planned = {
            (item["branch"], item["worktree"]): (
                item["state"],
                item["merged_by"],
                item["skip"],
            )
            for item in json.loads(out.getvalue())["repos"][0]["items"]
        }
        listed = {
            (item["branch"], item["worktree"]): (
                item["state"],
                item["merged_by"],
                item["skip"],
            )
            for item in self._entry()["items"]
        }
        self.assertEqual(listed, planned)

    def test_the_scan_runs_no_hook_fsmonitor_or_local_filter(self) -> None:
        marker = os.path.join(self.root, "ran")
        script = os.path.join(self.root, "plant.sh")
        self._write(self.root, "plant.sh", f"#!/bin/sh\ntouch {marker}\n")
        os.chmod(script, stat.S_IRWXU)
        hooks = os.path.join(self.root, "hooks")
        os.makedirs(hooks)
        for hook in ("post-index-change", "reference-transaction", "post-checkout"):
            shutil.copy(script, os.path.join(hooks, hook))
        git(self.repo, "config", "core.fsmonitor", script)
        git(self.repo, "config", "core.hooksPath", hooks)
        git(self.repo, "config", "core.pager", script)
        git(self.repo, "config", "filter.planted.clean", script)
        self._write(self.changed, ".gitattributes", "* filter=planted\n")

        with patch("subprocess.run", wraps=subprocess.run) as spy:
            changed = self._by_branch(self._entry())["changed"]
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(
            (changed["worktree_state"], changed["staged"]), ("changed", None)
        )
        self.assertIn("filter.planted.clean", changed["reason"])
        scans = [
            call
            for call in spy.call_args_list
            if call.args and call.args[0][:1] == ["git"]
        ]
        self.assertTrue(scans)
        for call in scans:
            with self.subTest(argv=call.args[0][:6]):
                self.assertNotIn("fetch", call.args[0])
                self.assertEqual(call.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
                self.assertIn("core.fsmonitor=false", call.args[0])

    def test_a_worktree_with_submodules_is_not_read(self) -> None:
        head = git(self.changed, "rev-parse", "HEAD")
        git(self.changed, "update-index", "--add", "--cacheinfo", f"160000,{head},sub")
        changed = self._by_branch(self._entry())["changed"]
        self.assertEqual((changed["state"], changed["staged"]), ("dirty", None))
        self.assertIn("submodules", changed["reason"])

    def test_the_scan_never_runs_a_planted_gpg_program(self) -> None:
        marker = os.path.join(self.root, "verified")
        self._write(self.root, "gpg.sh", f"#!/bin/sh\ntouch {marker}\nexit 1\n")
        os.chmod(os.path.join(self.root, "gpg.sh"), stat.S_IRWXU)
        git(self.repo, "config", "log.showSignature", "true")
        git(self.repo, "config", "gpg.program", os.path.join(self.root, "gpg.sh"))
        body = git(self.repo, "cat-file", "commit", "HEAD").replace(
            "\n\n",
            "\ngpgsig -----BEGIN PGP SIGNATURE-----\n \n -----END PGP SIGNATURE-----\n\n",
            1,
        )
        signed = subprocess.run(
            ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
            cwd=self.repo,
            input=body,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        git(self.repo, "log", "-1", signed)
        self.assertTrue(os.path.exists(marker))
        os.unlink(marker)
        run(["log", "-1", "--format=%ct", signed], cwd=self.repo, scan=True)
        self.assertFalse(os.path.exists(marker))

    def test_output_is_written_atomically(self) -> None:
        target = os.path.join(self.root, "out", "branch-tree.json")
        code = tree.branch_tree(
            [self.repo], fmt="json", output=target, worktrees_root=self.shared
        )
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["repos"][0]["path"], self.repo)
        self.assertEqual(
            sorted(os.listdir(os.path.dirname(target))),
            [".branch-tree.json.lock", "branch-tree.json"],
        )

    def test_lists_every_known_repository_also_plain_and_missing(self) -> None:
        plain = os.path.join(self.root, "repos", "plain")
        git(self.root, "init", "-b", "main", plain)
        self._commit("plain", cwd=plain)
        absent = os.path.join(self.root, "repos", "absent")
        ctx = CLIContext(
            config_merged={},
            repositories_base_dir=os.path.join(self.root, "base"),
            all_repositories=[
                {
                    "provider": "x",
                    "account": "y",
                    "repository": "repo",
                    "directory": self.repo,
                },
                {
                    "provider": "x",
                    "account": "y",
                    "repository": "plain",
                    "directory": plain,
                },
                {
                    "provider": "x",
                    "account": "y",
                    "repository": "absent",
                    "directory": absent,
                },
            ],
            binaries_dir="",
            user_config_path="",
        )
        args = create_parser("test").parse_args(["branch", "tree", "--format", "json"])
        out = io.StringIO()
        with (
            patch.object(tree, "WORKTREES_ROOT", self.shared),
            redirect_stdout(out),
            self.assertRaises(SystemExit) as done,
        ):
            handle_branch(args, ctx)
        self.assertEqual(done.exception.code, 0)
        repos = {repo["path"]: repo for repo in json.loads(out.getvalue())["repos"]}
        self.assertEqual(set(repos), {self.repo, plain, absent})
        self.assertEqual([item["branch"] for item in repos[plain]["items"]], ["main"])
        self.assertEqual((repos[absent]["missing"], repos[absent]["items"]), (True, []))

    def test_a_shared_worktree_of_an_unknown_repository_adds_it(self) -> None:
        other = os.path.join(self.root, "elsewhere", "other")
        git(self.root, "init", "-b", "main", other)
        self._commit("other", cwd=other)
        orphan = os.path.join(self.shared, "other", "feature")
        git(other, "worktree", "add", "-b", "feature", orphan, "main")
        repos = {repo["path"]: repo for repo in json.loads(self._tree())["repos"]}
        self.assertEqual(
            (repos[self.repo]["known"], repos[other]["known"]), (True, False)
        )
        self.assertIn(orphan, [item["worktree"] for item in repos[other]["items"]])

    def test_forge_facts_come_from_the_secret_service_at_most_every_ten_minutes(
        self,
    ) -> None:
        git(self.repo, "remote", "set-url", "origin", "https://github.com/me/repo.git")
        locked = self._entry()
        self.assertEqual(locked["forge"], "unavailable: Secret Service locked")
        self.assertEqual(self._by_branch(locked)["merged"]["merged_by"], "ancestor")
        self.assertEqual(self._by_branch(locked)["ahead"]["skip"], "forge unavailable")
        facts = ForgeFacts(
            merged_heads={
                git(self.repo, "rev-parse", ref): 9 for ref in ("ahead", "origin/ahead")
            },
            open_heads={},
        )
        with (
            patch.object(tree, "secret_service_token", return_value=("t0ken", None)),
            patch.object(tree, "facts_with_token", return_value=facts) as live,
        ):
            first = self._by_branch(self._entry())
            second = self._by_branch(self._entry())
            self.assertEqual(live.call_count, 1)
            with patch.object(tree, "now", return_value=time.time() + 601):
                self._entry()
            self.assertEqual(live.call_count, 2)
        self.assertEqual(
            (first["ahead"]["merged_by"], second["ahead"]["merged_by"]),
            ("pr#9", "pr#9"),
        )
        data = json.loads(self._tree())
        self.assertEqual(
            (data["delete_ready"], data["delete_reason"]),
            (False, "Secret Service locked"),
        )
        self.assertEqual(data["repos"][0]["forge"], "cached")
        with patch.object(tree, "secret_service_token", return_value=("t0ken", None)):
            self.assertTrue(json.loads(self._tree())["delete_ready"])

    def test_an_unwritable_cache_keeps_the_scan_and_names_it(self) -> None:
        git(self.repo, "remote", "set-url", "origin", "https://github.com/me/repo.git")
        blocker = os.path.join(self.root, "cache-is-a-file")
        self._write(self.root, "cache-is-a-file", "")
        with (
            patch.dict(os.environ, {"XDG_CACHE_HOME": blocker}),
            patch.object(tree, "secret_service_token", return_value=("t0ken", None)),
            patch.object(tree, "facts_with_token", return_value=ForgeFacts()),
        ):
            entry = self._entry()
        self.assertTrue(entry["forge"].startswith("live: cache not written"))
        self.assertIn("main", self._by_branch(entry))

    def test_branch_actions_rewrite_the_tree_file_when_it_exists(self) -> None:
        tree.branch_tree(
            [self.repo], fmt="json", output=self.tree_file, worktrees_root=self.shared
        )
        args = create_parser("test").parse_args(["branch", "open", "fresh"])
        cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)
        handle_branch(args, ctx=None)
        with open(self.tree_file, encoding="utf-8") as fh:
            entry = json.load(fh)["repos"][0]
        self.assertIn("fresh", [item["branch"] for item in entry["items"]])


if __name__ == "__main__":
    unittest.main()
