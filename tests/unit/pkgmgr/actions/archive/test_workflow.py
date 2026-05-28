"""Unit tests for `pkgmgr.actions.archive.workflow.run_archive`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pkgmgr.actions.archive.workflow import run_archive


class TestRunArchive(unittest.TestCase):
    def test_dry_run_does_not_touch_files_or_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            done = d / "001-done.md"
            done.write_text("# 001 - Done\n\n- [x] ok\n")
            readme = d / "README.md"
            readme.write_text("# Specs\n\n## Archive\n")

            plan = run_archive(d, readme, dry_run=True)

            self.assertTrue(done.exists())
            self.assertEqual(readme.read_text(), "# Specs\n\n## Archive\n")
            self.assertEqual(plan.new_entries, ["001 - Done"])
            self.assertEqual(plan.archived, [(done, "001 - Done")])

    def test_real_run_archives_and_deletes_completed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            done = d / "001-done.md"
            done.write_text("# 001 - Done\n\n- [x] ok\n")
            readme = d / "README.md"
            readme.write_text("# Specs\n\n## Archive\n")

            plan = run_archive(d, readme)

            self.assertFalse(done.exists())
            self.assertIn("- 001 - Done", readme.read_text())
            self.assertEqual(plan.new_entries, ["001 - Done"])

    def test_incomplete_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            wip = d / "002-wip.md"
            wip.write_text("# 002 - WIP\n\n- [ ] open\n")
            readme = d / "README.md"
            readme.write_text("# Specs\n\n## Archive\n")

            plan = run_archive(d, readme)

            self.assertTrue(wip.exists())
            self.assertEqual(plan.archived, [])
            self.assertEqual(plan.skipped_incomplete, [(wip, 1)])

    def test_already_archived_title_is_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            done = d / "001-done.md"
            done.write_text("# 001 - Done\n\n- [x] ok\n")
            readme = d / "README.md"
            readme.write_text("# Specs\n\n## Archive\n\n- 001 - Done\n")

            plan = run_archive(d, readme)

            self.assertEqual(plan.new_entries, [])
            self.assertEqual(plan.archived, [(done, "001 - Done")])
            # File still deleted; README unchanged.
            self.assertFalse(done.exists())
            self.assertEqual(
                readme.read_text(),
                "# Specs\n\n## Archive\n\n- 001 - Done\n",
            )

    def test_missing_directory_raises_filenotfound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            readme.write_text("# X\n## Archive\n")
            with self.assertRaises(FileNotFoundError):
                run_archive(Path(tmp) / "no-such-dir", readme)

    def test_missing_readme_raises_filenotfound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001-done.md").write_text("# 001 - Done\n- [x] ok\n")
            with self.assertRaises(FileNotFoundError):
                run_archive(d, d / "missing.md")


if __name__ == "__main__":
    unittest.main()
