from __future__ import annotations

import unittest

from pkgmgr.actions.release.files.changelog_lint import (
    lint_changelog_entry,
    transform_changelog_message,
)


class TestTransformChangelogMessage(unittest.TestCase):
    def test_heading_becomes_bold(self) -> None:
        out = transform_changelog_message("# Title\n\nbody")
        self.assertIn("**Title**", out)
        self.assertNotIn("# Title", out)

    def test_multi_hash_heading_becomes_bold(self) -> None:
        self.assertEqual(
            transform_changelog_message("### Sub heading"), "**Sub heading**"
        )

    def test_inline_code_becomes_italic(self) -> None:
        out = transform_changelog_message("use `pkgmgr release` now")
        self.assertEqual(out, "use *pkgmgr release* now")
        self.assertNotIn("`", out)

    def test_plain_message_is_unchanged(self) -> None:
        self.assertEqual(transform_changelog_message("just text"), "just text")

    def test_no_heading_or_backtick_survives(self) -> None:
        out = transform_changelog_message("# Heading\n\n* item with `code`")
        self.assertNotIn("`", out)
        for line in out.split("\n"):
            self.assertFalse(line.lstrip().startswith("#"))


class TestLintChangelogEntry(unittest.TestCase):
    def test_clean_entry_has_no_findings(self) -> None:
        entry = "## [1.0.0] - 2026-01-01\n\n* a clean bullet\n\n"
        self.assertEqual(lint_changelog_entry("CHANGELOG.md", entry), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
