from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from pkgmgr.actions.worktree import up
from pkgmgr.cli.commands.worktree import handle_worktree
from pkgmgr.cli.parser import create_parser
from tests.integration.test_branch_gc import GcFixture, git

PULL = ["origin/main", "store-i18n"]
PUSH = ["feature/iam-profile-rbac", "production"]


class FlowFixture(GcFixture):
    def setUp(self) -> None:
        super().setUp()
        self.linked_git_dir = os.path.join(self.repo, ".git", "worktrees", "wt-merged")
        self.linked_file = os.path.join(self.linked_git_dir, "pkgmgr", "flow.yml")
        self.addCleanup(os.chdir, os.getcwd())

    def _cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        args = create_parser("test").parse_args(["worktree", *argv])
        with (
            patch("pkgmgr.cli.commands.worktree.refresh_tree") as self.refresh,
            redirect_stdout(out),
            redirect_stderr(err),
            self.assertRaises(SystemExit) as done,
        ):
            handle_worktree(args, SimpleNamespace())
        return done.exception.code, out.getvalue(), err.getvalue()

    def _json(self, *argv: str) -> dict:
        code, out, err = self._cli(*argv, "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)


class TestFlowCli(FlowFixture, unittest.TestCase):
    def test_set_show_clear_json_on_a_linked_worktree(self) -> None:
        argv = [f"--pull={ref}" for ref in PULL] + [f"--push={b}" for b in PUSH]
        expected = {
            "worktree": self.merged_wt,
            "git_dir": self.linked_git_dir,
            "branch": "merged",
            "flow_branch": "merged",
            "pull": PULL,
            "push": PUSH,
            "source": "file",
            "warnings": [],
        }

        self.assertEqual(self._json("flow", "set", self.merged_wt, *argv), expected)
        self.refresh.assert_called_once_with([self.repo])
        self.assertEqual(self._json("flow", self.merged_wt), expected)
        self.assertTrue(os.path.isfile(self.linked_file))
        self.assertEqual(git(self.merged_wt, "status", "--porcelain"), "")
        cleared = self._json("flow", "clear", self.merged_wt)

        self.assertEqual(
            {**expected, "flow_branch": None, "pull": [], "push": [], "source": "none"},
            cleared,
        )
        self.assertFalse(os.path.exists(self.linked_file))

    def test_set_show_clear_text_on_the_main_worktree(self) -> None:
        os.chdir(self.repo)

        code, out, _ = self._cli("flow", "set", "--pull", "origin/main", "--no-push")
        self.assertEqual((code, out), (0, "pull: origin/main\npush: (none)\n"))
        self.assertEqual(
            self._cli("flow")[:2], (0, "pull: origin/main\npush: (none)\n")
        )
        shown = self._json("flow")
        self.assertEqual(
            (shown["worktree"], shown["git_dir"], shown["branch"]),
            (self.repo, os.path.join(self.repo, ".git"), "main"),
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.repo, ".git", "pkgmgr", "flow.yml"))
        )
        self.assertEqual(
            self._cli("flow", "clear")[:2], (0, "pull: (none)\npush: (none)\n")
        )

    def test_show_without_a_flow_succeeds_empty(self) -> None:
        shown = self._json("flow", self.merged_wt)
        self.assertEqual(
            (shown["source"], shown["flow_branch"], shown["pull"], shown["push"]),
            ("none", None, [], []),
        )
        self.assertEqual(shown["warnings"], [])

    def test_invalid_names_exit_2_and_write_nothing(self) -> None:
        escape = os.path.join(self.root, "escape")
        for bad in ("-x", "a..b", f"--output={escape}"):
            for flag, other in (("--pull", "--push"), ("--push", "--pull")):
                with self.subTest(bad=bad, flag=flag):
                    code, out, err = self._cli(
                        "flow", "set", self.merged_wt, f"{flag}={bad}", f"{other}=main"
                    )
                    self.assertEqual((code, out), (2, ""))
                    self.assertIn("is not a valid branch name", err)
        self.assertFalse(os.path.exists(os.path.join(self.linked_git_dir, "pkgmgr")))
        self.assertFalse(os.path.exists(escape))

    def test_usage_errors_exit_2_and_write_nothing(self) -> None:
        cases = (
            ("flow", "set", self.merged_wt, "--pull", "main"),
            ("flow", "set", self.merged_wt, "--pull", "main", "--no-pull", "--no-push"),
            ("flow", self.merged_wt, "--push", "main"),
            ("flow", "clear", self.merged_wt, "--no-pull"),
            ("flow", "show", self.merged_wt),
        )
        for argv in cases:
            with self.subTest(argv=argv[1:]):
                self.assertEqual(self._cli(*argv)[:2], (2, ""))
        self.assertFalse(os.path.exists(os.path.join(self.linked_git_dir, "pkgmgr")))

    def test_a_path_that_is_no_worktree_exits_2(self) -> None:
        absent = os.path.join(self.root, "absent")
        for path in (self.root, self.origin, absent):
            for argv in (
                ("flow", path),
                ("flow", "set", path, "--no-pull", "--no-push"),
            ):
                with self.subTest(argv=argv):
                    code, out, err = self._cli(*argv)
                    self.assertEqual((code, out), (2, ""))
                    self.assertIn("is not a git worktree", err)
        self.assertFalse(os.path.exists(os.path.join(self.origin, "pkgmgr")))

    def test_another_branch_warns_of_the_mismatch(self) -> None:
        self._json("flow", "set", self.merged_wt, "--pull", "main", "--push", "main")
        git(self.merged_wt, "checkout", "--quiet", "-b", "renamed")

        shown = self._json("flow", self.merged_wt)
        self.assertEqual(
            (shown["branch"], shown["flow_branch"], shown["source"], shown["pull"]),
            ("renamed", "merged", "file", ["main"]),
        )
        warning = "flow was set on merged, the worktree is on renamed"
        self.assertEqual(shown["warnings"], [warning])
        self.assertEqual(
            self._cli("flow", self.merged_wt)[1],
            f"WARN     {warning}\npull: main\npush: main\n",
        )

    def test_a_planted_symlink_reads_invalid_and_set_replaces_it(self) -> None:
        target = os.path.join(self.root, "planted.yml")
        with open(target, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"version": 1, "pull": ["planted"], "push": []}, fh)
        os.makedirs(os.path.dirname(self.linked_file))
        os.symlink(target, self.linked_file)

        shown = self._json("flow", self.merged_wt)
        self.assertEqual(
            (shown["source"], shown["pull"], shown["push"]), ("invalid", [], [])
        )
        self.assertTrue(shown["warnings"][0].startswith("pkgmgr/flow.yml ignored: "))
        self._json("flow", "set", self.merged_wt, "--pull", "main", "--no-push")
        self.assertFalse(os.path.islink(self.linked_file))
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(yaml.safe_load(fh)["pull"], ["planted"])


class TestUpFlow(FlowFixture, unittest.TestCase):
    def _up(
        self,
        branch: str,
        pull: list[str] | None,
        push: list[str] | None,
        base: str | None = None,
    ) -> tuple[int, dict]:
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = up.worktree_up(
                self.repo,
                branch,
                base=base,
                worktrees_dir=os.path.join(self.root, "wts"),
                path=None,
                hooks={},
                as_json=True,
                pull=pull,
                push=push,
            )
        return code, json.loads(out.getvalue()) if code != 2 else {}

    def _shown(self, path: str) -> tuple:
        shown = self._json("flow", path)
        return shown["source"], shown["flow_branch"], shown["pull"], shown["push"]

    def test_without_lists_the_flow_is_the_base(self) -> None:
        code, result = self._up("feature/d", None, None)

        self.assertEqual(code, 0)
        self.assertEqual(result["flow"], {"pull": ["origin/main"], "push": ["main"]})
        self.assertEqual(
            self._shown(result["path"]),
            ("file", "feature/d", ["origin/main"], ["main"]),
        )

    def test_given_lists_replace_the_base_each_on_its_own(self) -> None:
        _, both = self._up("feature/b", PULL, PUSH, base="origin/main")
        _, one = self._up("feature/o", None, ["production"])

        self.assertEqual(self._shown(both["path"]), ("file", "feature/b", PULL, PUSH))
        self.assertEqual(one["flow"], {"pull": ["origin/main"], "push": ["production"]})

    def test_a_base_that_is_no_branch_name_sets_no_flow(self) -> None:
        code, result = self._up("feature/c", None, None, base="main~0")

        self.assertEqual((code, result["flow"]), (0, None))
        self.assertIn("flow not set: base 'main~0'", " ".join(result["warnings"]))
        self.assertEqual(self._shown(result["path"])[0], "none")

    def test_invalid_names_refuse_before_the_checkout(self) -> None:
        escape = os.path.join(self.root, "escape")
        for pull, push in (
            (["-x"], None),
            (None, ["a..b"]),
            ([f"--output={escape}"], None),
        ):
            with self.subTest(pull=pull, push=push):
                self.assertEqual(self._up("feature/i", pull, push)[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "wts")))
        self.assertFalse(os.path.exists(escape))
        self.assertEqual(git(self.repo, "branch", "--list", "feature/i"), "")

    def test_up_parses_repeatable_lists(self) -> None:
        args = create_parser("test").parse_args(
            ["worktree", "up", "feature/x", "--pull", "a", "--pull", "b", "--push", "c"]
        )
        self.assertEqual((args.pull, args.push), (["a", "b"], ["c"]))


if __name__ == "__main__":
    unittest.main()
