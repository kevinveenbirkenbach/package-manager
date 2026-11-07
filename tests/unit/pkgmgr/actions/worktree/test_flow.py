from __future__ import annotations

import os
import stat
import tempfile
import unittest
from unittest.mock import patch

import yaml

from pkgmgr.actions.worktree import flow

PULL = ["origin/main", "store-i18n"]
PUSH = ["feature/iam-profile-rbac", "production"]
PLANTED = {"version": 1, "branch": "x", "pull": ["planted"], "push": ["planted"]}


class TestFlowFile(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.git_dir = os.path.realpath(tmp.name)
        self.folder = os.path.join(self.git_dir, flow.FLOW_DIR)
        self.file = os.path.join(self.folder, flow.FLOW_FILE)

    def _plant(self, data: bytes) -> None:
        os.makedirs(self.folder, exist_ok=True)
        with open(self.file, "wb") as fh:
            fh.write(data)

    def _outside(self, name: str) -> str:
        target = os.path.join(self.git_dir, name)
        with open(target, "w", encoding="utf-8") as fh:
            yaml.safe_dump(PLANTED, fh)
        return target

    def _invalid(self) -> str:
        found = flow.read_flow(self.git_dir)
        self.assertEqual(
            (found.source, found.branch, found.pull, found.push),
            ("invalid", None, [], []),
        )
        self.assertEqual(len(found.warnings), 1)
        self.assertTrue(found.warnings[0].startswith("pkgmgr/flow.yml ignored: "))
        return found.warnings[0]

    def test_round_trip_keeps_order_modes_and_schema(self) -> None:
        flow.write_flow(self.git_dir, "feature/x", PULL, PUSH)

        found = flow.read_flow(self.git_dir)
        self.assertEqual(
            (found.source, found.branch, found.pull, found.push, found.warnings),
            ("file", "feature/x", PULL, PUSH, []),
        )
        self.assertEqual(stat.S_IMODE(os.stat(self.folder).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(self.file).st_mode), 0o600)
        self.assertEqual(os.listdir(self.folder), [flow.FLOW_FILE])
        with open(self.file, encoding="utf-8") as fh:
            self.assertEqual(
                yaml.safe_load(fh),
                {"version": 1, "branch": "feature/x", "pull": PULL, "push": PUSH},
            )

    def test_missing_file_reads_as_none(self) -> None:
        self.assertEqual(flow.read_flow(self.git_dir), flow.Flow())
        os.makedirs(self.folder)
        self.assertEqual(flow.read_flow(self.git_dir).source, "none")

    def test_symlinked_file_is_never_followed(self) -> None:
        os.makedirs(self.folder)
        os.symlink(self._outside("planted.yml"), self.file)

        self._invalid()

    def test_symlinked_folder_is_never_followed_or_written(self) -> None:
        real = os.path.join(self.git_dir, "real")
        os.makedirs(real)
        os.rename(self._outside("planted.yml"), os.path.join(real, flow.FLOW_FILE))
        os.symlink(real, self.folder)

        self._invalid()
        with self.assertRaises(OSError):
            flow.write_flow(self.git_dir, None, [], [])
        with self.assertRaises(OSError):
            flow.clear_flow(self.git_dir)
        self.assertEqual(os.listdir(real), [flow.FLOW_FILE])
        with open(os.path.join(real, flow.FLOW_FILE), encoding="utf-8") as fh:
            self.assertEqual(yaml.safe_load(fh), PLANTED)

    def test_write_and_clear_replace_a_symlink_never_its_target(self) -> None:
        target = self._outside("victim.yml")
        os.makedirs(self.folder)
        os.symlink(target, self.file)

        flow.write_flow(self.git_dir, "x", ["main"], [])
        self.assertFalse(os.path.islink(self.file))
        self.assertEqual(flow.read_flow(self.git_dir).pull, ["main"])
        os.unlink(self.file)
        os.symlink(target, self.file)
        flow.clear_flow(self.git_dir)

        self.assertFalse(os.path.lexists(self.file))
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(yaml.safe_load(fh), PLANTED)

    def test_clear_without_a_file_is_a_no_op(self) -> None:
        flow.clear_flow(self.git_dir)
        flow.write_flow(self.git_dir, "x", PULL, PUSH)
        flow.clear_flow(self.git_dir)
        flow.clear_flow(self.git_dir)
        self.assertEqual(flow.read_flow(self.git_dir), flow.Flow())

    def test_oversized_file_reads_as_invalid(self) -> None:
        self._plant(b"version: 1\npull: []\npush: []\n" + b"#" * flow.MAX_BYTES)
        self.assertIn("larger than", self._invalid())

    def test_fifo_reads_as_invalid_without_blocking(self) -> None:
        os.makedirs(self.folder)
        os.mkfifo(self.file)
        self.assertIn("not a regular file", self._invalid())

    def test_directory_reads_as_invalid(self) -> None:
        os.makedirs(self.file)
        self.assertIn("not a regular file", self._invalid())

    def test_malformed_files_read_as_invalid(self) -> None:
        lists = "pull: []\npush: []\n"
        cases = {
            "yaml": b"pull: [\n",
            "not a mapping": b"- main\n",
            "unknown key": f"version: 1\n{lists}extra: 1\n".encode(),
            "missing key": b"version: 1\npull: []\n",
            "bool version": f"version: true\n{lists}".encode(),
            "other version": f"version: 2\n{lists}".encode(),
            "string list": b"version: 1\npull: main\npush: []\n",
            "number entry": b"version: 1\npull: [1]\npush: []\n",
            "option entry": b"version: 1\npull: ['--output=/tmp/x']\npush: []\n",
            "range entry": b"version: 1\npull: []\npush: [a..b]\n",
            "bad branch": f"version: 1\nbranch: -x\n{lists}".encode(),
            "nesting": b"[" * 30000,
            "binary": b"\xff\xfe",
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                self._plant(data)
                self._invalid()


class TestNames(unittest.TestCase):
    def test_branch_and_remote_tracking_names_pass_in_order(self) -> None:
        self.assertEqual(flow.check_names("pull", PULL + ["@"]), PULL + ["@"])

    def test_invalid_names_are_refused(self) -> None:
        for name in ("-x", "a..b", "--output=/tmp/x", "", "HEAD", "a b", "x\0y", 1):
            with self.subTest(name=name), self.assertRaises(flow.FlowError):
                flow.check_name("pull", name)
        with self.assertRaises(flow.FlowError):
            flow.check_names("push", "main")

    def test_option_like_names_never_reach_git(self) -> None:
        with patch.object(flow, "run") as run, self.assertRaises(flow.FlowError):
            flow.check_name("pull", "--output=/tmp/x")
        run.assert_not_called()

    def test_mismatch_warns_only_for_a_file_of_another_branch(self) -> None:
        found = flow.Flow(branch="a", source="file")
        self.assertEqual(flow.mismatch(found, "a"), [])
        self.assertEqual(
            flow.mismatch(found, None),
            ["flow was set on a, the worktree is on a detached HEAD"],
        )
        self.assertEqual(flow.mismatch(flow.Flow(source="invalid"), "a"), [])


if __name__ == "__main__":
    unittest.main()
