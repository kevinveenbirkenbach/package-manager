from __future__ import annotations

import os
import tempfile
import unittest

from pkgmgr.actions.gc.report.roots import scan_root

THRESHOLD = 16 * 1024
ET_CORE_HEADER = b"\x7fELF\x02\x01\x01" + bytes(9) + (4).to_bytes(2, "little")


class TestScanRoot(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, size: int = 0, head: bytes = b"") -> str:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(head + b"d" * size)
        return path

    def _big(self, rel: str, size: int = 64 * 1024) -> str:
        return self._write(rel, size)

    def test_children_over_threshold_get_kinds_biggest_first(self) -> None:
        self._big("node_modules/pkg/index.js", 200 * 1024)
        self._big("wt/data", 180 * 1024)
        self._write("wt/.git", head=b"gitdir: /elsewhere\n")
        self._big("clone/.git/objects/pack", 160 * 1024)
        self._big("bare.git/objects/blob", 140 * 1024)
        self._write("bare.git/HEAD", head=b"ref: refs/heads/main\n")
        self._big("venv/lib/site.py", 120 * 1024)
        self._write("venv/pyvenv.cfg", head=b"home = /usr\n")
        self._big(".cache/blob", 100 * 1024)
        self._big("tagged/blob", 90 * 1024)
        self._write("tagged/CACHEDIR.TAG", head=b"Signature: x\n")
        self._big("plain/blob", 80 * 1024)
        self._write("core", 70 * 1024, head=ET_CORE_HEADER)
        self._big("loose.bin", 60 * 1024)
        self._write("small/file", 10)
        cores: list[str] = []

        scanned = scan_root(self.root, THRESHOLD, cores)

        kinds = [(os.path.basename(c["path"]), c["kind"]) for c in scanned["children"]]
        self.assertEqual(
            kinds,
            [
                ("node_modules", "node_modules"),
                ("wt", "worktree"),
                ("clone", "git-repo"),
                ("bare.git", "git-repo"),
                ("venv", "venv"),
                (".cache", "cache"),
                ("tagged", "cache"),
                ("plain", "dir"),
                ("core", "core-dump"),
                ("loose.bin", "file"),
            ],
        )
        self.assertEqual(scanned["root"], self.root)
        self.assertEqual(cores, [os.path.join(self.root, "core")])
        sizes = [c["size_bytes"] for c in scanned["children"]]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertTrue(all(c["newest_mtime"] > 0 for c in scanned["children"]))

    def test_missing_root_raises(self) -> None:
        with self.assertRaises(OSError):
            scan_root(os.path.join(self.root, "absent"), THRESHOLD, [])


if __name__ == "__main__":
    unittest.main()
