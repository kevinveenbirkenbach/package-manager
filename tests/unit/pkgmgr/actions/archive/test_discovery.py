"""Unit tests for `pkgmgr.actions.archive.discovery`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pkgmgr.actions.archive.discovery import iter_archivable_files


class TestIterArchivableFiles(unittest.TestCase):
    def test_only_numbered_markdown_files_are_returned_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001-alpha.md").write_text("# 001 - A")
            (d / "002-beta.md").write_text("# 002 - B")
            (d / "README.md").write_text("# X")
            (d / "notes.md").write_text("# X")
            (d / "001-alpha.txt").write_text("x")

            result = [p.name for p in iter_archivable_files(d, include_template=True)]
            self.assertEqual(result, ["001-alpha.md", "002-beta.md"])

    def test_template_is_skipped_unless_opted_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "000-template.md").write_text("# 000 - Template")
            (d / "001-alpha.md").write_text("# 001 - A")

            self.assertEqual(
                [p.name for p in iter_archivable_files(d, include_template=False)],
                ["001-alpha.md"],
            )
            self.assertEqual(
                [p.name for p in iter_archivable_files(d, include_template=True)],
                ["000-template.md", "001-alpha.md"],
            )

    def test_missing_directory_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                iter_archivable_files(Path(tmp) / "missing", include_template=False),
                [],
            )


if __name__ == "__main__":
    unittest.main()
