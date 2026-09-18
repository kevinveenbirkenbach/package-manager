from __future__ import annotations

import unittest

from pkgmgr.actions.release.files.changelog_md import _insert_after_h1

ENTRY = "## [1.0.0] - 2026-09-18\n\nOfficial Release\n\n"


class TestInsertAfterH1(unittest.TestCase):
    def _assert_lint_clean(self, document: str) -> None:
        self.assertNotIn(
            "\n\n\n",
            document,
            f"MD012: multiple consecutive blank lines in\n{document!r}",
        )
        self.assertTrue(
            document.endswith("\n") and not document.endswith("\n\n"),
            f"MD012: blank line at end of file in\n{document!r}",
        )

    def test_an_empty_changelog_gets_one_trailing_newline(self) -> None:
        self._assert_lint_clean(_insert_after_h1("", ENTRY))

    def test_a_first_entry_under_a_bare_h1_gets_one_trailing_newline(self) -> None:
        self._assert_lint_clean(_insert_after_h1("# Changelog\n", ENTRY))

    def test_a_second_entry_stays_separated_from_the_first(self) -> None:
        existing = "# Changelog\n\n## [0.9.0] - 2026-09-01\n\nOlder\n"
        document = _insert_after_h1(existing, ENTRY)
        self._assert_lint_clean(document)
        self.assertIn("Official Release\n\n## [0.9.0]", document)

    def test_a_legacy_headerless_changelog_gains_an_h1(self) -> None:
        document = _insert_after_h1("## [0.9.0] - 2026-09-01\n\nOlder\n", ENTRY)
        self._assert_lint_clean(document)
        self.assertTrue(document.startswith("# Changelog\n\n## [1.0.0]"))


if __name__ == "__main__":
    unittest.main()
