from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import ANY, patch

from pkgmgr.actions.gc.report.core_dumps import (
    ELF_HEADER,
    ET_CORE,
    core_dumps,
    is_core_dump,
)

ET_EXEC = 2


def elf(e_type: int, order: str = "little") -> bytes:
    data = 1 if order == "little" else 2
    return b"\x7fELF" + bytes([2, data, 1]) + bytes(9) + e_type.to_bytes(2, order)


class TestCoreDumps(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _file(self, name: str, data: bytes, size: int | None = None) -> str:
        path = os.path.join(self.root, name)
        with open(path, "wb") as fh:
            fh.write(data + bytes(46))
        if size is not None:
            os.truncate(path, size)
        return path

    def test_et_core_is_detected_in_both_byte_orders(self) -> None:
        self.assertTrue(is_core_dump(self._file("core", elf(ET_CORE))))
        self.assertTrue(is_core_dump(self._file("core.1", elf(ET_CORE, "big"))))

    def test_other_elf_types_and_non_elf_are_ignored(self) -> None:
        self.assertFalse(is_core_dump(self._file("core", elf(ET_EXEC))))
        self.assertFalse(is_core_dump(self._file("core.2", b"#!/bin/sh\n")))
        short = os.path.join(self.root, "core.3")
        with open(short, "wb") as fh:
            fh.write(b"\x7fELF")
        self.assertFalse(is_core_dump(short))

    def test_symlink_is_not_followed(self) -> None:
        target = self._file("real", elf(ET_CORE))
        link = os.path.join(self.root, "core")
        os.symlink(target, link)

        self.assertFalse(is_core_dump(link))

    def test_reads_no_more_than_the_elf_header(self) -> None:
        path = self._file("core", elf(ET_CORE), size=1 << 20)

        with patch("os.read", wraps=os.read) as read:
            is_core_dump(path)

        read.assert_called_once_with(ANY, ELF_HEADER)

    def test_sparse_dump_is_sized_by_blocks_and_others_dropped(self) -> None:
        dump = self._file("core", elf(ET_CORE), size=1 << 30)
        binary = self._file("core.7", elf(ET_EXEC))

        dumps = core_dumps([dump, binary, dump])

        self.assertEqual([d["path"] for d in dumps], [dump])
        self.assertEqual(dumps[0]["apparent_bytes"], 1 << 30)
        self.assertLess(dumps[0]["size_bytes"], dumps[0]["apparent_bytes"])
        self.assertEqual(dumps[0]["mtime"], os.lstat(dump).st_mtime)


if __name__ == "__main__":
    unittest.main()
