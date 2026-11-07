from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from pkgmgr.actions.gc.report import walk as walk_module
from pkgmgr.actions.gc.report.walk import BLOCK, walk


def allocated(*paths: str) -> int:
    return sum(os.lstat(path).st_blocks * BLOCK for path in paths)


class TestWalk(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, data: bytes = b"x") -> str:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def test_sparse_file_counts_allocated_blocks_only(self) -> None:
        path = self._write("sparse")
        os.truncate(path, 1 << 30)

        stats = walk(self.root)

        self.assertEqual(stats.size_bytes, allocated(self.root, path))
        self.assertLess(stats.size_bytes, 1 << 30)

    def test_symlink_target_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            target = os.path.join(outside, "big")
            with open(target, "wb") as fh:
                fh.write(b"y" * (1 << 20))
            link = os.path.join(self.root, "link")
            os.symlink(target, link)

            stats = walk(self.root)

        self.assertEqual(stats.size_bytes, allocated(self.root, link))
        self.assertLess(stats.size_bytes, 1 << 20)

    def test_hard_link_is_counted_once(self) -> None:
        first = self._write("a", b"z" * 65536)
        os.link(first, os.path.join(self.root, "b"))

        self.assertEqual(walk(self.root).size_bytes, allocated(self.root, first))

    def test_foreign_entries_are_pruned_below_the_first_foreign_one(self) -> None:
        self._write("foreign_dir/one")
        self._write("foreign_dir/sub/two")
        self._write("foreign_file")
        self._write("mine")
        plain = walk(self.root)

        with patch.object(
            walk_module,
            "is_foreign",
            side_effect=lambda path, st: os.path.relpath(path, self.root).startswith(
                "foreign"
            ),
        ):
            stats = walk(self.root)

        self.assertEqual(plain.foreign_entries, 0)
        self.assertEqual(stats.foreign_entries, 2)
        self.assertEqual(stats.size_bytes, plain.size_bytes)

    def test_files_named_like_core_dumps_are_candidates(self) -> None:
        expected = {self._write("core"), self._write("deep/core.123")}
        self._write("core.abc")
        self._write("not-core")
        os.makedirs(os.path.join(self.root, "dir", "core"))

        self.assertEqual(set(walk(self.root).cores), expected)

    @unittest.skipIf(os.getuid() == 0, "root lists every directory")
    def test_unlistable_directory_is_counted(self) -> None:
        locked = os.path.join(self.root, "locked")
        os.mkdir(locked)
        os.chmod(locked, 0)
        try:
            stats = walk(self.root)
        finally:
            os.chmod(locked, 0o700)

        self.assertEqual(stats.unreadable, 1)

    def test_missing_path_reports_unreadable(self) -> None:
        stats = walk(os.path.join(self.root, "absent"))

        self.assertEqual((stats.size_bytes, stats.unreadable), (0, 1))

    def test_other_filesystem_is_skipped(self) -> None:
        self._write("file")

        stats = walk(self.root, dev=os.lstat(self.root).st_dev + 1)

        self.assertEqual(stats.size_bytes, 0)


if __name__ == "__main__":
    unittest.main()
