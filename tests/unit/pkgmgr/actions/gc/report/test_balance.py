from __future__ import annotations

import os
import tempfile
import unittest

from pkgmgr.actions.gc.report.balance import balance


class TestBalance(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        for rel in ("a/b", "c", "a-x"):
            os.makedirs(os.path.join(self.root, rel))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _path(self, rel: str) -> str:
        return os.path.join(self.root, rel)

    def test_nested_and_repeated_items_count_once(self) -> None:
        items = [
            (self._path("a/b"), 50),
            (self._path("a"), 100),
            (self._path("a-x"), 7),
            (self._path("c"), 10),
            (self._path("c"), 10),
            (self._path("gone"), 1000),
        ]

        rows = balance([self.root, self.root], items)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["attributed_bytes"], 117)
        self.assertTrue(os.path.ismount(row["filesystem"]))
        self.assertGreater(row["total_bytes"], 0)
        self.assertLessEqual(row["free_bytes"], row["total_bytes"])

    def test_unreadable_paths_get_no_row(self) -> None:
        self.assertEqual(balance([self._path("gone")], []), [])


if __name__ == "__main__":
    unittest.main()
