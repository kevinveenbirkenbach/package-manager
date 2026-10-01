from __future__ import annotations

import unittest
from unittest import mock

from pkgmgr.actions.release.files.editor import _open_editor_for_changelog


class TestOpenEditorForChangelog(unittest.TestCase):
    def _buffer(self, **kwargs: object) -> str:
        """Returns: what the editor was handed, with the editor itself a no-op."""
        seen: dict[str, str] = {}

        def record(argv: list[str]) -> int:
            with open(argv[1], encoding="utf-8") as handle:
                seen["text"] = handle.read()
            return 0

        with mock.patch(
            "pkgmgr.actions.release.files.editor.subprocess.call", side_effect=record
        ):
            _open_editor_for_changelog(**kwargs)
        return seen["text"]

    def test_the_rejection_reaches_the_editor_the_entry_is_fixed_in(self) -> None:
        text = self._buffer(
            initial_message="### Security\n\n- a bullet",
            findings=["changelog entry:3 error MD036/no-emphasis-as-heading"],
        )
        self.assertIn("MD036/no-emphasis-as-heading", text)
        self.assertIn("### Security", text)

    def test_every_finding_line_is_commented_out(self) -> None:
        text = self._buffer(findings=["first line\nsecond line"])
        for line in text.splitlines():
            if "line" in line and "ignored" not in line:
                self.assertTrue(line.startswith(";"), line)

    def test_a_finding_never_lands_in_the_entry(self) -> None:
        seen: dict[str, str] = {}

        def rewrite(argv: list[str]) -> int:
            with open(argv[1], encoding="utf-8") as handle:
                seen["text"] = handle.read()
            return 0

        with mock.patch(
            "pkgmgr.actions.release.files.editor.subprocess.call", side_effect=rewrite
        ):
            kept = _open_editor_for_changelog(
                initial_message="- a bullet", findings=["MD036 somewhere"]
            )
        self.assertEqual(kept, "- a bullet")

    def test_without_findings_the_header_stays_as_it_was(self) -> None:
        self.assertNotIn("markdown-lint rejected", self._buffer())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
