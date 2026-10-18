from __future__ import annotations

import shutil
import unittest
from unittest.mock import patch

from pkgmgr.actions.release.files import changelog_lint
from pkgmgr.actions.release.files.changelog_lint import (
    lint_changelog_context,
    lint_changelog_entry,
    transform_changelog_message,
)
from pkgmgr.actions.release.files.changelog_md import _insert_after_h1

_OLD_ASTERISK_FILE = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n* old bullet\n"


class TestTransformChangelogMessage(unittest.TestCase):
    def test_heading_is_pushed_below_the_release_heading(self) -> None:
        out = transform_changelog_message("# Title\n\nbody")
        self.assertIn("### Title", out)
        self.assertNotIn("**Title**", out)

    def test_a_heading_already_deep_enough_keeps_its_level(self) -> None:
        self.assertEqual(transform_changelog_message("### Sub heading"), "### Sub heading")

    def test_a_deeper_heading_is_left_alone(self) -> None:
        self.assertEqual(transform_changelog_message("#### Deeper"), "#### Deeper")

    def test_inline_code_becomes_italic(self) -> None:
        out = transform_changelog_message("use `pkgmgr release` now")
        self.assertEqual(out, "use *pkgmgr release* now")
        self.assertNotIn("`", out)

    def test_plain_message_is_unchanged(self) -> None:
        self.assertEqual(transform_changelog_message("just text"), "just text")

    def test_no_backtick_survives_and_no_heading_competes(self) -> None:
        out = transform_changelog_message("# Heading\n\n* item with `code`")
        self.assertNotIn("`", out)
        for line in out.split("\n"):
            if line.lstrip().startswith("#"):
                self.assertTrue(line.startswith("###"), line)


class TestLintChangelogEntry(unittest.TestCase):
    def test_clean_entry_has_no_findings(self) -> None:
        entry = "## [1.0.0] - 2026-01-01\n\n- a clean bullet\n\n"
        self.assertEqual(lint_changelog_entry("CHANGELOG.md", entry), [])

    def test_a_structured_message_survives_its_own_transform(self) -> None:
        body = transform_changelog_message(
            "# Security\n\n- a bullet\n\n## Fixed\n\n- another bullet"
        )
        entry = f"## [1.0.0] - 2026-01-01\n\n{body}\n\n"
        self.assertEqual(lint_changelog_entry("CHANGELOG.md", entry), [])

    def test_the_builtin_check_refuses_a_non_dash_list_marker(self) -> None:
        entry = "## [1.0.0] - 2026-01-01\n\n* a bullet\n\n"
        with patch.object(changelog_lint.shutil, "which", return_value=None):
            findings = lint_changelog_entry("CHANGELOG.md", entry)
        self.assertTrue(any("MD004" in finding for finding in findings), findings)


@unittest.skipUnless(shutil.which("markdownlint-cli2"), "markdownlint-cli2 is not installed")
class TestLintChangelogContext(unittest.TestCase):
    def test_a_marker_that_breaks_the_files_consistency_is_reported(self) -> None:
        entry = "## [1.1.0] - 2026-02-01\n\n- new bullet\n\n"
        merged = _insert_after_h1(_OLD_ASTERISK_FILE, entry)
        findings = lint_changelog_context("CHANGELOG.md", _OLD_ASTERISK_FILE, merged)
        self.assertTrue(any("MD004" in finding for finding in findings), findings)

    def test_a_finding_the_file_already_has_is_not_blamed_on_the_entry(self) -> None:
        existing = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n* old bullet \n"
        entry = "## [1.1.0] - 2026-02-01\n\n* new bullet\n\n"
        merged = _insert_after_h1(existing, entry)
        self.assertEqual(lint_changelog_context("CHANGELOG.md", existing, merged), [])

    def test_a_consistent_entry_has_no_findings(self) -> None:
        entry = "## [1.1.0] - 2026-02-01\n\n* new bullet\n\n"
        merged = _insert_after_h1(_OLD_ASTERISK_FILE, entry)
        self.assertEqual(lint_changelog_context("CHANGELOG.md", _OLD_ASTERISK_FILE, merged), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
