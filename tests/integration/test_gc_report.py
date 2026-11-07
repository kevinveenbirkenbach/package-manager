from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.gc.report import disk_report, render_text
from pkgmgr.actions.gc.report import docker_usage as docker_module
from pkgmgr.actions.gc.report import walk as walk_module
from pkgmgr.cli.commands.worktree import handle_gc
from pkgmgr.cli.parser import create_parser

GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
THRESHOLD = 32 * 1024
ELF_CORE = b"\x7fELF\x02\x01\x01" + bytes(9) + (4).to_bytes(2, "little")
ELF_EXEC = b"\x7fELF\x02\x01\x01" + bytes(9) + (2).to_bytes(2, "little")
DOCKER_DF = (
    '{"Active":"1","Reclaimable":"0B","Size":"1GB","TotalCount":"3","Type":"Images"}\n'
)


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True, text=True
    ).stdout


def write(path: str, data: bytes | str, size: int | None = None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data.encode() if isinstance(data, str) else data)
    if size is not None:
        os.truncate(path, size)
    return path


class TestDiskReport(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(self.tmp, "repo")
        git(self.tmp, "init", "-q", "-b", "main", self.repo)
        write(os.path.join(self.repo, "a.txt"), "base")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "checkout", "-q", "-b", "other")
        write(os.path.join(self.repo, "a.txt"), "kept")
        write(os.path.join(self.repo, "b.txt"), "kept-b")
        git(self.repo, "add", "a.txt", "b.txt")
        git(self.repo, "commit", "-q", "-m", "other")
        git(self.repo, "checkout", "-q", "main")

        self.clean = self._worktree("wt-clean", "-b", "clean")
        self.kept = self._worktree("wt-kept", "-b", "kept")
        write(os.path.join(self.kept, "a.txt"), "kept")
        git(self.kept, "add", "a.txt")
        write(os.path.join(self.kept, "b.txt"), "kept-b")
        self.lost = self._worktree("wt-lost", "-b", "lost")
        write(os.path.join(self.lost, "new.txt"), "only here")
        self.detached = self._worktree("wt-detached", "--detach")
        write(os.path.join(self.detached, "c.txt"), "c")
        git(self.detached, "add", "c.txt")
        git(self.detached, "commit", "-q", "-m", "unreachable")
        write(os.path.join(self.detached, "a.txt"), "kept")
        agents = os.path.join(self.repo, ".claude", "worktrees")
        self.agent = self._worktree(os.path.join(agents, "agent-y"), "-b", "agent-y")
        self.orphan = os.path.join(agents, "agent-x")
        write(os.path.join(self.orphan, "notes.txt"), "left behind")

        self.root = os.path.join(self.tmp, "root")
        self.dump = write(
            os.path.join(self.root, "core"), ELF_CORE + b"c" * 64 * 1024, 1 << 30
        )
        self.binary = write(
            os.path.join(self.root, "core.12"), ELF_EXEC + b"e" * 64 * 1024
        )
        write(os.path.join(self.root, "bigdir", "blob"), b"b" * 128 * 1024)
        write(os.path.join(self.root, "small"), "s")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _worktree(self, name: str, *args: str) -> str:
        path = os.path.join(self.tmp, name)
        git(self.repo, "worktree", "add", "-q", *args, path, "main")
        return path

    def _report(self) -> dict:
        with patch.object(docker_module, "_docker", return_value=DOCKER_DF):
            return disk_report([self.root], [self.repo], THRESHOLD, docker=True)

    def _cli(self, *argv: str) -> tuple[int, str]:
        args = create_parser("test").parse_args(["gc", *argv])
        out = io.StringIO()
        with (
            patch("pkgmgr.cli.commands.branch.main_repo_root", return_value=self.repo),
            patch(
                "pkgmgr.cli.commands.branch.cleanup",
                side_effect=AssertionError("the report must not run a cleanup"),
            ),
            patch.object(docker_module, "_docker", return_value=DOCKER_DF),
            redirect_stdout(out),
            self.assertRaises(SystemExit) as stop,
        ):
            handle_gc(args, None)
        return stop.exception.code, out.getvalue()

    def test_cli_report_prints_the_json_inventory(self) -> None:
        code, out = self._cli("--report", "--json", "--root", self.root, "--docker")
        report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertIn(self.dump, [dump["path"] for dump in report["core_dumps"]])
        self.assertIn(self.lost, [tree["path"] for tree in report["worktrees"]])
        self.assertIsNotNone(report["docker"])

    def test_cli_report_refuses_apply(self) -> None:
        self.assertEqual(self._cli("--report", "--apply"), (2, ""))

    def test_worktrees_and_orphaned_agent_dir(self) -> None:
        trees = {t["path"]: t for t in self._report()["worktrees"]}

        expected = {
            self.clean,
            self.kept,
            self.lost,
            self.detached,
            self.agent,
            self.orphan,
        }
        self.assertEqual(set(trees), expected)
        self.assertTrue(trees[self.orphan]["orphaned"])
        self.assertFalse(trees[self.agent]["orphaned"])
        self.assertEqual(trees[self.kept]["branch"], "kept")
        self.assertIsNone(trees[self.detached]["branch"])
        for tree in trees.values():
            self.assertGreater(tree["size_bytes"], 0)
            self.assertIsNotNone(tree["last_activity"])
            self.assertEqual(tree["foreign_entries"], 0)

    def test_foreign_entries_through_patched_owner_check(self) -> None:
        with patch.object(
            walk_module,
            "is_foreign",
            side_effect=lambda path, st: os.path.basename(path) == "new.txt",
        ):
            trees = {t["path"]: t for t in self._report()["worktrees"]}

        self.assertEqual(trees[self.lost]["foreign_entries"], 1)
        self.assertEqual(trees[self.clean]["foreign_entries"], 0)

    def test_preserved_verdicts_and_nothing_written(self) -> None:
        before = git(self.kept, "status", "--porcelain=v2", "--untracked-files=all")

        verdicts = {p["path"]: p for p in self._report()["preserved"]}

        self.assertEqual(set(verdicts), {self.kept, self.lost, self.detached})
        self.assertTrue(verdicts[self.kept]["preserved"])
        self.assertEqual(verdicts[self.kept]["paths"], 2)
        self.assertFalse(verdicts[self.lost]["preserved"])
        self.assertEqual(verdicts[self.lost]["reasons"], ["new.txt: content in no ref"])
        self.assertFalse(verdicts[self.detached]["preserved"])
        self.assertEqual(
            verdicts[self.detached]["reasons"], ["detached HEAD reachable from no ref"]
        )
        after = git(self.kept, "status", "--porcelain=v2", "--untracked-files=all")
        self.assertEqual(before, after)

    def test_roots_core_dumps_docker_and_balance(self) -> None:
        report = self._report()

        children = report["roots"][0]["children"]
        self.assertEqual(
            [(os.path.basename(c["path"]), c["kind"]) for c in children],
            [("bigdir", "dir"), ("core", "core-dump"), ("core.12", "file")],
        )
        self.assertEqual([d["path"] for d in report["core_dumps"]], [self.dump])
        dump = report["core_dumps"][0]
        self.assertEqual(dump["apparent_bytes"], 1 << 30)
        self.assertLess(dump["size_bytes"], dump["apparent_bytes"])
        self.assertEqual(report["docker"][0]["total"], 3)
        self.assertEqual(len(report["balance"]), 1)
        listed = sum(c["size_bytes"] for c in children)
        listed += sum(t["size_bytes"] for t in report["worktrees"])
        self.assertEqual(report["balance"][0]["attributed_bytes"], listed)
        self.assertEqual(report["warnings"], [])
        json.dumps(report)
        text = render_text(report)
        self.assertIn("orphaned", text)
        self.assertIn("core-dump", text)

    def test_unknown_repo_and_root_are_warnings(self) -> None:
        missing = os.path.join(self.tmp, "absent")

        report = disk_report([missing], [self.root], THRESHOLD, docker=False)

        self.assertEqual(report["worktrees"], [])
        self.assertIsNone(report["docker"])
        self.assertEqual(len(report["warnings"]), 2)


if __name__ == "__main__":
    unittest.main()
