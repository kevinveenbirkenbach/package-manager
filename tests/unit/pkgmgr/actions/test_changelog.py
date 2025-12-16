from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.changelog import generate_changelog
from pkgmgr.core.git.queries import GitChangelogQueryError
from pkgmgr.cli.commands.changelog import _find_previous_and_current_tag


class TestGenerateChangelog(unittest.TestCase):
    @patch("pkgmgr.actions.changelog.get_changelog")
    def test_generate_changelog_default_range_no_merges(self, mock_get_changelog) -> None:
        mock_get_changelog.return_value = "abc123 (HEAD -> main) Initial commit"

        output = generate_changelog(cwd="/repo")

        self.assertEqual(output, "abc123 (HEAD -> main) Initial commit")
        mock_get_changelog.assert_called_once_with(
            cwd="/repo",
            from_ref=None,
            to_ref="HEAD",
            include_merges=False,
        )

    @patch("pkgmgr.actions.changelog.get_changelog")
    def test_generate_changelog_with_range_and_merges(self, mock_get_changelog) -> None:
        mock_get_changelog.return_value = "def456 (tag: v1.1.0) Some change"

        output = generate_changelog(
            cwd="/repo",
            from_ref="v1.0.0",
            to_ref="v1.1.0",
            include_merges=True,
        )

        self.assertEqual(output, "def456 (tag: v1.1.0) Some change")
        mock_get_changelog.assert_called_once_with(
            cwd="/repo",
            from_ref="v1.0.0",
            to_ref="v1.1.0",
            include_merges=True,
        )

    @patch("pkgmgr.actions.changelog.get_changelog")
    def test_generate_changelog_giterror_returns_error_message(self, mock_get_changelog) -> None:
        mock_get_changelog.side_effect = GitChangelogQueryError("simulated git failure")

        result = generate_changelog(cwd="/repo", from_ref="v0.1.0", to_ref="v0.2.0")

        self.assertIn("[ERROR] Failed to generate changelog", result)
        self.assertIn("simulated git failure", result)
        self.assertIn("v0.1.0..v0.2.0", result)

    @patch("pkgmgr.actions.changelog.get_changelog")
    def test_generate_changelog_empty_output_returns_info(self, mock_get_changelog) -> None:
        mock_get_changelog.return_value = "   \n   "

        result = generate_changelog(cwd="/repo", from_ref=None, to_ref="HEAD")

        self.assertIn("[INFO] No commits found for range 'HEAD'", result)


class TestFindPreviousAndCurrentTag(unittest.TestCase):
    def test_no_semver_tags_returns_none_none(self) -> None:
        tags = ["foo", "bar", "v1.2", "v1.2.3.4"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)
        self.assertIsNone(prev_tag)
        self.assertIsNone(cur_tag)

    def test_latest_tags_when_no_target_given(self) -> None:
        tags = ["v1.0.0", "v1.2.0", "v1.1.0", "not-a-tag"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)
        self.assertEqual(prev_tag, "v1.1.0")
        self.assertEqual(cur_tag, "v1.2.0")

    def test_single_semver_tag_returns_none_and_that_tag(self) -> None:
        tags = ["v0.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)
        self.assertIsNone(prev_tag)
        self.assertEqual(cur_tag, "v0.1.0")

    def test_with_target_tag_in_the_middle(self) -> None:
        tags = ["v1.0.0", "v1.1.0", "v1.2.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v1.1.0")
        self.assertEqual(prev_tag, "v1.0.0")
        self.assertEqual(cur_tag, "v1.1.0")

    def test_with_target_tag_first_has_no_previous(self) -> None:
        tags = ["v1.0.0", "v1.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v1.0.0")
        self.assertIsNone(prev_tag)
        self.assertEqual(cur_tag, "v1.0.0")

    def test_unknown_target_tag_returns_none_none(self) -> None:
        tags = ["v1.0.0", "v1.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v2.0.0")
        self.assertIsNone(prev_tag)
        self.assertIsNone(cur_tag)


if __name__ == "__main__":
    unittest.main()
