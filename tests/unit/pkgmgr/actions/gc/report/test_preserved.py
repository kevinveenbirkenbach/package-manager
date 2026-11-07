from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from pkgmgr.actions.gc.report import preserved as module

HEAD_BLOB = "1" * 40
INDEX_BLOB = "2" * 40
STATUS = "\0".join(
    [
        f"1 .M N... 100644 100644 100644 {HEAD_BLOB} {INDEX_BLOB} dir/a file.txt",
        " ".join(
            ["u UU N...", *["100644"] * 4, HEAD_BLOB, INDEX_BLOB, HEAD_BLOB, "c.txt"]
        ),
        "? new file",
        "",
    ]
)


class TestPreservedParsing(unittest.TestCase):
    def test_status_records_keep_paths_with_spaces(self) -> None:
        with patch.object(module, "_git", return_value=STATUS):
            entries = module._status_entries("/wt")

        self.assertEqual(
            entries,
            [
                ("dir/a file.txt", INDEX_BLOB),
                ("c.txt", module.UNMERGED),
                ("new file", None),
            ],
        )

    def test_blob_must_sit_at_the_same_path_of_some_tip(self) -> None:
        wanted = [("a", {HEAD_BLOB}), ("b", {HEAD_BLOB, INDEX_BLOB})]
        answer = f"{HEAD_BLOB}\nt2:a missing\n{HEAD_BLOB}\nt2:b missing"

        with patch.object(module, "run", return_value=answer) as run:
            absent = module._absent("/repo", ["t1", "t2"], wanted)

        self.assertEqual(absent, ["b"])
        self.assertEqual(run.call_args.kwargs["input_text"], "t1:a\nt2:a\nt1:b\nt2:b\n")

    def test_special_files_are_never_opened(self) -> None:
        with tempfile.TemporaryDirectory() as tree:
            os.mkfifo(os.path.join(tree, "fifo"))
            os.mkdir(os.path.join(tree, "sub"))

            with patch.object(module, "run") as run:
                hashes = module._hashes(tree, ["fifo", "gone", "sub"])

        run.assert_not_called()
        self.assertEqual(
            hashes,
            {"fifo": module.SPECIAL, "gone": module.DELETED, "sub": module.DIRECTORY},
        )

    def test_no_tips_means_nothing_is_preserved(self) -> None:
        with patch.object(module, "run") as run:
            self.assertEqual(module._absent("/repo", [], [("a", {HEAD_BLOB})]), ["a"])

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
